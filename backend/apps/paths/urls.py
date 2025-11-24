from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 기본 라우터 생성
router = DefaultRouter()

# PathViewSet을 'paths'라는 이름으로 라우터에 등록
# basename='path'는 URL 이름 생성 시 사용됩니다 (예: path-list, path-detail)
router.register('', views.PathViewSet, basename='path')

# CommentViewSet을 위한 URL 패턴을 수동으로 추가
# /paths/{path_pk}/comments/
comment_list = views.CommentViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

# /paths/{path_pk}/comments/{pk}/
comment_detail = views.CommentViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    # 라우터가 생성하는 URL들을 포함
    # 예: /paths/, /paths/{pk}/, /paths/mine/, /paths/{pk}/bookmark/
    path('', include(router.urls)),
    
    # 댓글 관련 URL 수동 등록
    path('<int:id>/comments/', comment_list, name='path-comment-list'),
    path('<int:id>/comments/<int:pk>/', comment_detail, name='path-comment-detail'),
]