from django.urls import path
from .views import (
    PetListCreateView, 
    PetRetrieveUpdateDestroyView, 
    PetBreedListView
)

urlpatterns = [
    # GET: 품종 목록 조회
    path('breeds/', PetBreedListView.as_view(), name='pet-breed-list'),
    
    # GET, POST: 반려견 목록 조회 및 등록
    path('', PetListCreateView.as_view(), name='pet-list-create'),
    
    # GET, PUT/PATCH, DELETE: 특정 반려견 상세 조회/수정/삭제
    path('<int:pk>/', PetRetrieveUpdateDestroyView.as_view(), name='pet-detail'),
]