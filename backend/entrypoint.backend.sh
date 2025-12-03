#!/bin/bash

# 에러 나면 멈춤
set -e

echo "🚀 Starting 7Hours Backend..."

# 1. DB 설정 (PostGIS 강제 지정)
export DB_HOST=db
export DB_PORT=5432

# 2. PostGIS 대기
echo "⏳ Waiting for PostGIS (db:5432)..."
until nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "✅ PostGIS Connected!"

# 3. MinIO 대기 (이미지 서버)
echo "⏳ Waiting for MinIO (minio:9000)..."
until nc -z minio 9000; do
  sleep 0.5
done
echo "✅ MinIO Connected!"

# 4. 마이그레이션 (DB 초기화)
echo "📦 Running Migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# 5. 서버 실행
echo "🔥 Starting Django Server..."
exec python manage.py runserver 0.0.0.0:8000
