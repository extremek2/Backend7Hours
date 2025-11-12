from django.core.management.base import BaseCommand
from apps.paths.services import PathService
import time # time 모듈 추가

class Command(BaseCommand):
    help = "두루누비 API에서 경로 데이터를 가져와 Path 모델에 저장합니다."

    def handle(self, *args, **options):
        # ------------------------------------
        # 1. 시작 시간 기록
        start_time = time.time() 
        # ------------------------------------
        
        # 샘플 위치/반경(m)
        lat, lng = 37.5665, 126.9780
        radius_m = 50000

        # DB에 존재하면 가져오고, 없으면 API 호출 후 admin_user로 저장
        paths = PathService.get_or_create_paths(lat, lng, radius_m)

        # ------------------------------------
        # 2. 종료 시간 기록 및 시간 계산
        end_time = time.time()
        duration = end_time - start_time
        # ------------------------------------
        
        # 3. 결과 출력 시 실행 시간 포함
        self.stdout.write(self.style.SUCCESS(
            f"{lat}, {lng} 근처 경로 {len(paths)}개 저장 완료"
        ))
        
        self.stdout.write(self.style.NOTICE(
            f"총 실행 시간: {duration:.4f} 초" # 소수점 4자리까지 출력
        ))