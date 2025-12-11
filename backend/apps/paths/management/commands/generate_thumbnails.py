from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
from django.core.files.base import ContentFile

from apps.paths.models import Path
from apps.paths.renderers import render_with_naver_api, render_with_contextily
from apps.paths.utils import GisUtils
from apps.paths.tasks import render_path  # wrapper 사용 권장

import traceback


class Command(BaseCommand):
    help = "DB에 저장된 Path 객체들을 순회하며 설정된 렌더러를 사용하여 썸네일을 생성합니다."

    def handle(self, *args, **options):

        # 설정에서 렌더링 엔진 선택 (기본값: 'CONTEXTILY')
        RENDER_ENGINE = getattr(settings, 'PATH_RENDER_ENGINE', 'CONTEXTILY').upper()

        # 사용 렌더러 표시
        self.stdout.write(self.style.NOTICE(f"[CONFIG] 썸네일 렌더링 엔진: {RENDER_ENGINE}"))

        # 대상 Path 가져오기 (썸네일 비어있는 경우만)
        paths = Path.objects.filter(
            Q(thumbnail__isnull=True) | Q(thumbnail__exact='')
        )
        total = paths.count()

        self.stdout.write(self.style.SUCCESS(f"[START] 총 {total}개의 Path 처리 시작"))

        # ----------------------------------------------------
        # 기존 render_with_contextily/render_with_naver_api 직접 호출을 제거
        # wrapper(render_path) 사용하여 일관성 유지
        # ----------------------------------------------------

        for idx, path_obj in enumerate(paths, start=1):
            try:
                self.stdout.write(f"[{idx}/{total}] Path ID {path_obj.id} 처리 중...")

                # 1. 렌더링 수행
                # render_path()는 PATH_RENDER_ENGINE에 따라 적절한 엔진 사용
                img_bytes = render_path(path_obj)

                if img_bytes is None:
                    raise ValueError("렌더링 결과가 None입니다. 이미지 생성 실패.")

                # 2. ImageField에 저장
                filename = f"path_{path_obj.id}_thumbnail.png"
                path_obj.thumbnail.save(
                    filename,
                    ContentFile(img_bytes.getvalue()),
                    save=True
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f" → Path {path_obj.id} 썸네일 생성 완료 (Engine: {RENDER_ENGINE})"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f" → ERROR (Path ID {path_obj.id}): {str(e)}"
                    )
                )
                traceback.print_exc()

        self.stdout.write(self.style.SUCCESS("[DONE] 모든 썸네일 처리 완료"))
