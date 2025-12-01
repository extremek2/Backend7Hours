# backend/apps/webrtc/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

User = get_user_model()
logger = logging.getLogger(__name__)

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """WebSocket 연결 시도 시 호출"""
        self.user = self.scope["user"]
        
        # 1. 사용자 인증 확인
        if not self.user.is_authenticated:
            logger.warning(f"Unauthenticated user tried to connect. Closing connection.")
            await self.close()
            return

        # 2. 각 사용자를 고유한 그룹에 추가
        #    - 그룹 이름은 'user_{user_id}' 형식으로 지정
        #    - 한 사용자가 여러 기기에서 접속해도 모두 같은 그룹에 속하게 됨
        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"✅ WebSocket connected for user '{self.user.email}' (ID: {self.user.id}). Group: '{self.user_group_name}'")

    async def disconnect(self, close_code):
        """WebSocket 연결 종료 시 호출"""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        logger.info(f"❌ WebSocket disconnected for user '{getattr(self.user, 'email', 'anonymous')}'")

    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신 시 호출"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            target_user_id = data.get('target_user_id')

            logger.info(f"📨 MSG Received: Type='{message_type}', TargetID='{target_user_id}', From='{self.user.email}'")

            if not target_user_id:
                logger.warning("Message received without 'target_user_id'. Ignoring.")
                return

            # 메시지를 받을 대상 그룹 이름 생성
            target_group_name = f"user_{target_user_id}"

            # 채널 레이어를 통해 대상 그룹으로 메시지 전송
            # 'type' 필드는 호출할 메서드 이름 ('webrtc.message')
            await self.channel_layer.group_send(
                target_group_name,
                {
                    'type': 'webrtc.message', # webrtc_message 메서드를 호출
                    'message': data,
                    'from_user_id': self.user.id
                }
            )
            logger.info(f"🚀 Forwarded message from User ID {self.user.id} to Group '{target_group_name}'")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from {self.user.email}: {text_data}")
        except Exception as e:
            logger.error(f"An error occurred in receive method: {e}", exc_info=True)


    async def webrtc_message(self, event):
        """
        그룹으로부터 메시지 수신 시 호출 (channel_layer.group_send에 의해 트리거됨)
        이 메시지를 클라이언트 WebSocket으로 전송합니다.
        """
        message = event['message']
        from_user_id = event['from_user_id']
        
        try:
            await self.send(text_data=json.dumps({
                'message': message,
                'from_user_id': from_user_id
            }))
            logger.info(f"📡 Sent message to client '{self.user.email}' (from User ID {from_user_id})")
        except Exception as e:
            logger.error(f"Failed to send message to client {self.user.email}: {e}", exc_info=True)
