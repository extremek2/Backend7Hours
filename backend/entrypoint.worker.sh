#!/bin/bash
set -e

echo "🚀 Starting Celery Worker"

# DB 준비 확인
echo "⏳ Waiting for DB at ${DB_HOST}:${DB_PORT}..."
until nc -z ${DB_HOST} ${DB_PORT}; do
    sleep 1
done
echo "✅ DB ready"

# Redis 준비 확인
echo "⏳ Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT:-6379}..."
until nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
    sleep 1
done
echo "✅ Redis ready"

# MinIO 준비 확인
echo "⏳ Waiting for MinIO at minio:9000..."
until nc -z minio 9000; do
    sleep 1
done
echo "✅ MinIO ready"

# Celery Worker 시작
exec celery -A core worker -l info