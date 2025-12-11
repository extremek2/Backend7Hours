from django.conf import settings
from django.db import models
from core.models import BaseModel, Comment, Like, Bookmark
from core.utils import UploadFilePathGenerator
from core.custom_storages import PostsStorage
from django.contrib.contenttypes.fields import GenericRelation

# 게시글
# 타입 분류

POST_REVIEW = 'review'
POST_INFO = 'info'
POST_CHOICES = [
    (POST_REVIEW, '산책후기'),
    (POST_INFO, '정보공유')
]

class Post(BaseModel):
    auth_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts"
    )
    post_type = models.CharField(
        max_length=20,
        choices=POST_CHOICES,
        default=POST_REVIEW
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    image = models.ImageField(
        upload_to=UploadFilePathGenerator('post_images', user_field='auth_user'),
        storage=PostsStorage(),
        null=True,
        blank=True
    )
    
    # 카운트 필드
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    comment_count = models.PositiveIntegerField(default=0, db_index=True)
    like_count = models.PositiveIntegerField(default=0, db_index=True)
    bookmark_count = models.PositiveIntegerField(default=0, db_index=True)
    
    
    # 1. 댓글 역참조 설정
    comments = GenericRelation(Comment, related_query_name='post')
    
    # 2. 좋아요 역참조 설정
    likes = GenericRelation(Like, related_query_name='post')
    
    # 3. 즐겨찾기 역참조 설정
    bookmarks = GenericRelation(Bookmark, related_query_name='post')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-like_count']),
            models.Index(fields=['post_type', '-created_at']),
        ]
    
    def __str__(self):
        return self.title