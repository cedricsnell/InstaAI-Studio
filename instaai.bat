@echo off
REM InstaAI Studio - Windows Batch Script
REM This makes it easier to run the CLI on Windows

cd /d "%~dp0src"
python main.py %*
