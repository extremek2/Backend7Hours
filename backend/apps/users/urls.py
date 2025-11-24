from django.urls import path
from .views import UserListCreateAPIView, UserRetrieveUpdateDestroyAPIView, EmailTokenObtainPairView, KakaoLoginView, UserBookmarkListView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # JWT 토큰
    path('token/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 유저 CRUD
    path('', UserListCreateAPIView.as_view(), name='user-list-create'),
    path('<int:pk>/', UserRetrieveUpdateDestroyAPIView.as_view(), name='user-detail'),
    
    # 현재 로그인 유저의 즐겨찾기 목록
    path('me/bookmarks/', UserBookmarkListView.as_view(), name='user-bookmarks-list'),

    # 회원가입
    # path('register/', UserRegisterView.as_view(), name='user-register'),
]