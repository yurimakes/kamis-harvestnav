# 로컬 실행과 개발

현재 가격 조회는 공공데이터포털 `perRegion/price`입니다. Python 3.12 또는 3.13, Node.js 22.12 이상을 사용합니다. 개발 검증 환경은 Linux Python 3.12.14 / Node.js 24.22.1이며, Windows에서는 Python 3.13 가상환경의 테스트·빌드·실행 출력과 화면이 확인됐습니다. 모든 Windows 환경을 검증했다는 뜻은 아닙니다.

## Windows 최초 설치

VS Code에서 저장소 폴더를 열고 프로젝트 루트의 PowerShell 터미널에서 순서대로 실행합니다. 기존 `.venv`는 재생성하지 않습니다.

```powershell
if (-not (Test-Path -LiteralPath '.\.venv\Scripts\python.exe')) {
    py -3.13 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw '가상환경 생성 실패' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python 의존성 설치 실패' }
npm.cmd --prefix frontend ci
if ($LASTEXITCODE -ne 0) { throw '프론트엔드 의존성 설치 실패' }
npm.cmd --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw '프론트엔드 빌드 실패' }
```

Python 3.12로 새 가상환경을 만들 경우에만 생성 명령의 `-3.13`을 `-3.12`로 바꿉니다. 가상환경 활성화나 PowerShell 실행 정책 변경은 필요하지 않습니다.

## 인증키를 한 번 저장한 뒤 실행

[로컬 인증키 관리](local-env.md)에 따라 VS Code에서 프로젝트 루트 `.env`를 작성합니다. 공공데이터포털 serviceKey를 사용하며 KAMIS 자체 인증 ID/KEY와 혼용하지 않습니다.

```powershell
& '.\.venv\Scripts\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

화면: `http://127.0.0.1:8000`, API 문서: `http://127.0.0.1:8000/docs`, 종료: Ctrl+C. 인증이 없어도 합성 계산과 지도는 실행됩니다. `.env`만 존재한다고 승인·실제 조회가 성공한 것은 아닙니다.

기존 실행 스크립트를 사용할 수 있는 환경에서는 `.\scripts\run-local.ps1 -SkipBuild`도 가능합니다. `-WithPortal`은 저장된 유효 키가 없을 때만 프로세스용 입력을 받습니다. 서명 정책으로 스크립트가 차단되면 위 Python 직접 명령을 사용합니다.

## 수정 후 검증

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q
if ($LASTEXITCODE -ne 0) { throw '테스트 실패' }
npm.cmd --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw '프론트엔드 빌드 실패' }
```

화면 파일을 수정한 뒤에는 빌드하고 서버를 다시 시작합니다. API 자동 테스트는 임시 설정과 합성 응답을 사용하며 실제 인증 조회를 대신하지 않습니다.

개발 서버가 필요하면 백엔드는 위 Python 명령으로 실행하고, 별도 터미널에서 `npm.cmd --prefix frontend run dev`를 실행합니다. Vite의 `/api` 프록시는 백엔드 8000 포트로 연결됩니다.
