@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo =============================================
echo       Podcast 音频标签批量更新工具
echo =============================================
echo.
echo 将扫描本目录及子目录中带有 podcast.json 的节目文件夹。
echo 默认只修改标签和内嵌封面，不会重新编码音频。
echo 建议先运行 预览标签.bat 检查结果。
echo.
set /p CONFIRM=确认写入所有标签吗？输入 Y 继续：
if /I not "%CONFIRM%"=="Y" (
  echo 已取消，文件未修改。
  pause
  exit /b 0
)
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import mutagen" >nul 2>&1
  if errorlevel 1 (
    echo 正在安装依赖 mutagen...
    py -3 -m pip install --user mutagen
    if errorlevel 1 goto :error
  )
  py -3 update_podcast_tags.py --apply
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
  python update_podcast_tags.py --apply
  goto :done
)
echo 未检测到 Python 3。请先安装 Python 3，并勾选 Add Python to PATH。
goto :error
:done
echo.
echo 处理完毕。请查看 podcast_tag_update_log.txt。
pause
exit /b 0
:error
echo.
echo 运行失败，请检查上方错误信息。
pause
exit /b 1
