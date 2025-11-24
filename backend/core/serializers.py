from rest_framework import serializers

from core.models import Bookmark, Comment
from apps.paths.models import Path
from apps.posts.models import Post
from apps.paths.serializers import PathSerializer, AuthorSerializer, BookmarkedPathSerializer
from apps.posts.serializers import PostSerializer


class BookmarkSerializer(serializers.ModelSerializer):
    """
    어떤 모델이든 즐겨찾기 객체를 직렬화하는 범용 Serializer.
    `content_object`의 실제 타입에 따라 다른 Serializer를 동적으로 사용합니다.
    """
    bookmarked_object = serializers.SerializerMethodField()

    class Meta:
        model = Bookmark
        fields = ['id', 'created_at', 'bookmarked_object']

    def get_bookmarked_object(self, obj):
        """
        `content_object`의 타입에 따라 적절한 Serializer를 선택하여 직렬화하고,
        Moshi가 타입을 식별할 수 있도록 'content_type_name' 필드를 추가합니다. 
        """
        data = None
        content_type_name = None

        if isinstance(obj.content_object, Path):
            # context를 전달하여 PathSerializer 내부에서 request 객체 등에 접근할 수 있도록 함
            data = PathSerializer(obj.content_object, context=self.context).data
            content_type_name = 'path'
        if isinstance(obj.content_object, Post):
            data = PostSerializer(obj.content_object, context=self.context).data
            content_type_name
        
        if data is not None:
            # 직렬화된 데이터에 타입 이름 필드를 추가합니다.
            data['content_type_name'] = content_type_name

        # 다른 타입의 객체가 추가될 경우를 대비
        return data

class CommentSerializer(serializers.ModelSerializer):
    """
    어떤 모델이든 댓글 객체를 직렬화하는 범용 Serializer.
    """
    author = AuthorSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'created_at']
