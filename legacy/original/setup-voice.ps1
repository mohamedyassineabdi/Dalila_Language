param([switch]$Cuda)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3.11 -m venv .venv-voice
if ($LASTEXITCODE -ne 0) { throw 'Python environment failed.' }
$p = '.\.venv-voice\Scripts\python.exe'
& $p -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
$index = if ($Cuda) { 'https://download.pytorch.org/whl/cu128' } else { 'https://download.pytorch.org/whl/cpu' }
& $p -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url $index
if ($LASTEXITCODE -ne 0) { throw 'PyTorch install failed.' }
& $p -m pip install -r requirements-voice.txt
if ($LASTEXITCODE -ne 0) { throw 'Voice dependencies failed.' }
Write-Host 'Voice packages installed. For CUDA change TTS_DEVICE=cuda in .env.'
