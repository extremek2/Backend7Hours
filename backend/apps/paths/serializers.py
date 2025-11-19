from rest_framework import serializers
from .models import Path


class CoordSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    # z는 서버에서 채움, 클라이언트는 보내지 않아도 됨

class UserPathCreateSerializer(serializers.Serializer):
    path_name = serializers.CharField(required=False, allow_blank=True)
    path_comment = serializers.CharField(required=False, allow_blank=True)
    level = serializers.IntegerField(required=False, default=2)
    distance = serializers.FloatField(required=False)
    coords = CoordSerializer(many=True)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    duration = serializers.IntegerField(required=False)
    thumbnail = serializers.CharField(required=False, allow_blank=True)
    is_private = serializers.BooleanField(required=False, default=False)

class UserPathUpdateSerializer(serializers.ModelSerializer):
    # distance = serializers.SerializerMethodField()

    class Meta:
        model = Path
        fields = ["path_name", "path_comment", "level", "distance", "duration", "thumbnail", "is_private"]

class PathSerializer(serializers.ModelSerializer):
    
    auth_user_nickname = serializers.CharField(source='auth_user.nickname', read_only=True)
    coords = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Path
        fields = [
            "id", "source", "path_name", "path_comment", "level",
            "distance", "duration", "is_private", "thumbnail", "coords", "auth_user_nickname"
        ]

    def get_coords(self, obj):
        if getattr(obj, "geom", None) is None:
            return []
        return [
            {"lat": pt[1], "lng": pt[0], "z": pt[2] if len(pt) > 2 else 0}
            for pt in obj.geom
        ]

    def get_distance(self, obj):
        # annotate(distance_m=Distance(...))에서 주입된 거리값 사용
        distance_m = getattr(obj, "distance_m", None)
        if distance_m is not None:
            # annotate로 Distance 객체일 수도, float일 수도 있음
            try:
                return round(distance_m.m, 2)
            except AttributeError:
                return float(distance_m)
        
        
        # 2. distance_m이 없으면 모델의 distance 필드 사용 (POST/PATCH 요청용)
        if obj.distance is not None:
            return float(obj.distance)
        
        return 0.0