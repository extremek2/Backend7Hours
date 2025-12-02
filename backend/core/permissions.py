from rest_framework.permissions import BasePermission
class IsAuthorOrReadOnly(BasePermission):
    """
    읽기: 모두 허용
    수정/삭제: 작성자만 가능
    """
    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        
        # Comment인지 Post인지에 따라 작성자 필드 다름
        if hasattr(obj, 'auth_user'):
            return obj.auth_user == request.user
        elif hasattr(obj, 'author'):
            return obj.author == request.user
        
        return False  # 작성자 필드가 없으면 기본적으로 거부