from django.db import models
from django.contrib.gis.db import models as gis_models


# 공통 모델로 작성일/수정일 추가
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        
# 일정 관리용 모델로 공통모델 + 이벤트 발생일/다음 이벤트 예정일 추가
class BaseScheduleModel(BaseModel):
    event_date = models.DateTimeField()  # 시작 or 발생일
    due_date = models.DateTimeField(null=True, blank=True)  # 마감일 or 다음 예정일

    class Meta:
        abstract = True
        
class BasePlaceModel(BaseModel):
    title = models.CharField(max_length=255)          # 장소명
    tel = models.CharField(max_length=50, null=True, blank=True)  # 전화번호
    address = models.CharField(max_length=255, null=True, blank=True)  # 주소
    coordinates = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)# 좌표 (PostGIS)
    source = models.CharField(max_length=50, default="unknown")   # 데이터 출처
    is_active = models.BooleanField(default=True)    # 활성화 여부
    
    # 3중 카테고리 (통합 Place 모델에서 사용)
    category1 = models.ForeignKey('places.Category1', on_delete=models.SET_NULL, null=True, blank=True)
    category2 = models.ForeignKey('places.Category2', on_delete=models.SET_NULL, null=True, blank=True)
    category3 = models.ForeignKey('places.Category3', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        abstract = True