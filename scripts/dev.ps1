$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "backend\.venv\Scripts\python.exe")) {
  python -m venv backend\.venv
  & backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
}
if (-not (Test-Path "frontend\node_modules")) {
  Push-Location frontend; npm install; Pop-Location
}
if (-not (Test-Path "tools\cursor-runner\node_modules")) {
  Push-Location tools\cursor-runner; npm install; Pop-Location
}

Write-Host "API  http://127.0.0.1:8787"
Write-Host "UI   http://127.0.0.1:5173"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8787"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
