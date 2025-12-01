from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from .models import Post
from core.models import Comment, Like, Bookmark
from core.serializers import CommentSerializer
from core.redis_client import redis_client, get_redis_key
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ContentType 캐싱 (모듈 레벨)
# ============================================================================
_POST_CONTENT_TYPE = None

def _get_post_content_type():
    """ContentType을 모듈 레벨에서 캐싱하여 반복 조회 방지"""
    global _POST_CONTENT_TYPE
    
    if _POST_CONTENT_TYPE is None:
        try:
            if apps.ready and apps.is_installed('django.contrib.contenttypes'):
                _POST_CONTENT_TYPE = ContentType.objects.get_for_model(Post)
        except Exception as e:
            logger.warning(f"ContentType 조회 실패: {e}")
            return None
    
    return _POST_CONTENT_TYPE


# ============================================================================
# Redis Count Mixin
# ============================================================================
class RedisCountMixin:
    """Redis에서 카운트를 조회하는 헬퍼 메서드 Mixin"""
    
    def get_count_from_redis(self, obj, type_name):
        """
        Redis에서 카운트 값을 가져오고, 실패 시 DB 값으로 Fallback합니다.
        
        ⚠️ view_count는 특별 처리:
        - DB 값 + Redis 델타(view_delta) 합산
        - 실시간 정확한 조회수 제공
        
        Args:
            obj: Post 인스턴스
            type_name: 'view', 'comment', 'like', 'bookmark'
        
        Returns:
            int: 카운트 값
        """
        db_field = f'{type_name}_count'
        db_count = getattr(obj, db_field, 0)
        
        try:
            # 1. Redis 연결 확인
            if not redis_client:
                logger.debug(f"Redis client not available. Using DB value for {type_name}_count")
                return db_count
            
            # 2. view_count는 델타 방식 (DB + Redis 델타 합산)
            if type_name == 'view':
                delta_key = get_redis_key(obj.pk, 'view_delta')
                redis_delta = redis_client.get(delta_key)
                delta = int(redis_delta) if redis_delta else 0
                
                total = db_count + delta
                logger.debug(f"Post {obj.pk} view_count: DB={db_count} + Redis델타={delta} = {total}")
                return total
            
            # 3. 기타 카운트는 기존 방식 (Redis 값 그대로 사용)
            key = get_redis_key(obj.pk, type_name)
            redis_value = redis_client.get(key)
            
            # Redis에 값이 없으면 DB 값으로 초기화 (Cache Repopulation)
            if redis_value is None:
                logger.info(f"Redis cache miss: {key}. Repopulating from DB (value={db_count})")
                redis_client.setex(key, 86400, db_count)  # 24시간 TTL
                return db_count
            
            # Redis 값 반환
            return int(redis_value)
            
        except Exception as e:
            # Redis 에러 시 DB Fallback
            logger.error(f"Redis error for {type_name}_count (Post {obj.pk}): {e}", exc_info=True)
            return db_count


# ============================================================================
# User Status Mixin (좋아요/북마크 상태 체크)
# ============================================================================
class UserStatusMixin:
    """사용자의 좋아요/북마크 상태를 확인하는 Mixin"""
    
    def _check_user_status(self, obj, model_class, attr_name):
        """
        사용자가 좋아요/북마크 했는지 확인합니다.
        
        Args:
            obj: Post 인스턴스
            model_class: Like 또는 Bookmark 모델
            attr_name: Prefetch된 속성명 ('user_likes' 또는 'user_bookmarks')
        
        Returns:
            bool: 사용자가 좋아요/북마크 했으면 True
        """
        request = self.context.get('request')
        
        # 1. 인증되지 않은 사용자
        if not request or not request.user.is_authenticated:
            return False
        
        # 2. Prefetch된 데이터 우선 사용 (N+1 쿼리 방지)
        if hasattr(obj, attr_name):
            return len(getattr(obj, attr_name)) > 0
        
        # 3. Fallback: DB 직접 조회
        content_type = _get_post_content_type()
        if not content_type:
            logger.warning("ContentType not available for user status check")
            return False
        
        return model_class.objects.filter(
            content_type=content_type,
            object_id=obj.id,
            user=request.user
        ).exists()


# ============================================================================
# Empty Serializer (Toggle 전용)
# ============================================================================
class ToggleSerializer(serializers.Serializer):
    """좋아요/북마크 토글 API 전용 빈 Serializer"""
    pass


