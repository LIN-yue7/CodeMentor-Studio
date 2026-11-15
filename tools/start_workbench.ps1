
param(
    [string]$Python = "python",
    [ValidateRange(1024, 65535)][int]$Port = 8765,
    [switch]$Live
)
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
Push-Location $repo
try {
    if (-not (Test-Path -LiteralPath "workbench-web/dist/index.html")) {
        throw "Build the workspace first: npm --prefix workbench-web ci; npm --prefix workbench-web run build"
    }
    $previous = $env:CODEMENTOR_AI_MODE
    $previousRetries = $env:LLM__MAX_RETRIES
    try {
        $env:CODEMENTOR_AI_MODE = if ($Live) { "live" } else { "local" }
        if ($Live) { $env:LLM__MAX_RETRIES = "0" }
        $environmentArgs = @()
        if (Test-Path -LiteralPath '.env') { $environmentArgs = @('--env-file', '.env') }
        & $Python -m uvicorn app.workbench:app @environmentArgs --host 127.0.0.1 --port $Port --limit-concurrency 32
        if ($LASTEXITCODE -ne 0) { throw "CodeMentor failed to start." }
    } finally {
        $env:CODEMENTOR_AI_MODE = $previous
        $env:LLM__MAX_RETRIES = $previousRetries
    }
} finally {
    Pop-Location
}
