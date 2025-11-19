from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

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
        
# 다중 카테고리 모델
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

# 댓글
class Comment(BaseModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='작성자')
    content = models.TextField(verbose_name='댓글 내용')

    # GenericForeignKey를 위한 세 가지 필드
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f'{self.author.username} 님의 댓글 : {self.content_object}'

# 좋아요    
class Like(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')

    # GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        # 한 사용자가 같은 객체에 두 번 '좋아요'를 누르지 못하도록 유니크 제약 조건 설정
        unique_together = ('user', 'content_type', 'object_id')
        verbose_name = '좋아요'
        verbose_name_plural = '좋아요 목록'
    
    def __str__(self):
        return f'{self.user.username} 님의 즐겨찾기 : {self.content_object}'
    
# 즐겨찾기
class Bookmark(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')

    # GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        # 한 사용자가 같은 객체를 두 번 즐겨찾기하지 못하도록 제약 조건 설정
        unique_together = ('user', 'content_type', 'object_id')
        verbose_name = '즐겨찾기'
        verbose_name_plural = '즐겨찾기 목록'
    
    def __str__(self):
        return f'{self.user.username} 님의 북마크 : {self.content_object}'