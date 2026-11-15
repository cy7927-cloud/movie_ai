@echo off
chcp 65001 >nul
cd /d "%~dp0"
python verify_release.py || (echo Integrity check failed & pause & exit /b 1)
python -m unittest discover -s tests -v
pause
