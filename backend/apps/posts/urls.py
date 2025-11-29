from django.urls import path
from .views import (
    PostListCreateView, 
    PostRetrieveUpdateDestroyView, 
    PostCommentViewSet, 
    PostLikeToggleView, 
    PostBookmarkToggleView
)

# 1. Post 기본 URL (APIView 기반으로 분리하여 라우팅 충돌 방지)
urlpatterns = [
    # 목록 조회 및 생성: /posts/
    path('', PostListCreateView.as_view(), name='post-list-create'), 
    
    # 상세 조회, 수정, 삭제: /posts/{pk}/ 
    path('<int:pk>/', PostRetrieveUpdateDestroyView.as_view(), name='post-detail-update-destroy'),
    
    # 좋아요 토글: /posts/{pk}/like-toggle/
    path('<int:pk>/like-toggle/', PostLikeToggleView.as_view(), name='post-like-toggle'),
    
    # 북마크 토글: /posts/{pk}/bookmark-toggle/
    path('<int:pk>/bookmark-toggle/', PostBookmarkToggleView.as_view(), name='post-bookmark-toggle'),

    # 2. 댓글 중첩 URL (ViewSet 기반, 수동 등록)
    path('<int:post_pk>/comments/', 
         PostCommentViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='post-comment-list'),
         
    path('<int:post_pk>/comments/<int:pk>/', 
         PostCommentViewSet.as_view({
             'get': 'retrieve', 
             'put': 'update', 
             'patch': 'partial_update', 
             'delete': 'destroy'
         }), 
         name='post-comment-detail'),
]