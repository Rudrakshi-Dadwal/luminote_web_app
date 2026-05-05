from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models import SummarizeRequest, SummarizeResponse
from app.summarizer import SummarizationUnavailableError, summarize_transcript
from app.transcript import TranscriptUnavailableError, fetch_transcript


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("luminote")

app = FastAPI(
    title="Free YouTube Video Summarizer",
    description="A local-first YouTube transcript summarizer using free tools.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "message": "Invalid request body.",
                "errors": exc.errors(),
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        payload = {"detail": detail}
    else:
        payload = {"detail": {"message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled backend error")
    return JSONResponse(
        status_code=500,
        content={"detail": {"message": "Internal server error. Check the backend terminal logs."}},
    )


@app.get("/", response_class=FileResponse)
@app.get("/index.html", response_class=FileResponse)
def index() -> FileResponse:
    """Serve the main index.html file"""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail={"message": "index.html not found"})
    return FileResponse(index_file)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/health")
def api_health() -> dict:
    return {"status": "ok"}


@app.post("/api/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """Summarize a YouTube video from its transcript.
    
    Args:
        request: Contains YouTube URL and preferred language
        
    Returns:
        SummarizeResponse with video summary, bullets, timestamps
    """
    logger.info(f"Summarizing video: {request.url[:50]}...")
    
    try:
        if not request.url or len(request.url.strip()) < 8:
            raise ValueError("Please provide a valid YouTube URL")
            
        transcript = fetch_transcript(request.url, language=request.language)
        logger.info(f"Transcript retrieved for {transcript.video_id}")
        
        summary = summarize_transcript(transcript.segments)
        logger.info(f"Summary generated for {transcript.video_id}")
        
    except ValueError as exc:
        logger.warning(f"Validation error: {str(exc)}")
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc)},
        ) from exc
    except TranscriptUnavailableError as exc:
        logger.warning(f"Transcript unavailable for {request.url}: {str(exc)}")
        raise HTTPException(
            status_code=404,
            detail={
                "message": str(exc),
                "fallback": "Choose a public video with captions, try another language, or add a local audio transcription fallback.",
            },
        ) from exc
    except SummarizationUnavailableError as exc:
        logger.warning(f"Summarization unavailable: {str(exc)}")
        raise HTTPException(
            status_code=503,
            detail={
                "message": str(exc),
                "fallback": "Switch to extractive mode in .env if your laptop cannot load the local Hugging Face model.",
            },
        ) from exc
    except Exception as exc:
        logger.exception(f"Unexpected error summarizing {request.url}")
        raise HTTPException(
            status_code=500,
            detail={"message": "An unexpected error occurred. Please check the server logs."},
        ) from exc

    return SummarizeResponse(
        video_id=transcript.video_id,
        language=transcript.language,
        transcript_source=transcript.source,
        model_used=summary["model_used"],
        tldr=summary["tldr"],
        bullets=summary["bullets"],
        timestamps=summary["timestamps"],
        transcript_characters=len(transcript.full_text),
        fallback_suggestion=None,
    )
