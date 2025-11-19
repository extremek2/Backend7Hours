import os
from storages.backends.s3boto3 import S3Boto3Storage

# S3Boto3Storage를 상속받아 MinIO 접속 정보를 공유
# 기본 경로는 {bucket_name}/{}
# bucket_name만 환경 변수를 사용하여 개별적으로 정의
# location 기본값은 settings.py의 AWS_LOCATION='media'
# 나머지 location 추가는 각 모델의 이미지 필드에서 재정의 (media/{location}/)

class UsersStorage(S3Boto3Storage):
    # users 관련 모델의 저장경로(users/media/)
    bucket_name = os.environ.get('MINIO_USERS_BUCKET')

class PetsStorage(S3Boto3Storage):
    # Pets 관련 모델의 저장경로(pets/media/)
    bucket_name = os.environ.get('MINIO_PETS_BUCKET')

class PathsStorage(S3Boto3Storage):
    # Paths 관련 모델의 저장경로(paths/media/)
    bucket_name = os.environ.get('MINIO_PATHS_BUCKET')

class PlacesStorage(S3Boto3Storage):
    # Places 관련 모델의 저장경로(places/media/)
    bucket_name = os.environ.get('MINIO_PLACES_BUCKET')

class PostsStorage(S3Boto3Storage):
    # Posts 관련 모델의 저장경로(places/media/)
    bucket_name = os.environ.get('MINIO_POSTS_BUCKET')