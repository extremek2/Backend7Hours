from rest_framework import serializers
from .models import Place, Category1, Category2, Category3

class Category1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Category1
        fields = ['id', 'name']

class Category2Serializer(serializers.ModelSerializer):
    parent = Category1Serializer(read_only=True)
    class Meta:
        model = Category2
        fields = ['id', 'name', 'parent']

class Category3Serializer(serializers.ModelSerializer):
    parent = Category2Serializer(read_only=True)
    class Meta:
        model = Category3
        fields = ['id', 'name', 'parent']

class PlaceSerializer(serializers.ModelSerializer):
    category1 = Category1Serializer(read_only=True)
    category2 = Category2Serializer(read_only=True)
    category3 = Category3Serializer(read_only=True)
    distance = serializers.SerializerMethodField(read_only=True)  # 추가

    class Meta:
        model = Place
        fields = [
            'id', 'title', 'tel', 'address', 'coordinates',
            'source', 'is_active',
            'category1', 'category2', 'category3',
            'raw_data', 'created_at', 'updated_at',
            'distance'  # 추가
        ]

    def get_distance(self, obj):
        # distance가 annotate로 붙어있으면 meters로 반환
        if hasattr(obj, 'distance') and obj.distance is not None:
            return float(obj.distance.m)  # meters 단위
        return None