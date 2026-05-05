@echo off
REM LUMINOTE Startup Script for Windows
REM This script activates the virtual environment and starts the server

cls
echo.
echo ╔════════════════════════════════════════════════════╗
echo ║     LUMINOTE - YouTube Video Summarizer             ║
echo ║     Starting Backend Server...                      ║
echo ╚════════════════════════════════════════════════════╝
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo ❌ Virtual environment not found!
    echo.
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        echo Please install Python 3.9+ from python.org
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

REM Check if requirements are installed
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo ⏳ Installing dependencies (this may take 2-5 minutes)...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Start the server
echo.
echo ✅ Virtual environment ready!
echo.
echo ════════════════════════════════════════════════════
echo 🚀 Starting FastAPI Backend Server...
echo ════════════════════════════════════════════════════
echo.
echo 📱 Once the server starts, open your browser to:
echo    👉 http://127.0.0.1:8000
echo.
echo 🛑 To stop the server, press Ctrl+C
echo.
echo ════════════════════════════════════════════════════
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
