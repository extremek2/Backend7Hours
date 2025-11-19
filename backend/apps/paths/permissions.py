from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `auth_user` attribute.
    Read permissions are allowed to any request.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the path.
        # The object must have an owner, and the owner must be the request user.
        # if obj.source != 'USER':
        #     return False # 사용자가 생성한 경로가 아니면 수정/삭제 불가
        print(f"obj.auth_user: {obj.auth_user}, request.user: {request.user}")
        return obj.auth_user and obj.auth_user == request.user
