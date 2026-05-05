# LUMINOTE - Free YouTube Video Summarizer

A fast, local-first YouTube video summarizer built for college students. No API keys needed, no paid services required. **It just works!**

## 🎯 What It Does

- Extracts captions from YouTube videos (auto-generated or manual)
- Summarizes transcripts into readable study notes
- Creates bullet points and timestamps of key moments
- Works entirely locally on your laptop

## 🛠️ Tech Stack

- **Backend**: FastAPI (async, fast, production-ready)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (no bloat)
- **Caption Retrieval**: `youtube-transcript-api` (primary) + `yt-dlp` (fallback) + Whisper (audio fallback)
- **Summarization**: Local extractive summarizer (fast) + optional Hugging Face models

## 📁 Project Structure

```text
LUMINOTE WEB APP/
├── app/
│   ├── __init__.py           # Package initialization
│   ├── main.py              # FastAPI app and API endpoints
│   ├── models.py            # Request/Response Pydantic models
│   ├── transcript.py        # YouTube caption fetching with fallbacks
│   ├── summarizer.py        # Text summarization logic
│   └── utils.py             # Helper functions
├── static/
│   ├── index.html           # Main HTML page
│   ├── app.js               # Frontend logic
│   └── styles.css           # Styling
├── .env                     # Configuration (created for you)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Quick Start (3 Steps)

### Step 1: One-Click Start (Recommended!)

**Windows:**
- Double-click `START.bat` in the project folder
- Wait for: "Uvicorn running on http://127.0.0.1:8000"

**Mac/Linux:**
```bash
chmod +x start.sh
./start.sh
```

### Step 2: Open Browser
Once you see the server running, open:
```
http://127.0.0.1:8000
```

### Step 3: Start Summarizing!
Paste a YouTube URL and click "Generate Summary"

---

## Alternative: Manual Setup (3 Steps)

## Alternative: Manual Setup (3 Steps)

If you prefer to set up manually:

### Step 1: Create Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 3: Start the Server

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open: **http://127.0.0.1:8000**

---

## 📱 How to Use

1. **Paste a YouTube URL** - Works with any public video (shorts, long-form, anything)
2. **Click "Generate Summary"** - The app fetches captions automatically
3. **Get your notes** - TLDR, bullet points, and key timestamps

## ⚙️ Configuration (.env File)

The `.env` file controls app behavior:

```env
# Maximum characters to process (to save memory)
MAX_TRANSCRIPT_CHARS=18000

# Optional: YouTube cookies file for yt-dlp (helps bypass some restrictions)
# YTDLP_COOKIE_FILE=/path/to/cookies.txt

# Optional: Force extractive mode (faster, no ML model download)
SUMMARIZER_MODE=extractive
```

## 🔧 Troubleshooting

### "Failed to fetch" Error
- **Check**: Is the FastAPI server running on http://127.0.0.1:8000?
- **Fix**: In terminal, run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- **Also check**: Firewall isn't blocking localhost:8000

### "Captions not available" Error
The app tries **three fallback methods** to get captions:
1. YouTube's official captions API (fast)
2. `yt-dlp` with YouTube cookies (requires Chrome/Edge/Firefox installed)
3. Whisper audio transcription (requires `ffmpeg` in PATH)

**To enable Whisper transcription:**
```powershell
# On Windows, use Chocolatey or download ffmpeg from ffmpeg.org
choco install ffmpeg

# Then set in .env:
ENABLE_WHISPER_FALLBACK=true
WHISPER_MODEL=tiny  # tiny, base, small, medium, large (larger = slower)
```

### "Method Not Allowed" Error
- **Cause**: Frontend trying to GET instead of POST
- **Fix**: We fixed this! Just use the latest code.

### "JSON Errors" / "Backend returned non-JSON"
- **Cause**: API server crashed or returned error HTML instead of JSON
- **Fix**: Check terminal where server is running for error messages
- **Also**: Make sure you're using Python 3.9+

## 📊 Advanced Features

### Use Hugging Face Models Instead of Extractive Mode

Edit `.env`:
```env
SUMMARIZER_MODE=abstractive
SUMMARIZER_MODEL=sshleifer/distilbart-cnn-12-6
```

**Warning**: First run downloads 500MB+. Set `MAX_TRANSCRIPT_CHARS=12000` to save memory.

### Process Specific Languages

Pass language code in the form:
- English: `en` (default)
- Spanish: `es`
- French: `fr`
- Or any ISO 639-1 code

### Use YouTube Cookies

If YouTube blocks transcript fetching:
1. Export cookies from Chrome: https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdj
2. Save as `.txt` file
3. Set in `.env`: `YTDLP_COOKIE_FILE=path/to/cookies.txt`

## 🎓 What We Learned (Improvements Made)

### Bugs Fixed ✅
- **Missing Dependencies**: Added `yt-dlp`, `openai-whisper`, `requests` to requirements
- **Poor Error Messages**: Improved error handling with clear, actionable messages
- **API Connection Issues**: Better API endpoint routing and error detection
- **Missing .env**: Created with sensible defaults
- **Synchronous Functions**: Made API handler async for better performance
- **JSON Parsing**: Added robust error handling in frontend

### Code Quality Improvements ✅
- Added async/await for non-blocking operations
- Comprehensive input validation
- Better logging throughout the backend
- User-friendly error messages with fallback suggestions
- Console logging in frontend for debugging
- CORS properly configured
- Multiple fallback methods for caption retrieval

## 📈 How to Improve This Project Further

1. **Database**: Save summaries (SQLite, PostgreSQL)
2. **User Accounts**: Store user preferences and summary history
3. **Batch Processing**: Upload/process multiple videos
4. **Export Options**: Download as PDF, Word, Markdown
5. **Custom Models**: Let users choose summarization models
6. **Dark Mode**: Add theme toggle
7. **Mobile App**: React Native version
8. **Rate Limiting**: Prevent abuse
9. **Caching**: Store summaries for popular videos
10. **Analytics**: Track which videos are summarized

## 🤝 Contributing

This is a college project! Feel free to:
- Add features
- Improve error handling
- Optimize performance
- Add more languages
- Submit improvements

## 📜 License

MIT - Use however you want!

## 🎯 Credits

**Team LUMINOTE**
- Rudrakshi Dadwal - Backend and UI Design
- Kashish Rawat - Frontend and AI Integration
- Student 3 - Testing and Documentation

---

**Need Help?** Check the console (F12 in browser) and terminal output for detailed error messages.
