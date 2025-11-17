# posts/admin.py
from django.contrib import admin
from django.contrib.gis import admin as gis_admin  # 👈 GeoDjango의 admin 임포트
from .models import Location
from .models import Place

# 👈 admin.ModelAdmin 대신 gis_admin.GISModelAdmin을 사용
@admin.register(Location)
class LocationAdmin(gis_admin.GISModelAdmin):
    """Location Model Admin"""
    pass

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin): # 👈 Place에 PointField가 있다면 gis_admin.GISModelAdmin 사용
    """Place Model Admin"""
    # 템플릿에 보여줄 필드를 설정할 수 있습니다.
    list_display = ('name', 'photo') # 'name'과 'photo' 필드가 있다고 가정
    pass