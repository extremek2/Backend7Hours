from rest_framework import generics, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserRegisterSerializer, EmailTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

# 소셜 로그인용
from allauth.socialaccount.providers.kakao.views import KakaoOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView

User = get_user_model()

# 카카오 로그인
class KakaoLoginView(SocialLoginView):
    adapter_class = KakaoOAuth2Adapter
    
    # GET으로 redirect 오면 POST로 변환
    def get(self, request, *args, **kwargs):
        """
        #카카오 GET(code=xxxx) → POST 방식으로 변환
        """
        request.POST = request.GET  # code, state를 POST로 옮김
        return self.post(request, *args, **kwargs)

# 이메일 JWT 로그인
class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

# 회원가입 + 카카오 로그인 토스
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