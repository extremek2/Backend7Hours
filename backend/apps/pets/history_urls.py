from django.urls import path
from .views import (
    PetEventListCreateView,
    PetEventRetrieveUpdateDestroyView,
    PetCheckupListCreateView,
    PetCheckupRetrieveUpdateDestroyView,
)

urlpatterns = [
    # 히스토리 전체 항목 
    path('', PetEventListCreateView.as_view(), name='pet-history-list-create'),
    path('<int:history_id>/', PetEventRetrieveUpdateDestroyView.as_view(), name='pet-history-detail'),

    # 히스토리 세부 항목 (예: 건강검진)
    path('checkups/', PetCheckupListCreateView.as_view(), name='pet-checkup-list-create'),
    path('checkups/<int:checkup_id>/', PetCheckupRetrieveUpdateDestroyView.as_view(), name='pet-checkup-detail'),
]