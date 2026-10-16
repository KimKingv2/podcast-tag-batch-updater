@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import mutagen" >nul 2>&1
  if errorlevel 1 (
    echo 正在安装依赖 mutagen...
    py -3 -m pip install --user mutagen
    if errorlevel 1 goto :error
  )
  py -3 update_podcast_tags.py --dry-run
  goto :done
)
where python >nul 2>&1
if not errorlevel 1 (
  python -c "import mutagen" >nul 2>&1
  if errorlevel 1 (
    echo 正在安装依赖 mutagen...
    python -m pip install --user mutagen
    if errorlevel 1 goto :error
  )
  python update_podcast_tags.py --dry-run
  goto :done
)
echo 未检测到 Python 3。请先安装 Python 3，并勾选 Add Python to PATH。
goto :error
:done
echo.
echo 以上仅为预览，没有修改音频文件。
pause
exit /b 0
:error
echo 运行失败，请检查上方错误信息。
pause
exit /b 1
