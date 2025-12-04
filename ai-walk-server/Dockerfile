# 베이스 이미지
FROM python:3.12-slim

# 작업 디렉토리
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Python 의존성 먼저 설치 (캐시 최적화)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# 코드 복사
COPY . /app/

# 엔트리포인트 스크립트 실행 권한 부여
RUN chmod +x /app/entrypoint.diary.sh

# 엔트리포인트 실행
ENTRYPOINT ["./entrypoint.diary.sh"]