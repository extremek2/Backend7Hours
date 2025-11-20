# backend/apps/paths/tasks.py

import io
import matplotlib.pyplot as plt
import geopandas as gpd
from celery import shared_task

# 🔽 [1. 수정] 'MinIO'가 아니라 'Minio' 입니다.
from minio import Minio 

from django.conf import settings 
from .models import Path 

# MinIO 클라이언트 초기화
# 🔽 [2. 수정] 'MinIO'가 아니라 'Minio' 입니다.
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

@shared_task
def render_path_and_upload(path_id):
    """
    Path 객체의 ID를 받아 geom을 렌더링하고,
    그 이미지 URL을 'thumbnail' 필드에 저장합니다.
    """
    try:
        # 2. Path 모델로 객체 조회
        path_obj = Path.objects.get(pk=path_id)

        # 3. GeoDataFrame으로 변환 (렌더링 준비)
        gdf = gpd.GeoDataFrame([{'id': path_obj.id}], 
                               geometry=[path_obj.geom], 
                               crs=path_obj.geom.crs)
        
        # 4. 이미지 렌더링 (Matplotlib)
        fig, ax = plt.subplots(figsize=(6, 6)) # 썸네일용 사이즈
        gdf.plot(ax=ax, linewidth=2, color='blue') 
        ax.set_axis_off()

        # 5. 메모리 내 파일(BytesIO)로 저장
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png', bbox_inches='tight', transparent=True)
        img_data.seek(0)
        plt.close(fig)

        # 6. MinIO에 업로드
        bucket_name = settings.MINIO_BUCKET_NAME
        object_name = f"path_thumbnails/path_{path_obj.id}.png"
        data_length = img_data.getbuffer().nbytes

        minio_client.put_object(
            bucket_name,
            object_name,
            data=img_data,
            length=data_length,
            content_type="image/png"
        )
        
        # 7. Path 모델의 'thumbnail' 필드에 URL 업데이트
        image_url = f"https://{settings.MINIO_ENDPOINT}/{bucket_name}/{object_name}"
        path_obj.thumbnail = image_url
        path_obj.save(update_fields=['thumbnail']) # thumbnail 필드만 저장

        return f"Success: Uploaded {object_name} for path_id {path_id}"

    except Path.DoesNotExist:
        return f"Error: Path with id={path_id} does not exist."
    except Exception as e:
        return f"Error: {str(e)}"