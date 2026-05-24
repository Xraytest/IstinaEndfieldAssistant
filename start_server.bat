@echo off
REM Start IstinaEndfieldAssistant Server
REM This script starts the server (TCP and web dashboard)

REM Set the working directory to the script's location
cd /d "%~dp0"

REM Add src directory to Python path
set "PYTHONPATH=%cd%\src;%PYTHONPATH%"

REM Start the server
REM We assume the server entry point is in src/core or similar
REM From the context, the server uses port 9999 for TCP and 8000 for web dashboard
REM We need to find the actual server main file.

REM Let's try to run a server module if it exists, otherwise show an error.
if exist src\server\main.py (
    python src\server\main.py %*
) else if exist src\core\server\main.py (
    python src\core\server\main.py %*
) else if exist src\main_server.py (
    python src\main_server.py %*
) else (
    echo [Error] Server entry point not found.
    echo Please ensure the server code is available.
    pause
    exit /b 1
)