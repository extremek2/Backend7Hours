from django.conf import settings
from django.db import models
from core.models import BaseModel
from django.contrib.gis.db.models import LineStringField

class Path(BaseModel):
    auth_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paths"
    )
    path_name = models.CharField(max_length=45)
    path_comment = models.TextField(null=True, blank=True)
    level = models.IntegerField(default=2)          # 난이도 1,2,3
    distance = models.FloatField(null=True, blank=True)  # km
    duration = models.IntegerField(null=True, blank=True) # 분 단위
    is_private = models.BooleanField(default=False)
    thumbnail = models.CharField(max_length=255, null=True, blank=True)
    geom = LineStringField(dim=3, null=True, blank=True)  # 3D LineString (x=lon, y=lat, z=ele)

    def __str__(self):
        return f"{self.path_name} ({self.auth_user.username})"