# 🐍 Python 3.11 슬림 버전 (가볍고 빠름)
FROM python:3.11-slim

# 1. 파이썬 로그가 버퍼링 없이 바로 출력되도록 설정
ENV PYTHONUNBUFFERED=1

# 2. 작업 폴더 설정
WORKDIR /app

# 3. 🌍 GeoDjango 필수 시스템 패키지 설치 (여기가 에러 났던 부분 수정)
# - binutils, libproj-dev, gdal-bin: 지도 데이터 처리용
# - netcat-openbsd: DB 연결 대기용 (entrypoint.sh에서 사용)
# - python3-gdal 등 충돌나는 패키지는 제거함
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    netcat-openbsd \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 4. 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 복사
COPY . .

# 6. 실행 권한 부여 (윈도우에서 넘어온 파일 호환성 해결)
COPY entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# 7. 실행 명령
ENTRYPOINT ["./entrypoint.sh"]
