from django.urls import path, include
from .views import (
    PetListCreateView,
    PetRetrieveUpdateDestroyView,
    PetBreedListView,
    InvitationCodeCreateView,
    PetLocationCreateView,
)
from .event_urls import urlpatterns as event_urls

urlpatterns = [
    # 초대 코드 생성
    path('invitations/', InvitationCodeCreateView.as_view(), name='create-invitation'),
    # 위치 정보 생성(업데이트)
    path('locations/', PetLocationCreateView.as_view(), name='pet-location-create'),
    # 품종 목록
    path('breeds/', PetBreedListView.as_view(), name='pet-breed-list'),
    # 반려견 목록 및 등록
    path('', PetListCreateView.as_view(), name='pet-list-create'),
    # 특정 반려견의 상세/수정/삭제 및 하위 항목 연결
    path('<int:pk>/', PetRetrieveUpdateDestroyView.as_view(), name='pet-detail'),
    # 하위 항목인 히스토리 (events_urls.py 로 확장)
    path('<int:pk>/events/', include(event_urls)),
]