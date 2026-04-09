# 🐾 7Hours Backend

## 📌 프로젝트 개요
7Hours Backend는 반려견 산책 데이터를 기반으로 경로 기록, 분석, AI 처리, 실시간 모니터링 기능을 제공하는 서버입니다. 모바일(Android) 애플리케이션과 연동되어 **데이터 수집 → 처리 → 저장 → 제공**까지의 전체 파이프라인을 담당합니다.

본 문서는 기능 상세보다는 **백엔드 시스템 구조와 동작 흐름을 설명하는 기술 중심**으로 작성되었습니다.

---

## ⚙️ 백엔드 주요 역할
- **사용자 인증**: JWT 기반 권한 관리 및 토큰 보안 유지
- **데이터 처리**: GPS/GPX 경로 데이터 저장, 조회 및 구조 변환
- **공간 분석**: PostGIS를 활용한 산책로 경로 거리 및 반경 기반 공간 쿼리 처리
- **비동기 처리**: AI 일기 생성, 이미지 생성, 고도 분석 등의 무거운 로직 분리
- **실시간 통신**: WebRTC P2P 연결을 위한 시그널링 서버 역할 수행
- **인프라**: Docker & Docker Compose를 활용한 개발/운영 환경 컨테이너화

---

## 🔄 시스템 처리 흐름
1. **Request**: 모바일 앱에서 JWT 인증을 거쳐 Django API 서버로 요청 전달
2. **Storage**: 산책 경로 데이터를 **PostgreSQL(PostGIS)**에 정규화하여 저장
3. **Queue**: 무거운 로직(AI 생성 등)을 **Celery/Redis** 작업 큐에 등록
4. **Async Task**: Worker에서 비동기 처리 후 결과를 DB 및 **MinIO**에 적재
5. **Real-time**: 산책 모니터링 시 **Django Channels**를 통해 시그널링 수행
6. **Response**: 최종 처리 결과를 REST API를 통해 앱으로 반환

---

## 🏗️ 시스템 구성
- **API 서버**: Django, Django REST Framework
- **Database**: PostgreSQL + PostGIS (공간 데이터 특화)
- **Message Broker**: Redis
- **Task Queue**: Celery (비동기 처리)
- **Object Storage**: MinIO (S3 Compatible 미디어 저장소)
- **Real-time**: Django Channels (ASGI 기반 실시간 통신)

---

## 🧠 주요 설계 결정 (Design Decisions)

### 📍 PostGIS를 활용한 공간 데이터 최적화
- **Issue**: 수백 개의 위경도 좌표를 단순 텍스트로 저장할 경우, 경로 조회 및 공간 연산 성능 저하 발생
- **Solution**: 단순 좌표 저장을 넘어 **`LineString` 객체**로 구조화하고 공간 인덱스를 적용했습니다.
- **Benefit**: 공간 쿼리 성능을 최적화하고, 산책 총거리 계산 및 사용자와의 거리, 고도 분석의 정확도를 확보했습니다.

### ⚡ Celery/Redis 기반 비동기 아키텍처
- **Issue**: AI 생성 및 분석 로직의 긴 실행 시간으로 인해 API 응답 지연(Timeout) 및 서버 자원 점유 발생
- **Solution**: 무거운 비즈니스 로직을 **별도 Worker**로 분리하여 비동기 처리 구조를 구축했습니다.
- **Benefit**: 사용자에게 즉각적인 응답을 제공하여 **UX를 개선**하고 시스템의 안정성을 높였습니다.

### 📂 MinIO를 이용한 미디어 독립 저장
- **Issue**: 고해상도 이미지와 대용량 데이터를 DB에 직접 저장할 경우, 백업 성능 저하 및 DB 비대화 발생
- **Solution**: **오브젝트 스토리지인 MinIO**를 도입하여 DB 데이터와 미디어 파일을 분리했습니다.
- **Benefit**: DB 부하를 줄이고 **스토리지 확장성**을 확보하여 대규모 미디어 데이터 관리를 용이하게 했습니다.

### 📡 Django Channels를 이용한 실시간 시그널링
- **Issue**: WebRTC 연결을 위한 시그널링 단계에서 HTTP 프로토콜만으로는 양방향 실시간성 확보의 한계
- **Solution**: **Django Channels** 기반의 ASGI 서버를 도입하여 양방향 통신 환경을 구축했습니다.
- **Benefit**: 저지연(Low-latency) 시그널링을 수행하여 **P2P 연결의 안정성**을 확보했습니다.

---

## 🃏 담당 업무
| 담당자 | 수행업무                                    |
| --- | --------------------------------------- |
| 장혁준 | Planning, Frontend, Backend             |
| 조석현 | Planning, Frontend(Core Trail Features) |
| 송준영 | Backend(Architecture, Database)         |
| 이준호 | UI/UX(Figma), Infra(AWS)                |

---

## 📎 참고
- 실제 구현 화면 및 시연 영상은 **[프론트엔드 저장소](https://github.com/jhj1111/Android7Hours)**에서 확인하실 수 있습니다.
