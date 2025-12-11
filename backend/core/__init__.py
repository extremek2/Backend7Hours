from __future__ import absolute_import, unicode_literals

# Django가 시작될 때 이 app(celery.py의 app)을
# 항상 임포트하도록 하여, @shared_task가 이 앱을 사용하게 합니다.
from .celery import app as celery_app

__all__ = ('celery_app',)