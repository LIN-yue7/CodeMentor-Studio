param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Push-Location $repo
try {
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        & $Python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
    }
    & ./.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    & npm.cmd --prefix workbench-web ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & npm.cmd --prefix workbench-web run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    if (-not (Test-Path -LiteralPath '.env')) {
        $bytes = New-Object byte[] 32
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
        $sessionKey = [Convert]::ToBase64String($bytes)
        @('CODEMENTOR_AI_MODE=local', 'LLM__MAX_RETRIES=0', 'DATABASE__SQLITE_PATH=./data/studio.db', "CODEMENTOR_SESSION_SECRET=$sessionKey") | Set-Content -LiteralPath '.env' -Encoding UTF8
    }
    Write-Output 'Ready. Run Start-Studio.cmd and open http://127.0.0.1:8780/ .'
} finally { Pop-Location }
