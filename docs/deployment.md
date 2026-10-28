# Render에 배포하기

React 화면을 빌드하고 기존 FastAPI가 화면과 API를 같은 주소에서 제공합니다. 계산 엔진이나 가격 어댑터를 별도 언어로 바꾸지 않습니다. 저장소는 Private 상태로 연결할 수 있습니다.

## 최초 배포

1. 기존 Render 계정에 로그인하고 GitHub의 `yurimakes/kamis-harvestnav`에 대한 접근을 연결합니다. 저장소 선택이 가능하면 이 저장소만 허용합니다.
2. Render 대시보드에서 **New → Blueprint**를 선택하고 저장소와 배포할 브랜치를 고릅니다. 루트의 `render.yaml`을 사용합니다.
3. 생성 예정 항목이 **Web Service 1개 / Free / Singapore**인지 확인합니다. 데이터베이스와 디스크는 필요하지 않습니다.
4. `DATA_GO_KR_SERVICE_KEY` 입력란에 기존 공공데이터포털 **Decoding 인증키 전체**를 Render 화면에서 직접 저장합니다. 채팅·GitHub·프론트엔드 변수에는 넣지 않습니다.
5. 배포를 시작하고 빌드 및 서비스 상태가 **Live**가 되는지 확인합니다. 실제 주소는 Render가 생성한 `https://…onrender.com` 값을 사용하며 추측해 만들지 않습니다.

로컬 `.env`는 Render로 자동 복사되지 않습니다. 이미 가진 동일 인증키를 배포 서비스 환경변수에 한 번 저장합니다. 키를 새로 발급받을 필요는 없습니다. 키 없이 실행하면 합성 계산은 가능하지만 실제 가격은 인증 미설정으로 표시됩니다.

## Blueprint 대신 Web Service를 직접 만들 경우

| 항목 | 값 |
|---|---|
| Repository | `yurimakes/kamis-harvestnav` |
| Branch | 배포 준비 커밋이 포함된 브랜치 |
| Language / Runtime | Python 3 |
| Root Directory | 비워 둠 |
| Region | Singapore |
| Instance Type | Free |
| Build Command | `bash scripts/render-build.sh` |
| Start Command | `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --no-access-log` |
| Health Check Path | `/api/health` |
| Auto-Deploy | Off |

환경변수는 `PYTHON_VERSION=3.12.14`, `NODE_VERSION=24.22.1`, `PYTHONUNBUFFERED=1`과 비밀값 `DATA_GO_KR_SERVICE_KEY`를 설정합니다. `VITE_` 접두사로 키를 설정하지 않습니다. 시작 명령의 `$PORT`는 Render가 제공하는 환경변수입니다.

## 배포 후 확인

- 루트 주소에서 현재 쿨민트 화면과 재생 버튼이 열리는지 확인합니다.
- `/api/health`의 `service=HarvestNav`, `kamis_configured=true`를 확인합니다. 이 값은 키 설정 여부이며 실제 API 승인·조회 성공을 보증하지 않습니다.
- 합성 기본 5,000kg·가락60/구리40에서 현재 수취액 6,272,375원, 최대 후보 구리100% 6,710,000원을 확인합니다.
- KAMIS 화면에서 서울·여름(고랭지)·상품·2026-10-06~27을 조회합니다. 실제 응답이 성공하면 원단위와 kg 중량, 조사일, 원/kg 가격을 확인하고 조회 근거를 저장합니다. 이전 로컬 검증 결과를 배포 환경 성공으로 대체하지 않습니다.
- 조회 실패 시 연결·인증·단위 오류를 확인합니다. 키나 전체 요청 URL이 포함된 자료를 공유하지 않습니다.

시뮬레이션 입력과 내보내기 파일은 브라우저에서 사용합니다. 별도 사용자 계정·서버 저장 DB가 없으며 앱 내부 캐시는 재시작하면 사라집니다.

## UI를 수정한 뒤 갱신

배포 브랜치에 변경을 반영한 뒤 Render에서 **Manual Deploy → Deploy latest commit**을 실행합니다. 자동 배포는 기본적으로 꺼 두었습니다. 새 빌드에서 Python 시험이 실패하거나 프론트엔드 빌드에 실패하면 중단합니다.

기존 배포를 되돌릴 때에는 Render의 배포 이력에서 이전 정상 버전을 선택합니다. 로컬 작업 파일이나 Git 이력을 강제로 초기화하지 않습니다.

## 무료 서비스의 첫 접속

Render Free Web Service는 15분 동안 요청이 없으면 중지되며 다음 접속에서 기동에 약 1분 걸릴 수 있습니다. 시연 전에 실제 주소를 열어 화면과 가격 조회가 준비됐는지 확인합니다. 유료 플랜으로 자동 전환하거나 인위적인 유지 요청을 설정하지 않습니다. 무료 인스턴스 외에도 플랫폼의 사용량 한도가 적용됩니다.

공식 안내: [FastAPI 배포](https://render.com/docs/deploy-fastapi), [Blueprint 설정](https://render.com/docs/blueprint-spec), [환경변수](https://render.com/docs/configure-environment-variables), [무료 서비스 제한](https://render.com/docs/free).
