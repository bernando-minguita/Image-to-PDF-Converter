@echo off
setlocal
py "%~dp0image_to_pdf.py"
if errorlevel 1 (
  echo.
  echo The app exited with an error.
  pause
)
