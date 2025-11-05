from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 owner 필드가 요청하는 사용자(request.user)와 일치할 때만 
    수정/삭제 권한을 허용하고, 그 외에는 읽기(GET, HEAD, OPTIONS)만 허용합니다.
    """
    def has_object_permission(self, request, view, obj):
        # 읽기 권한은 항상 허용 (안드로이드의 'home'이나 'community'에서 타인의 정보를 볼 수 있도록)
        if request.method in permissions.SAFE_METHODS:
            return True

        # 쓰기(PUT, POST, PATCH, DELETE) 권한은 객체의 소유자에게만 허용
        # obj.owner는 Pet 모델의 owner 필드입니다.
        return obj.owner == request.user