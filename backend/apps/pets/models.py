from core.models import BaseModel, BaseScheduleModel
from django.db import models
from django.conf import settings
from core.utils import UploadFilePathGenerator
from core.custom_storages import PetsStorage


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
        upload_to=UploadFilePathGenerator('profile'),
        storage=PetsStorage(),
        null=True,
        blank=True
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
    
    
# 반려견 활동 기록
# 이벤트 타입 분류 CHOICE 리스트
CHECKUP = 'CHECKUP'
VACCINE = 'VACCINE'
FEED_PURCHASE = 'FEED_PURCHASE'

EVENT_TYPE_CHOICES = [
    (CHECKUP, '건강검진'),
    (VACCINE, '예방접종'),
    (FEED_PURCHASE, '사료구매'),
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