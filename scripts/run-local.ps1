param(
    [Alias('WithKamis')][switch]$WithPortal,
    [switch]$SkipBuild,
    [ValidateSet('3.13', '3.12')][string]$PythonVersion = '3.13'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $projectRoot

$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonPath)) {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python Launcher(py)와 Python 3.13이 필요합니다.'
    }
    & py "-$PythonVersion" -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 가상환경 생성 실패' }
}
if (-not $SkipBuild) {
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'Node.js 22.12 이상과 npm.cmd가 필요합니다.'
    }
    & $pythonPath -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python 의존성 설치 실패' }
    Push-Location (Join-Path $projectRoot 'frontend')
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw '프론트엔드 의존성 설치 실패' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw '프론트엔드 빌드 실패' }
    } finally { Pop-Location }
} elseif (-not (Test-Path (Join-Path $projectRoot 'frontend\dist\index.html'))) {
    throw '빌드된 화면이 없습니다. -SkipBuild 없이 먼저 실행하세요.'
}

$previousKey = [Environment]::GetEnvironmentVariable('DATA_GO_KR_SERVICE_KEY', 'Process')
try {
    & $pythonPath -c "from backend.app.services.portal import configured; raise SystemExit(0 if configured() else 1)"
    $hasPortalKey = ($LASTEXITCODE -eq 0)
    if ($WithPortal -and -not $hasPortalKey) {
        Write-Host '공공데이터포털 인증키(serviceKey)를 입력하세요. 일반 인증키 Decoding 값을 권장합니다.'
        Write-Host '인증키는 화면에 표시하거나 파일에 저장하지 않고 이번 서버 프로세스에서만 사용합니다.'
        foreach ($variable in @('DATA_GO_KR_SERVICE_KEY')) {
            $secret = Read-Host -Prompt $variable -AsSecureString
            $pointer = [IntPtr]::Zero
            try {
                $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
                $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
                if ([string]::IsNullOrWhiteSpace($plain)) { throw '빈 인증값은 사용할 수 없습니다.' }
                [Environment]::SetEnvironmentVariable($variable, $plain, 'Process')
            } finally {
                $plain = $null
                if ($pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
                $secret.Dispose()
            }
        }
    }
    Write-Host 'HarvestNav: http://127.0.0.1:8000 (종료: Ctrl+C)'
    & $pythonPath -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
    if ($LASTEXITCODE -ne 0) { throw '서버 실행 실패' }
} finally {
    [Environment]::SetEnvironmentVariable('DATA_GO_KR_SERVICE_KEY', $previousKey, 'Process')
}