# ============================================================================
# Post List Serializer
# ============================================================================
class PostListSerializer(RedisCountMixin, UserStatusMixin, serializers.ModelSerializer):
    """
    게시글 목록용 Serializer
    
    Features:
    - Redis에서 카운트 조회 (view, comment, like, bookmark)
    - 사용자의 좋아요/북마크 상태 제공
    - Prefetch 최적화 지원
    """
    
    # 작성자 정보
    auth_id = serializers.ReadOnlyField(source='auth_user.id')
    auth_name = serializers.ReadOnlyField(source='auth_user.nickname')
    auth_profile_image = serializers.SerializerMethodField()
    
    # Redis 카운트 필드
    view_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    
    # 사용자 상태 필드
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'auth_id', 'auth_name', 'auth_profile_image', 
            'post_type', 'title', 'image',
            'view_count', 'comment_count', 'like_count', 'bookmark_count',
            'is_liked', 'is_bookmarked',
            'created_at', 'updated_at',
        ]
    
    # ---- Redis 카운트 조회 메서드 ----
    def get_view_count(self, obj):
        """조회수 (Redis → DB Fallback)"""
        return self.get_count_from_redis(obj, 'view')
    
    def get_comment_count(self, obj):
        """댓글 수 (Redis → DB Fallback)"""
        return self.get_count_from_redis(obj, 'comment')
    
    def get_like_count(self, obj):
        """좋아요 수 (Redis → DB Fallback)"""
        return self.get_count_from_redis(obj, 'like')
    
    def get_bookmark_count(self, obj):
        """북마크 수 (Redis → DB Fallback)"""
        return self.get_count_from_redis(obj, 'bookmark')
    
    # ---- 사용자 상태 확인 메서드 ----
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요 했는지 확인"""
        return self._check_user_status(obj, Like, 'user_likes')
    
    def get_is_bookmarked(self, obj):
        """현재 사용자가 북마크 했는지 확인"""
        return self._check_user_status(obj, Bookmark, 'user_bookmarks')
    
    # ---- 사용자 프로필 이미지 확인 메서드 ----
    def get_auth_profile_image(self, obj):
        # obj: 현재 직렬화 중인 Post 인스턴스 (Post 객체)
        
        # 1. Post 객체에서 auth_user 객체에 접근
        auth_user = obj.auth_user
        
        # 2. auth_user가 존재하고 profile_image 필드에 값이 있는지 확인
        if auth_user and auth_user.profile_image:
            
            # 3. profile_image가 실제 파일을 가지고 있는지 (경로가 비어있지 않은지) 확인
            # .name 속성을 통해 파일 경로가 설정되어 있는지 확인합니다.
            if auth_user.profile_image.name:
                # 파일이 연결되어 있다면, 안전하게 .url 반환
                return auth_user.profile_image.url
        
        # auth_user가 없거나, profile_image 필드가 null 또는 ''일 경우 None 반환
        return None


# ============================================================================
# Post Detail Serializer
# ============================================================================
class PostDetailSerializer(PostListSerializer):
    """
    게시글 상세용 Serializer (PostListSerializer 상속)
    
    Additional Features:
    - 게시글 본문(content) 포함
    - 최근 댓글 50개 포함
    """
    
    comments = serializers.SerializerMethodField()
    
    class Meta(PostListSerializer.Meta):
        # 부모의 fields에 content와 comments 추가
        fields = PostListSerializer.Meta.fields + ['content', 'comments']
    
    def get_comments(self, obj):
        """
        최근 댓글 50개 조회
        
        1. Prefetch된 'recent_comments' 우선 사용
        2. Fallback: DB에서 직접 조회
        
        Returns:
            list: 댓글 목록 (직렬화된 데이터)
        """
        # 1. Prefetch된 데이터 사용 (View에서 최적화 완료)
        if hasattr(obj, 'recent_comments'):
            comments = obj.recent_comments
        else:
            # 2. Fallback: DB 직접 조회
            content_type = _get_post_content_type()
            if not content_type:
                logger.warning(f"ContentType not available for comments (Post {obj.pk})")
                return []
            
            comments = Comment.objects.filter(
                content_type=content_type,
                object_id=obj.id
            ).select_related('author').order_by('-created_at')[:50]
        
        # 3. 댓글 직렬화
        return CommentSerializer(comments, many=True, context=self.context).data


# ============================================================================
# Post Write Serializer
# ============================================================================
class PostWriteSerializer(serializers.ModelSerializer):
    """
    게시글 작성/수정용 Serializer
    
    Validations:
    - 제목: 최소 2자
    - 내용: 최소 5자
    """
    
    class Meta:
        model = Post
        fields = ['post_type', 'title', 'content', 'image']
    
    def validate_title(self, value):
        """제목 유효성 검사"""
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("제목은 최소 2자 이상이어야 합니다.")
        return cleaned  # 공백 제거된 값 반환
    
    def validate_content(self, value):
        """내용 유효성 검사"""
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise serializers.ValidationError("내용은 최소 5자 이상이어야 합니다.")
        return cleaned  # 공백 제거된 값 반환