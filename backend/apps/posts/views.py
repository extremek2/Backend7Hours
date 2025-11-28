from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Prefetch, F
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from .models import Post
from core.models import Comment, Like, Bookmark
from core.views import BaseCommentViewSet
from .serializers import PostListSerializer, PostDetailSerializer, PostWriteSerializer
from .permissions import IsOwnerOrReadOnly

from core.redis_client import redis_client, get_redis_key
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# 실시간 조회수 증가 헬퍼 함수
# ============================================================================
def increment_view_count_sync(post_pk):
    """
    조회수를 즉시(동기적으로) 증가시킵니다.
    
    Redis 델타 방식 (하이브리드):
    1. Redis 델타 즉시 증가 (동기 - 빠름)
    2. 델타가 10 이상이면 DB 동기화 (비동기 - 응답 속도 유지)
    
    Args:
        post_pk: Post의 Primary Key
    
    Returns:
        int: 현재 델타 값
    """
    if not redis_client:
        # Redis 없으면 DB 직접 업데이트
        Post.objects.filter(pk=post_pk).update(view_count=F('view_count') + 1)
        return 0
    
    delta_key = get_redis_key(post_pk, 'view_delta')
    
    try:
        # 1. Redis 델타 즉시 증가 (매우 빠름 ~1ms)
        delta = redis_client.incr(delta_key)
        redis_client.expire(delta_key, 3600)  # 1시간 TTL
        
        logger.debug(f"Post {post_pk}: view_delta = {delta}")
        
        # 2. 임계값 도달 시 DB 동기화 (비동기로 처리)
        if delta >= 10:
            from .tasks import sync_view_count_to_db
            sync_view_count_to_db.delay(post_pk)
            logger.info(f"Post {post_pk}: DB 동기화 Task 예약 (delta={delta})")
        
        return delta
        
    except Exception as e:
        logger.error(f"Redis 처리 실패 (Post {post_pk}): {e}", exc_info=True)
        # Redis 실패 시 DB 직접 업데이트
        Post.objects.filter(pk=post_pk).update(view_count=F('view_count') + 1)
        return 0


# ============================================================================
# Redis 헬퍼 함수
# ============================================================================
def _get_redis_count(post_pk, type_name):
    """Redis에서 현재 카운트를 조회하거나 DB 필드를 fallback"""
    if not redis_client:
        # Redis 사용 불가 시 DB 필드 fallback
        result = Post.objects.filter(pk=post_pk).values(f'{type_name}_count').first()
        if not result:
            raise Http404("Post not found")
        return result[f'{type_name}_count']
    
    # view는 델타 방식 (DB + Redis 델타 합산)
    if type_name == 'view':
        post = Post.objects.filter(pk=post_pk).values('view_count').first()
        if not post:
            raise Http404("Post not found")
        
        db_count = post['view_count']
        delta_key = get_redis_key(post_pk, 'view_delta')
        delta = redis_client.get(delta_key)
        delta = int(delta) if delta else 0
        
        return db_count + delta
    
    # 기타 카운트
    key = get_redis_key(post_pk, type_name)
    count = redis_client.get(key)
    
    if count is not None:
        return int(count)
    
    # Redis에 없으면 DB에서 가져와서 Redis에 캐싱
    result = Post.objects.filter(pk=post_pk).values(f'{type_name}_count').first()
    if not result:
        raise Http404("Post not found")
    
    count = result[f'{type_name}_count']
    redis_client.setex(key, 86400, count)  # 24시간 캐싱
    return count


# ============================================================================
# 1. Post 목록 조회 및 생성 View
# ============================================================================
class PostListCreateView(generics.ListCreateAPIView):
    """게시글 목록 조회 및 생성"""
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Post.objects.select_related('auth_user')
        
        # 검색 필터
        query = self.request.GET.get('query')
        if query:
            queryset = queryset.filter(title__icontains=query)
                
        user = self.request.user
        content_type = ContentType.objects.get_for_model(Post)
        
        # 목록 최적화: 좋아요/북마크 상태만 Prefetch
        if user.is_authenticated:
            user_likes = Like.objects.filter(
                content_type=content_type,
                user=user
            )
            user_bookmarks = Bookmark.objects.filter(
                content_type=content_type,
                user=user
            )
            queryset = queryset.prefetch_related(
                Prefetch('likes', queryset=user_likes, to_attr='user_likes'),
                Prefetch('bookmarks', queryset=user_bookmarks, to_attr='user_bookmarks')
            )
        
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostWriteSerializer
        return PostListSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def perform_create(self, serializer):
        serializer.save(auth_user=self.request.user)


