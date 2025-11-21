from rest_framework import generics, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserRegisterSerializer, EmailTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated

from core.models import Bookmark
from core.serializers import BookmarkSerializer

# [추가] 카카오 로그인을 위한 import
from allauth.socialaccount.providers.kakao.views import KakaoOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView

User = get_user_model()

# [추가] 카카오 로그인 뷰
class KakaoLoginView(SocialLoginView):
    adapter_class = KakaoOAuth2Adapter

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

class UserListCreateAPIView(generics.ListCreateAPIView):
    """
    GET: 전체 유저 조회 (인증 필요)
    POST: 유저 생성
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = [permissions.AllowAny]  # 개발 편의를 위해 인증 없이 허용
    
    
    def post(self, request, *args, **kwargs):
        if 'access_token' in request.data:
            print("🔄 [Server] '/users/'로 카카오 토큰이 들어옴 -> KakaoLoginView로 토스!")
            
            # 1. 뷰 인스턴스 생성
            view = KakaoLoginView()
            
            # 2. 기본 셋업 (이건 방금 추가하셨죠?)
            view.setup(request, *args, **kwargs)
            
            # 3. [핵심 추가!] DRF 설정값 수동 주입
            # 이 줄이 없으면 get_serializer_context()에서 에러가 납니다.
            view.format_kwarg = None 
            
            # 4. post 실행
            return view.post(request, *args, **kwargs)

        return super().post(request, *args, **kwargs)
    

    def create(self, request, *args, **kwargs):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # return generics.Response(UserSerializer(user).data, status=201)
        return Response(UserSerializer(user).data, status=201)


class UserRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: 개별 유저 조회
    PUT: 유저 정보 수정
    DELETE: 유저 삭제
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class UserRegisterView(generics.CreateAPIView):
    """
    회원가입 (인증 없이 가능)
    """
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]


class UserBookmarkListView(generics.ListAPIView):
    """
    현재 로그인한 사용자의 모든 즐겨찾기 목록을 조회합니다.
    """
    serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        요청을 보낸 사용자의 즐겨찾기만 필터링합니다.
        성능 최적화를 위해 `select_related`와 `prefetch_related`를 사용합니다.
        - `select_related`: 정방향 ForeignKey 관계인 `content_type`을 join하여 가져옵니다.
        - `prefetch_related`: 역방향 GenericForeignKey 관계인 `content_object`를 별도 쿼리로 효율적으로 가져옵니다.
        """
        user = self.request.user
        return Bookmark.objects.filter(user=user).select_related('content_type').prefetch_related('content_object')