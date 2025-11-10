from django.urls import path
from .views import PlaceListAPIView

urlpatterns = [
    path('', PlaceListAPIView.as_view(), name='place-list'),
]