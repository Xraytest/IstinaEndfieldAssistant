@echo off
REM Start IstinaPlatform Server (TCP 9999 + Web Dashboard 8000)
cd /d "%~dp0"

set "SERVER_DIR=%~dp0..\IstinaPlatform"
if exist "%SERVER_DIR%\src\server\main.py" (
    cd /d "%SERVER_DIR%"
    set "PYTHONPATH=%cd%\src;%PYTHONPATH%"
    python src\server\main.py %*
) else (
    echo [Error] IstinaPlatform server not found at %SERVER_DIR%
    pause
    exit /b 1
)