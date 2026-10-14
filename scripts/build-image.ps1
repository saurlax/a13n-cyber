param(
    [string]$Image = 'a13n-cyber:dev',
    [string]$PythonBaseImage = 'python:3.13-slim-bookworm',
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
        docker image save -o dist/a13n-cyber.tar $Image
        if ($LASTEXITCODE -ne 0) { throw 'Docker image export failed' }
        Get-FileHash -Algorithm SHA256 -LiteralPath dist/a13n-cyber.tar
    }
} finally { Pop-Location }
