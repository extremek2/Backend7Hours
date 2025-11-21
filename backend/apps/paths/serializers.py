from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Path
from core.models import Comment, Bookmark


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

# 댓글 작성자 정보 Serializer
class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'nickname']

# 댓글 Serializer
class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'created_at']

class PathSerializer(serializers.ModelSerializer):
    
    auth_user_nickname = serializers.CharField(source='auth_user.nickname', read_only=True)
    coords = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    
    # Nested Serializer로 댓글 목록 추가
    comments = CommentSerializer(many=True, read_only=True)
    
    # 즐겨찾기 관련 필드 추가
    bookmarks_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Path
        fields = [
            "id", "source", "path_name", "path_comment", "level",
            "distance", "duration", "is_private", "thumbnail", "coords", 
            "auth_user_nickname", "comments", "bookmarks_count", "is_bookmarked"
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

    def get_bookmarks_count(self, obj):
        # ViewSet에서 annotate로 전달된 값을 사용하는 것이 효율적
        return getattr(obj, 'bookmarks_count', obj.bookmarks.count())

    def get_is_bookmarked(self, obj):
        # ViewSet에서 annotate로 전달된 값을 사용하는 것이 효율적
        is_bookmarked = getattr(obj, 'is_bookmarked', None)
        if is_bookmarked is not None:
            return is_bookmarked
        
        # annotate가 없을 경우 수동으로 확인 (비효율적일 수 있음)
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return obj.bookmarks.filter(user=user).exists()
        return False

class BookmarkedPathSerializer(serializers.ModelSerializer):
    auth_user_nickname = serializers.CharField(source='auth_user.nickname', read_only=True)
    distance = serializers.SerializerMethodField()
    bookmarks_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Path
        fields = [
            "id", "source", "path_name", "path_comment", "level",
            "distance", "duration", "is_private", "thumbnail",
            "auth_user_nickname", "bookmarks_count", "is_bookmarked"
        ]

    def get_distance(self, obj):
        distance_m = getattr(obj, "distance_m", None)
        if distance_m is not None:
            try:
                return round(distance_m.m, 2)
            except AttributeError:
                return float(distance_m)
        if obj.distance is not None:
            return float(obj.distance)
        return 0.0

    def get_bookmarks_count(self, obj):
        return getattr(obj, 'bookmarks_count', obj.bookmarks.count())

    def get_is_bookmarked(self, obj):
        is_bookmarked = getattr(obj, 'is_bookmarked', None)
        if is_bookmarked is not None:
            return is_bookmarked
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return obj.bookmarks.filter(user=user).exists()
        return False