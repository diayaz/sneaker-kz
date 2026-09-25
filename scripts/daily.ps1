# Ежедневная задача: курсы Нацбанка + все парсеры. Логи — backend\logs\daily_<дата>.log
$ErrorActionPreference = "Stop"
$backend = Resolve-Path (Join-Path $PSScriptRoot "..\backend")
Set-Location $backend
$env:PYTHONIOENCODING = "utf-8"
& "$backend\.venv\Scripts\python.exe" manage.py daily
exit $LASTEXITCODE
