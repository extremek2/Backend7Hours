from rest_framework import serializers
from .models import Path

class CoordSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    # z는 서버에서 채움, 클라이언트는 보내지 않아도 됨

class UserPathCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    path_name = serializers.CharField(required=False, allow_blank=True)
    path_comment = serializers.CharField(required=False, allow_blank=True)
    coords = CoordSerializer(many=True)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    duration = serializers.IntegerField(required=False)

class PathSerializer(serializers.ModelSerializer):
    coords = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Path
        fields = [
            "id", "path_name", "path_comment", "level",
            "distance", "duration", "is_private", "thumbnail", "coords"
        ]

    def get_coords(self, obj):
        if not obj.geom:
            return []
        return [
            {"lat": pt[1], "lng": pt[0], "z": pt[2] if len(pt) > 2 else 0}
            for pt in obj.geom
        ]

    def get_distance(self, obj):
        # annotate(distance_m=Distance(...))에서 주입된 거리값 사용
        distance_m = getattr(obj, "distance_m", None)
        if distance_m is not None:
            return round(distance_m.m, 2)  # m 단위로 반환
        return None