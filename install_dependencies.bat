@echo off
setlocal
py -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo Installation failed. Check your Python and internet connection.
  pause
  exit /b 1
)
echo.
echo Pillow installed.
pause
