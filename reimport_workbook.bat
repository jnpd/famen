@echo off
setlocal
chcp 65001 >nul
cd /d %~dp0

if "%~1"=="" (
  echo ========================================
  echo  Valve Knowledge Base - Workbook Refresh
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
echo WARNING:
echo Existing datasets with the same name will be replaced.
echo Use this when refreshing source Excel data or fixing field metadata such as units.
echo.
choice /C YN /M "Continue"
if errorlevel 2 exit /b 0

echo.
call backend\.venv\Scripts\python.exe backend\scripts\import_workbook.py "%EXCEL_PATH%" --replace
set ERR=%ERRORLEVEL%

echo.
if not "%ERR%"=="0" (
  echo [ERROR] Workbook refresh failed.
) else (
  echo [SUCCESS] Workbook refreshed. Reload the browser.
)
echo.
pause
exit /b %ERR%
