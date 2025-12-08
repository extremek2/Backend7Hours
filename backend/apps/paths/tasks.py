import io
import logging

from functools import lru_cache
from celery import shared_task
from minio import Minio
from minio.error import S3Error 

from django.conf import settings 
from django.db import connection
from django.core.files.base import ContentFile

from .models import Path
from .utils import GisUtils
from shapely.geometry import LineString
from .renderers import render_with_naver_api, render_with_contextily , render_polyline_on_static_map

# --------------------------------------------------------------------------
# THUMBNAIL_RENDER_CONFIG 단일 변수로 추출
# --------------------------------------------------------------------------
CONFIG = settings.THUMBNAIL_RENDER_CONFIG

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
    CDN이 설정되어 있으면 CDN URL을, 아니면 직접 엔드포인트 URL을 반환합니다
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

# --------------------------------------------------------------------------
# Wrapper: PATH_RENDER_ENGINE 기준으로 렌더러 선택
# --------------------------------------------------------------------------
def render_path(path_obj) -> io.BytesIO:
    """
    PATH_RENDER_ENGINE에 따라 자동으로 렌더러를 호출하고 BytesIO 이미지 반환
    """
    engine = getattr(settings, 'PATH_RENDER_ENGINE', 'CONTEXTILY')
    
    if engine == 'NAVER':
        # 네이버 API 렌더링 + Polyline 합성
        img_bg = render_with_naver_api(path_obj)
        path_coords = [(c[1], c[0]) for c in path_obj.geom.coords]
        center_lng, center_lat, zoom_level = GisUtils.calculate_map_center_and_zoom(path_obj.geom)
        return render_polyline_on_static_map(
            static_map_img=img_bg,
            path_coords=path_coords,
            center_lat=center_lat,
            center_lng=center_lng,
            zoom=zoom_level
        )
    
    # 기본: CONTEXTILY
    return render_with_contextily(path_obj)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def render_path_and_upload(self, path_id):
    """
    Path 객체의 썸네일 이미지를 렌더링하고 ImageField에 저장
    """
    logger.info(f"STARTING render_path_and_upload for path_id {path_id} (Attempt {self.request.retries + 1})")

    # DB 연결 상태 확인
    if connection.connection and not connection.is_usable():
        connection.close()
    
    try:
        path_obj = Path.objects.get(pk=path_id)
        
        # ----------------------------------------------------------------------
        # 1. 경로 렌더링
        # ----------------------------------------------------------------------
        img_data = render_path(path_obj)
        if not img_data:
            logger.error(f"Renderer returned no image data for path {path_id}")
            return "Error: No image data generated"
        
        # ----------------------------------------------------------------------
        # 2. ImageField 저장
        # ----------------------------------------------------------------------
        file_name = f"path_{path_obj.id}.png"
        path_obj.thumbnail.save(
            file_name,
            ContentFile(img_data.getvalue()),
            save=False
        )
        # thumbnail 이름은 저장되었으므로 DB에 직접 반영
        path_obj.save(update_fields=['thumbnail'])
        logger.info(f"Successfully saved thumbnail for path_id {path_id}")
        return f"Success: {file_name}"
    
    except Path.DoesNotExist:
        logger.warning(f"Path with id={path_id} does not exist")
        return f"Error: Path {path_id} not found"
    
    except S3Error as e:
        logger.error(
            f"S3 error for path {path_id} (attempt {self.request.retries + 1}/{self.max_retries}): {e}",
            exc_info=True
        )
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=e, countdown=countdown)
    
    except Exception as e:
        logger.error(
            f"Unexpected error for path {path_id} (attempt {self.request.retries + 1}/{self.max_retries}): {e}",
            exc_info=True
        )
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=e, countdown=countdown)


@shared_task
def calculate_path_metrics_and_update(path_id):
    
    from apps.paths.dem_utils import get_dem
    
    """
    Path metrics 계산 및 업데이트 (DEM 기반, z값 null 처리 가능)
    """
    try:
        path = Path.objects.get(id=path_id)

        if not path.geom:
            logger.warning(f"[Metrics] Path {path_id} has no geometry.")
            return {"status": "failed", "reason": "No geometry to calculate."}

        # DEM 인스턴스
        dem = get_dem()

        # 3D 좌표 추가 (z값 null/0 가능)
        geom_3d = dem.add_elevation_to_linestring(path.geom)
        path.geom = geom_3d

        # 난이도 계산
        level = dem.estimate_difficulty_level(geom_3d)
        path.level = level

        # 로깅으로 확인
        logger.info(f"[Metrics] Path {path_id} geom.z sample: {[pt[2] for pt in geom_3d.coords[:5]]}")
        logger.info(f"[Metrics] Path {path_id} calculated level: {level}")

        # DB 반영
        Path.objects.filter(id=path_id).update(
            geom=geom_3d,
            level=level
        )

        return {"status": "completed", "updated_fields": ['geom', 'level']}

    except Path.DoesNotExist:
        logger.warning(f"[Metrics] Path {path_id} not found.")
        return {"status": "failed", "reason": f"Path {path_id} not found."}
    except Exception as e:
        logger.error(f"[Metrics] Calculation failed for Path {path_id}: {e}", exc_info=True)
        raise
