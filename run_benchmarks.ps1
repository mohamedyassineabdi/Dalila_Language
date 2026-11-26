param([int]$Limit=60,[switch]$AcceptPublicTerms,[switch]$IncludeLarge,[switch]$Cuda)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$p='.\.venv\Scripts\python.exe'
if (!(Test-Path $p)) { & .\setup.ps1 }
if (!$AcceptPublicTerms) { throw 'Read reports/MODEL_AND_DATA_REVIEW.md; then use -AcceptPublicTerms if authorized.' }
& $p -m pip install -r requirements-benchmark.txt
if ($LASTEXITCODE -ne 0) { throw 'Benchmark dependency installation failed' }
$models=@('tn-small','tn-whisperx','small')
if ($IncludeLarge) {
  & $p -m pip install -r requirements-convert.txt
  if ($LASTEXITCODE -ne 0) { throw 'Conversion dependency installation failed' }
  $models+=@('turbo','tn-codeswitch')
}
if ($Cuda) { $env:ASR_DEVICE='cuda';$env:ASR_COMPUTE_TYPE='int8_float16' }
else { $env:ASR_DEVICE='cpu';$env:ASR_COMPUTE_TYPE='int8' }
& $p verify_models.py
& $p prepare_models.py --models $models
& $p collect_public_audio.py --limit $Limit --accept-public-terms
if ($LASTEXITCODE -ne 0) { throw 'Dataset collection failed; check network and dataset access' }
$env:ASR_OFFLINE='1'
& $p evaluate.py --audio data/public_linto/manifest.jsonl --public --models $models --out reports/public_asr.json
if ($LASTEXITCODE -ne 0) { throw 'Benchmark failed' }
Write-Host 'See reports/public_asr.json and reports/prepared_models.json. Inspect coverage before comparing scores.'
