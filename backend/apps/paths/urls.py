from django.urls import path
from .views import UserPathCreateView

urlpatterns = [
    path("", UserPathCreateView.as_view(), name="user-path-create"),
]