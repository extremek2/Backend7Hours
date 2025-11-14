from django.db import models


# 공통 모델로 작성일/수정일 추가
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']
        
# 일정 관리용 모델로 공통모델 + 이벤트 발생일/다음 이벤트 예정일 추가
class BaseScheduleModel(BaseModel):
    event_date = models.DateTimeField()  # 시작 or 발생일
    due_date = models.DateTimeField(null=True, blank=True)  # 마감일 or 다음 예정일

    class Meta:
        abstract = True
        ordering = ['-event_date']
        

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    # Self-Referencing ForeignKey: 'self'를 사용하여 같은 모델 참조
    parent = models.ForeignKey(
    'self',  
    on_delete=models.SET_NULL, 
    null=True, 
    blank=True, 
    related_name='children',
    verbose_name='상위 카테고리'
    )

    def __str__(self):
        return self.name