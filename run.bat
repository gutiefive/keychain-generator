@echo off
setlocal

set ROOT=%~dp0

echo ========================================
echo   Keychain Generator
echo ========================================
echo.

:: ── Backend ──────────────────────────────
echo [1/4] Setting up Python backend...
cd /d "%ROOT%backend"

if not exist "venv" (
    echo       Creating virtual environment...
    py -3 -m venv venv
)

call venv\Scripts\activate.bat
echo [2/4] Installing Python dependencies...
pip install -q -r requirements.txt

echo [3/4] Starting FastAPI on :8000...
start "Keychain-Backend" cmd /c "venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: ── Frontend ─────────────────────────────
cd /d "%ROOT%frontend"

if not exist "node_modules" (
    echo       Installing npm packages...
    call npm install
)

echo [4/4] Starting Vite on :5173...
start "Keychain-Frontend" cmd /c "npm run dev"

echo.
echo   ======================================
echo     Keychain Generator is running!
echo     Frontend: http://localhost:5173
echo     Backend:  http://localhost:8000
echo   ======================================
echo.
echo   Close this window to stop both servers.
pause
