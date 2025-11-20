# backend/core/celery.py

import os
from celery import Celery

# 1. Celery가 Django 설정을 찾을 수 있도록 환경 변수 설정
# 'core.settings'는 settings.py 파일의 위치입니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# 2. Celery 앱 인스턴스 생성
# 'core'는 이 프로젝트의 이름입니다.
app = Celery('core')

# 3. Django의 settings.py에서 Celery 관련 설정을 불러옵니다.
# 'CELERY_'로 시작하는 모든 설정값을 가져옵니다.
app.config_from_object('django.conf:settings', namespace='CELERY')

# 4. INSTALLED_APPS에 등록된 모든 앱에서 'tasks.py' 파일을
#    자동으로 찾아서 로드합니다. (apps/paths/tasks.py를 찾게 됩니다)
app.autodiscover_tasks()