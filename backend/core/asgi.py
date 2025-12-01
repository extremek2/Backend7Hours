import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import apps.webrtc.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# This is the standard ASGI application for Django
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                apps.webrtc.routing.websocket_urlpatterns
            )
        )
    ),
})
