@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

echo ========================================
echo  Valve Knowledge Base V1
echo  Vue3 + FastAPI + SQLite
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Please install Python 3.11+ and enable Add Python to PATH.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js/npm not found. Please install Node.js 20+.
  pause
  exit /b 1
)

if not exist backend\.venv\Scripts\python.exe (
  echo [1/4] Creating Python virtual environment...
  python -m venv backend\.venv
  if errorlevel 1 goto :fail
) else (
  echo [1/4] Python virtual environment exists.
)

echo [2/4] Installing backend dependencies...
call backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 goto :fail

if not exist frontend\node_modules (
  echo [3/4] Installing frontend dependencies...
  pushd frontend
  call npm install
  if errorlevel 1 (
    echo Default npm registry failed. Retrying with npmmirror...
    call npm install --registry=https://registry.npmmirror.com
  )
  if errorlevel 1 (
    popd
    goto :fail
  )
  popd
) else (
  echo [3/4] Frontend dependencies already installed.
)

echo [4/4] Starting services...
start "ValveKB-Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "ValveKB-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Web : http://localhost:5173
echo API : http://127.0.0.1:8000/docs
echo DB  : backend\data\valve_knowledge.db
echo.
timeout /t 4 /nobreak >nul
start "" http://localhost:5173
exit /b 0

:fail
echo.
echo [ERROR] Installation/startup failed. Keep this window and check the error above.
pause
exit /b 1
