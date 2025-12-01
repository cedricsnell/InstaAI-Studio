@echo off
echo ================================================
echo   InstaAI Studio - Analytics API Server
echo ================================================
echo.
echo Starting on: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo ================================================
echo.

cd /d "%~dp0"
py -m src.api.main

pause
