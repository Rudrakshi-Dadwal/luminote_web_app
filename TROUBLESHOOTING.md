# LUMINOTE Troubleshooting Guide

Encountering issues? This guide covers the most common problems and their solutions.

## Common Errors & Fixes

### ❌ "Failed to fetch" Error

**What it means**: The frontend can't connect to the backend API server.

**Root causes & solutions**:

1. **Backend server not running**
   - Check if terminal shows: `Uvicorn running on http://127.0.0.1:8000`
   - If not, run: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

2. **Wrong port or host**
   - Default: `http://127.0.0.1:8000`
   - If you changed it, update the frontend to match
   - In `app.js`, modify `resolveApiBase()` function

3. **Firewall blocking**
   - Windows Firewall might block Python
   - Go to Windows Defender → Firewall → Allow app through firewall
   - Enable "Python" or "Uvicorn"

4. **Virtual environment not activated**
   - On Windows: `.\.venv\Scripts\Activate.ps1`
   - On Mac/Linux: `source .venv/bin/activate`
   - You should see `(.venv)` in terminal

5. **Port 8000 already in use**
   - Find what's using it: `netstat -ano | findstr :8000`
   - Use different port: `python -m uvicorn app.main:app --port 8001`
   - Update frontend to match new port

---

### ❌ "Captions not available" Error

**What it means**: The app couldn't fetch video captions through any method.

**The app tries 3 methods in order**:

1. **YouTube's Official API** (youtube-transcript-api)
   - Works for 95% of videos
   - Requires video to be public with captions

2. **yt-dlp Fallback** (if step 1 fails)
   - Works for videos YouTube hides captions from
   - Requires: yt-dlp installed ✅ (included in requirements.txt)
   - Optional: YouTube cookies from Chrome/Edge

3. **Whisper Audio Transcription** (if step 1 & 2 fail)
   - Records and transcribes audio locally
   - Requires:
     - ffmpeg installed
     - openai-whisper installed
     - ~1-2 minutes per video

**Solutions**:

**For Method 2 (yt-dlp)**:
```powershell
# yt-dlp should already be installed, but verify:
pip install --upgrade yt-dlp

# Optional: Export YouTube cookies for better access
# 1. Install Cookie Editor in Chrome: chrome.google.com/webstore
# 2. Go to YouTube.com, click Cookie Editor
# 3. Click "Export" → "Export as Netscape Format"
# 4. Save as cookies.txt in your project
# 5. In .env, add: YTDLP_COOKIE_FILE=cookies.txt
```

**For Method 3 (Whisper)**:
```powershell
# Install ffmpeg (required for audio processing)
# Option 1: Chocolatey
choco install ffmpeg

# Option 2: Direct download
# https://ffmpeg.org/download.html
# Add to system PATH

# Verify ffmpeg is installed:
ffmpeg -version

# Install openai-whisper (already in requirements.txt):
pip install --upgrade openai-whisper

# Enable in .env:
ENABLE_WHISPER_FALLBACK=true
WHISPER_MODEL=tiny  # tiny, base, small, medium, large
```

**Note**: Whisper with "base" or larger models requires 8GB+ RAM.

---

### ❌ "Method Not Allowed" Error

**What it means**: Frontend sent wrong HTTP method (GET instead of POST).

**Status**: ✅ **FIXED** - We updated the code to properly send POST requests.

**Manual fix if error persists**:
- Open DevTools (F12)
- Check Network tab - what request is being sent?
- Verify `app.js` line ~20: should be `method: "POST"`

---

### ❌ "JSON Error" / "Backend returned non-JSON response"

**What it means**: Backend is crashing or returning error HTML instead of JSON.

**Debug steps**:

1. **Check terminal** where uvicorn is running
   - Look for red error messages
   - Note the full error message

2. **Common reasons**:
   - Missing dependency: `pip install -r requirements.txt --upgrade`
   - Syntax error in code: Check Python version `python --version` (needs 3.9+)
   - Unhandled exception: Check logs in terminal

