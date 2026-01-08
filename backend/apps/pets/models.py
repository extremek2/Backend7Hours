import secrets
from datetime import timedelta
from django.utils import timezone
from core.models import BaseModel, BaseScheduleModel
from django.db import models
from django.conf import settings
from core.utils import UploadFilePathGenerator
from core.custom_storages import PetsStorage
from core.utils import get_presigned_url


# 반려견 품종
class PetBreed(models.Model):
    breed_name = models.CharField(max_length=45, unique=True, null=True)
    category = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="분류",
        help_text="소형견 / 중형견 / 대형견"
    )

    class Meta:
        db_table = 'pet_breed'
        verbose_name = '품종'
        verbose_name_plural = '품종 목록'
        ordering = ['category', 'breed_name']  # 한글 가나다순으로 변경 가능: ['breed_name'] 그대로 사용 가능

    def __str__(self):
        return self.breed_name

# 반려견 기본 정보
# 성별 분류
GENDER_MALE = 'M'
GENDER_FEMALE = 'F'
GENDER_CHOICES = [
    (GENDER_MALE, '남아'),
    (GENDER_FEMALE, '여아'),
]

class Pet(BaseModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pets',
        verbose_name='집사'
    )
    name = models.CharField(max_length=45)
    
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        null=True,
        blank=True
    )
    
    birthday = models.DateField(null=True, blank=True)
    neutering = models.BooleanField(default=False, help_text='중성화 수술 여부')
    
    breed = models.ForeignKey(
        PetBreed,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='품종',
        help_text="반려견의 품종 이름(문자열)을 입력합니다. (예: '푸들')."
    )
    
    image = models.ImageField(
        upload_to=UploadFilePathGenerator('profile', user_field='owner'),
        storage=PetsStorage(),
        null=True,
        blank=True
    )

    last_location = models.OneToOneField(
        'pets.PetLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='최근 위치'
    )
    
    linked_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_as_pet',
        verbose_name='연결된 사용자 계정'
    )

    class Meta:
        db_table = 'pet'
        verbose_name = '반려견'
        verbose_name_plural = '반려견 목록'
        indexes = [
            models.Index(fields=['owner', 'created_at']),  # 사용자별 반려견 조회
        ]

    def __str__(self):
        return f"{self.owner.username}의 {self.name}"

    def get_image_url(self):
        """펫 이미지의 Pre-signed URL 반환"""
        if self.image:
            return get_presigned_url(self.image.url)
        return None

# 신규: 반려견 위치 추적 모델
class PetLocation(BaseModel):
    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='locations',
        verbose_name='반려견'
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name='위도'
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name='경도'
    )
    accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text="위치 정확도 (미터 단위)",
        verbose_name='정확도'
    )
    battery_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="GPS 장치의 배터리 잔량 (%)",
        verbose_name='배터리 잔량'
    )

    class Meta:
        db_table = 'pet_location'
        verbose_name = '반려견 위치'
        verbose_name_plural = '반려견 위치 기록'
        ordering = ['pet', '-created_at']
        indexes = [
            models.Index(fields=['pet', '-created_at']),
        ]

    def __str__(self):
        return f"{self.pet.name}의 위치 at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

def default_expires_at():
    # 코드는 생성 후 24시간 동안 유효
    return timezone.now() + timedelta(hours=24)

def generate_invitation_code():
    return secrets.token_urlsafe(16)

class InvitationCode(BaseModel):
    """펫 등록 초대를 위한 일회성 초대 코드 모델"""
    code = models.CharField(max_length=32, unique=True, default=generate_invitation_code)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='generated_invitations',
        verbose_name='생성한 사용자'
    )
    expires_at = models.DateTimeField(default=default_expires_at, verbose_name='만료 시각')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='사용 시각')
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invitation',
        verbose_name='사용자'
    )

    def is_valid(self):
        """코드가 유효한지 (사용되지 않았고, 만료되지 않았는지) 확인"""
        return self.used_by is None and timezone.now() < self.expires_at

    class Meta:
        db_table = 'pet_invitation_code'
        verbose_name = '펫 초대 코드'
        verbose_name_plural = '펫 초대 코드 목록'

    def __str__(self):
        return f"Code for {self.created_by.email} ({self.code})"


# 반려견 활동 기록
# 이벤트 타입 분류 CHOICE 리스트
CHECKUP = 'CHECKUP'
VACCINE = 'VACCINE'
FEED_PURCHASE = 'FEED_PURCHASE'
TRAIL_DIARY = 'TRAIL_DIARY'

EVENT_TYPE_CHOICES = [
    (CHECKUP, '건강검진'),
    (VACCINE, '예방접종'),
    (FEED_PURCHASE, '사료구매'),
    (TRAIL_DIARY, '산책 다이어리'),
]
class PetEvent(BaseScheduleModel):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default=CHECKUP) # 우선 기본값 CHECKUP
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'pet_event'
        verbose_name = '반려견 활동 기록'
        verbose_name_plural = '반려견 활동 기록 목록'
        ordering = ['-event_date']  # 최신순 정렬
        indexes = [
            models.Index(fields=['pet', 'event_date']),  # 반려견별 일정 조회
            models.Index(fields=['pet', 'is_completed']),  # 미완료 일정 조회
            models.Index(fields=['event_type', 'event_date']),  # 유형별 조회
        ]

    def __str__(self):
        return f"{self.pet.name}의 {self.get_event_type_display()} 활동 기록"


# 반려견 검진 기록 상세
class PetCheckup(BaseModel):
    event = models.OneToOneField(PetEvent, on_delete=models.CASCADE, related_name='checkup')
    hospital_name = models.CharField(max_length=100)
    memo = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'pet_event_checkup'
        verbose_name = '반려견 검진 기록 상세'
        verbose_name_plural = '반려견 검진 기록 상세 목록'

    def __str__(self):
        return f"{self.event.pet.name}의 검진 - {self.hospital_name}"
    
    
class PetTrail(BaseModel):
    event = models.OneToOneField(
        PetEvent,
        on_delete=models.CASCADE,
        related_name='trail'
    )

   # 느슨한 참조
    path_id = models.BigIntegerField(null=True, blank=True)
    path_name = models.CharField(max_length=45, blank=True)

    distance = models.FloatField(help_text="미터 단위")
    duration = models.IntegerField(help_text="초 단위")

    ai_summary = models.TextField(blank=True)
    ai_generated = models.BooleanField(default=False)