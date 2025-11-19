import os
import uuid


class UploadFilePathGenerator:
    def __init__(self, path, user_field='user'):
        """
        Args:
            path: 기본 업로드 경로
            user_field: user_id를 가져올 필드명 (기본: 'user')
        """
        self.path = path
        self.user_field = user_field

    def __call__(self, instance, filename):
        # 1. 고유 파일명 생성
        ext = os.path.splitext(filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        
        # 2. user_id 추출
        user_id = self._get_user_id(instance)
        
        # 3. 경로 생성: path/user_id/filename
        return os.path.join(self.path, str(user_id), unique_filename)
    
    def _get_user_id(self, instance):
        """인스턴스에서 user_id를 추출"""
        try:
            # user_field 경로를 따라가기 (예: 'post.author')
            obj = instance
            for attr in self.user_field.split('.'):
                obj = getattr(obj, attr)
            
            # ForeignKey 객체면 .id 추출, 아니면 그대로 반환
            return obj.id if hasattr(obj, 'id') else obj
            
        except (AttributeError, TypeError):
            return 'public'
    
    def deconstruct(self):
        path = f'{self.__class__.__module__}.{self.__class__.__qualname__}'
        args = (self.path,)
        kwargs = {}
        
        # 기본값과 다르면 kwargs에 추가
        if self.user_field != 'user':
            kwargs['user_field'] = self.user_field
        
        return path, args, kwargs