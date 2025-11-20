from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    
    # 1. 목록 정렬 기준을 'email'로 변경
    ordering = ('email',)
    
    # 2. 관리자 목록 화면에 보여질 필드
    list_display = ('email', 'full_name', 'nickname', 'is_staff', 'is_active')
    
    # 3. 검색 창에서 검색할 필드 (이메일, 이름, 닉네임으로 검색)
    search_fields = ('email', 'full_name', 'nickname')
    
    # 4. 사용자 상세 정보 수정 화면 구성 (username 제거)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'nickname', 'phone', 'address')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

# 기존 User 모델 등록
admin.site.register(CustomUser, CustomUserAdmin)