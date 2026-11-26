$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:ASR_DEVICE = 'cpu'
$env:ASR_COMPUTE_TYPE = 'int8'
$env:ASR_THREADS = '4'
$env:OLLAMA_NO_CLOUD = '1'
$python = '.\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { & powershell -ExecutionPolicy Bypass -File .\setup.ps1; if ($LASTEXITCODE -ne 0) { throw 'Setup failed' } }
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) {
    try {
        $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3
    } catch {
        Start-Process -FilePath $ollama.Source -ArgumentList 'serve' -WindowStyle Hidden
        for ($i=0; $i -lt 20; $i++) { Start-Sleep -Seconds 1; try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2; break } catch {} }
    }
    & $python -c "from dalila.llm import installed_ollama_model; import sys; sys.exit(0 if installed_ollama_model() else 1)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'No supported local model found. Downloading Qwen3 4B once (several GB)...'
        & $ollama.Source pull qwen3:4b
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Model download failed. Limited local fallback remains available.' }
    }
} else {
    Write-Warning 'Ollama executable not found. Limited fallback remains available.'
}
Write-Host 'Starting Dalila v0.4.0 at http://127.0.0.1:7860'
& $python -m uvicorn app:app --host 127.0.0.1 --port 7860
