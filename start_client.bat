@echo off
REM Start IstinaEndfieldAssistant Client
REM This script starts the PyQt6 GUI client

REM Set the working directory to the script's location
cd /d "%~dp0"

REM Add src directory to Python path
set "PYTHONPATH=%cd%\src;%PYTHONPATH%"

REM Start the client
python src\gui\pyqt6\main.py %*

REM Pause to see any error messages
pause