# ============================================================================
# 2. Post 상세 조회, 수정, 삭제 View (실시간 조회수 반영)
# ============================================================================
class PostRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """게시글 상세 조회, 수정, 삭제"""
    queryset = Post.objects.all()
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostWriteSerializer
        return PostDetailSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerOrReadOnly()]

    def get_object(self):
        """
        Post 상세 조회 시 필요한 쿼리 최적화를 적용하고, 조회수를 즉시 증가시킵니다.
        """
        pk = self.kwargs.get('pk')
        content_type = ContentType.objects.get_for_model(Post)
        user = self.request.user
        
        # ✅ 조회수 즉시 증가 (실시간 반영)
        if self.request.method == 'GET':
            increment_view_count_sync(pk)
        
        # 1번의 쿼리로 모든 것 가져오기
        queryset = Post.objects.filter(pk=pk).select_related('auth_user')
        
        # ✅ 최근 댓글 Prefetch (슬라이스 제거 - Prefetch에서 처리 불가)
        recent_comments_qs = Comment.objects.filter(
            content_type=content_type
        ).select_related('author').order_by('-created_at')
        
        queryset = queryset.prefetch_related(
            Prefetch('comments', queryset=recent_comments_qs, to_attr='recent_comments')
        )
        
        # 좋아요/북마크 상태 Prefetch
        if user.is_authenticated:
            user_likes = Like.objects.filter(content_type=content_type, user=user)
            user_bookmarks = Bookmark.objects.filter(content_type=content_type, user=user)
            
            queryset = queryset.prefetch_related(
                Prefetch('likes', queryset=user_likes, to_attr='user_likes'),
                Prefetch('bookmarks', queryset=user_bookmarks, to_attr='user_bookmarks')
            )
        
        # 객체 가져오기
        instance = queryset.first()
        if not instance:
            from django.http import Http404
            raise Http404("Post not found")
        
        # 권한 체크
        self.check_object_permissions(self.request, instance)
        
        return instance


# ============================================================================
# 3. 좋아요 토글 View
# ============================================================================
class PostLikeToggleView(APIView):
    """게시글 좋아요 토글"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        user = request.user
        content_type = ContentType.objects.get_for_model(Post)
        
        like, created = Like.objects.get_or_create(
            user=user, 
            content_type=content_type, 
            object_id=post.pk
        )
        
        if created:
            is_liked = True
            http_status = status.HTTP_201_CREATED
        else:
            like.delete()
            is_liked = False
            http_status = status.HTTP_200_OK
        
        # Redis 카운트 조회
        like_count = _get_redis_count(post.pk, 'like')
        
        return Response({
            'is_liked': is_liked, 
            'like_count': like_count
        }, status=http_status)


# ============================================================================
# 4. 북마크 토글 View
# ============================================================================
class PostBookmarkToggleView(APIView):
    """게시글 북마크 토글"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        post = get_object_or_404(Post, id=pk)
        user = request.user
        
        content_type = ContentType.objects.get_for_model(Post)
        bookmark, created = Bookmark.objects.get_or_create(
            user=user, 
            content_type=content_type, 
            object_id=post.pk
        )
        
        if created:
            is_bookmarked = True
            http_status = status.HTTP_201_CREATED
            response_status = 'bookmark added'
        else:
            bookmark.delete()
            is_bookmarked = False
            http_status = status.HTTP_200_OK
            response_status = 'bookmark removed'

        # Redis 카운트 조회
        bookmark_count = _get_redis_count(post.pk, 'bookmark')
        
        return Response({
            'is_bookmarked': is_bookmarked, 
            'bookmark_count': bookmark_count,
            'status': response_status
        }, status=http_status)


# ============================================================================
# 5. 댓글 ViewSet
# ============================================================================
class PostCommentViewSet(BaseCommentViewSet):
    """게시글에 종속된 댓글 목록, 생성, 상세 조회, 수정, 삭제"""
    parent_field = 'post'
    parent_lookup_kwarg = 'post_pk'
    parent_model = Post
    
    def get_queryset(self):
        parent_id = self.kwargs.get(self.parent_lookup_kwarg)
        if parent_id is None:
            return Comment.objects.none()
            
        post_content_type = ContentType.objects.get_for_model(self.parent_model)
        
        return Comment.objects.filter(
            content_type=post_content_type, 
            object_id=parent_id
        ).select_related('author')

    def get_object(self):
        from rest_framework import serializers
        
        post_pk = self.kwargs.get(self.parent_lookup_kwarg)
        comment_pk = self.kwargs.get('pk')
        
        if not post_pk or not comment_pk:
            raise serializers.ValidationError(
                {"detail": "Post ID 또는 Comment ID가 URL에 누락되었습니다."}
            )

        post_content_type = ContentType.objects.get_for_model(self.parent_model)
        
        obj = get_object_or_404(
            Comment.objects.select_related('author'),
            pk=comment_pk,
            content_type=post_content_type, 
            object_id=post_pk
        )
        
        self.check_object_permissions(self.request, obj)
        
        return obj

    def perform_create(self, serializer):
        from rest_framework import serializers
        
        parent_id = self.kwargs.get(self.parent_lookup_kwarg)
        if parent_id is None:
            raise serializers.ValidationError(
                {"detail": "Post ID (PK)가 URL에 누락되었습니다."}
            )

        post_content_type = ContentType.objects.get_for_model(self.parent_model)

        serializer.save(
            author=self.request.user, 
            content_type=post_content_type, 
            object_id=parent_id,
        )