# LUMINOTE - Developer Quick Reference

Fast answers to common questions during development.

## 🚀 Getting Started Fast

```powershell
# One-liner setup (if you have Python 3.9+)
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt

# Start dev server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Test API
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"
```

---

## 📁 File Purposes

| File | Purpose | Edit when |
|------|---------|-----------|
| `app/main.py` | API endpoints, error handling | Adding endpoints, changing routes |
| `app/transcript.py` | YouTube caption fetching | Fixing caption issues, adding sources |
| `app/summarizer.py` | Text summarization logic | Changing summary algorithm |
| `app/models.py` | Request/Response schemas | Changing API response format |
| `app/utils.py` | Helper functions | Adding utility functions |
| `static/app.js` | Frontend logic | Changing UI behavior, styling |
| `static/index.html` | HTML structure | Changing form layout, sections |
| `static/styles.css` | Styling | Changing colors, fonts, layout |
| `.env` | Configuration | Changing model, limits, feature flags |
| `requirements.txt` | Dependencies | Adding new Python packages |

---

## 🔌 API Endpoints

### Health Check
```
GET /health
GET /api/health
Response: {"status": "ok"}
```

### Summarize Video
```
POST /api/summarize
Content-Type: application/json

Request:
{
  "url": "https://www.youtube.com/watch?v=...",
  "language": "en"
}

Response:
{
  "video_id": "...",
  "language": "en",
  "transcript_source": "YouTube captions",
  "model_used": "local extractive summarizer",
  "tldr": "Summary...",
  "bullets": ["Point 1", "Point 2"],
  "timestamps": [
    {"time": "0:05", "seconds": 5.0, "text": "..."}
  ],
  "transcript_characters": 12345,
  "fallback_suggestion": null
}
```

### Static Files
```
GET /static/app.js
GET /static/styles.css
GET /static/index.html
GET / (redirects to index.html)
```

---

## 🔍 Debugging

### Backend Logging
```python
import logging
logger = logging.getLogger("luminote")

logger.info("Message")
logger.warning("Warning")
logger.error("Error")
logger.exception("Exception with traceback")
```

