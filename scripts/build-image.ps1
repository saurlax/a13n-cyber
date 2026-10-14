param(
    [string]$Image = 'tsec-step-agent:dev',
    [string]$PythonBaseImage = 'python:3.12-slim-bookworm',
    [switch]$Export
)
$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $repoPath
try {
    docker build --platform linux/amd64 --build-arg "PYTHON_BASE_IMAGE=$PythonBaseImage" -t $Image .
    if ($LASTEXITCODE -ne 0) { throw 'Docker build failed' }
    docker run --rm --network none $Image doctor
    if ($LASTEXITCODE -ne 0) { throw 'Offline image self-check failed' }
    if ($Export) {
        New-Item -ItemType Directory -Force dist | Out-Null
        docker image save -o dist/tsec-step-agent.tar $Image
        if ($LASTEXITCODE -ne 0) { throw 'Docker image export failed' }
        Get-FileHash -Algorithm SHA256 -LiteralPath dist/tsec-step-agent.tar
    }
} finally { Pop-Location }
