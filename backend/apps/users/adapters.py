from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
import uuid



class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    
    def is_auto_signup_allowed(self, request, sociallogin):
        print("✅ [Adapter] is_auto_signup_allowed 호출됨 -> 무조건 True 반환")
        return True

    def populate_user(self, request, sociallogin, data):
        print("✅ [Adapter] populate_user 호출됨")
        user = super().populate_user(request, sociallogin, data)
        
        if not user.email:
            base_email = f"{sociallogin.account.uid}@kakao.social"
            counter = 0
            email = base_email
            while get_user_model().objects.filter(email=email).exists():
                counter += 1
                email = f"{sociallogin.account.uid}_{counter}@kakao.social"
            user.email = email
            print(f"⚠️ [Adapter] 이메일 자동 생성: {user.email}")

        if not getattr(user, 'nickname', None):
            random_suffix = uuid.uuid4().hex[:8]
            user.nickname = f"user_{random_suffix}"
            print(f"⚠️ [Adapter] 닉네임 자동 생성: {user.nickname}")
            
        # [추가] full_name도 강제로 채우기 (DB not null 조건 방지)
        if not getattr(user, 'full_name', None):
             user.full_name = data.get("name", "Unknown")

        return user

    # [추가] 가입 저장 직전 단계 확인
    def save_user(self, request, sociallogin, form=None):
        print("✅ [Adapter] save_user 호출됨 -> 유저 저장 시도")
        return super().save_user(request, sociallogin, form)