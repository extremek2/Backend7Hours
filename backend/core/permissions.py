from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    읽기: 모두 허용
    수정/삭제: 작성자만 가능
    """
    def has_object_permission(self, request, view, obj):
        # SAFE METHODS → GET, HEAD, OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True

        # 수정/삭제 요청 시 작성자만 허용
        return obj.author == request.user