from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    
    full_name = models.CharField(max_length=100, verbose_name="이름")
    nickname = models.CharField(max_length=50, blank=True, null=True, verbose_name="별명")
    email = models.EmailField(unique=True, verbose_name="이메일")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="전화번호")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="주소")
    
    provider = models.CharField(max_length=30, blank=True, null=True)
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    
    # 로그인 식별자
    USERNAME_FIELD = "username"
    
    REQUIRED_FIELDS = ["email"]  # createsuperuser 시 요청됨

    def __str__(self):
        return self.username