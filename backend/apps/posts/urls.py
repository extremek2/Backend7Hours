from django.urls import path, include
from .views import PostViewSet, LikeToggleAPIView, BookmarkToggleAPIView

# ViewSet의 as_view()를 사용하여 CRUD 액션 정의
post_list = PostViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

post_detail = PostViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # 게시글 목록 / 생성
    path('', post_list, name='post-list'),
    # 게시글 상세 / 수정 / 삭제
    path('<int:pk>/', post_detail, name='post-detail'),
    # 좋아요 토글
    path('<int:post_id>/like-toggle/', LikeToggleAPIView.as_view(), name='post-like-toggle'),
    # 북마크 토글
    path('<int:post_id>/bookmark-toggle/', BookmarkToggleAPIView.as_view(), name='post-bookmark-toggle'),
]