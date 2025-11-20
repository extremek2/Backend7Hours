from django.conf import settings
from django.db import models
from core.models import BaseModel, Comment, Bookmark
from django.contrib.gis.db.models import LineStringField
from django.contrib.contenttypes.fields import GenericRelation

class Path(BaseModel):
    # 경로 출처 선택지
    SOURCE_CHOICES = [
        ('USER', '사용자 생성'),
        ('PUBLIC_API', '공공 API'),
    ]

    auth_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="paths",
        null=True,
        blank=True
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='PUBLIC_API'
    )
    path_name = models.CharField(max_length=45)
    path_comment = models.TextField(null=True, blank=True)
    level = models.IntegerField(default=2)          # 난이도 1,2,3
    distance = models.FloatField(null=True, blank=True)  # m 단위
    duration = models.IntegerField(null=True, blank=True) # 분 단위
    is_private = models.BooleanField(default=False)
    thumbnail = models.CharField(max_length=255, null=True, blank=True)
    geom = LineStringField(dim=3, null=True, blank=True)  # 3D LineString (x=lon, y=lat, z=ele)
    
    # 댓글 역참조 설정
    comments = GenericRelation(Comment, related_query_name='path')
    
    # 즐겨찾기 역참조 설정
    bookmarks = GenericRelation(Bookmark, related_query_name='path')

    def __str__(self):
        username = self.auth_user.username if self.auth_user else 'N/A'
        return f"{self.path_name} ({username})"