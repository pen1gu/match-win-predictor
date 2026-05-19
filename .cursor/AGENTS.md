# winner-prediction Cursor Agent

프로젝트 특성: Python(서버 중심) 코드가 `server/` 패키지 안에서 계층적으로 연결됩니다.

## 역할

- 변경 제안을 하기 전에, **현재 코드 구조**(어떤 모듈이 어떤 모듈을 import/호출하는지)를 먼저 확인한 뒤 가장 작은 수정으로 해결합니다.
- “대중적인” 일반 가이드도 따르되, 이 프로젝트에서는 특히 아래 **핵심 3가지**를 반드시 수행합니다.

## 필수(핵심 3가지)

### 1) Lint(문법/정적) 검증

이 repo는 `ruff/flake8/black` 같은 명시적 lint 설정 파일이 보이지 않습니다. 따라서 Cursor가 제안한 변경이 **문법적으로 깨지지 않는지** 우선 확인합니다.

권장 커맨드(로컬에서 실행):

```bash
python -m compileall server client predict_test.py test.py
python -m py_compile predict_test.py test.py
```

### 2) 코드 검증(실행 전/부작용 최소)

DB나 크롤링을 실제로 돌리지 않고, “import/모듈 로딩” 단계에서 깨지는지 확인합니다.

권장 커맨드(로컬에서 실행):

```bash
python - <<'PY'
import importlib
import pkgutil

import server

mods = [m.name for m in pkgutil.walk_packages(server.__path__, server.__name__ + ".")]
failed = []
for name in mods:
    try:
        importlib.import_module(name)
    except Exception as e:
        failed.append((name, repr(e)))

if failed:
    print("IMPORT_FAIL", len(failed))
    for n, e in failed[:50]:
        print(n, e)
    raise SystemExit(1)

print("OK", len(mods))
PY
```

주의:

- 위 import sweep이 실패할 때는 “네트워크/DB 호출”이 아니라 **패키지/의존성 설치 문제**나 **import-time 코드의 side effect**를 먼저 의심합니다.

### 3) 전체 구조 의존성 체크(현재 프로젝트 기준)

아래 경로(계층)에서 “입력/출력 타입(모델 필드 포함)”이 맞는지 확인합니다.

#### (A) 크롤러 -> 모델 객체 생성

- `server/app/crawler/fotmob.py`의 메서드들은 `server/app/models/**`의 SQLModel 객체를 조립해 반환합니다.
- 변경 시에는 해당 메서드가 생성하는 모델 필드가 실제 모델 정의(`server/app/models/**`)와 일치하는지 확인합니다.

#### (B) tasks -> db_store 저장

- `server/app/tasks/task.py`는 크롤러 결과를 받아 `server/app/store/db_store.py`의 `save()`로 저장합니다.
- `save()`는 내부적으로 `upsert_model()`을 호출하며, conflict 컬럼은 기본적으로
  - 모델에 `__upsert_conflict_cols__`가 있으면 그 값을 사용
  - 없으면 SQLModel 테이블의 **primary_key 컬럼들**을 사용합니다.
- 따라서 모델의 `primary_key=True`/복합 PK 변경은 저장 동작에 직접 영향을 주므로, 변경 시 반드시 같이 점검합니다.

#### (C) compute -> 모델 필드 기대값

- 예측 로직은 `server/app/compute/player_rating.py`에서 모델 필드를 직접 사용합니다.
- 특히 아래 필드들이 존재/의미 있게 채워져야 합니다.
  - `Player.info.current_market_value`
  - `Player.match_affect_features.form_rating`
  - `Player.info.fan_rating`
  - `Player.info.position`(리스트) 및 `Player.info.age`
- 변경 시에는 compute 로직에서 사용하는 키/속성명이 모델 정의(`server/app/models/players/*`)와 정확히 맞는지 확인합니다.

## 그 외 대중적인 Skills(일반 원칙)

- 최소 변경: “정확히 필요한 수정”만 합니다(불필요한 리팩토링/네이밍 변경 금지).
- 스타일 유지: 기존 `from server...` import 패턴, async 스타일, 로깅(`server/utils/logger/get_logger`) 사용을 따릅니다.
- 영향도 요약: 변경 PR/커밋 전에 “어떤 계층(A~C)을 건드리는지”를 한 문단으로 정리합니다.
- 부작용 관리: 크롤링/DB 쓰기는 실제 실행이 필요할 때만, 그리고 로컬/CI 환경 차이를 고려해 안내합니다.
- 테스트 전략: pytest 설정이 보이지 않으므로 우선은 `compileall/import sweep` 같은 “실행 전 검증”을 기본으로 삼고, DB가 필요하면 별도 스모크 시나리오로 분리해 안내합니다.
