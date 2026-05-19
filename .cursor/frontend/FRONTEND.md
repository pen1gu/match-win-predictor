# FastAPI 기반 규칙 (API ↔ 프론트 연동)

이 레포의 데모는 `client/demo_server.py`(표준 라이브러리 HTTP)를 쓰지만, **비동기 DB 세션**은 `server/app/models/session.py`의 `get_session()`으로 이미 FastAPI `Depends` 패턴과 맞춰 두었다. 아래는 FastAPI로 API를 추가·이전할 때 따를 규칙이다.

## 앱 구조

- **`FastAPI()` 인스턴스**는 한 곳에서 생성하고, 라우트는 **`APIRouter`**로 기능별 모듈 분리 후 `app.include_router(...)`로 붙인다.
- **DB 세션**: 엔드포인트 인자에 `session: AsyncSession = Depends(get_session)` 형태로 주입한다. 라우트 본문에서 세션을 직접 열고 닫지 않는다.
- **수명 주기**: 엔진 생성/해제가 필요하면 `@asynccontextmanager` 기반 **lifespan**에서 처리한다(전역 엔진이면 dispose 시점만 명확히).

## 요청·응답

- 바깥으로 노출하는 JSON은 가능하면 **Pydantic `BaseModel`**(또는 프로젝트에서 쓰는 동등한 스키마)로 request/response를 정의하고, 엔드포인트 반환 타입을 명시한다.
- DB 엔티티(SQLModel)를 그대로 직렬화하기보다, **응답 전용 모델**로 매핑해 필드 노출을 제어한다(순환 참조·민감 필드 방지).
- `client/web_demo`·`predict_test.py` 등이 소비하는 **키 이름·null 허용·날짜 형식(ISO 문자열 등)** 은 기존 데모 응답과 맞출지, 버전 경로(`/api/v1`)로 구분할지 팀에서 정하고 바꿀 때는 **클라이언트와 동시에** 수정한다.

## 비동기·DB

- I/O가 있는 핸들러는 **`async def`**; 동기 전용 작업은 `run_in_threadpool` 등으로 블로킹을 피한다.
- SQLAlchemy 2.0 / **AsyncSession** 패턴을 유지하고, 기존 `server/app/models/**`·쿼리 스타일과 일관되게 맞춘다.

## 보안·운영

- **CORS**: 브라우저에서 호출하는 경우 `CORSMiddleware`에 허용 origin을 명시한다(개발용 `*`는 로컬 한정).
- **설정**: URL·시크릿은 `server/config/settings`(또는 환경 변수)만 사용하고 코드에 하드코딩하지 않는다.
- **에러**: 예상 가능한 실패는 적절한 HTTP 상태 코드와 본문; 처리하지 않은 예외는 500으로 일관되게 로깅(`server/utils/logger/get_logger`)한다.

## 이 프로젝트와의 정합성

- import는 **`from server...`** 패키지 경로를 유지한다.
- 도메인 규칙(모델 필드·저장·compute)은 `.cursor/rules/server-app-pipeline.mdc` 및 `.cursor/AGENTS.md`와 충돌하지 않게 한다.
