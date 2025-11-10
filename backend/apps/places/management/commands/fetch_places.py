from django.core.management.base import BaseCommand
from apps.places.services import fetch_kcisa_places, save_kcisa_to_place
from apps.places.services import fetch_ktour_places, save_ktour_to_place

class Command(BaseCommand):
    help = "KCISA 및 KTOUR API에서 장소 데이터를 가져와 Place 모델에 저장합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            '--kcisa',
            action='store_true',
            help='KCISA 데이터만 가져오기'
        )
        parser.add_argument(
            '--ktour',
            action='store_true',
            help='KTOUR 데이터만 가져오기'
        )
        parser.add_argument(
            '--num',
            type=int,
            default=1000,
            help='API 호출 시 가져올 데이터 수 (기본 1000)'
        )

    def handle(self, *args, **options):
        num = options['num']

        # 기본: 둘 다 가져오기
        if options['kcisa'] or not (options['kcisa'] or options['ktour']):
            self.stdout.write("KCISA 데이터 가져오는 중...")
            rows = fetch_kcisa_places(numOfRows=num)
            save_kcisa_to_place(rows)
            self.stdout.write(self.style.SUCCESS(f"KCISA 데이터 저장 완료: {len(rows)}개"))

        if options['ktour'] or not (options['kcisa'] or options['ktour']):
            self.stdout.write("KTOUR 데이터 가져오는 중...")
            rows = fetch_ktour_places(numOfRows=num)
            save_ktour_to_place(rows)
            self.stdout.write(self.style.SUCCESS(f"KTOUR 데이터 저장 완료: {len(rows)}개"))
