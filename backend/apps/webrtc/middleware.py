# backend/apps/webrtc/middleware.py
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.authentication import JWTTokenUserAuthentication
from channels.middleware import BaseMiddleware
import logging

logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user(token_key):
    try:
        # JWT 토큰을 디코드하여 페이로드를 가져옵니다.
        untyped_token = UntypedToken(token_key)
        
        # 페이로드에서 사용자 ID를 추출합니다.
        user_id = untyped_token.payload.get('user_id')
        
        if user_id is None:
            logger.warning("JWT token has no user_id")
            return AnonymousUser()
            
        # 사용자 ID로 유저 객체를 조회합니다.
        User = get_user_model()
        user = User.objects.get(id=user_id)
        return user

    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        logger.error(f"JWT authentication failed: {e}")
        return AnonymousUser()
    except Exception as e:
        logger.error(f"An unexpected error occurred during JWT auth: {e}")
        return AnonymousUser()

class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        try:
            # WebSocket 요청 헤더에서 'authorization' 헤더를 찾습니다.
            auth_header = next(
                (value for key, value in scope.get('headers', []) if key == b'authorization'),
                b''
            ).decode('utf-8')

            if auth_header.startswith('Bearer '):
                token_key = auth_header.split(' ')[1]
                scope['user'] = await get_user(token_key)
                logger.info(f"Authenticated user {scope['user']} for WebSocket.")
            else:
                scope['user'] = AnonymousUser()
                logger.warning("No Bearer token found in WebSocket headers.")

        except Exception as e:
            logger.error(f"Exception in JwtAuthMiddleware: {e}")
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
