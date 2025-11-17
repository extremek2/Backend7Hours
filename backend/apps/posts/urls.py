# posts/urls.py (새로 만들기)
from django.urls import path
from . import views

urlpatterns = [
    path('nearby/', views.find_nearby_locations, name='find_nearby'),
    path('create-route/', views.create_route_from_coords, name='create_route'),
    path('map/', views.show_line_map, name='show_line_map'),
]