### Frontend Debugging
```javascript
// Check if backend is reachable
fetch("http://127.0.0.1:8000/api/health")
  .then(r => r.json())
  .then(console.log)
  .catch(e => console.error("Backend not running:", e))

// Test API with specific URL
const testUrl = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
fetch("http://127.0.0.1:8000/api/summarize", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({url: testUrl, language: "en"})
})
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

### Check What's Running
```powershell
netstat -ano | findstr :8000     # Check if server is running
tasklist | findstr python         # See Python processes
pip list | findstr -i youtube     # See installed packages
```

---

## 🧪 Testing

### Test a YouTube URL Directly
```powershell
# In PowerShell
$url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
$body = @{url=$url; language="en"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/summarize" `
  -Method Post -Body $body -ContentType "application/json"
```

### Test Video ID Extraction
```python
from app.utils import extract_video_id

# These should all return "dQw4w9WgXcQ"
print(extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
print(extract_video_id("https://youtu.be/dQw4w9WgXcQ"))
print(extract_video_id("dQw4w9WgXcQ"))
```

### Test Transcript Fetching
```python
from app.transcript import fetch_transcript

result = fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ", language="en")
print(f"Video: {result.video_id}")
print(f"Language: {result.language}")
print(f"Source: {result.source}")
print(f"Segments: {len(result.segments)}")
print(f"First segment: {result.segments[0].text}")
```

---

## 📦 Managing Dependencies

```powershell
# See what's installed
pip list

# Install new package
pip install package-name

# Install specific version
pip install package-name==1.2.3

# Update all packages
pip install -r requirements.txt --upgrade

# Generate requirements from current env
pip freeze > requirements.txt

# Install from requirements
pip install -r requirements.txt
```

---

## 🔧 Common Edits

### Change API Port
```python
# In command line, use --port flag:
python -m uvicorn app.main:app --port 8001

# Then update frontend:
// In app.js, modify resolveApiBase()
return "http://127.0.0.1:8001"
```

### Change Max Transcript Size
```env
# In .env:
MAX_TRANSCRIPT_CHARS=25000  # Increase from 18000
```

### Use Different Summarization Model
```env
# In .env:
SUMMARIZER_MODE=abstractive
SUMMARIZER_MODEL=facebook/bart-large-cnn

# Or use DistilBART (lighter):
SUMMARIZER_MODEL=sshleifer/distilbart-cnn-6-6
```

### Add Input Validation
```python
# In app/models.py:
from pydantic import BaseModel, Field, validator

class SummarizeRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    language: str = Field(default="en", regex=r"^[a-z]{2}(-[A-Z]{2})?$")
    
    @validator('url')
    def url_must_be_valid(cls, v):
        if "youtube.com" not in v and "youtu.be" not in v:
            raise ValueError("Must be a YouTube URL")
        return v
```

### Add CORS for Different Origins
```python
# In app/main.py:
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://myapp.com"],  # Specific origins
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## 🐛 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'app'` | Module not in path | Run from project root: `cd "LUMINOTE WEB APP"` |
| `Address already in use` | Port 8000 busy | Use `--port 8001` or kill process on 8000 |
| `TranscriptUnavailableError` | No captions available | Install `yt-dlp` and `ffmpeg` for fallbacks |
| `JSON Decode Error` | Server returned HTML error | Check terminal for error, likely exception |
| `CORS Error` | Frontend origin not allowed | Fix CORS settings in main.py |
| `No module named 'transformers'` | Dependency not installed | Run `pip install -r requirements.txt` |

---

## 📊 Performance Checklist

- [ ] Using extractive mode (no ML model) if fast performance needed
- [ ] MAX_TRANSCRIPT_CHARS limited to 12000-18000
- [ ] No large ML models in free tier
- [ ] Caching implemented for repeated videos (if applicable)
- [ ] Proper error handling (no 500 errors)
- [ ] Timeouts set (90 seconds max)
- [ ] Logging configured for debugging

---

## 🔐 Security Checklist

- [ ] No hardcoded credentials in code
- [ ] .env file is in .gitignore
- [ ] Input validation on all endpoints
- [ ] Error messages don't leak internal details
- [ ] No SQL injection (using ORM/parametrized queries)
- [ ] CORS properly configured
- [ ] Rate limiting implemented (future)
- [ ] HTTPS in production (use gunicorn + nginx)

---

## 📝 Code Style

### Python
```python
# Use type hints
def fetch_transcript(url: str, language: str = "en") -> TranscriptResult:
    pass

# Docstrings
"""Fetch YouTube video transcript with fallbacks.
    
Args:
    url: YouTube URL or video ID
    language: Preferred language code (default "en")
    
Returns:
    TranscriptResult with video_id, language, source, segments
    
Raises:
    TranscriptUnavailableError: If no captions available
"""

# Logging instead of print
logger.info(f"Processing video: {video_id}")
```

### JavaScript
```javascript
// Use const by default, let for loops
const videoUrl = document.querySelector("#url").value;
for (let i = 0; i < items.length; i++) { }

// Async/await over .then() chains
const response = await fetch(url);
const data = await response.json();

// Clear variable names
const isLoading = true;
const hasError = false;
```

---

## 🚀 Deployment Checklist

- [ ] Update requirements.txt with all dependencies
- [ ] Remove debug code and console.logs
- [ ] Set LOG_LEVEL=INFO in .env
- [ ] Test with production settings
- [ ] Use gunicorn for production: `gunicorn -w 4 app.main:app`
- [ ] Setup HTTPS (via nginx or Let's Encrypt)
- [ ] Database backups configured
- [ ] Monitoring/alerting setup
- [ ] Documentation updated

---

**Pro Tip**: Create a `.vscode/settings.json` for Python formatting:
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true
}
```

---

Need more help? Check README.md, TROUBLESHOOTING.md, or the error message in your terminal!
