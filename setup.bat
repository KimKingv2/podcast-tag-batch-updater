@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo =============================================
echo     Podcast Tag Batch Updater - Setup
echo =============================================
echo.
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -m pip install --user -r requirements.txt
  if errorlevel 1 goto :error
  goto :done
)
where python >nul 2>&1
if not errorlevel 1 (
  python -m pip install --user -r requirements.txt
  if errorlevel 1 goto :error
  goto :done
)
echo Python 3 was not found. Install Python 3 and enable Add Python to PATH.
goto :error
:done
echo.
echo Dependencies installed.
pause
exit /b 0
:error
echo.
echo Installation failed. Check the error above.
pause
exit /b 1
