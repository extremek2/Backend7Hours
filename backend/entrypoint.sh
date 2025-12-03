#!/bin/bash
set -e


echo "🚀 Starting container setup..."

export DB_HOST=db
export DB_PORT=5432

echo "⏳ Waiting for PostGIS at ${DB_HOST}:${DB_PORT}..."
until nc -z ${DB_HOST} ${DB_PORT}; do
  sleep 1
done
echo "✅ DB is ready!"

# MinIO 서비스 대기 (서비스 이름: 'minio', 포트: 9000 사용)
echo "⏳ Waiting for MinIO service at minio:9000..."
# nc 명령어는 대부분의 Docker 이미지에 기본으로 설치되어 있지 않으므로, 
# 만약 위의 DB 대기 로직이 작동한다면 이미 설치되어 있다는 의미입니다.
until nc -z minio 9000; do
  sleep 1
done
echo "✅ MinIO is ready!"

# MC CLIENT 별칭 변수 지정
ALIAS_NAME=$MINIO_CLIENT_ALIAS 

# MinIO 초기 설정 (Alias 설정 및 버킷 생성)
echo "⚙️ Setting up MinIO aliases and buckets..."
# Alias 설정 시, 서비스 이름 'minio'와 .env에서 읽어온 환경 변수 사용
mc alias set $ALIAS_NAME $MINIO_ENDPOINT_URL $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

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
  mc mb "$ALIAS_NAME/$BUCKET_NAME" || true
done

echo "✅ MinIO buckets created."
# =============================================================

# 마이그레이션 수행
if [ "$RUN_MIGRATION" = "true" ]; then
  echo "📚 Running Django migrations..."
  python manage.py makemigrations users --noinput
  python manage.py makemigrations --noinput
  python manage.py migrate --noinput
fi

# 개발 환경에서 슈퍼유저 자동 생성
if [ "$CREATE_SUPERUSER" = "true" ] && [ "$DJANGO_ENV" != "prod" ]; then
  echo "👤 Ensuring superuser exists..."

  python manage.py shell <<'EOF'
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username_field = getattr(User, 'USERNAME_FIELD', None)  # None일 수도 있음
email_env = os.getenv('DJANGO_SUPERUSER_EMAIL')
password_env = os.getenv('DJANGO_SUPERUSER_PASSWORD')
username_env = os.getenv('DJANGO_SUPERUSER_USERNAME')

# 슈퍼유저 조회 조건
lookup = {}
if username_field:
    lookup[username_field] = username_env
else:
    # username 필드가 없으면 email로 조회
    lookup['email'] = email_env

u = User.objects.filter(**lookup).first()

if u:
    if not u.check_password(password_env):
        u.set_password(password_env)
        u.save()
        print("🔑 Superuser password updated")
    else:
        print("ℹ️ Superuser already exists")
else:
    create_args = {
        'email': email_env,
        'password': password_env
    }
    if username_field:
        create_args[username_field] = username_env
    User.objects.create_superuser(**create_args)
    print("🆕 Superuser created")
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
