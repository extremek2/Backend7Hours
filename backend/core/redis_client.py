import redis
import os
import logging
from django.conf import settings # Django 설정값을 가져오기 위해 import

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# 1. 설정값 정의 (settings.py 또는 환경변수에서 가져옴)
# ------------------------------------------------------------

# settings.py에 정의된 설정을 사용하거나 기본값을 'redis'로 설정
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
REDIS_DB_SIGNAL_COUNT = 0 # 시그널/카운팅용 DB는 0번 사용 (Celery와 분리)


# ------------------------------------------------------------
# 2. Redis 클라이언트 초기화
# ------------------------------------------------------------

redis_client = None

def initialize_redis_client():
    """Redis 클라이언트 객체를 초기화하고 반환"""
    global redis_client
    
    if redis_client is not None:
        return redis_client # 이미 초기화되었으면 기존 객체 반환 (Singleton 패턴)

    try:
        # StrictRedis 객체 생성
        client = redis.StrictRedis(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            db=REDIS_DB_SIGNAL_COUNT,
            socket_timeout=5, # 연결 타임아웃 설정
            decode_responses=True # Redis에서 가져온 데이터를 문자열로 디코딩
        )
        client.ping() # 연결 테스트
        redis_client = client
        logger.info(f"Redis Client successfully initialized at {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_SIGNAL_COUNT}")
        return redis_client
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT}: {e}")
        redis_client = None # 연결 실패 시 None 반환
        return None

# 모듈이 로드될 때 클라이언트 초기화
initialize_redis_client()

# Redis 키 생성 헬퍼 함수
def get_redis_key(object_id, type_name):
    """
    Redis 카운터 키를 생성합니다. (예: post:3:like_count)
    :param object_id: Post의 PK
    :param type_name: 카운트 타입 (예: 'like', 'comment', 'bookmark')
    """
    return f"post:{object_id}:{type_name}_count"