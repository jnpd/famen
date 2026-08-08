@echo off
setlocal
cd /d %~dp0

if "%~1"=="" (
  echo ========================================
  echo  Valve Knowledge Base - Excel Batch Import
  echo ========================================
  echo.
  set /p "EXCEL_PATH=请输入 Excel 完整路径: "
) else (
  set "EXCEL_PATH=%~1"
)

if "%EXCEL_PATH%"=="" (
  echo [ERROR] 未提供 Excel 文件。
  pause
  exit /b 1
)

if not exist "%EXCEL_PATH%" (
  echo [ERROR] 文件不存在: %EXCEL_PATH%
  pause
  exit /b 1
)

if not exist backend\.venv\Scripts\python.exe (
  echo [INFO] 未发现后端虚拟环境，先运行 start.bat 初始化项目。
  pause
  exit /b 1
)

echo.
echo 即将批量导入：
echo %EXCEL_PATH%
echo.
echo 默认规则：
echo - 自动识别每个 Sheet 的表头
 echo - 自动跳过目录/说明/汇总/索引类 Sheet
 echo - 可信度低于 60%% 的 Sheet 不自动写入
 echo - 自动推荐到基础字典/标准数字/参数/材料/公式/BOM规则库
 echo - 已存在同名数据集默认跳过，避免重复导入
 echo.

call backend\.venv\Scripts\python.exe backend\scripts\import_workbook.py "%EXCEL_PATH%"
set ERR=%ERRORLEVEL%

echo.
if not "%ERR%"=="0" (
  echo [ERROR] 导入失败，请把上面的错误信息发给 ChatGPT。
) else (
  echo [SUCCESS] 导入完成。刷新浏览器页面即可查看。
)
echo.
pause
exit /b %ERR%
