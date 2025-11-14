from rest_framework import serializers
from .models import Place
from core.models import Category

class CategorySerializer(serializers.ModelSerializer):
    # 상위 카테고리 정보 (1계층 출력 시 2계층까지, 2계층 출력 시 1계층까지 접근 가능)
    # parent 필드는 Category 객체 자체를 참조합니다.
    parent_category = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'parent_category']
        # 'parent'는 ID로 출력됨 (기본 동작)

    # parent 객체의 상세 정보(이름)를 얻기 위한 메서드
    def get_parent_category(self, obj):
        # Category 객체에 parent가 있는 경우에만 상세 정보를 재귀적으로 출력합니다.
        # 주의: 이 시리얼라이저가 무한 재귀에 빠지는 것을 방지하기 위해 
        # depth를 제한하거나 (CategorySerializer(obj.parent)) 이처럼 이름만 추출합니다.
        if obj.parent:
            # 여기서는 부모의 이름과 ID만 출력하도록 간단하게 처리합니다.
            return {
                'id': obj.parent.id,
                'name': obj.parent.name
            }
        return None


class PlaceSerializer(serializers.ModelSerializer):
    # CategorySerializer와 distance 필드는 유지
    category = CategorySerializer(read_only=True)
    distance = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Place
        fields = [
            'id', 'title', 'tel', 'address', 'coordinates',
            'source', 'is_active',
            'category',
            'created_at', 'updated_at',
            'distance' 
        ]

    def get_distance(self, obj):
        # distance가 annotate로 붙어있으면 meters로 반환
        if hasattr(obj, 'distance') and obj.distance is not None:
            return float(obj.distance.m)  # meters 단위
        return None