import requests
from celery import shared_task
from django.conf import settings
from apps.pets.models import PetTrail
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=30, retry_kwargs={'max_retries': 3})
def generate_trail_diary(self, trail_id: int):
    try:
        trail = PetTrail.objects.get(id=trail_id)
    except PetTrail.DoesNotExist:
        logger.warning(f"PetTrail {trail_id} not found")
        return f"PetTrail {trail_id} not found"

    payload = {
        "distance": trail.distance,
        "duration": trail.duration,
        "pathName": trail.path_name,  # 클라이언트 key와 맞춤
    }

    try:
        response = requests.post(
            f"{settings.AI_DIARY_SERVER_URL}/generate-diary",
            json=payload,
            timeout=180
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call AI server for trail {trail_id}: {e}")
        raise self.retry(exc=e)

    diary = response.json().get("diary")
    if not diary:
        raise ValueError(f"AI diary empty for trail {trail_id}")

    trail.ai_summary = diary
    trail.ai_generated = True
    trail.save(update_fields=["ai_summary", "ai_generated"])
    logger.info(f"AI diary generated for trail {trail_id}")
