# 로컬 실행과 개발

> 현재 기본 조회는 공공데이터포털 `perRegion/price`입니다. 인증·단위·실행은 [현재 연동 가이드](portal-integration.md)를 우선 적용하세요. 아래 자체 API 설명은 이전 구현 기록이며 serviceKey와 혼용하지 않습니다.

Python 3.12 또는 3.13과 Node.js 22.12 이상을 사용합니다. 기본 생성 버전은 3.13이며 기존 `.venv`가 있으면 그대로 사용합니다. Linux Python 3.12.14 / Node.js 24.22.1에서 검증했고 사용자 Windows Python 3.13에서 이전 40개 계산 테스트 통과 출력이 확인됐습니다. 이번 PowerShell 수정본의 Windows 실행 검증은 별도입니다.

## Windows PowerShell

프로젝트 루트에서 실행합니다. 설치·빌드 후 서버를 시작합니다. 패키지 명령은 `npm.cmd`로 호출합니다.

```powershell
.\scripts\run-local.ps1
```

주소: `http://127.0.0.1:8000`, 종료: Ctrl+C. 실제 환경변수를 설정하지 않아도 합성 계산과 지도는 사용할 수 있습니다.

이미 설치·빌드한 화면만 실행할 때:

```powershell
.\scripts\run-local.ps1 -SkipBuild
```

Python 3.12로 **새 가상환경**을 만들 때만 `-PythonVersion 3.12`를 지정합니다. 기존 가상환경은 이 옵션으로 재생성하지 않습니다.

다운로드 차단 때문에 실행되지 않는 경우 자신이 확인한 해당 파일에만 `Unblock-File -LiteralPath '.\scripts\run-local.ps1'`을 적용합니다. AllSigned/Restricted 또는 조직 정책은 변경하지 않습니다.

## KAMIS 자체 API 인증으로 실행

KAMIS 자체 Open API 인증 ID와 KEY를 준비합니다. **공공데이터포털 serviceKey와 서로 다릅니다.** 두 값을 채팅·소스·명령어 문자열에 쓰지 않습니다.

```powershell
.\scripts\run-local.ps1 -WithKamis -SkipBuild
```

ID와 KEY를 각각 가려진 입력란으로 받습니다. 이번 PowerShell 프로세스와 자식 서버의 환경변수로만 설정하며 파일·사용자/시스템 환경설정에 저장하지 않습니다. 서버 종료 시 이전 프로세스 환경값으로 복원합니다. `.env.example`은 변수명 안내이며 `.env`를 자동 로딩하지 않습니다.

브라우저의 **KAMIS 가격 흐름**에서 기간·지역·품종·등급을 확인하고 조회합니다. 실제 응답의 품목·품종·등급·단위와 공식 화면 수치를 대조한 뒤 **조회·분석 근거 JSON 저장**, **선택 가격표 CSV 저장**을 사용합니다. 조회 성공이 현재 명세·단위·현장 효과를 모두 검증했다는 뜻은 아닙니다.

실패 화면은 인증/조건/연결/응답 형식을 구분합니다. 오류 화면과 인증값을 가린 상태 정보만 공유하고 키는 보내지 않습니다. 공식 기간별 API 명세 및 코드표를 대조하는 작업은 아직 남아 있습니다.

## 개발과 검증

프로젝트 루트에서:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
Push-Location frontend
npm.cmd run dev
Pop-Location
```

Vite 개발 프록시는 `/api`를 8000 포트로 전달합니다. API 문서는 백엔드 실행 후 `http://127.0.0.1:8000/docs`입니다. 화면 수정 후 `npm.cmd run build`를 실행하고 서버를 재시작합니다.
