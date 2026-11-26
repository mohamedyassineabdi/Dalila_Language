$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3.11 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 first.' }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependencies failed to install.' }
if (!(Test-Path .env)) { Copy-Item .env.example .env }
Write-Host 'Done. Run .\run.ps1 after installing Ollama and pulling a model.'
