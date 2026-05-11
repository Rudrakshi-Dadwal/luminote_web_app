# Luminote - YouTube AI Summarizer

A production-ready FastAPI backend for summarizing YouTube videos using Google Gemini AI.

## Features

- **Robust Transcript Extraction**: Multiple fallback strategies (YouTube API, yt-dlp, Whisper)
- **Hierarchical Summarization**: Chunks long transcripts and summarizes hierarchically
- **Google Gemini Integration**: Uses Gemini 1.5 Flash for high-quality summaries
- **Async FastAPI**: Scalable async endpoints
- **Deployment Ready**: Optimized for Render, Railway, and other platforms
- **Error Handling**: Comprehensive exception handling with structured responses

## Architecture

```
YouTube URL → Transcript Extraction → Text Cleaning → Chunking → Gemini Summarization → Final Summary
```

## Project Structure

```
app/
├── main.py              # FastAPI application
├── routes/
│   └── summarize.py     # API routes
├── services/
│   ├── transcript_service.py    # Transcript extraction
│   └── summarization_service.py # Gemini summarization
├── models/
│   └── __init__.py      # Pydantic models
├── utils/
│   └── __init__.py      # Utility functions
├── config/
│   └── settings.py      # Configuration
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Setup

1. **Clone and install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ENABLE_WHISPER_FALLBACK=true
   WHISPER_MODEL=tiny
   ```

3. **Run locally**:
   ```bash
   python -m app.main
   ```

## API Usage

### Health Check
```bash
GET /health
```

### Summarize Video
```bash
POST /api/summarize
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "language": "en"
}
```

**Response**:
```json
{
  "video_id": "VIDEO_ID",
  "language": "en",
  "transcript_source": "YouTube captions",
  "model_used": "gemini-1.5-flash",
  "tldr": "Summary text...",
  "bullets": ["Key point 1", "Key point 2"],
  "timestamps": [
    {
      "time": "00:30",
      "seconds": 30.0,
      "text": "Key moment..."
    }
  ],
  "transcript_characters": 15000
}
```

## Deployment

### Render
1. Connect your GitHub repo
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables in Render dashboard

### Railway
1. Connect repo
2. Set PORT environment variable
3. Railway auto-detects Python and installs requirements.txt

## Configuration

Key settings in `app/config/settings.py`:

- `GEMINI_API_KEY`: Your Google AI API key
- `GEMINI_MODEL`: Model to use (default: gemini-1.5-flash)
- `MAX_CHUNK_TOKENS`: Token limit per API call
- `ENABLE_WHISPER_FALLBACK`: Use Whisper for videos without transcripts

## Transcript Sources

1. **YouTube API**: Manual/auto-generated captions
2. **yt-dlp**: Alternative caption extraction
3. **Whisper**: Local AI transcription fallback

## Error Handling

- `400`: Invalid URL or request
- `404`: Transcript unavailable
- `500`: Server error

All errors return structured JSON responses.

## Production Best Practices

- Async endpoints prevent blocking
- Chunking handles long videos
- Hierarchical summarization maintains quality
- Environment variables for secrets
- CORS enabled for web clients
- Comprehensive logging
- Graceful fallbacks

## License

MIT License