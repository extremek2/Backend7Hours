from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체에 대한 읽기 권한은 모두에게 허용하며, 
    쓰기 권한은 해당 객체의 소유자에게만 허용합니다.
    (obj.owner 필드를 확인합니다.)
    """

    def has_object_permission(self, request, view, obj):
        # 1. 읽기 권한 (GET, HEAD, OPTIONS)은 항상 허용합니다.
        if request.method in permissions.SAFE_METHODS:
            return True

        # 2. 쓰기 권한 (PUT, PATCH, DELETE)은 소유자에게만 허용합니다.
        # 요청 사용자가 객체의 'owner' 필드와 일치하는지 확인합니다.
        # obj는 Pet 인스턴스 또는 PetEvent 인스턴스가 될 수 있습니다.
        
        # Pet 객체의 경우
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        # PetEvent 객체의 경우 (Pet Event의 소유권은 Pet의 owner를 따름)
        if hasattr(obj, 'pet'):
            return obj.pet.owner == request.user
            
        # PetCheckup 객체의 경우 (PetEvent를 거쳐 소유권을 확인)
        if hasattr(obj, 'event') and hasattr(obj.event, 'pet'):
            return obj.event.pet.owner == request.user

        # 해당 필드가 없는 경우 (혹은 예상치 못한 객체)는 기본적으로 거부
        return False