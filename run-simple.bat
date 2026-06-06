@echo off
REM LUMINOTE Startup Script for Windows
REM This script automatically handles everything to get the app running

setlocal enabledelayedexpansion

cls
echo.
echo ╔════════════════════════════════════════════════════╗
echo ║     LUMINOTE - YouTube Video Summarizer             ║
echo ║     Unified Startup Script                          ║
echo ╚════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% installed
echo.

REM Check if virtual environment exists
echo Checking virtual environment...
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)
echo ✅ Virtual environment activated
echo.

REM Check if dependencies are installed
echo Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies (this may take 2-5 minutes)...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)
echo ✅ Dependencies installed
echo.

REM Check GEMINI_API_KEY
echo Checking configuration...
if "!GEMINI_API_KEY!"=="" (
    echo ❌ GEMINI_API_KEY not set!
    echo.
    echo Please set your Gemini API key:
    echo   set GEMINI_API_KEY=your-key-here
    echo.
    echo Get a free key from: https://ai.google.dev/
    echo.
    pause
    exit /b 1
)
echo ✅ GEMINI_API_KEY is set
echo.

REM Check if port 8000 is available
echo Checking if port 8000 is available...
netstat -ano | findstr ":8000" >nul
if errorlevel 0 (
    netstat -ano | findstr ":8000" >nul
    if not errorlevel 1 (
        echo ❌ Port 8000 is already in use
        echo Please close other applications using this port
        pause
        exit /b 1
    )
)
echo ✅ Port 8000 is available
echo.

REM Start the server
echo ════════════════════════════════════════════════════
echo 🚀 Starting FastAPI Backend Server...
echo ════════════════════════════════════════════════════
echo.
echo 📱 Once the server is ready:
echo    - Browser will open automatically
echo    - Navigate to http://127.0.0.1:8000
echo.
echo 🛑 To stop the server, press Ctrl+C or close this window
echo.
echo ════════════════════════════════════════════════════
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo 🛑 Server stopped
pause
