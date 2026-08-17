# mydart-mcp 설치 스크립트 (Windows)
#
#   1) 이 파일이 있는 폴더에서 주소창에 powershell 입력 → 엔터
#   2) 아래 한 줄 실행
#        powershell -ExecutionPolicy Bypass -File .\install.ps1
#
# 인증키를 물어본다. 미리 주려면:
#        powershell -ExecutionPolicy Bypass -File .\install.ps1 -ApiKey "발급받은키"

param([string]$ApiKey = "")

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }

function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
function Ok($text)   { Write-Host "   OK  $text" -ForegroundColor Green }
function Warn($text) { Write-Host "   !!  $text" -ForegroundColor Yellow }

Write-Host "mydart-mcp 설치" -ForegroundColor White
Write-Host "설치 폴더: $root"

# --- 0. Microsoft Store 버전 Claude 확인 --------------------------------------
# Store 버전은 설정 파일을 격리된 폴더에서 읽어, 표준 위치에 넣어도 인식하지 못한다.
Step "Claude 버전 확인"
if (Get-Command Get-AppxPackage -ErrorAction SilentlyContinue) {
    if (Get-AppxPackage *Claude* -ErrorAction SilentlyContinue) {
        Warn "Microsoft Store 버전 Claude가 설치돼 있습니다."
        Warn "이 상태로는 설정을 넣어도 Claude가 읽지 못합니다. 먼저 아래를 실행하세요:"
        Warn "    Get-AppxPackage *Claude* | Remove-AppxPackage"
        Warn "그다음 https://claude.ai/download 에서 정식 버전을 설치하고 다시 실행하세요."
        exit 1
    }
}
Ok "Store 버전 없음"

# --- 1. 인증키 -----------------------------------------------------------------
# 이미 설정에 들어 있으면 그대로 쓴다. 재설치할 때 다시 입력하지 않아도 된다.
Step "OpenDART 인증키"
$configPath = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
if (-not $ApiKey -and (Test-Path $configPath)) {
    try {
        $ApiKey = (Get-Content $configPath -Raw | ConvertFrom-Json).mcpServers.mydart.env.DART_API_KEY
        if ($ApiKey) { Ok "기존 설정에서 인증키를 찾았습니다." }
    } catch { $ApiKey = "" }
}
if (-not $ApiKey) {
    Write-Host "   https://opendart.fss.or.kr 에서 무료로 발급받을 수 있습니다 (40자리)."
    $ApiKey = (Read-Host "   인증키를 붙여넣고 엔터").Trim()
}
if (-not $ApiKey) { throw "인증키가 없으면 설치해도 조회가 되지 않습니다." }
Ok "$($ApiKey.Length)자 확인 (화면에 키는 표시하지 않습니다)"

# --- 2. uv 설치 ---------------------------------------------------------------
Step "uv 준비"
$uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path $uv)) {
    $found = (Get-Command uv -ErrorAction SilentlyContinue).Source
    if ($found) { $uv = $found }
}
if (-not (Test-Path $uv)) {
    Write-Host "   uv가 없어 설치합니다 (1분 내외)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
    $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
}
if (-not (Test-Path $uv)) { throw "uv 설치에 실패했습니다. https://astral.sh/uv 를 참고하세요." }
Ok (& $uv --version)

# --- 3. 실행 중인 서버 종료 ---------------------------------------------------
# 돌고 있으면 실행 파일이 잠겨 설치가 "액세스가 거부되었습니다"로 실패한다.
Step "실행 중인 Claude / 서버 종료"
Get-Process Claude, mydart-mcp -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500
Ok "종료 완료"

# --- 4. 프로그램 설치 ---------------------------------------------------------
Step "mydart-mcp 설치"
if (-not (Test-Path (Join-Path $root "pyproject.toml"))) {
    throw "pyproject.toml이 없습니다. 압축을 푼 폴더 중 pyproject.toml이 바로 보이는 폴더에서 실행하세요."
}
& $uv tool install --force $root
$exe = Join-Path $env:USERPROFILE ".local\bin\mydart-mcp.exe"
if (-not (Test-Path $exe)) { throw "설치는 됐는데 $exe 를 찾지 못했습니다." }
Ok $exe

# --- 5. Claude 설정에 등록 ----------------------------------------------------
# 기존 서버(myacc 등)는 건드리지 않고 mydart만 추가한다.
Step "Claude 설정 등록"
if (Test-Path $configPath) {
    Copy-Item $configPath "$configPath.bak" -Force
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path $configPath) | Out-Null
    $config = [pscustomobject]@{}
}
if (-not $config.mcpServers) {
    $config | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{}) -Force
}
$server = [ordered]@{ command = $exe; env = [ordered]@{ DART_API_KEY = $ApiKey } }
$config.mcpServers | Add-Member -NotePropertyName mydart -NotePropertyValue $server -Force
[System.IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 30))
Ok $configPath
Ok ("등록된 서버: " + (($config.mcpServers.PSObject.Properties.Name) -join ", "))

# --- 6. DART 연결 확인 --------------------------------------------------------
# Claude에 붙이기 전에 여기서 걸러야 원인이 한 곳으로 좁혀진다.
Step "DART 연결 확인"
$env:DART_API_KEY = $ApiKey
$selftest = Join-Path $env:USERPROFILE ".local\bin\mydart-mcp-selftest.exe"
if (Test-Path $selftest) {
    & $selftest
} else {
    Warn "자체점검 프로그램을 찾지 못했습니다. 나중에 mydart-mcp-selftest 로 확인하세요."
}

Write-Host "`n끝났습니다." -ForegroundColor Green
Write-Host "Claude Desktop을 실행하고 설정 → 개발자에서 mydart 를 확인하세요."
Write-Host "위 자체점검이 6개 모두 통과였다면 DART 쪽은 정상입니다."
