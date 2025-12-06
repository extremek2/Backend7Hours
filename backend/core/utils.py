import os
import uuid
from urllib.parse import urlparse
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# MINIO에 이미지 URL 등록
class UploadFilePathGenerator:
    def __init__(self, path, user_field=None):
        """
        Args:
            path: 기본 업로드 경로
            user_field: user_id를 가져올 필드명
                        - ForeignKey가 있는 모델: 'auth_user' 등
                        - User 자신: None 또는 'self'
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
        # User 자신인 경우
        if self.user_field is None or self.user_field == 'self':
            return getattr(instance, 'id', None)
        
        # ForeignKey 경로를 따라가서 id 추출
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
    
def parse_minio_url(minio_url: str):
    """
    MinIO URL을 파싱하여 bucket_name과 object_name 추출
    
    예시:
    http://some_domain:9000/my-bucket/path/to/file.png
    -> bucket_name: 'my-bucket'
    -> object_name: 'path/to/file.png'
    """
    logger.info(f"Parsing MinIO URL: {minio_url}")
    if not minio_url:
        return None, None
        
    try:
        logger.info(f"Parsing MinIO URL: {minio_url}")
        parsed = urlparse(minio_url)
        print(f"Parsed URL: {parsed}")
        path_parts = parsed.path.lstrip('/').split('/', 1)
        print(f"Path parts: {path_parts}")
        
        if len(path_parts) == 2:
            logger.debug(f"Parsed bucket: {path_parts[0]}, object: {path_parts[1]}")
            bucket_name = path_parts[0]
            object_name = path_parts[1]
            return bucket_name, object_name
    except Exception as e:
        logger.error(f"Error parsing MinIO URL '{minio_url}': {e}")

    return None, None

def get_presigned_url(minio_url: str, expires_days=7):
    """
    전체 MinIO URL을 받아 Pre-signed URL을 생성
    """
    print(f"Generating presigned URL for: {minio_url}")
    if not minio_url:
        return None

    bucket_name, object_name = parse_minio_url(minio_url)
    
    if not bucket_name or not object_name:
        logger.warning(f"Could not parse bucket/object name from URL: {minio_url}")
        return minio_url # 파싱 실패 시 원본 URL 반환
    
    try:
        # settings.MINIO_CLIENT를 사용하여 presigned URL 생성
        url = settings.MINIO_CLIENT.presigned_get_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(days=expires_days)
        )
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL for '{object_name}' in bucket '{bucket_name}': {e}")
        return minio_url # 에러 발생 시 원본 URL 반환
