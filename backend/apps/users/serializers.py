from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction
from django.utils import timezone
from apps.pets.models import Pet, InvitationCode

User = get_user_model()

# 이메일 기반 JWT 발급
class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user with this email was found.")

        if not user.check_password(password):
            raise serializers.ValidationError("Incorrect password.")

        if not user.is_active:
            raise serializers.ValidationError("User is disabled.")

        # The user is valid, now we can generate the tokens
        refresh = self.get_token(user)

        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data, # Add user info to the response
        }

        return data

# 회원가입
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_verification = serializers.CharField(write_only=True, required=True)
    invitation_code = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['nickname', 'full_name', 'email', 'profile_image', 'password', 'password_verification', 'invitation_code']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_verification']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        invitation_code = attrs.get('invitation_code')
        if invitation_code:
            try:
                code_obj = InvitationCode.objects.get(code=invitation_code)
                if not code_obj.is_valid():
                    raise serializers.ValidationError({"invitation_code": "만료되었거나 이미 사용된 초대 코드입니다."})
            except InvitationCode.DoesNotExist:
                raise serializers.ValidationError({"invitation_code": "유효하지 않은 초대 코드입니다."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        invitation_code_str = validated_data.pop('invitation_code', None)
        validated_data.pop('password_verification')
        
        user = User.objects.create(
            nickname=validated_data.get('nickname', ''),
            full_name=validated_data.get('full_name', ''),
            email=validated_data['email'],
            profile_image=validated_data.get('profile_image', None),
        )
        user.set_password(validated_data['password'])
        user.save()

        if invitation_code_str:
            code_obj = InvitationCode.objects.get(code=invitation_code_str)
            inviting_user = code_obj.created_by

            Pet.objects.create(
                owner=inviting_user,
                linked_user=user,
                name=user.nickname
            )

            code_obj.used_by = user
            code_obj.used_at = timezone.now()
            code_obj.save()
            
        return user

class UserSerializer(serializers.ModelSerializer):
    is_pet = serializers.SerializerMethodField()
    profile_image = serializers.ImageField(use_url=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'nickname', 'profile_image', 'is_pet']

    def get_is_pet(self, obj):
        """
        Check if the user is linked as a pet.
        'linked_as_pet' is the related_name from the OneToOneField in the Pet model.
        """
        return hasattr(obj, 'linked_as_pet')
        
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'nickname', 'profile_image']

        # [중요] 이메일이나 ID는 수정 못하게 '읽기 전용'으로 설정합니다.
        read_only_fields = ['id', 'email', 'full_name']
        
        extra_kwargs = {
            'profile_image': {'required': False},
            'nickname': {'required': False},
        }

    