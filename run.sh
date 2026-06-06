#!/bin/bash

# LUMINOTE Startup Script for macOS and Linux
# This script automatically handles everything to get the app running

clear

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║     LUMINOTE - YouTube Video Summarizer             ║"
echo "║     Unified Startup Script (macOS/Linux)            ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_step() {
    echo -e "${YELLOW}📍 $1${NC}"
}

# Step 1: Check Python version
log_step "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    log_error "Python3 not found! Please install Python 3.9+"
    echo "Visit: https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
log_success "Python $PYTHON_VERSION installed"
echo ""

# Step 2: Check virtual environment
log_step "Checking virtual environment..."
if [ -d ".venv" ]; then
    log_success "Virtual environment exists"
else
    log_info "Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        log_error "Failed to create virtual environment"
        exit 1
    fi
    log_success "Virtual environment created"
fi
echo ""

# Step 3: Activate virtual environment
log_step "Activating virtual environment..."
source .venv/bin/activate
log_success "Virtual environment activated"
echo ""

# Step 4: Install dependencies
log_step "Checking dependencies..."
if python3 -c "import fastapi" 2>/dev/null; then
    log_success "Dependencies already installed"
else
    log_info "Installing dependencies (this may take 2-5 minutes)..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        log_error "Failed to install dependencies"
        exit 1
    fi
    log_success "Dependencies installed"
fi
echo ""

# Step 5: Check Gemini API key
log_step "Checking configuration..."
if [ -z "$GEMINI_API_KEY" ]; then
    log_error "GEMINI_API_KEY not set!"
    echo ""
    echo "Please set your Gemini API key:"
    echo "  export GEMINI_API_KEY=your-key-here"
    echo ""
    echo "Get a free key from: https://ai.google.dev/"
    echo ""
    exit 1
fi
log_success "GEMINI_API_KEY is set"
echo ""

# Step 6: Check if port 8000 is available
log_step "Checking if port 8000 is available..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    log_error "Port 8000 is already in use"
    log_info "Close the application using this port or change PORT in .env"
    exit 1
fi
log_success "Port 8000 is available"
echo ""

# Step 7: Start the server
echo "════════════════════════════════════════════════════"
echo "🚀 Starting FastAPI Backend Server..."
echo "════════════════════════════════════════════════════"
echo ""
echo "📱 Once the server is ready:"
echo "   - Browser will open automatically"
echo "   - Navigate to http://127.0.0.1:8000"
echo ""
echo "🛑 To stop the server, press Ctrl+C"
echo ""
echo "════════════════════════════════════════════════════"
echo ""

# Start the server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
UVICORN_PID=$!

# Wait for server to be ready
log_step "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        log_success "Backend is ready!"
        break
    fi
    if [ $i -lt 30 ]; then
        printf "  Waiting... (%d/30)\r" "$i"
    fi
    sleep 1
done
echo ""

# Open browser
log_step "Opening browser..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:8000
elif command -v open &> /dev/null; then
    open http://127.0.0.1:8000
else
    log_info "Please open your browser to http://127.0.0.1:8000"
fi
log_success "Browser opened"
echo ""

# Success message
echo "════════════════════════════════════════════════════"
log_success "LUMINOTE is Ready!"
echo "════════════════════════════════════════════════════"
log_success "Application started successfully"
log_info "Open your browser to http://127.0.0.1:8000"
log_info "Press Ctrl+C to stop the server"
echo ""

# Keep running
wait $UVICORN_PID
