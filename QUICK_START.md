# ⚡ LUMINOTE - Quick Setup Checklist

## 🚀 Get Started in 5 Minutes

Use this checklist to get LUMINOTE running and test it.

### Step 1: Setup Environment ✅
- [ ] Have Python 3.9+ installed: `python --version`
- [ ] Open terminal in project folder
- [ ] Create virtual environment: `python -m venv .venv`
- [ ] Activate it: `.\.venv\Scripts\Activate.ps1` (Windows) or `source .venv/bin/activate` (Mac/Linux)

### Step 2: Install Dependencies ✅
- [ ] Run: `pip install -r requirements.txt`
- [ ] Wait for installation to complete (2-5 minutes)
- [ ] Verify: `pip list | findstr fastapi` should show fastapi installed

### Step 3: Start Backend Server ✅
- [ ] Run: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
- [ ] Wait for message: `Uvicorn running on http://127.0.0.1:8000`
- [ ] Leave this terminal open!

### Step 4: Open the App ✅
- [ ] Open browser: http://127.0.0.1:8000
- [ ] You should see the LUMINOTE interface
- [ ] If not, check terminal for errors

### Step 5: Test It ✅
- [ ] Paste a YouTube URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- [ ] Click "Generate Summary"
- [ ] Wait 10-30 seconds
- [ ] See your summary appear!

---

## 🔧 Setup with Optional Features

### Enable Whisper Audio Transcription
If videos don't have captions, Whisper can transcribe audio:

```powershell
# Install ffmpeg first
choco install ffmpeg  # Windows with Chocolatey

# Or download from: https://ffmpeg.org/download.html
# Then add to PATH

# Verify ffmpeg is installed:
ffmpeg -version

# In .env, set (already should be):
ENABLE_WHISPER_FALLBACK=true
WHISPER_MODEL=tiny
```

**Note**: First run downloads ~500MB. Uses ~2GB RAM. Be patient!

### Add YouTube Cookies (Optional)
If YouTube blocks transcript fetching:

```powershell
# 1. Install Cookie Editor in Chrome
# 2. Go to YouTube.com
# 3. Click Cookie Editor → Export → Netscape Format
# 4. Save as cookies.txt in project
# 5. In .env, add: YTDLP_COOKIE_FILE=cookies.txt
```

---

## 🧪 Test Different Scenarios

### Scenario 1: Video with Manual Captions ✅ (Fastest)
```
URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
Expected: ⚡ Summary in 5-10 seconds
Source: "YouTube captions"
```

### Scenario 2: Video with Auto-Generated Captions ✅ (Also fast)
```
URL: https://www.youtube.com/watch?v=Dkk9ZjaLcly
Expected: ⚡ Summary in 10-15 seconds
Source: "YouTube auto-generated captions"
```

### Scenario 3: Video Without Captions ⚠️ (Falls back to yt-dlp)
```
URL: [Video without captions]
Expected: Takes 20-30 seconds
Source: "yt-dlp" if available
```

### Scenario 4: Edge Case - Private/Deleted Video ❌
```
URL: [Private video]
Expected: Error: "This video is unavailable, private, age restricted..."
Action: Choose a different video
```

---

## ⚠️ If Something Goes Wrong

### "Failed to fetch" Error
```powershell
# Check if server is running in other terminal
netstat -ano | findstr :8000

# Should see: TCP    127.0.0.1:8000    LISTENING

# If not, run in new terminal:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### "Captions not available" Error
```powershell
# This is expected for videos without captions
# Try another video with captions:
# - TED talks: https://www.youtube.com/watch?v=hO8X6ZC7arE
# - News: https://www.youtube.com/watch?v=xXy2EKN1FQQ

# If you want audio transcription:
# 1. Install ffmpeg (see above)
# 2. Set ENABLE_WHISPER_FALLBACK=true in .env
```

### "Invalid YouTube URL" Error
```
❌ These DON'T work:
- https://youtube.com (missing /watch or video ID)
- https://www.youtube.com/results?search_query=... (search)
- https://www.youtube.com/channel/... (channel, not video)

