@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -c "import cv2,numpy,PIL,skimage" >nul 2>&1
if errorlevel 1 (
    echo Installing missing offline-only Python dependencies...
    python -m pip install -r requirements.txt || (echo Dependencies unavailable. See README.md & pause & exit /b 1)
)
python production_cli.py status || (echo Project files incomplete & pause & exit /b 1)
start "" "http://127.0.0.1:8766"
python studio_product.py --port 8766
pause
