from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid

def generate_unique_nickname():
    return 'user_' + uuid.uuid4().hex[:8]

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('이메일은 필수입니다.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None  # username 제거
    # 4. 이메일 필드 (고유값 필수)
    email = models.EmailField(unique=True, verbose_name="이메일")

    full_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="이름")
    
    # 5. 닉네임: default에 함수 자체를 넘겨야 함 (괄호 없이!)
    nickname = models.CharField(
        max_length=50,
        unique=True,
        default=generate_unique_nickname, # 함수 자체를 전달
        verbose_name="별명"
    )
    
    # MinIO 설정을 settings.py에서 했다면, 자동으로 MinIO에 저장됩니다.
    profile_image = models.ImageField(
        upload_to='profile_images/', 
        blank=True, 
        null=True, 
        verbose_name="프로필 이미지"
    )
    
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="전화번호")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="주소")
    
    provider = models.CharField(max_length=30, blank=True, null=True)
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    
    # 6. 로그인 식별자를 이메일로 변경
    USERNAME_FIELD = "email"
    
    # 7. createsuperuser 할 때 추가로 물어볼 필드 (이메일은 위에서 이미 필수이므로 제외)
    REQUIRED_FIELDS = [] 

    # 8. 커스텀 매니저 연결
    objects = CustomUserManager()

    def __str__(self):
        return self.email
    
    