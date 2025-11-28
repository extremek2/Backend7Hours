from rest_framework import serializers
from .models import Bookmark, Comment
from apps.users.serializers import UserSerializer
from apps.paths.models import Path
from apps.posts.models import Post


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
            from apps.paths.serializers import PathSerializer
            data = PathSerializer(obj.content_object, context=self.context).data
            content_type_name = 'PATH' # DTO의 override val type과 일치
        elif isinstance(obj.content_object, Post):
            from apps.posts.serializers import PostListSerializer
            data = PostListSerializer(obj.content_object, context=self.context).data
            content_type_name = 'POST' # DTO의 override val type과 일치
        
        if data is not None:
            # 직렬화된 데이터에 타입 이름 필드를 추가합니다.
            data['type'] = content_type_name
            # Moshi는 'id' 필드를 BookmarkedObject 인터페이스에서 요구하므로, 
            # 내부 Serializer가 반드시 'id'를 출력해야 합니다.
            if 'id' not in data:
                            data['id'] = obj.content_object.pk
        # 다른 타입의 객체가 추가될 경우를 대비
        return data


# 댓글에 사용할 작성자 필드 재정의
class AuthorNestedSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ['id', 'nickname']

# 댓글 전용
class CommentSerializer(serializers.ModelSerializer):
    """
    어떤 모델이든 댓글 객체를 직렬화하는 범용 Serializer
    """
    author = AuthorNestedSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'created_at']