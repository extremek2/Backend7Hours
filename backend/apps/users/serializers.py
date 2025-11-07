from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_verification = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'password', 'password_verification']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_verification']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_verification')
        user = User.objects.create(
            username=validated_data['username'],
            full_name=validated_data.get('full_name', ''),
            email=validated_data['email'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'nickname']