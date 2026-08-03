@echo off
REM ============================================================
REM  HR Analysis Dashboard - LOCAL DEV (hot reload, no build)
REM
REM  Opens two windows that both reload on save:
REM    - API      : uvicorn --reload   (restarts on .py changes)
REM    - Frontend : vite dev server    (HMR on .jsx/.css changes)
REM
REM  Use start.bat for deployment; this one never builds and is
REM  bound to localhost only.
REM
REM  Usage:
REM    dev.bat          normal - installs anything missing, migrates, runs
REM    dev.bat fast     skips all setup and launches immediately
REM ============================================================

setlocal enabledelayedexpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "FAST="
if /i "%~1"=="fast" set "FAST=1"

echo ==============================================
echo   HR Analysis Dashboard - local dev mode
echo ==============================================

where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] "uv" is not installed or not on PATH.
    echo         Install it from https://astral.sh/uv and re-run.
    goto :fail
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] "npm" is not installed or not on PATH.
    echo         Install Node.js from https://nodejs.org and re-run.
    goto :fail
)

if not exist "%ROOT%.env" (
    echo [ERROR] .env not found in "%ROOT%".
    echo         Copy .env.example to .env and fill in DB + Google credentials.
    goto :fail
)

REM API_PORT comes from .env so the Vite proxy below can point at it; an
REM already-set environment variable still wins. Dev binds to localhost only.
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "API_PORT=" "%ROOT%.env"`) do set "ENV_API_PORT=%%B"
if "%API_PORT%"=="" set "API_PORT=%ENV_API_PORT%"
if "%API_PORT%"=="" set "API_PORT=8000"
if "%VITE_PORT%"=="" set "VITE_PORT=5173"
set "DEV_API_HOST=127.0.0.1"

if defined FAST (
    echo.
    echo [fast] Skipping dependency install and migrations.
    goto :launch
)

echo.
echo [1/3] Checking backend dependencies...
if not exist "%ROOT%.venv" (
    echo       .venv missing - running uv sync
    call uv sync
    if errorlevel 1 (
        echo [ERROR] uv sync failed.
        goto :fail
    )
) else (
    echo       .venv present - skipping ^(run "uv sync" yourself after editing pyproject^)
)

echo.
echo [2/3] Checking frontend dependencies...
if not exist "%ROOT%frontend\node_modules" (
    echo       node_modules missing - running npm install
    pushd "%ROOT%frontend"
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        popd
        goto :fail
    )
    popd
) else (
    echo       node_modules present - skipping
)

echo.
echo [3/3] Applying database migrations...
call uv run alembic upgrade head
if errorlevel 1 (
    echo [ERROR] alembic upgrade failed. Check DB_* settings in .env
    echo         and that PostgreSQL is running.
    goto :fail
)

:launch
echo.
echo Starting dev servers...

start "DEV API (reload)" /D "%ROOT%" cmd /k "uv run uvicorn backend.api.main:app --reload --host %DEV_API_HOST% --port %API_PORT%"

REM Let uvicorn bind before the proxy in front of it starts.
timeout /t 2 /nobreak >nul

set "VITE_API_PROXY_TARGET=http://127.0.0.1:%API_PORT%"
start "DEV Frontend (Vite HMR)" /D "%ROOT%frontend" cmd /k "set VITE_API_PROXY_TARGET=%VITE_API_PROXY_TARGET% && npm run dev -- --port %VITE_PORT%"

echo.
echo   Open this ....... http://localhost:%VITE_PORT%
echo   API direct ...... http://localhost:%API_PORT%/api
echo   API docs ........ http://localhost:%API_PORT%/docs
echo.
echo   Edit backend/  -^> uvicorn restarts automatically.
echo   Edit frontend/ -^> the browser hot-reloads, no build needed.
echo.
echo   Note: use port %VITE_PORT%, not %API_PORT%. Port %API_PORT% serves the last
echo   built frontend/dist, which does NOT update as you edit.
echo.
echo   The sheet sync writes to the DB every SYNC_INTERVAL_SECONDS, so numbers
echo   can shift while you test. To hold them steady, run:
echo       set SYNC_INTERVAL_SECONDS=86400 ^&^& dev.bat
echo.
echo   Close the two opened windows to stop.
endlocal
exit /b 0

:fail
echo.
echo Dev startup aborted.
endlocal
pause
exit /b 1
