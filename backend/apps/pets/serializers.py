from rest_framework import serializers
from django.db import transaction
from .models import Pet, PetBreed, PetEvent, PetCheckup

# pet_breed
class PetBreedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetBreed
        fields = ['id', 'breed_name']

# pet        
class PetSerializer(serializers.ModelSerializer):
    # 1. ID 대신 'breed_name' 문자열로 통신
    breed = serializers.SlugRelatedField(
        queryset=PetBreed.objects.all(),
        slug_field='breed_name',
        required=True
    )
    
    # 2. owner의 username 출력
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
    def create(self, validated_data):
        user = self.context.get('request').user
        
        # 유효성 검사를 통과한 데이터에 owner 필드를 추가
        if not user.is_authenticated:
            raise serializers.ValidationError({"owner": "사용자 인증이 필요합니다."})
            
        validated_data['owner'] = user
        return super().create(validated_data)
     

# pet_checkup
class PetCheckupSerializer(serializers.ModelSerializer):
    # event 필드 참조 (데이터 중복 없이 PetEvent에서 가져옴)
    pet_name = serializers.CharField(source='event.pet.name', read_only=True)
    event_date = serializers.DateTimeField(source='event.event_date', read_only=True)
    due_date = serializers.DateTimeField(source='event.due_date', read_only=True)

    class Meta:
        model = PetCheckup
        fields = [
            'id', 'event', 'pet_name', 'hospital_name', 'memo',
            'event_date', 'due_date', 'created_at'
        ]
        # read_only_fields에 'id'와 'event'를 명시적으로 추가하여 외부 쓰기 차단
        read_only_fields = ['id', 'event', 'created_at', 'pet_name', 'event_date', 'due_date']
        
        
# pet_event
class PetEventSerializer(serializers.ModelSerializer):
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    # 한글 레이블 반환
    event_type_display = serializers.ReadOnlyField(source='get_event_type_display')
    # 관련 checkup 역참조
    checkup = PetCheckupSerializer(required=False)
    
    class Meta:
        model = PetEvent
        fields = [
            'id', 'pet', 'pet_name', 'event_type_display',
            'event_date', 'due_date', 'is_completed', 'created_at', 'updated_at', 'checkup'
        ]
        read_only_fields = ['created_at', 'updated_at', 'pet_name', 'event_type_display']

    @transaction.atomic # 원자적 트랜잭션으로 두 객체의 생성/실패를 보장
    def create(self, validated_data):
        # 1. checkup 데이터 분리 (존재할 경우)
        checkup_data = validated_data.pop('checkup', None) 
        
        # 2. PetEvent 객체 생성 (부모)
        # 이 시점에 PetEventListCreateView의 perform_create에서 전달된 pet=request.user가 적용됨
        pet_event = PetEvent.objects.create(**validated_data)
        
        # 3. checkup 데이터가 있고, 이벤트 타입이 'CHECKUP'인 경우에만 자식 객체 생성
        # 데이터 일관성 검증 (선택적)
        if checkup_data and pet_event.event_type == 'CHECKUP':
            PetCheckup.objects.create(event=pet_event, **checkup_data)
        
        # 4. 이벤트 타입이 'CHECKUP'인데 checkup 데이터가 없는 경우
        elif pet_event.event_type == 'CHECKUP' and not checkup_data:
            # 이 경우 클라이언트에게 오류를 반환하거나, 빈 Checkup 객체를 생성할 수 있습니다.
            # 여기서는 Validation Error를 발생시키는 것이 적절합니다.
            raise serializers.ValidationError(
                {'checkup': '이벤트 타입이 "건강검진" 일 경우, 검진 상세 정보는 필수입니다.'}
            )
            
        return pet_event

    def update(self, instance, validated_data):
        # 1. checkup 데이터 분리 (업데이트 시에도 처리 필요)
        checkup_data = validated_data.pop('checkup', None)
        
        # 2. PetEvent 객체 업데이트
        instance = super().update(instance, validated_data)
        
        # 3. checkup 객체 업데이트 또는 생성
        if checkup_data:
            # checkup이 이미 존재하는 경우 업데이트
            if hasattr(instance, 'checkup'):
                checkup_instance = instance.checkup
                for key, value in checkup_data.items():
                    setattr(checkup_instance, key, value)
                checkup_instance.save()
            # checkup이 없으면 새로 생성 (이벤트 타입이 CHECKUP인지 확인해야 함)
            elif instance.event_type == 'CHECKUP':
                PetCheckup.objects.create(event=instance, **checkup_data)
            
        return instance
