from core.models import BaseModel, BaseScheduleModel
from django.db import models
from django.conf import settings


# 반려견 품종
class PetBreed(BaseModel):
    breed_name = models.CharField(max_length=45, unique=True)

    class Meta:
        db_table = 'pet_breed'
        verbose_name = '품종'
        verbose_name_plural = '품종 목록'

    def __str__(self):
        return self.breed_name


# 반려견 기본 정보
class Pet(BaseModel):
    GENDER_MALE = 'M'
    GENDER_FEMALE = 'F'
    GENDER_CHOICES = [
        (GENDER_MALE, '남아'),
        (GENDER_FEMALE, '여아'),
    ]

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
        default=None,
        null=True,
        blank=True
    )
    
    birthday = models.DateField(null=True, blank=True)
    neutering = models.BooleanField(default=False)
    
    breed = models.ForeignKey(
        PetBreed,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='품종'
    )

    class Meta:
        db_table = 'pet'
        verbose_name = '반려견'
        verbose_name_plural = '반려견 목록'

    def __str__(self):
        return f"{self.owner.username}의 {self.name}"
    
    
class EventType(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'event_type'
        verbose_name = '활동 유형'
        verbose_name_plural = '활동 유형 목록'

    def __str__(self):
        return self.name


# 반려견 활동 기록
class PetEvent(BaseScheduleModel):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='events')
    event_type = models.ForeignKey(EventType, on_delete=models.SET_NULL, null=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'pet_event'
        verbose_name = '반려견 활동 기록'
        verbose_name_plural = '반려견 활동 기록 목록'

    def __str__(self):
        return f"{self.pet.name}의 {self.event_type.name if self.event_type else '활동'}"


# 반려견 검진 기록 상세
class PetCheckup(BaseScheduleModel):
    event = models.OneToOneField(PetEvent, on_delete=models.CASCADE, related_name='checkup_detail')
    hospital_name = models.CharField(max_length=100)
    memo = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'pet_event_checkup'
        verbose_name = '반려견 검진 기록 상세'
        verbose_name_plural = '반려견 검진 기록 상세 목록'

    def __str__(self):
        return f"{self.event.pet.name}의 검진 - {self.hospital_name}"