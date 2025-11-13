# backend/apps/posts/models.py
from django.contrib.gis.db import models as gis_models

# Location 모델 (GeoDjango 필드 사용)
class Location(gis_models.Model): 
    name = gis_models.CharField(max_length=100)
    geom = gis_models.GeometryField(srid=4326) 

    def __str__(self):
        return self.name

# Route 모델 (GeoDjango 필드 사용)
class Route(gis_models.Model):
    name = gis_models.CharField(max_length=100)
    path = gis_models.LineStringField(srid=4326)

    def __str__(self):
        return self.name

# Place 모델 (GeoDjango 필드 + Minio 필드)
# 1. gis_models.Model 을 상속받도록 수정
# 2. 중복 정의된 필드를 하나로 합침
class Place(gis_models.Model):
    name = gis_models.CharField(max_length=100)
    
    # GeoDjango 필드 (DB에 저장)
    location = gis_models.PointField(srid=4326) # srid=4326 추가 권장
    
    # Minio에 저장될 필드
    photo = gis_models.ImageField(upload_to='places_photos/', blank=True, null=True)
    document = gis_models.FileField(upload_to='places_docs/', blank=True, null=True)

    def __str__(self):
        return self.name