from rest_framework import serializers
from .models import Pet, PetBreed, PetHistory, PetCheckup
from users.models import CustomUser

class PetBreedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetBreed
        fields = ['id', 'breed_name']
        
class PetSerializer(serializers.ModelSerializer):
    # 1. breed 필드 오버라이드: ID 대신 'breed_name' 문자열로 통신합니다.
    #    - queryset: 입력받은 이름이 존재하는지 확인할 PetBreed 객체 목록
    #    - slug_field: 실제로 읽고 쓸 때 사용할 PetBreed 모델의 필드 이름 ('breed_name')
    breed = serializers.SlugRelatedField(
        queryset=PetBreed.objects.all(),
        slug_field='breed_name',
        required=True
    )
    
    # 2. owner 필드 (읽기 전용): 소유자의 username을 출력합니다.
    #    쓰기는 필요 없으므로 'read_only=True'로 설정합니다.
    owner = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Pet
        # API에서 사용할 필드 목록 정의
        fields = [
            'id', 'owner', 'name', 'gender', 'birthday', 
            'neutering', 'breed'
        ]
        read_only_fields = ['owner'] # 명시적으로 owner 필드는 수정 불가

    # 3. 추가 로직: 등록/수정 시 현재 로그인한 사용자를 owner로 자동 할당
    #    뷰에서 self.request.user를 context로 전달해야 동작합니다.
    def create(self, validated_data):
        # 뷰에서 context={'request': request}를 전달했을 경우
        user = self.context['request'].user
        
        # 유효성 검사를 통과한 데이터에 owner 필드를 추가
        if not user.is_authenticated:
            raise serializers.ValidationError({"owner": "사용자 인증이 필요합니다."})
            
        validated_data['owner'] = user
        return super().create(validated_data)
    
    
class PetHistorySerializer(serializers.ModelSerializer):
# pet 필드: Pet 객체의 ID를 받아야 함 (별도 로직 필요 없음)

    class Meta:
        model = PetHistory
        fields = [
            'id', 'pet', 'event_type', 'event_title', 'event_date', 
            'next_due_date', 'quantity', 'price', 'notes', 'created_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        
class PetCheckupSerializer(serializers.ModelSerializer):
    # pet_history_id를 직접 참조하는 대신, history 객체의 ID를 받습니다.
    # history 필드는 NULL을 허용하므로 required=False
    class Meta:
        model = PetCheckup
        fields = [
            'id', 'pet', 'history', 'checkup_date', 'clinic_name', 
            'next_checkup_date', 'notes', 'created_at'
        ]
        read_only_fields = ['created_at']