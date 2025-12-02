import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
import apps.webrtc.routing
from apps.webrtc.middleware import JwtAuthMiddleware # 새로운 미들웨어 임포트

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# This is the standard ASGI application for Django
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JwtAuthMiddleware( # AuthMiddlewareStack을 JwtAuthMiddleware로 교체
            URLRouter(
                apps.webrtc.routing.websocket_urlpatterns
            )
        )
    ),
})
