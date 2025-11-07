from core.models import BaseModel, BaseScheduleModel
from django.db import models
from django.conf import settings # CustomUser 참조를 위해 필요


# 반려견 품종
class PetBreed(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    # CustomUser 참조 (FK: auth_user_id)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pets', # user.pets로 접근 가능
        verbose_name='집사'
    )
    name = models.CharField(max_length=45)
    
    # gender -> mysql의 Enum('M','F')
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        default=None,
        null=True,
        blank=True
    )
    
    birthday = models.DateField(null=True, blank=True)
    neutering = models.BooleanField(default=False) # TINYINT(1)
    
    # PetBreed 참조 (FK: pet_breed_id)
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

    def __str__(self):
        return self.name


# 반려견 활동 기록
class PetEvent(BaseScheduleModel):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='events')
    event_type = models.ForeignKey('EventType', on_delete=models.SET_NULL, null=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'pet_event'
        verbose_name = '반려견 활동 기록'

# 반려견 검진 기록 상세
class PetCheckup(BaseScheduleModel):
    event = models.OneToOneField('PetEvent', on_delete=models.CASCADE, related_name='checkup_detail')
    hospital_name = models.CharField(max_length=100)
    memo = models.TextField(null=True, blank=True)
    class Meta:
        db_table = 'pet_event_checkup'
        verbose_name = '반려견 검진 기록 상세'