$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host 'AI Director - private Qwen3VL gateway smoke test' -ForegroundColor Cyan
Write-Host 'We will send one text request and three compressed movie storyboard frames, NOT the movie.'
Write-Host 'No paid video generation calls.'

if (-not $env:DIRECTOR_GATEWAY_API_KEY) {
  $secure = Read-Host 'Paste API Key (hidden, never saved)' -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { $env:DIRECTOR_GATEWAY_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

try {
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python is not on PATH. Use your existing Python installation.'
  }
  python private_gateway_bridge.py health
  if ($LASTEXITCODE -ne 0) { throw 'Health check failed.' }
  python private_gateway_bridge.py models
  if ($LASTEXITCODE -ne 0) { throw 'Authenticated model list failed.' }
  python private_gateway_bridge.py text
  if ($LASTEXITCODE -ne 0) { throw 'Text inference failed.' }
  python private_gateway_bridge.py vision --task LESSON_LESSON_01
  if ($LASTEXITCODE -ne 0) { throw 'Vision inference failed. Inspect error; do not mark success.' }
  $report = Join-Path $PSScriptRoot 'output\gateway_director_lab\index.html'
  if (Test-Path $report) { Start-Process $report }
  Write-Host 'Model reply obtained; result is an unverified director hypothesis, NOT movie reconstruction approval.' -ForegroundColor Green
}
finally {
  Remove-Item Env:\DIRECTOR_GATEWAY_API_KEY -ErrorAction SilentlyContinue
}
