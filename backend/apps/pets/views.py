from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Pet, PetBreed, PetEvent
from .serializers import (
    PetSerializer, 
    PetBreedSerializer,
    PetEventSerializer,
)
from .permissions import IsOwnerOrReadOnly # 곧 정의할 커스텀 권한


class PetListCreateView(generics.ListCreateAPIView):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    # 1. 목록 조회 필터링: 현재 로그인된 사용자의 반려견만 보여줍니다.
    def get_queryset(self):
        # 요청자가 인증되지 않았다면 빈 쿼리셋을 반환
        if not self.request.user.is_authenticated:
            return Pet.objects.none()
            
        # 요청한 사용자가 소유한 Pet 객체들만 필터링합니다.
        return Pet.objects.filter(owner=self.request.user).order_by('-id')

    # 2. 생성 시 owner 자동 할당:
    #    PetSerializer의 create 메서드에서 이 요청 정보를 사용하여 owner를 자동 할당합니다.
    def perform_create(self, serializer):
        # 시리얼라이저의 create 메서드에 request 객체를 context로 전달합니다.
        # 이렇게 하면 시리얼라이저가 owner 필드를 자동으로 설정합니다.
        serializer.save(owner=self.request.user)
        
class PetRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    # 3. 권한 설정: 커스텀 권한 (IsOwnerOrReadOnly)을 적용합니다.
    permission_classes = [IsOwnerOrReadOnly] 
    
    # 참고: get_queryset을 오버라이드하여 소유자 필터링을 할 수도 있지만, 
    # 상세 조회/수정/삭제는 IsOwnerOrReadOnly 권한 클래스에서 더 강력하게 제어합니다.
    
class PetBreedListView(generics.ListAPIView):
    queryset = PetBreed.objects.all().order_by('breed_name')
    serializer_class = PetBreedSerializer
    # 품종 목록은 로그인 없이도 볼 수 있도록 허용합니다.
    permission_classes = [permissions.AllowAny]
    
    
# 히스토리 전체 항목
class PetEventListCreateView(generics.ListCreateAPIView):
    serializer_class = PetEventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        특정 pet_id 하위의 히스토리만 조회
        """
        pet_id = self.kwargs.get('pet_id')
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
        pet_id = self.kwargs.get('pet_id')
        try:
            pet = Pet.objects.get(id=pet_id, owner=self.request.user)
        except Pet.DoesNotExist:
            raise PermissionDenied("해당 반려견에 대한 접근/생성 권한이 없습니다.")

        serializer.save(pet=pet)

class PetEventRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PetEvent.objects.all()
    serializer_class = PetEventSerializer
    permission_classes = [IsOwnerOrReadOnly]