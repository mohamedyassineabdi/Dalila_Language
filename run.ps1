$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:ASR_DEVICE = 'cpu'
$env:ASR_COMPUTE_TYPE = 'int8'
$env:ASR_THREADS = '4'
if (-not $env:ASR_BEAM_SIZE) { $env:ASR_BEAM_SIZE = '1' }
$env:OLLAMA_NO_CLOUD = '1'
if (-not $env:DALILA_GENERAL_ASR) { $env:DALILA_GENERAL_ASR = 'base' }
$env:DALILA_PREPARE_MODELS = '1'
$python = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { & powershell -ExecutionPolicy Bypass -File .\setup.ps1; if ($LASTEXITCODE -ne 0) { throw 'Setup failed' } }
& $python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('espeakng_loader') else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing multilingual offline speech voices (one-time download, about 10 MB)...'
    & $python -m pip install -r requirements-tts.txt
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Offline voice package installation failed; other installed voices remain available.' }
}
& $python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('piper') else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing local neural speech engine (one-time)...'
    & $python -m pip install -r requirements-neural-tts.txt
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Neural speech unavailable; offline fallback remains.' }
}
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) {
    try {
        $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3
    } catch {
        Start-Process -FilePath $ollama.Source -ArgumentList 'serve' -WindowStyle Hidden
        for ($i=0; $i -lt 20; $i++) { Start-Sleep -Seconds 1; try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2; break } catch {} }
    }
    $selected = & $python -c "from app import installed_ollama_model; print(installed_ollama_model() or '')"
    $preferred = & $python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OLLAMA_MODEL','qwen3:4b'))"
    if ((-not $selected) -or ($preferred -eq 'qwen3:4b' -and $selected -eq 'qwen3:8b')) {
        Write-Host 'Preparing the faster Qwen3 4B model (one-time download, several GB)...'
        & $ollama.Source pull qwen3:4b
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Model download failed. Limited local fallback remains available.' }
    }
} else {
    Write-Warning 'Ollama executable not found. Limited fallback remains available.'
}
Write-Host 'Starting Dalila v0.7.0 at http://127.0.0.1:7860'
& $python -m uvicorn app:app --host 127.0.0.1 --port 7860
