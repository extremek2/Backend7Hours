from django.db import models

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