import io
import logging
import matplotlib.pyplot as plt
import geopandas as gpd
from celery import shared_task
from functools import lru_cache
from minio import Minio
from minio.error import S3Error 

from django.conf import settings 
from django.db import connection

from .models import Path 

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_minio_client():
    """
    MinIO 클라이언트를 캐싱하여 재사용합니다.
    Celery Worker 프로세스당 하나의 클라이언트 인스턴스만 유지합니다.
    """
    try:
        return Minio(
            endpoint=settings.AWS_S3_ENDPOINT_URL,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            secure=settings.AWS_S3_SECURE_URLS,
        )
    except Exception as e:
        logger.critical(f"Failed to initialize MinIO client: {e}", exc_info=True)
        raise

def build_image_url(bucket_name: str, object_name: str) -> str:
    """
    MinIO/S3 이미지 URL을 생성합니다.
    CDN이 설정되어 있으면 CDN URL을, 아니면 직접 엔드포인트 URL을 반환합니다.
    """
    domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)
    
    if domain:
        # CDN 사용
        scheme = getattr(settings, 'AWS_S3_SCHEME', 'https')
        return f"{scheme}://{domain}/{bucket_name}/{object_name}"
    
    # 직접 연결
    endpoint = settings.AWS_S3_ENDPOINT_URL
    clean_endpoint = endpoint.replace('http://', '').replace('https://', '')
    scheme = 'https' if settings.AWS_S3_SECURE_URLS else 'http'
    
    return f"{scheme}://{clean_endpoint}/{bucket_name}/{object_name}"

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def render_path_and_upload(self, path_id):
    """
    Path 객체의 썸네일 이미지를 렌더링하고 MinIO에 업로드합니다.
    
    Args:
        path_id (int): Path 모델의 Primary Key
        
    Returns:
        str: 성공/실패 메시지
        
    Raises:
        Retry: 재시도 가능한 오류 발생 시
    """
    # DB 연결 상태 확인
    if connection.connection and not connection.is_usable():
        connection.close()
    
    try:
        # 1. Path 객체 조회
        path_obj = Path.objects.get(pk=path_id)
        
        # 2. GeoDataFrame 생성 및 렌더링
        gdf = gpd.GeoDataFrame(
            [{'id': path_obj.id}], 
            geometry=[path_obj.geom], 
            crs=path_obj.geom.crs
        )
        
        fig, ax = plt.subplots(figsize=(6, 6))
        gdf.plot(ax=ax, linewidth=2, color='blue') 
        ax.set_axis_off()
        
        # 3. 이미지를 메모리에 저장
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png', bbox_inches='tight', transparent=True)
        plt.close(fig)  # 메모리 해제
        img_data.seek(0)
        
        # 4. MinIO에 업로드
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        object_name = f"{settings.AWS_LOCATION}/thumbnail/path_{path_obj.id}.png"
        
        minio_client = get_minio_client()
        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=img_data,
            length=img_data.getbuffer().nbytes,
            content_type="image/png"
        )
        
        # 5. 썸네일 URL 생성 및 DB 저장
        image_url = build_image_url(bucket_name, object_name)
        
        path_obj.thumbnail = image_url
        path_obj.save(update_fields=['thumbnail'])
        
        logger.info(f"Successfully uploaded thumbnail for path_id {path_id}")
        return f"Success: {object_name}"
        
    except Path.DoesNotExist:
        logger.warning(f"Path with id={path_id} does not exist")
        # 존재하지 않는 객체는 재시도 불필요
        return f"Error: Path {path_id} not found"
        
    except S3Error as e:
        logger.error(
            f"S3 error for path {path_id} (attempt {self.request.retries + 1}/{self.max_retries}): {e}",
            exc_info=True
        )
        # 지수 백오프 적용 (60초 → 120초 → 180초)
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=e, countdown=countdown)
        
    except Exception as e:
        logger.error(
            f"Unexpected error for path {path_id} (attempt {self.request.retries + 1}/{self.max_retries}): {e}",
            exc_info=True
        )
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=e, countdown=countdown)