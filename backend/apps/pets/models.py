from django.db import models
from django.conf import settings # CustomUser 참조를 위해 필요


# 반려견 품종
class PetBreed(models.Model):
    breed_name = models.CharField(max_length=45, unique=True)

    class Meta:
        db_table = 'pet_breed'
        verbose_name = '품종'
        verbose_name_plural = '품종 목록'

    def __str__(self):
        return self.breed_name


# 반려견 기본 정보
class Pet(models.Model):
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
    
    



# 반려견 활동 기록
class PetHistory(models.Model):
    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='histories',
        verbose_name='반려견'
    )
    event_type = models.CharField(max_length=45)
    event_title = models.CharField(max_length=45, null=True, blank=True)
    event_date = models.DateTimeField()
    next_due_date = models.DateTimeField(null=True, blank=True)
    quantity = models.FloatField(null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pet_history'
        verbose_name = '반려견 활동 기록'

# 반려견 검진 기록 상세
class PetCheckup(models.Model):
    pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='checkups',
        verbose_name='반려견'
    )
    history = models.ForeignKey(
        PetHistory,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='관련 기록'
    )
    checkup_date = models.DateTimeField()
    clinic_name = models.CharField(max_length=45, null=True, blank=True)
    next_checkup_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pet_checkup'
        verbose_name = '반려견 검진 기록 상세'