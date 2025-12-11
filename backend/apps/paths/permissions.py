from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 소유자에게만 쓰기 권한을 부여하는 커스텀 권한.
    읽기 권한은 모두에게 허용됩니다.
    """
    def has_object_permission(self, request, view, obj):
        # GET, HEAD, OPTIONS 요청과 같은 안전한 메소드는 항상 허용
        if request.method in permissions.SAFE_METHODS:
            return True

        # 쓰기 권한은 객체의 'author' 또는 'user'가 요청한 사용자와 동일한 경우에만 허용
        # Comment 모델은 'author', Bookmark/Like 모델은 'user' 필드를 사용
        if hasattr(obj, 'auth_user'):
            return obj.auth_user == request.user
        if hasattr(obj, 'author'):
            return obj.author == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
            
        return False