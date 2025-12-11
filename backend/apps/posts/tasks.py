from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
import logging

from core.redis_client import redis_client, get_redis_key 
from .models import Post 

logger = logging.getLogger(__name__)

# Redis에서 DB로 카운트를 동기화하는 임계값
SYNC_THRESHOLD = 10

# 동기화할 카운트 필드 목록 (view 제외 - view는 별도 처리)
COUNT_FIELDS = ['comment', 'like', 'bookmark']


# ============================================================================
# 조회수 증가 Task (델타 방식)
# ============================================================================
@shared_task
def increment_view_count(post_pk):
    """
    게시글 조회수를 증가시킵니다.
    
    Redis 델타 방식:
    1. Redis에 델타만 누적 (post_view_delta:{post_pk})
    2. 델타가 SYNC_THRESHOLD에 도달하면 DB 동기화
    3. 실제 조회수 = DB 값 + Redis 델타 (Serializer에서 합산)
    
    Args:
        post_pk: Post의 Primary Key
    """
    if not redis_client:
        # Redis 없으면 직접 DB 업데이트
        logger.warning(f"Redis not available. Updating DB directly for Post {post_pk}")
        Post.objects.filter(pk=post_pk).update(view_count=F('view_count') + 1)
        return

    delta_key = get_redis_key(post_pk, 'view_delta')
    
    try:
        # 1. Redis 델타 증가
        delta = redis_client.incr(delta_key)
        
        # 2. TTL 설정 (1시간 - 주기적 동기화 전까지 유지)
        redis_client.expire(delta_key, 3600)
        
        logger.debug(f"Post {post_pk}: view_delta = {delta}")
        
        # 3. 임계값 도달 시 DB 동기화 (별도 Task로 분리)
        if delta >= SYNC_THRESHOLD:
            sync_view_count_to_db.delay(post_pk)
            
    except Exception as e:
        logger.error(f"Redis INCR 실패 (Post {post_pk}): {e}", exc_info=True)
        # Redis 실패 시 DB 직접 업데이트
        Post.objects.filter(pk=post_pk).update(view_count=F('view_count') + 1)


@shared_task
def sync_view_count_to_db(post_pk):
    """
    Redis 델타를 DB에 동기화합니다.
    
    Process:
    1. Redis 델타 값 가져오기
    2. DB에 델타만큼 증가
    3. Redis 델타를 0으로 리셋
    
    Args:
        post_pk: Post의 Primary Key
    """
    if not redis_client:
        logger.warning(f"Redis not available for sync (Post {post_pk})")
        return
    
    delta_key = get_redis_key(post_pk, 'view_delta')
    
    try:
        # Pipeline으로 원자적 처리
        with redis_client.pipeline() as pipe:
            pipe.get(delta_key)
            pipe.set(delta_key, 0)  # 델타 리셋
            results = pipe.execute()
        
        delta = int(results[0]) if results[0] else 0
        
        if delta > 0:
            # DB에 델타만큼 증가
            with transaction.atomic():
                Post.objects.filter(pk=post_pk).update(
                    view_count=F('view_count') + delta
                )
            logger.info(f"✅ Post {post_pk}: DB에 조회수 +{delta} 동기화 완료")
        else:
            logger.debug(f"Post {post_pk}: 동기화할 델타 없음 (delta={delta})")
            
    except Exception as e:
        logger.error(f"❌ DB 동기화 실패 (Post {post_pk}): {e}", exc_info=True)


@shared_task(ignore_result=True)
def sync_all_view_counts_to_db():
    """
    주기적으로 모든 Redis view 델타를 DB에 동기화하는 Task
    
    Celery Beat 스케줄러에 의해 실행됩니다 (예: 1시간마다)
    - Redis 패턴: post_view_delta:*
    - 모든 델타를 DB에 반영 후 리셋
    """
    if not redis_client:
        logger.warning("Redis not available for periodic sync")
        return
    
    try:
        # Redis 키 패턴 검색: post_view_delta:*
        pattern = get_redis_key('*', 'view_delta')
        delta_keys = redis_client.keys(pattern)
        
        synced_count = 0
        total_delta = 0
        
        for key in delta_keys:
            try:
                # key는 bytes 타입이므로 디코딩
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                
                # post_pk 추출 (예: "post_view_delta:123" → "123")
                parts = key_str.split(':')
                if len(parts) < 2:
                    continue
                post_pk = parts[-1]
                
                # Pipeline으로 원자적 처리
                with redis_client.pipeline() as pipe:
                    pipe.get(key)
                    pipe.set(key, 0)
                    results = pipe.execute()
                
                delta = int(results[0]) if results[0] else 0
                
                if delta > 0:
                    # DB 업데이트
                    Post.objects.filter(pk=post_pk).update(
                        view_count=F('view_count') + delta
                    )
                    
                    synced_count += 1
                    total_delta += delta
                    logger.debug(f"Periodic sync: Post {post_pk} +{delta}")
                    
            except Exception as e:
                logger.error(f"Periodic sync error for key {key}: {e}")
                continue
        
        logger.info(
            f"✅ 주기적 동기화 완료: {synced_count}개 게시글, "
            f"총 {total_delta} 조회수 반영"
        )
        
    except Exception as e:
        logger.error(f"❌ 주기적 동기화 실패: {e}", exc_info=True)


# ============================================================================
# 기타 카운트(comment, like, bookmark) 동기화 Task
# ============================================================================
@shared_task
def sync_post_counts_to_db(post_pk):
    """
    특정 Post의 Redis 카운트(comment, like, bookmark)를 DB로 동기화합니다.
    
    Note: view_count는 별도 처리하므로 제외
    
    Args:
        post_pk: Post의 Primary Key
    """
    if not redis_client:
        logger.error(f"Redis client not initialized for Post {post_pk}")
        return 
        
    update_data = {}
    
    # 1. Redis에서 각 카운트 값 조회
    for field in COUNT_FIELDS:
        key = get_redis_key(post_pk, field)
        redis_value = redis_client.get(key)
        
        if redis_value is not None:
            try:
                count = int(redis_value)
                update_data[f'{field}_count'] = count
            except ValueError:
                logger.error(f"Invalid Redis value for {key}: {redis_value}")
                continue
    
    # 2. DB 업데이트
    if update_data:
        try:
            with transaction.atomic():
                updated_count = Post.objects.filter(pk=post_pk).update(**update_data)
            
            if updated_count == 0:
                logger.warning(f"Post {post_pk} not found during sync")
            else:
                logger.info(f"✅ Post {post_pk} 카운트 동기화: {update_data}")
                
        except Exception as e:
            logger.error(f"❌ Post {post_pk} DB 업데이트 실패: {e}", exc_info=True)


@shared_task
def sync_all_active_posts_counts():
    """
    활성 상태인 모든 Post의 카운트 동기화 Task를 예약합니다.
    
    Celery Beat에 의해 주기적으로 호출됩니다.
    각 게시글에 대해 개별 Task를 생성하여 병렬 처리합니다.
    """
    post_pks = Post.objects.filter(is_active=True).values_list('pk', flat=True)
    
    for pk in post_pks:
        sync_post_counts_to_db.delay(pk)
    
    logger.info(f"✅ {len(post_pks)}개 게시글의 카운트 동기화 예약 완료")