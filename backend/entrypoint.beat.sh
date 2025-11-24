#!/bin/bash
set -e

echo "🚀 Starting Celery Beat"

# DB 대기
echo "⏳ Waiting for DB at ${DB_HOST}:${DB_PORT}..."
until nc -z ${DB_HOST} ${DB_PORT}; do
    sleep 1
done
echo "✅ DB ready"

# Redis 대기
echo "⏳ Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT:-6379}..."
until nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
    sleep 1
done
echo "✅ Redis ready"


echo "⏳ Waiting for backend at ${DJANGO_PORT}..."
until nc -z backend ${DJANGO_PORT}; do
    sleep 1
done
echo "✅ Backend is ready"

# 마지막에 Beat 실행
echo "🚀 Launching Celery Beat..."
exec celery -A core beat --loglevel=info