✅ These work:
- https://www.youtube.com/watch?v=... (standard)
- https://youtu.be/... (short)
- https://www.youtube.com/shorts/... (shorts)
```

### ModuleNotFoundError
```powershell
# Make sure you:
# 1. Activated venv: .\.venv\Scripts\Activate.ps1
# 2. Installed deps: pip install -r requirements.txt
# 3. Are in correct folder: cd "LUMINOTE WEB APP"
```

---

## 📊 Performance Tips

| Setting | For | How |
|---------|-----|-----|
| Fast summary | 📱 Laptop/Slow internet | `MAX_TRANSCRIPT_CHARS=10000` in .env |
| Accurate summary | 💪 Powerful computer | `MAX_TRANSCRIPT_CHARS=30000` |
| Instant results | ⚡ Can't wait | Use `SUMMARIZER_MODE=extractive` |
| Better quality | 🎯 Have time | Use abstractive model + more chars |

---

## 🎯 What to Try Next

1. **Summarize different videos** - See how it handles long/short content
2. **Try different languages** - Enter "es", "fr", "de" in Language field
3. **Check error handling** - What happens with invalid URLs?
4. **Monitor server logs** - Watch terminal for what happens behind scenes
5. **Read TROUBLESHOOTING.md** - If you hit issues
6. **Check IMPROVEMENTS.md** - Ideas for features

---

## 📚 Key Files

| File | Purpose | Look when |
|------|---------|-----------|
| app/main.py | Backend API | Errors or adding endpoints |
| app/transcript.py | Caption fetching | "Captions not available" |
| app/summarizer.py | Summary logic | Changing how summaries work |
| static/app.js | Frontend | "Failed to fetch" errors |
| static/index.html | UI structure | Changing form/layout |
| .env | Configuration | Changing behavior |
| README.md | Instructions | Setting up/running |
| TROUBLESHOOTING.md | Error fixes | Debugging |

---

## 🎓 Code Structure Quick Tour

```
LUMINOTE WEB APP/
├── app/              ← Backend (Python/FastAPI)
│   ├── main.py      (endpoints: /api/summarize, /)
│   ├── transcript.py (fetch YouTube captions + fallbacks)
│   ├── summarizer.py (create bullets, tldr, timestamps)
│   ├── models.py    (request/response schemas)
│   └── utils.py     (helper functions)
│
├── static/          ← Frontend (HTML/CSS/JavaScript)
│   ├── index.html   (form, results display)
│   ├── app.js       (form submission, API calls)
│   └── styles.css   (styling)
│
├── .env             ← Configuration (not in git)
├── requirements.txt ← Dependencies
└── README.md        ← Documentation
```

---

## 🚀 Commands Cheat Sheet

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Deactivate environment
deactivate

# Install dependencies
pip install -r requirements.txt

# Start server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Test API health
Invoke-RestMethod "http://127.0.0.1:8000/api/health"

# Check what's running on port 8000
netstat -ano | findstr :8000

# Kill process on port 8000 (Windows)
taskkill /PID [number] /F

# See Python version
python --version

# List installed packages
pip list

# Upgrade specific package
pip install --upgrade yt-dlp
```

---

## ✅ Success Checklist

When you see these, everything is working:

- [ ] Terminal shows: `Uvicorn running on http://127.0.0.1:8000`
- [ ] Browser opens to localhost:8000
- [ ] You can type in YouTube URL
- [ ] Page shows "Generating Summary..." after click
- [ ] Summary appears in 10-30 seconds
- [ ] Summary has: TLDR, Bullets, Timestamps, Video ID

**If all ✅, you're good to go!**

---

## 🎯 Next: Try These Test Videos

1. **Short & Easy** (captions always available)
   - https://www.youtube.com/watch?v=dQw4w9WgXcQ

2. **Medium Length**
   - https://www.youtube.com/watch?v=Dkk9ZjaLcly

3. **Long Form** (educational)
   - https://www.youtube.com/watch?v=hO8X6ZC7arE

4. **Shorts Format** 
   - https://www.youtube.com/shorts/[video-id]

---

## 📞 Get Help

1. **Check terminal** - 90% of issues show there
2. **Read TROUBLESHOOTING.md** - Most errors covered
3. **Check browser console** - F12 → Console tab
4. **Look at code** - If you know Python, check the code!

---

**Ready? Go to Step 1 above and start! 🚀**
