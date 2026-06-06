#!/usr/bin/env python
"""
LUMINOTE unified startup script.

This script checks the local environment, installs dependencies into .venv,
starts the FastAPI backend, waits for /health, and opens the app.
"""

from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
VENV_DIR = ROOT_DIR / ".venv"
HEALTH_URL = "http://127.0.0.1:8000/health"
APP_URL = "http://127.0.0.1:8000"

load_dotenv(ROOT_DIR / ".env")


def log_section(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def log_success(message: str) -> None:
    print(f"[OK] {message}")


def log_error(message: str) -> None:
    print(f"[ERROR] {message}")


def log_info(message: str) -> None:
    print(f"[INFO] {message}")


def log_step(message: str) -> None:
    print(f"[STEP] {message}")


def check_python_version() -> bool:
    log_step("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        log_error(f"Python 3.9+ required. Found: {version.major}.{version.minor}")
        return False
    log_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True


def venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def check_venv() -> bool:
    log_step("Checking virtual environment...")
    python_path = venv_python()

    if python_path.exists():
        log_success("Virtual environment exists")
        return True

    log_info("Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    except subprocess.CalledProcessError as exc:
        log_error(f"Failed to create virtual environment: {exc}")
        return False

    if not python_path.exists():
        log_error(f"Virtual environment was created, but {python_path} was not found")
        return False

    log_success("Virtual environment created")
    return True


def install_dependencies() -> bool:
    log_step("Checking dependencies...")
    python_cmd = str(venv_python())

    probe = "import fastapi, uvicorn, dotenv, google.generativeai"
    try:
        subprocess.run(
            [python_cmd, "-c", probe],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log_success("Dependencies already installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    log_info("Installing dependencies into .venv (this may take a few minutes)...")
    try:
        subprocess.run([python_cmd, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    except subprocess.CalledProcessError as exc:
        log_error(f"Failed to install dependencies: {exc}")
        return False

    log_success("Dependencies installed")
    return True


def check_gemini_key() -> bool:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        log_success(f"GEMINI_API_KEY is set ({key[:10]}...)")
        return True

    log_error("GEMINI_API_KEY not found in .env or environment")
    log_info("Get a free Gemini API key from: https://ai.google.dev/")
    return False


def is_port_available(port: int = 8000) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def start_backend() -> subprocess.Popen[str] | None:
    log_step("Starting FastAPI backend...")

    if not is_port_available(8000):
        log_error("Port 8000 is already in use")
        log_info("Stop the existing process or change the backend port")
        return None

    command = [
        str(venv_python()),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        log_error(f"Failed to start backend: {exc}")
        return None

    log_success(f"Backend process started (PID: {process.pid})")
    return process


def wait_for_backend(process: subprocess.Popen[str], url: str = HEALTH_URL, max_wait: int = 30) -> bool:
    log_step(f"Waiting for backend to be ready (max {max_wait} seconds)...")

    for attempt in range(1, max_wait + 1):
        if process.poll() is not None:
            log_error("Backend process exited before becoming ready")
            log_backend_output(process)
            return False

        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    log_success("Backend is ready")
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            pass

        if attempt < max_wait:
            print(f"  Waiting... ({attempt}/{max_wait})", end="\r")
        time.sleep(1)

    print()
    log_error(f"Backend did not respond after {max_wait} seconds")
    return False


def log_backend_output(process: subprocess.Popen[str]) -> None:
    try:
        stdout, stderr = process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        return

    if stdout and stdout.strip():
        log_info("Backend stdout:")
        print(stdout.strip())
    if stderr and stderr.strip():
        log_error("Backend stderr:")
        print(stderr.strip())


def open_browser(url: str = APP_URL) -> None:
    log_step(f"Opening browser to {url}...")
    try:
        webbrowser.open(url)
        log_success("Browser opened")
    except Exception as exc:
        log_error(f"Could not open browser: {exc}")
        log_info(f"Open manually: {url}")


def main() -> int:
    print()
    print("=" * 60)
    print("  LUMINOTE - YouTube AI Summarizer")
    print("  Startup Script")
    print("=" * 60)

    log_section("Step 1: Check Python Version")
    if not check_python_version():
        return 1

    log_section("Step 2: Virtual Environment")
    if not check_venv():
        return 1

    log_section("Step 3: Install Dependencies")
    if not install_dependencies():
        return 1

    log_section("Step 4: Check Configuration")
    if not check_gemini_key():
        return 1

    log_section("Step 5: Start Backend")
    backend_process = start_backend()
    if not backend_process:
        return 1

    log_section("Step 6: Wait for Backend Ready")
    if not wait_for_backend(backend_process):
        backend_process.terminate()
        return 1

    log_section("Step 7: Open Browser")
    open_browser()

    log_section("LUMINOTE is Ready")
    log_success("Application started successfully")
    log_info(f"Open browser: {APP_URL}")
    log_info("Press Ctrl+C to stop the server")

    try:
        backend_process.wait()
    except KeyboardInterrupt:
        log_step("Shutting down...")
        backend_process.terminate()
        log_success("Server stopped")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        raise SystemExit(1)
    except Exception as exc:
        print(f"\nUnexpected error: {exc}")
        raise SystemExit(1)
