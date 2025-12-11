# WebRTC 시그널링 서버 개선 방안

현재 구축된 Django Channels 기반 WebRTC 시그널링 서버는 메시지 중계를 위한 기본적인 기능을 제공합니다. 그러나 실제 서비스에 적용하기 위한 안정성과 보안, 사용자 경험 개선을 위해 다음과 같은 추가 작업을 고려할 수 있습니다.

---

## 1. 통화 권한 확인 (Authorization Check) - **가장 중요**

*   **설명**: 현재 시그널링 서버는 모든 인증된 사용자가 다른 어떤 사용자에게든 메시지를 보낼 수 있도록 허용합니다. 이는 보안상 취약할 수 있으며, 예를 들어 '사용자(owner)'는 자신이 등록한 '펫(linked_user)'에게만 모니터링을 요청할 수 있도록 제한해야 합니다.
*   **구현 방안**:
    *   `apps/webrtc/consumers.py` 내의 `receive` 메서드에서 메시지를 실제로 다른 사용자에게 전송하기 전에, 요청을 보낸 사용자(`self.user`)와 메시지를 받을 대상 사용자(`target_user_id`) 간의 `Pet` 모델 관계를 확인합니다.
    *   `Pet` 모델(`apps/pets/models.py`)의 `owner` 필드와 `linked_user` 필드를 활용하여, `self.user`가 `target_user_id`를 `linked_user`로 가진 `Pet`의 `owner`인지 확인합니다.
    *   이러한 데이터베이스 조회는 비동기(`database_sync_to_async`)로 처리하여 WebSocket Consumer의 성능에 영향을 주지 않도록 합니다.

*   **예시 코드 (apps/webrtc/consumers.py):**

    ```python
    # apps/webrtc/consumers.py

    import json
    import logging
    from channels.generic.websocket import AsyncWebsocketConsumer
    from django.contrib.auth import get_user_model
    from channels.db import database_sync_to_async
    from apps.pets.models import Pet # Pet 모델 임포트

    User = get_user_model()
    logger = logging.getLogger(__name__)

    class CallConsumer(AsyncWebsocketConsumer):
        # ... (connect, disconnect 메서드)

        async def receive(self, text_data):
            try:
                data = json.loads(text_data)
                message_type = data.get('type')
                target_user_id = data.get('target_user_id')

                if not target_user_id:
                    logger.warning(f"User {self.user.id} sent message without 'target_user_id'. Ignoring.")
                    await self.send(text_data=json.dumps({"error": "Target user ID is missing."}))
                    return
                
                # 펫(linked_user)은 다른 사용자를 호출할 수 없도록 제한 (예: 펫은 항상 stream을 제공하는 역할)
                if await self.is_linked_as_pet(self.user.id):
                    logger.warning(f"User {self.user.id} is a linked pet and cannot initiate calls.")
                    await self.send(text_data=json.dumps({"error": "Pet accounts cannot initiate calls."}))
                    return


                # 권한 확인: 요청 보낸 사용자(owner)가 대상 사용자(linked_user)를 호출할 권한이 있는지 확인
                is_authorized = await self.check_call_authorization(self.user.id, target_user_id)
                if not is_authorized:
                    logger.warning(f"Authorization failed: User {self.user.id} tried to call {target_user_id}.")
                    await self.send(text_data=json.dumps({"error": "Unauthorized to call this user."}))
                    return

                # 메시지를 받을 대상 그룹 이름 생성
                target_group_name = f"user_{target_user_id}"

                # 채널 레이어를 통해 대상 그룹으로 메시지 전송
                await self.channel_layer.group_send(
                    target_group_name,
                    {
                        'type': 'webrtc.message',
                        'message': data,
                        'from_user_id': self.user.id
                    }
                )
                logger.info(f"🚀 Forwarded message from User ID {self.user.id} to Group '{target_group_name}'")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from {self.user.email}: {text_data}")
            except Exception as e:
                logger.error(f"An error occurred in receive method: {e}", exc_info=True)

        # 권한 확인을 위한 비동기 함수
        @database_sync_to_async
        def check_call_authorization(self_user_id, target_user_id):
            """
            self_user_id(호출자)가 target_user_id(호출 대상)를 모니터링할 권한이 있는지 확인합니다.
            펫 모델의 owner-linked_user 관계를 사용합니다.
            """
            # self_user_id가 Pet의 owner이고, target_user_id가 해당 Pet의 linked_user인지 확인
            return Pet.objects.filter(
                owner__id=self_user_id,
                linked_user__id=target_user_id
            ).exists()
            
        @database_sync_to_async
        def is_linked_as_pet(self_user_id):
            """
            self_user_id가 어떤 Pet의 linked_user로 등록되어 있는지 확인합니다.
            """
            return Pet.objects.filter(linked_user__id=self_user_id).exists()
    ```

---

## 2. 사용자 온라인 상태 확인 (User Presence)

*   **설명**: 모니터링을 시작하기 전에 대상 펫(연결된 사용자)이 현재 온라인 상태인지, 즉 WebSocket에 연결되어 있는지를 확인하는 기능입니다. 이를 통해 사용자 경험을 개선하고 불필요한 통화 시도를 줄일 수 있습니다.
*   **구현 방안**:
    *   **접속 시 기록**: 사용자가 `CallConsumer`에 `connect`할 때, Redis와 같은 캐시 저장소에 해당 사용자 ID의 온라인 상태를 기록합니다 (예: `SET user:{user_id}:online 1 EX 60`). `EX 60`은 60초 후 자동 만료를 의미하며, 주기적인 갱신이 필요합니다.
    *   **접속 해제 시 삭제**: `disconnect`할 때 해당 기록을 삭제합니다.
    *   **확인 API**: 클라이언트가 `target_user_id`의 온라인 상태를 확인할 수 있는 REST API 엔드포인트를 Django에 추가합니다. 이 API는 Redis에서 상태를 조회하여 반환합니다.

---

## 3. 통화 상태 관리 (Call State Management)

*   **설명**: 단순히 메시지를 중계하는 것을 넘어, '통화'라는 개념의 상태를 관리하여 사용자가 통화 요청, 수락, 거절, 종료 등의 명확한 피드백을 받을 수 있도록 합니다.
*   **구현 방안**:
    *   **상태 정의**: 통화에 대한 상태(예: `INITIATED` (요청), `RINGING` (울림), `ACCEPTED` (수락), `REJECTED` (거절), `ACTIVE` (진행 중), `ENDED` (종료))를 정의합니다.
    *   **중앙 상태 저장**: Redis 또는 데이터베이스에 현재 진행 중인 통화의 상태를 저장합니다. 통화 ID를 사용하여 여러 통화를 구분할 수 있습니다.
    *   **메시지 처리**: `CallConsumer`는 특정 메시지 유형(예: `type: "call_request"`, `type: "call_accept"`, `type: "call_reject"`, `type: "call_end"`)을 수신하면, 해당 통화의 상태를 업데이트하고 적절한 사용자에게 다음 시그널링 메시지를 전달합니다.
    *   **제약 조건**: (선택 사항) 특정 펫이 이미 통화 중인 경우 다른 통화 요청을 거절하고, 이를 호출자에게 알리는 등의 로직을 추가하여 복잡한 시나리오를 처리할 수 있습니다.
