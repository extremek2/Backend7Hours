#!/bin/sh
set -e

echo "🚀 Starting container with DJANGO_ENV=${DJANGO_ENV:-dev}"

# 1️⃣ DB 대기
echo "⏳ Waiting for MySQL to be ready..."
timeout=30
counter=0
until nc -z db 3306; do
  sleep 1
  counter=$((counter+1))
  if [ $counter -ge $timeout ]; then
    echo "❌ MySQL not ready after $timeout seconds"
    exit 1
  fi
done
echo "✅ MySQL is up!"

# 2️⃣ 마이그레이션
echo "Applying database migrations..."
python manage.py migrate --noinput

# 3️⃣ 개발 환경일 때만 슈퍼유저 자동 생성
if [ "$DJANGO_ENV" != "prod" ]; then
  echo "👤 Creating superuser if not exists..."
  python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin1234')
EOF
fi

# 4️⃣ 서버 실행
if [ "$DJANGO_ENV" = "prod" ]; then
  echo "🔥 Starting Gunicorn (Production)"
  exec gunicorn core.wsgi:application --bind 0.0.0.0:8000
else
  echo "💻 Starting Django Development Server"
  exec python manage.py runserver 0.0.0.0:8000
fi
