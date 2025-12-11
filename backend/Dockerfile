# Python 기반 이미지
FROM python:3.11-slim

# 환경 변수
ENV PYTHONUNBUFFERED 1

# 작업 디렉토리
WORKDIR /app

# 패키지 설치를 위한 기본 유틸
RUN apt-get update && apt-get install -y \
    build-essential \
    binutils \
    wget \
    netcat-openbsd \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    pkg-config \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

# === Install MinIO mc (build-time) ===
RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc \
    -O /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

# requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# entrypoint 스크립트 등록
COPY entrypoint.backend.sh /entrypoint.backend.sh
RUN chmod +x /entrypoint.backend.sh

ENTRYPOINT ["/entrypoint.backend.sh"]