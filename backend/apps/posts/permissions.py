from rest_framework.permissions import BasePermission

class IsOwnerOrReadOnly(BasePermission):
    """
    객체의 작성자(auth_user)만 수정/삭제 가능
    """
    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return obj.auth_user == request.user