@echo off
rem One-time setup: create the venv, install dependencies, download the
rem offline speech model. Re-runnable; skips work that's already done.
cd /d "%~dp0"

echo === Creating virtual environment (.venv) ===
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

echo === Installing dependencies ===
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo === Downloading offline speech model (for speaking challenges) ===
".venv\Scripts\python.exe" setup_models.py

echo.
echo Setup complete. Launch the game with run_wordmine.bat
pause
