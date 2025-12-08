#!/bin/bash
set -e

echo "🚀 Starting container setup..."
echo "🔧 Environment loaded with DB_ENGINE=${DB_ENGINE}"

# DB 동적 환경 변수 설정
DB_PORT_VAR="DB_PORT_${DB_ENGINE}"
DB_ENGINE_PATH_VAR="DB_ENGINE_${DB_ENGINE}"
DB_VOLUME_PATH_VAR="DB_VOLUME_PATH_${DB_ENGINE}"

export DB_PORT=${!DB_PORT_VAR}
export DJANGO_DB_ENGINE=${!DB_ENGINE_PATH_VAR}
export DB_VOLUME_PATH=${!DB_VOLUME_PATH_VAR}

echo "📡 Using DB port: ${DB_PORT}"

# DB 서비스 대기
echo "⏳ Waiting for DB service at ${DB_HOST}:${DB_PORT}..."
until nc -z ${DB_HOST} ${DB_PORT}; do
  sleep 1
done
echo "✅ DB is ready!"


# MinIO 서비스 대기 (서비스 이름: 'minio', 포트: 9000 사용)
echo "⏳ Waiting for MinIO service at ${MINIO_HOST}:${MINIO_PORT}..."
until nc -z ${MINIO_HOST} ${MINIO_PORT}; do
  sleep 1
done
echo "✅ MinIO is ready!"

# MinIO 초기 설정 (Alias 설정 및 버킷 생성)
echo "⚙️ Setting up MinIO aliases and buckets..."
mc alias set $MINIO_CLIENT_ALIAS $MINIO_ENDPOINT_URL $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# 버킷 리스트 정의
BUCKETS=(
  $MINIO_USERS_BUCKET
  $MINIO_PETS_BUCKET
  $MINIO_PATHS_BUCKET
  $MINIO_POSTS_BUCKET
  $MINIO_PLACES_BUCKET
)

for BUCKET_NAME in "${BUCKETS[@]}"; do
  echo "  -> Creating bucket: $BUCKET_NAME"
  mc mb "$MINIO_CLIENT_ALIAS/$BUCKET_NAME" --ignore-existing

  echo " -> Setting anonymous read policy for: $BUCKET_NAME"
  mc anonymous set public "$MINIO_CLIENT_ALIAS/$BUCKET_NAME"
done

echo "✅ MinIO buckets created with anonymous access enabled."
# =============================================================

# DEM script 실행 (초기 다운로드 후 스킵됨)
bash /app/scripts/download_dem.sh


# 마이그레이션 수행
if [ "$RUN_MIGRATION" = "true" ]; then
  echo "📚 Running Django migrations..."
  python manage.py makemigrations users --noinput
  python manage.py makemigrations --noinput
  python manage.py migrate --noinput
fi

# django.contrib.sites 초기화
if [ "$ENABLE_SITE_UPDATE" = "true" ]; then
  echo "🌍 Updating django_site domain and name..."
  python manage.py shell <<EOF
from django.contrib.sites.models import Site
import os
domain = os.getenv("SITE_DOMAIN", "localhost:8000")
name = os.getenv("SITE_NAME", domain)
Site.objects.update_or_create(
    id=1,
    defaults={"domain": domain, "name": name},
)
print(f"✔️ django_site updated → {domain}")
EOF
fi

# 개발 환경에서 슈퍼유저 자동 생성
if [ "$CREATE_SUPERUSER" = "true" ] && [ "$DJANGO_ENV" != "prod" ]; then
  echo "👤 Ensuring superuser exists..."
  python manage.py shell <<'EOF'
import os
from django.contrib.auth import get_user_model
User = get_user_model()

email = os.getenv('DJANGO_SUPERUSER_EMAIL')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

if email and password:
    user, created = User.objects.update_or_create(
        email=email,
        defaults={'is_superuser': True, 'is_staff': True, 'is_active': True}
    )
    if not user.check_password(password):
        user.set_password(password)
        user.save()
    if created:
        print(f"🆕 Superuser '{email}' created")
    else:
        print(f"ℹ️ Superuser '{email}' exists. Password ensured")
else:
    print("⚠️ DJANGO_SUPERUSER_EMAIL or PASSWORD missing.")
EOF
fi

# 서버 실행
if [ "$DJANGO_ENV" = "prod" ]; then
  echo "🔥 Starting Gunicorn (Production)"
  exec gunicorn core.wsgi:application --bind 0.0.0.0:${DJANGO_PORT}
else
  echo "💻 Starting Django Development Server"
  exec python manage.py runserver 0.0.0.0:${DJANGO_PORT}
fi