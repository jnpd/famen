@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0

if "%~1"=="" (
  echo ========================================
  echo  Valve Knowledge Base - Workbook Import
  echo ========================================
  echo.
  echo Drag an Excel file onto this BAT file,
  echo or enter the full Excel path below.
  echo.
  set /p "EXCEL_PATH=Excel path: "
) else (
  set "EXCEL_PATH=%~1"
)

if "%EXCEL_PATH%"=="" (
  echo [ERROR] Excel path is empty.
  pause
  exit /b 1
)
if not exist "%EXCEL_PATH%" (
  echo [ERROR] File not found:
  echo %EXCEL_PATH%
  pause
  exit /b 1
)
if not exist backend\.venv\Scripts\python.exe (
  echo [ERROR] Python virtual environment not found.
  echo Run start.bat once first.
  pause
  exit /b 1
)

echo.
echo Workbook:
echo %EXCEL_PATH%
echo.
echo Rules:
echo - Detect sheet headers automatically
echo - Skip description/index/summary sheets by default
echo - Skip confidence below 60 percent
echo - Preserve/infer engineering units
echo - Existing datasets with same name are skipped
echo.

call backend\.venv\Scripts\python.exe backend\scripts\import_workbook.py "%EXCEL_PATH%"
set ERR=%ERRORLEVEL%

echo.
if not "%ERR%"=="0" (
  echo [ERROR] Workbook import failed.
) else (
  echo [SUCCESS] Import finished. Reload the browser.
)
echo.
pause
exit /b %ERR%
