# Python 기반 이미지
FROM python:3.11-slim

# 환경 변수
ENV PYTHONUNBUFFERED 1

# 작업 디렉토리
WORKDIR /app

# MySQL client 빌드용 패키지
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    netcat-openbsd \
 && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 코드 복사
COPY . .

# entrypoint 스크립트 사용
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]