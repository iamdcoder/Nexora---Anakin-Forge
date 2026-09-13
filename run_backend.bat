@echo off
setlocal
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo .venv not found. Run setup.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set "PYTHONPATH=%~dp0;%~dp0backend"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
