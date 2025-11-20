"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from apps.users.views import KakaoLoginView

# [1] 에러 방지용 가짜 뷰 함수 정의
def fake_signup_view(request):
    return HttpResponse("200 OK")

# [2] URL 패턴을 '하나의 리스트'로 통합
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- 앱별 URL 연결 ---
    path("posts/", include("apps.posts.urls")),
    
    # [중요] 이 줄이 있어야 안드로이드의 '/users/' 요청이 apps/users/urls.py로 연결됩니다!
    path('users/', include('apps.users.urls')),
    
    path('pets/', include('apps.pets.urls')),
    path('places/', include('apps.places.urls')),
    path('paths/', include('apps.paths.urls')),
    path('swagger/', include('apps.swagger.urls')),

    # --- 카카오 로그인 관련 URL ---
    # 1. 카카오 로그인 직접 경로 (혹시 모르니 유지)
    path('users/kakao/login/', KakaoLoginView.as_view(), name='kakao_login'),
    
    # 2. [핵심] NoReverseMatch 에러 방지용 가짜 URL
    path('accounts/signup/', fake_signup_view, name='socialaccount_signup'),
]


# """ 기존 코드 """
# URL configuration for core project.

# The `urlpatterns` list routes URLs to views. For more information please see:
#     https://docs.djangoproject.com/en/5.2/topics/http/urls/
# Examples:
# Function views
#     1. Add an import:  from my_app import views
#     2. Add a URL to urlpatterns:  path('', views.home, name='home')
# Class-based views
#     1. Add an import:  from other_app.views import Home
#     2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
# Including another URLconf
#     1. Import the include() function: from django.urls import include, path
#     2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
# """
# from django.contrib import admin
# from django.urls import path, include
# from apps.users.views import KakaoLoginView

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path("posts/", include("apps.posts.urls")),
#     path('users/', include('apps.users.urls')),
#     path('pets/', include('apps.pets.urls')),
#     path('places/', include('apps.places.urls')),
#     path('paths/', include('apps.paths.urls')),
#     path('swagger/', include('apps.swagger.urls')),
#     path('users/kakao/login/', KakaoLoginView.as_view(), name='kakao_login'),
# ]