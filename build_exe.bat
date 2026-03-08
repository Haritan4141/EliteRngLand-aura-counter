@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean EliteRngLandAuraTool.spec

echo.
echo Build completed.
echo EXE: dist\EliteRngLandAuraTool.exe
echo.
pause

