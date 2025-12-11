from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from .models import Pet, PetBreed, PetEvent, InvitationCode, PetLocation
from .serializers import (
    PetSerializer, 
    PetBreedSerializer,
    PetEventSerializer,
    InvitationCodeSerializer,
    PetLocationSerializer,
)
from .permissions import IsOwnerOrReadOnly # 곧 정의할 커스텀 권한


class PetListCreateView(generics.ListCreateAPIView):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    # 1. 목록 조회 필터링: 현재 로그인된 사용자의 반려견만 보여줍니다.
    def get_queryset(self):
        user = self.request.user
        print(f"DEBUG: Fetching pets for user {user}")
        # 1. 미인증 사용자: 권한이 없으므로 빈 쿼리셋 반환
        if not user.is_authenticated:
            return Pet.objects.none()
        
        # 3. 일반 사용자인 경우: 요청한 사용자가 소유한 Pet 객체들만 필터링
        if self.request.user.is_superuser:
            return Pet.objects.all().order_by('-id')
            
        # 3. 일반 인증 사용자: 본인이 소유한 Pet 객체들만 반환
        return Pet.objects.filter(owner=user).order_by('-id')

    # 2. 생성 시 owner 자동 할당:
    #    PetSerializer의 create 메서드에서 이 요청 정보를 사용하여 owner를 자동 할당
    def perform_create(self, serializer):
        user = self.request.user
        print(f"DEBUG: Creating pet for user {user}")
        
        # 임시: 인증되지 않은 경우 첫 번째 사용자를 owner로 설정
        if not user.is_authenticated:
            from apps.users.models import CustomUser
            default_user = CustomUser.objects.first()  # 또는 특정 ID: .get(id=1)
            if not default_user:
                raise PermissionDenied("테스트용 기본 사용자가 없습니다.")
            owner_to_save = default_user
        else:
            owner_to_save = user
            
        serializer.save(owner=owner_to_save)
        
class PetRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    # 3. 권한 설정: 커스텀 권한 (IsOwnerOrReadOnly)을 적용합니다.
    permission_classes = [IsOwnerOrReadOnly]
    # permission_classes = [permissions.AllowAny] # 임시 적용
    
    # 참고: get_queryset을 오버라이드하여 소유자 필터링을 할 수도 있지만, 
    # 상세 조회/수정/삭제는 IsOwnerOrReadOnly 권한 클래스에서 더 강력하게 제어합니다.
    
class PetBreedListView(generics.ListAPIView):
    queryset = PetBreed.objects.all().order_by('category', 'breed_name')
    serializer_class = PetBreedSerializer
    # 품종 목록은 로그인 없이도 볼 수 있도록 허용합니다.
    permission_classes = [permissions.AllowAny]
   
# 이벤트 전체 항목
class PetEventListCreateView(generics.ListCreateAPIView):
    serializer_class = PetEventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        특정 pet_id 하위의 이벤트만 조회
        """
        pet_id = self.kwargs.get('pk')
        print(f"{self.kwargs}")
        print(f"DEBUG: Fetching events for pet_id {pet_id} by user {self.request.user}")
        if not pet_id:
            return PetEvent.objects.none()

        # 본인 반려견인지 검사
        if not self.request.user.is_authenticated:
            return PetEvent.objects.none()

        return PetEvent.objects.filter(
            pet__id=pet_id,
            pet__owner=self.request.user
        ).order_by('-event_date')

    def perform_create(self, serializer):
        pet_id = self.kwargs.get('pk')
        print(f"DEBUG: Creating event for pet_id {pet_id} by user {self.request.user}")
        try:
            pet = Pet.objects.get(id=pet_id, owner=self.request.user)
        except Pet.DoesNotExist:
            raise PermissionDenied("해당 반려견에 대한 접근/생성 권한이 없습니다.")

        serializer.save(pet=pet)

class PetEventRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PetEvent.objects.all()
    serializer_class = PetEventSerializer
    permission_classes = [IsOwnerOrReadOnly]

class InvitationCodeCreateView(generics.CreateAPIView):
    """
    인증된 사용자를 위해 펫 초대 코드를 생성합니다.
    """
    serializer_class = InvitationCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # 요청을 보낸 사용자를 created_by 필드에 할당하여 초대 코드를 생성합니다.
        serializer.save(created_by=self.request.user)

class PetLocationCreateView(generics.CreateAPIView):
    """
    '펫'으로 등록된 사용자의 위치 정보를 생성(업데이트)합니다.
    """
    serializer_class = PetLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def perform_create(self, serializer):
        # 요청을 보낸 사용자가 'linked_user'로 등록된 Pet 객체를 찾습니다.
        try:
            pet_instance = Pet.objects.get(linked_user=self.request.user)
        except Pet.DoesNotExist:
            raise PermissionDenied("You are not registered as a trackable pet.")

        # 새 위치 정보를 생성하고, 찾은 Pet 인스턴스와 연결합니다.
        new_location = serializer.save(pet=pet_instance)

        # Pet 모델의 'last_location' 필드를 방금 생성된 위치로 업데이트합니다.
        pet_instance.last_location = new_location
        pet_instance.save(update_fields=['last_location', 'updated_at'])