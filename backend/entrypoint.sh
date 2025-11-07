#!/bin/bash
set -e

echo "🚀 Starting container setup..."
echo "🔧 Environment loaded with DB_ENGINE=${DB_ENGINE}"

# DB 엔진별 동적 변수 설정
DB_PORT_VAR="DB_PORT_${DB_ENGINE}"
DB_PKG_VAR="DB_PKG_${DB_ENGINE}"
DB_REQS_VAR="DB_REQS_${DB_ENGINE}"
DB_ENGINE_PATH_VAR="DB_ENGINE_${DB_ENGINE}"
DB_VOLUME_PATH_VAR="DB_VOLUME_PATH_${DB_ENGINE}"

export DB_PORT=${!DB_PORT_VAR}
export DB_PKG=${!DB_PKG_VAR}
export DB_REQS=${!DB_REQS_VAR}
export DJANGO_DB_ENGINE=${!DB_ENGINE_PATH_VAR}
export DB_VOLUME_PATH=${!DB_VOLUME_PATH_VAR}

echo "📡 Using DB port: ${DB_PORT}"
echo "📦 Installing system package for ${DB_ENGINE}: ${DB_PKG}"


# 시스템 패키지 설치
apt-get update -qq && apt-get install -y ${DB_PKG} && rm -rf /var/lib/apt/lists/*


# Python 패키지 설치
if [ -n "$DB_REQS" ]; then
  echo "📘 Installing Python DB driver: ${DB_REQS}"
  pip install --no-cache-dir ${DB_REQS}
fi

if [ "$ENABLE_POSTGIS" = "true" ]; then
  echo "📘 Installing Python GIS packages: ${DB_REQS_postgis}"
  pip install --no-cache-dir ${DB_REQS_postgis}
fi

# DB 서비스 대기
echo "⏳ Waiting for DB service at ${DB_HOST}:${DB_PORT}..."
until nc -z ${DB_HOST} ${DB_PORT}; do
  sleep 1
done
echo "✅ DB is ready!"

# 마이그레이션 수행
if [ "$RUN_MIGRATION" = "true" ]; then
  echo "📚 Running Django migrations..."
  python manage.py migrate --noinput
fi

# 개발 환경에서 슈퍼유저 자동 생성
if [ "$CREATE_SUPERUSER" = "true" ] && [ "$DJANGO_ENV" != "prod" ]; then
  echo "👤 Ensuring superuser exists..."
  python manage.py createsuperuser \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "$DJANGO_SUPERUSER_EMAIL" \
    --noinput || true

  python manage.py shell <<EOF
from django.contrib.auth import get_user_model
import os
User = get_user_model()
u = User.objects.filter(username=os.getenv('DJANGO_SUPERUSER_USERNAME')).first()
if u and not u.check_password(os.getenv('DJANGO_SUPERUSER_PASSWORD')):
    u.set_password(os.getenv('DJANGO_SUPERUSER_PASSWORD'))
    u.save()
    print("✅ Admin password updated.")
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