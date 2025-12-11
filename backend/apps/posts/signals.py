from django.db.models.signals import post_save, post_delete
from django.db.models import F
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from core.models import Comment, Like, Bookmark 
from .models import Post
from core.redis_client import redis_client, get_redis_key
import logging

logger = logging.getLogger(__name__)

# ContentType 캐싱 (모듈 레벨)
_POST_CONTENT_TYPE = None


def _get_post_content_type():
    """ContentType을 캐싱하여 반복 조회 방지"""
    global _POST_CONTENT_TYPE
    if _POST_CONTENT_TYPE is None:
        # NOTE: 이 함수는 apps.py ready()에서 호출되거나, 
        # ContentType이 로드된 후 호출되어야 안전합니다.
        _POST_CONTENT_TYPE = ContentType.objects.get_for_model(Post)
    return _POST_CONTENT_TYPE

# Lua 스크립트: 0 미만으로 내려가지 않도록 DECR
DECR_MIN_ZERO = """
local current = redis.call('GET', KEYS[1])
if current and tonumber(current) > 0 then
    return redis.call('DECR', KEYS[1])
else
    redis.call('SET', KEYS[1], 0)
    return 0
end
"""

def _update_redis_count(instance, action):
    """
    Generic Foreign Key (GFK) 관계의 Post 객체에 대해 Redis 카운트를 업데이트합니다.
    """
    if not redis_client:
        logger.warning("Redis client not available. Skipping counter update.")
        return
    
    try:
        # Post 모델에 대해서만 처리 (캐싱된 ContentType 사용)
        post_content_type = _get_post_content_type()
        if post_content_type is None or instance.content_type_id != post_content_type.id:
            return
        
        post_pk = instance.object_id
        
        # 인스턴스 타입에 따라 Redis 키 설정
        type_name = None
        if isinstance(instance, Like):
            type_name = 'like'
        elif isinstance(instance, Bookmark):
            type_name = 'bookmark'
        elif isinstance(instance, Comment):
            type_name = 'comment'
        else:
            return
        
        key = get_redis_key(post_pk, type_name)
        
        if action == 'increment':
            # 카운트 증가 + TTL 설정
            redis_client.incr(key)
            redis_client.expire(key, 86400)  # 24시간
            logger.debug(f"Redis INCR: {key} (Post {post_pk})")
            
        elif action == 'decrement':
            # Lua 스크립트로 원자적 감소 (0 미만 방지)
            redis_client.eval(DECR_MIN_ZERO, 1, key)
            logger.debug(f"Redis DECR: {key} (Post {post_pk})")
    
    except Exception as e:
        logger.error(f"Redis update failed for {instance}: {e}", exc_info=True)


def _update_db_count(post_pk, type_name, delta):
    """
    DB의 카운트 필드를 업데이트합니다. (F() 표현식으로 원자적 연산)
    """
    try:
        field_name = f'{type_name}_count'
        
        # 1. 쿼리셋 정의 (해당 Post 객체)
        qs = Post.objects.filter(pk=post_pk)
        
        # 2. 감소 연산(-1)일 경우, 현재 카운트가 0보다 클 때만 업데이트하도록 필터링
        if delta < 0:
            qs = qs.filter(**{f'{field_name}__gt': 0})
            
        # 3. 업데이트 실행
        updated_count = qs.update(
            **{field_name: F(field_name) + delta}
        )
        
        if updated_count > 0:
            logger.debug(f"DB updated: Post {post_pk} {field_name} += {delta}")
        else:
            logger.debug(f"DB update skipped (count is already 0 or post not found): Post {post_pk}")
            
    except Exception as e:
        logger.error(f"DB update failed for Post {post_pk}: {e}", exc_info=True)


# -------------------------------------------------------------
# 1. 좋아요 (Like) 시그널
# -------------------------------------------------------------
@receiver(post_save, sender=Like)
def increment_like_count(sender, instance, created, **kwargs):
    """Like 객체가 생성되면 좋아요 카운트 증가"""
    if created:
        _update_redis_count(instance, 'increment')
        
        # DB도 업데이트 (선택사항)
        if instance.content_type_id == _get_post_content_type().id:
            _update_db_count(instance.object_id, 'like', 1)

@receiver(post_delete, sender=Like)
def decrement_like_count(sender, instance, **kwargs):
    """Like 객체가 삭제되면 좋아요 카운트 감소"""
    _update_redis_count(instance, 'decrement')
    
    # DB도 업데이트 (선택사항)
    if instance.content_type_id == _get_post_content_type().id:
        _update_db_count(instance.object_id, 'like', -1)


# -------------------------------------------------------------
# 2. 북마크 (Bookmark) 시그널
# -------------------------------------------------------------
@receiver(post_save, sender=Bookmark)
def increment_bookmark_count(sender, instance, created, **kwargs):
    """Bookmark 객체가 생성되면 북마크 카운트 증가"""
    if created:
        _update_redis_count(instance, 'increment')
        
        if instance.content_type_id == _get_post_content_type().id:
            _update_db_count(instance.object_id, 'bookmark', 1)

@receiver(post_delete, sender=Bookmark)
def decrement_bookmark_count(sender, instance, **kwargs):
    """Bookmark 객체가 삭제되면 북마크 카운트 감소"""
    _update_redis_count(instance, 'decrement')
    
    if instance.content_type_id == _get_post_content_type().id:
        _update_db_count(instance.object_id, 'bookmark', -1)


# -------------------------------------------------------------
# 3. 댓글 (Comment) 시그널
# -------------------------------------------------------------
@receiver(post_save, sender=Comment)
def increment_comment_count(sender, instance, created, **kwargs):
    """Comment 객체가 생성되면 댓글 카운트 증가"""
    if created:
        _update_redis_count(instance, 'increment')
        
        if instance.content_type_id == _get_post_content_type().id:
            _update_db_count(instance.object_id, 'comment', 1)

@receiver(post_delete, sender=Comment)
def decrement_comment_count(sender, instance, **kwargs):
    """Comment 객체가 삭제되면 댓글 카운트 감소"""
    _update_redis_count(instance, 'decrement')
    
    if instance.content_type_id == _get_post_content_type().id:
        _update_db_count(instance.object_id, 'comment', -1)