@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title CandyProject Dev

echo.
echo  ==========================================
echo   CandyProject ^— Dev Environment Launcher
echo  ==========================================
echo.

:: ── 1. Check prerequisites ────────────────────────────────────────────────────

where python >nul 2>&1 || (
    echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
    pause & exit /b 1
)
where node >nul 2>&1 || (
    echo [ERROR] Node.js not found. Install Node.js 18+ and add to PATH.
    pause & exit /b 1
)
where npm >nul 2>&1 || (
    echo [ERROR] npm not found. Install Node.js 18+ and add to PATH.
    pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER%
for /f "tokens=1" %%v in ('node --version') do set NODE_VER=%%v
echo [OK] Node.js %NODE_VER%
echo.

:: ── 2. Python venv ────────────────────────────────────────────────────────────

if not exist ".venv\" (
    echo [1/4] Creating Python virtual environment...
    python -m venv .venv
    if errorlevel 1 ( echo [ERROR] Failed to create venv. & pause & exit /b 1 )
    echo       Done.
) else (
    echo [1/4] Python venv already exists, skipping creation.
)

:: ── 3. Install / upgrade Python deps ─────────────────────────────────────────

echo [2/4] Installing Python dependencies...
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"
if errorlevel 1 ( echo [ERROR] pip install failed. & pause & exit /b 1 )
echo       Done.

:: ── 4. Copy .env if missing ───────────────────────────────────────────────────

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo       Created .env from .env.example
)

:: ── 5. Install / update Node deps ────────────────────────────────────────────

echo [3/4] Installing Node.js dependencies...
cd web
if not exist "node_modules\" (
    npm install --silent
) else (
    npm install --silent
)
if errorlevel 1 ( echo [ERROR] npm install failed. & cd .. & pause & exit /b 1 )
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo       Created web\.env from web\.env.example
)
cd ..
echo       Done.

:: ── 6. Launch backend + frontend in separate windows ─────────────────────────

echo [4/4] Starting servers...
echo.
echo   Backend  ^(FastAPI^)  →  http://localhost:8000
echo   Frontend ^(Vite^)     →  http://localhost:5173
echo   API Docs            →  http://localhost:8000/docs
echo.

:: Backend window
start "Candy API" cmd /k "call .venv\Scripts\activate.bat && uvicorn candy.main:app --host 0.0.0.0 --port 8000 --reload"

:: Short pause so backend has a head start
timeout /t 2 /nobreak >nul

:: Frontend window
start "Candy Web" cmd /k "cd web && npm run dev"

echo  Both servers launched in separate windows.
echo  Close this window or press Ctrl+C to stop.
echo.
pause
