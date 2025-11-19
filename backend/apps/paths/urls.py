from django.urls import path
from .views import PathListCreateView, PathDetailView, MyPathListView

urlpatterns = [
    path("", PathListCreateView.as_view(), name="path-list-create"),
    path("mine/", MyPathListView.as_view(), name="my-path-list"),
    path("<int:pk>/", PathDetailView.as_view(), name="path-detail"),
]