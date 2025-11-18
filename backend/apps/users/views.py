from rest_framework import generics, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserRegisterSerializer, EmailTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()

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