3. **Solutions**:
   ```powershell
   # Reinstall all dependencies
   pip install -r requirements.txt --upgrade
   
   # Run with verbose logging
   python -m uvicorn app.main:app --log-level debug
   
   # Check Python version (need 3.9+)
   python --version
   ```

---

### ⚠️ "Request timed out (90 seconds)"

**What it means**: Video processing is taking too long.

**Common causes**:
- Large transcript (100+ minutes)
- Using heavy Hugging Face model (not extractive mode)
- Computer is slow/low memory
- Network issues downloading ML model

**Solutions**:
```env
# In .env, use fast extractive mode:
SUMMARIZER_MODE=extractive

# Reduce processing limit:
MAX_TRANSCRIPT_CHARS=12000

# Or extend timeout in app.js (if needed):
# Change 90000 to 180000 (3 minutes)
```

---

### ❌ "Invalid YouTube URL"

**What it means**: URL format is wrong.

**Valid formats**:
```
✅ https://www.youtube.com/watch?v=dQw4w9WgXcQ
✅ https://youtu.be/dQw4w9WgXcQ
✅ https://www.youtube.com/shorts/dQw4w9WgXcQ
✅ dQw4w9WgXcQ (just the video ID)
❌ https://youtube.com/channel/... (channel, not video)
❌ https://youtube.com/results?search_query=... (search, not video)
```

---

### ❌ Whisper Not Working / "ffmpeg not installed"

**Solutions**:

**Windows**:
```powershell
# Using Chocolatey (recommended)
choco install ffmpeg

# Or manually:
# 1. Download: https://ffmpeg.org/download.html
# 2. Extract to: C:\ffmpeg
# 3. Add to PATH:
$env:Path += ";C:\ffmpeg\bin"
setx Path "$env:Path"

# Verify:
ffmpeg -version
```

**Mac**:
```bash
brew install ffmpeg
```

**Linux**:
```bash
sudo apt-get install ffmpeg
```

---

### ❌ High Memory Usage / "Model Downloaded 2GB"

**Why it happens**:
- Using abstractive summarization with large models
- ML models are big (500MB - 2GB each)

**Solutions**:
```env
# In .env, use extractive (no model download):
SUMMARIZER_MODE=extractive

# Or use small model:
SUMMARIZER_MODEL=sshleifer/distilbart-cnn-6-6  # 300MB
SUMMARIZER_MODE=abstractive

# Limit transcript size:
MAX_TRANSCRIPT_CHARS=10000
```

---

## Advanced Debugging

### Enable Detailed Logging

**Backend**:
```powershell
python -m uvicorn app.main:app --log-level debug --reload
```

**Frontend**:
1. Open Developer Tools (F12)
2. Go to Console tab
3. Run test: `fetch('http://127.0.0.1:8000/api/health').then(r => r.json()).then(console.log)`

### Check What's Running on Ports

```powershell
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :5500

# Mac/Linux
lsof -i :8000
lsof -i :5500

# Kill a process (Windows)
taskkill /PID [number] /F

# Kill a process (Mac/Linux)
kill -9 [PID]
```

### Database/Cache Issues

The app doesn't use persistent storage, so no cache to clear. Each run is fresh.

---

## Still Having Issues?

1. **Check terminal output** - error messages are there
2. **Open Developer Tools** (F12) → Console tab → look for red errors
3. **Try in Incognito** - clear browser cache
4. **Restart everything**:
   ```powershell
   # Deactivate venv
   deactivate
   
   # Reactivate
   .\.venv\Scripts\Activate.ps1
   
   # Reinstall
   pip install -r requirements.txt --upgrade
   
   # Restart server
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

---

## Performance Tips

1. **Use extractive mode** (no ML model) - instant summaries
2. **Limit transcript size** - set `MAX_TRANSCRIPT_CHARS=10000`
3. **Use small videos** - 10-30 minutes is sweet spot
4. **Enable cookies** - sometimes faster than auto-transcription
5. **Keep Python up to date** - `python -m pip install --upgrade pip`

---

**Can't find your issue here?** Check the terminal where the server is running - the error message is usually the answer!
