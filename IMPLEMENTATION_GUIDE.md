# IMPLEMENTATION GUIDE: Production-Grade Fixes

This document provides exact code replacements for all identified bugs.

## FILE 1: app/services/transcript_service.py - ENHANCED VERSION

**CHANGES:**
1. Add DiagnosticInfo class for tracking
2. Add retry logic with exponential backoff
3. Add TooManyRequests handling
4. Improve error messages
5. Add comprehensive logging

**KEY ADDITIONS:**

```python
class DiagnosticInfo:
    """Track diagnostic information during transcript fetching."""
    def __init__(self, video_id: str):
        self.video_id = video_id
        self.attempts = []
        self.transcript_found = False
        self.transcript_type = "unknown"
        self.transcript_length = 0
        self.success_method = None
    
    def log_attempt(self, method: str, status: str, error: str = None):
        """Log an attempt with timestamp."""
        attempt = {
            "method": method,
            "status": status,
            "error": error,
            "timestamp": time.time(),
        }
        self.attempts.append(attempt)
        logger.info(f"[{self.video_id}] {method}: {status} ({error or 'OK'})")
```

**RETRY LOGIC WITH EXPONENTIAL BACKOFF:**

```python
async def _fetch_from_youtube_api_with_retry(
    self, video_id: str, preferred_languages: List[str], diag: DiagnosticInfo
) -> Optional[TranscriptResult]:
    """Fetch transcript with retry logic."""
    for attempt in range(self.max_retries):
        try:
            # ... existing code ...
        except TooManyRequests:
            if attempt < self.max_retries - 1:
                wait_time = min(self.retry_delay * (2 ** attempt), self.max_backoff)
                logger.warning(f"Rate limited. Retrying in {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                continue
            else:
                diag.log_attempt("YouTube API", "rate_limited")
                return None
```

---

## FILE 2: app/services/summarization_service.py - ADD FALLBACK

**CHANGES:**
1. Import local summarizer
2. Add Gemini error handling
3. Add fallback to extractive summarization
4. Add better chunk validation

**KEY ADDITIONS:**

```python
from app.summarizer import summarize_transcript as extractive_summarize

async def summarize_transcript(self, segments: List[TranscriptSegment]) -> dict:
    """Summarize with Gemini, fallback to extractive."""
    try:
        # Try Gemini...
    except Exception as gemini_error:
        logger.warning(f"Gemini failed: {gemini_error}. Using extractive summarization.")
        # Fallback to local extractive summarizer
        return extractive_summarize(segments)
```

---

## FILE 3: app/routes/summarize.py - ADD DIAGNOSTIC MODE

**CHANGES:**
1. Add `?diagnostic=true` query parameter support
2. Return diagnostic info in response
3. Better error messages

**KEY ADDITIONS:**

```python
@router.post("/api/summarize", response_model=SummarizeResponse)
async def summarize(
    request: SummarizeRequest,
    diagnostic: bool = Query(False),
) -> SummarizeResponse:
    """Summarize YouTube video with optional diagnostics."""
    result, diag = await transcript_service.fetch_transcript(
        request.url, request.language, diagnostic=diagnostic
    )
    # ... rest of code ...
    # If diagnostic=True, include diag info in response
```

---

## FILE 4: app/config/settings.py - ADD LOGGING CONFIG

**CHANGES:**
1. Add logging configuration
2. Add validation for required settings
3. Add timeout configs

```python
class Settings(BaseSettings):
    # ... existing ...
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # or "text"
    
    # Retry settings
    transcript_retry_count: int = 3
    transcript_retry_delay: float = 1.0
    
    @field_validator('gemini_api_key')
    @classmethod
    def validate_gemini_key(cls, v):
        if not v:
            raise ValueError("GEMINI_API_KEY is required")
        return v
```

---

## FILE 5: app/utils.py - ENHANCED URL PARSING

**CHANGES:**
1. Protocol normalization
2. Better error messages
3. Query param handling
4. Comprehensive logging

✓ ALREADY COMPLETED (see above)

---

## CONFIGURATION EXAMPLE: .env

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-1.5-flash
TRANSCRIPT_TIMEOUT=30
ENABLE_WHISPER_FALLBACK=true
WHISPER_MODEL=tiny
MAX_TRANSCRIPT_CHARS=18000
MAX_CHUNK_TOKENS=4000
CHUNK_OVERLAP=500
LOG_LEVEL=INFO
LOG_FORMAT=json
DEBUG=false
PORT=8000
HOST=0.0.0.0
```

---

## TEST CASES FOR VERIFICATION

### Test 1: Standard YouTube URL
```
Input: https://www.youtube.com/watch?v=TYhNHX372ek
Expected: ✓ Transcript fetched, summary generated
```

### Test 2: Short URL
```
Input: youtu.be/TYhNHX372ek
Expected: ✓ Video ID extracted, transcript fetched
```

### Test 3: Short URL with query param
```
Input: youtu.be/?v=TYhNHX372ek
Expected: ✓ Video ID extracted from query param
```

### Test 4: URL with timestamp
```
Input: https://youtube.com/watch?v=TYhNHX372ek&t=45s
Expected: ✓ Timestamp ignored, video ID extracted
```

### Test 5: Direct video ID
```
Input: TYhNHX372ek
Expected: ✓ Recognized as valid ID, transcript fetched
```

### Test 6: Age-restricted video
```
Input: [age-restricted video URL]
Expected: ✓ Detects TranscriptsDisabled, explains to user
```

### Test 7: Very long video (4+ hours)
```
Input: [long video URL]
Expected: ✓ Chunks transcript, summarizes chunks, final summary
```

### Test 8: Diagnostic mode
```
Input: POST /api/summarize?diagnostic=true
Expected: Response includes transcr ipt_type, length, method used
```

---

## ROLLOUT PLAN

1. **Phase 1:** Update utils.py (URL parsing) ✓
2. **Phase 2:** Update transcript_service.py (retry logic, diagnostics)
3. **Phase 3:** Update summarization_service.py (Gemini fallback)
4. **Phase 4:** Update routes/summarize.py (diagnostic endpoint)
5. **Phase 5:** Update config/settings.py (validation, logging)
6. **Phase 6:** Test with 20+ diverse YouTube URLs
7. **Phase 7:** Deploy to production with monitoring

---

## SUCCESS METRICS

- ✓ 90%+ of public videos with captions summarized successfully
- ✓ All error types categorized and reported
- ✓ Average response time < 15 seconds (excluding Whisper)
- ✓ Diagnostic mode provides actionable feedback
- ✓ Fallback chain documented in logs
