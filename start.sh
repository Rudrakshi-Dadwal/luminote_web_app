#!/bin/bash
# LUMINOTE Startup Script for macOS and Linux
# This script activates the virtual environment and starts the server

clear

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║     LUMINOTE - YouTube Video Summarizer             ║"
echo "║     Starting Backend Server...                      ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "Please install Python 3.9+ from python.org"
        read -p "Press enter to exit..."
        exit 1
    fi
fi

# Activate virtual environment
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    read -p "Press enter to exit..."
    exit 1
fi

# Check if requirements are installed
pip show fastapi > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⏳ Installing dependencies (this may take 2-5 minutes)..."
    echo ""
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        read -p "Press enter to exit..."
        exit 1
    fi
fi

# Start the server
echo ""
echo "✅ Virtual environment ready!"
echo ""
echo "════════════════════════════════════════════════════"
echo "🚀 Starting FastAPI Backend Server..."
echo "════════════════════════════════════════════════════"
echo ""
echo "📱 Once the server starts, open your browser to:"
echo "    👉 http://127.0.0.1:8000"
echo ""
echo "🛑 To stop the server, press Ctrl+C"
echo ""
echo "════════════════════════════════════════════════════"
echo ""

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

read -p "Press enter to exit..."
