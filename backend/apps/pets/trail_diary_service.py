from django.db import transaction
from apps.pets.models import PetEvent, PetTrail

class TrailDiaryService:

    @staticmethod
    @transaction.atomic
    def create_trail_diary(
        *,
        pet_event: PetEvent,
        path_id: int | None = None,
        path_name: str | None = None,
        distance: float,
        duration: int,
    ) -> PetTrail:
        """
        TRAIL_DIARY 이벤트 생성 후
        - PetTrail 생성
        - AI 파이프라인 트리거
        """

        trail = PetTrail.objects.create(
            event=pet_event,
            path_id=path_id,
            path_name=path_name,
            distance=distance,
            duration=duration,
        )

        def on_commit():
            from .tasks import generate_trail_diary
            generate_trail_diary.delay(trail.id)

        transaction.on_commit(on_commit)

        return trail