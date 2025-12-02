from rest_framework.permissions import BasePermission

class IsOwnerOrReadOnly(BasePermission):
    """
    객체의 작성자(auth_user)만 수정/삭제 가능
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