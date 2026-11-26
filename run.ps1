$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:ASR_DEVICE = 'cpu'
$env:ASR_COMPUTE_TYPE = 'int8'
$env:ASR_THREADS = '4'
& .\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 7860
