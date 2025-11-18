from django.urls import path
from .views import (
    PetEventListCreateView,
    PetEventRetrieveUpdateDestroyView,
)

urlpatterns = [
    # GET/POST: /pets/{pet_id}/events/
    # 모든 이벤트 목록 조회 및 (PetEvent/PetCheckup) 동시 생성 처리
    path('', PetEventListCreateView.as_view(), name='pet-event-list-create'),
    
    # GET/PUT/PATCH/DELETE: /pets/{pet_id}/events/{event_id}/
    # 특정 이벤트 상세 조회 및 (PetEvent/PetCheckup) 동시 수정/삭제 처리
    path('<int:pk>/', PetEventRetrieveUpdateDestroyView.as_view(), name='pet-event-detail'),
]