@echo off
REM ============================================================
REM  HR Analysis Dashboard - production-style start script
REM  Run this on the target machine from the project root.
REM  Builds the frontend, runs DB migrations, then starts a
REM  single uvicorn process that serves both the API (/api/*)
REM  and the built dashboard (everything else).
REM ============================================================

setlocal enabledelayedexpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ==============================================
echo   HR Analysis Dashboard - starting deployment
echo ==============================================

where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] "uv" is not installed or not on PATH.
    echo         Install it from https://astral.sh/uv and re-run this script.
    goto :fail
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] "npm" is not installed or not on PATH.
    echo         Install Node.js from https://nodejs.org and re-run this script.
    goto :fail
)

if not exist "%ROOT%.env" (
    echo [ERROR] .env not found in "%ROOT%".
    echo         Copy .env.example to .env and fill in DB + Google credentials first.
    goto :fail
)

REM Pull API_HOST / API_PORT out of .env (falls back to defaults below if
REM either key is absent). A var already set in the calling environment
REM wins over both, so `set API_PORT=9000 && start.bat` still works.
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "API_HOST=" "%ROOT%.env"`) do set "ENV_API_HOST=%%B"
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /i "API_PORT=" "%ROOT%.env"`) do set "ENV_API_PORT=%%B"

if "%API_HOST%"=="" set "API_HOST=%ENV_API_HOST%"
if "%API_PORT%"=="" set "API_PORT=%ENV_API_PORT%"
if "%API_HOST%"=="" set "API_HOST=0.0.0.0"
if "%API_PORT%"=="" set "API_PORT=8000"

if not exist "%ROOT%service.json" (
    echo [WARN] service.json not found - Google Sheets sync will fail unless
    echo        GOOGLE_SERVICE_ACCOUNT_FILE in .env points somewhere else valid.
)

echo.
echo [1/4] Installing backend dependencies (uv sync)...
call uv sync --frozen
if errorlevel 1 (
    echo [ERROR] uv sync failed.
    goto :fail
)

echo.
echo [2/4] Running database migrations (alembic upgrade head)...
call uv run alembic upgrade head
if errorlevel 1 (
    echo [ERROR] alembic upgrade failed. Check DB_* settings in .env.
    goto :fail
)

echo.
echo [3/4] Installing frontend dependencies and building...
pushd "%ROOT%frontend"
call npm install
if errorlevel 1 (
    echo [ERROR] npm install failed.
    popd
    goto :fail
)
call npm run build
if errorlevel 1 (
    echo [ERROR] npm run build failed.
    popd
    goto :fail
)
popd

echo.
echo [4/4] Starting server (API + dashboard on one port)...
echo   App: http://localhost:%API_PORT%
echo   API: http://localhost:%API_PORT%/api  (docs at /docs)
echo.
uv run uvicorn backend.api.main:app --host %API_HOST% --port %API_PORT%

endlocal
exit /b 0

:fail
echo.
echo Deployment aborted.
endlocal
pause
exit /b 1
