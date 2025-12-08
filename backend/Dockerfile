# Python 기반 이미지
FROM python:3.11-slim

# 환경 변수
ENV PYTHONUNBUFFERED 1

# 작업 디렉토리
WORKDIR /app

# 패키지 설치를 위한 기본 유틸
RUN apt-get update && apt-get install -y \
    # 빌드 도구
    build-essential \
    binutils \
    pkg-config \
    # 네트워크 도구
    wget \
    curl \
    netcat-openbsd \
    # GDAL 및 GIS 라이브러리
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    # elevation 패키지 의존성
    make \
    unzip \
    # 이미지 최적화: 캐시 정리
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# === Install MinIO mc (build-time) ===
RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc \
    -O /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

# GDAL 버전 확인 (디버깅용)
RUN gdal-config --version && gdalinfo --version

# requirements.txt 복사 및 설치
COPY requirements.txt .

# pip 업그레이드 및 의존성 설치
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt


COPY scripts/download_dem.sh /tmp/download_dem.sh
RUN chmod +x /tmp/download_dem.sh && /tmp/download_dem.sh && rm /tmp/download_dem.sh

# 소스 복사
COPY . .

# entrypoint 스크립트 등록
COPY entrypoint.backend.sh /entrypoint.backend.sh
RUN chmod +x /entrypoint.backend.sh

# 헬스체크 (AWS ECS에서 유용)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

ENTRYPOINT ["/entrypoint.backend.sh"]