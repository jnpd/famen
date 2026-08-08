@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"

if "%~1"=="" (
  echo ========================================
  echo  Valve Knowledge Base - Workbook Import
  echo ========================================
  echo.
  set /p "EXCEL_PATH=Excel full path: "
) else (
  set "EXCEL_PATH=%~1"
)

if "%EXCEL_PATH%"=="" (
  echo [ERROR] No Excel file was provided.
  pause
  exit /b 1
)

if not exist "%EXCEL_PATH%" (
  echo [ERROR] File not found:
  echo "%EXCEL_PATH%"
  pause
  exit /b 1
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo [ERROR] Python virtual environment was not found.
  echo Run start.bat once, then try again.
  pause
  exit /b 1
)

echo.
echo Workbook:
echo "%EXCEL_PATH%"
echo.
echo Rules:
echo - Detect each sheet header automatically.
echo - Skip metadata, description, summary and index sheets by default.
echo - Skip sheets below 60%% confidence by default.
echo - Route detected tables to the most suitable knowledge base.
echo - Skip an existing dataset with the same name by default.
echo.

call "backend\.venv\Scripts\python.exe" "backend\scripts\import_workbook.py" "%EXCEL_PATH%"
set "ERR=%ERRORLEVEL%"

echo.
if not "%ERR%"=="0" (
  echo [ERROR] Import failed. Copy the error text above to ChatGPT.
) else (
  echo [SUCCESS] Import finished. Refresh the browser page.
)
echo.
pause
exit /b %ERR%
