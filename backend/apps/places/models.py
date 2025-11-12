from django.db import models
from django.contrib.gis.db import models as gis_models
from core.models import BasePlaceModel
from django.contrib.gis.geos import Point

# 카테고리 모델
class Category1(models.Model):
    name = models.CharField(max_length=50, unique=True)

class Category2(models.Model):
    parent = models.ForeignKey(Category1, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=50)

class Category3(models.Model):
    parent = models.ForeignKey(Category2, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=50)
    
# KCISA API
class KCISAPlace(BasePlaceModel):
    issued_date = models.DateField(null=True, blank=True)
    category1 = models.CharField(max_length=50, null=True, blank=True)
    category2 = models.CharField(max_length=50, null=True, blank=True)
    category3 = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    charge = models.CharField(max_length=255, null=True, blank=True)

    def set_coordinates(self, coord_str: str):
        # 좌표 문자열에서 N, E, S, W 같은 문자를 제거하고 float로 변환
        if not coord_str:
            return None
        try:
            # 공백 및 방향 문자 제거
            coord_str = coord_str.replace("N", "").replace("E", "").replace("S", "-").replace("W", "-").strip()
            parts = [p.strip() for p in coord_str.split(",")]
            if len(parts) != 2:
                return None
            lat, lng = map(float, parts)
            return Point(lng, lat, srid=4326)
        except Exception as e:
            print(f"좌표 변환 실패: {coord_str} ({e})")
            return None

# KoreaTour API
class KoreaTourPlace(BasePlaceModel):
    addr1 = models.CharField(max_length=255, null=True, blank=True)
    addr2 = models.CharField(max_length=255, null=True, blank=True)
    areacode = models.CharField(max_length=10, null=True, blank=True)
    cat1 = models.CharField(max_length=50, null=True, blank=True)
    cat2 = models.CharField(max_length=50, null=True, blank=True)
    cat3 = models.CharField(max_length=50, null=True, blank=True)
    contentid = models.CharField(max_length=50, null=True, blank=True)
    contenttypeid = models.CharField(max_length=50, null=True, blank=True)
    createdtime = models.DateTimeField(null=True, blank=True)
    dist = models.FloatField(null=True, blank=True)
    firstimage = models.URLField(null=True, blank=True)
    firstimage2 = models.URLField(null=True, blank=True)
    cpyrhtDivCd = models.CharField(max_length=10, null=True, blank=True)
    mapx = models.FloatField(null=True, blank=True)
    mapy = models.FloatField(null=True, blank=True)
    mlevel = models.IntegerField(null=True, blank=True)
    modifiedtime = models.DateTimeField(null=True, blank=True)
    sigungucode = models.CharField(max_length=10, null=True, blank=True)

    def set_coordinates(self):
        if self.mapx is not None and self.mapy is not None:
            self.coordinates = Point(self.mapx, self.mapy)

# 통합 Place 모델            
class Place(BasePlaceModel):
    # 3중 카테고리
    category1 = models.ForeignKey('Category1', on_delete=models.SET_NULL, null=True, blank=True)
    category2 = models.ForeignKey('Category2', on_delete=models.SET_NULL, null=True, blank=True)
    category3 = models.ForeignKey('Category3', on_delete=models.SET_NULL, null=True, blank=True)

    raw_data = models.JSONField(null=True, blank=True)  # 원본 API JSON 저장
    source = models.CharField(max_length=50, null=True, blank=True)  # API 출처