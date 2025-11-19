from django.conf import settings
from django.db import models
from core.models import BaseModel
from core.models import Comment, Like, Bookmark
from core.utils import UploadFilePathGenerator
from core.custom_storages import PostsStorage
from django.contrib.contenttypes.fields import GenericRelation


class Post(BaseModel):
    auth_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts"
    )
    title = models.CharField(max_length=255)
    content = content = models.TextField()
    
    image = models.ImageField(
        upload_to=UploadFilePathGenerator('post_images', user_field='auth_user'),
        storage=PostsStorage(),
        null=True,
        blank=True
    )
    
    # 1. 댓글 역참조 설정
    comments = GenericRelation(Comment, related_query_name='post')
    
    # 2. 좋아요 역참조 설정
    likes = GenericRelation(Like, related_query_name='post')
    
    # 3. 즐겨찾기 역참조 설정
    bookmarks = GenericRelation(Bookmark, related_query_name='post')