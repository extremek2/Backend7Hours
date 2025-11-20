from rest_framework import serializers
from .models import Post

class PostSerializer(serializers.ModelSerializer):
    auth_user = serializers.ReadOnlyField(source='auth_user.id')
    
    # count 필드
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    bookmarks_count = serializers.IntegerField(source='bookmarks.count', read_only=True)
    
    # 상태 필드
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'auth_user', 'post_type', 'title', 'content', 'image',
            'created_at', 'updated_at',
            'comments_count', 'likes_count', 'bookmarks_count',
            'is_liked', 'is_bookmarked',
        ]
        read_only_fields = (
            'created_at', 'updated_at',
            'comments_count', 'likes_count', 'bookmarks_count',
            'is_liked', 'is_bookmarked',
        )

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.bookmarks.filter(user=request.user).exists()

    # image 필드의 URL을 반환하도록 설정할 수도 있습니다.
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     if instance.image:
    #         representation['image_url'] = instance.image.url
    #     return representation