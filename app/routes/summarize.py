from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.models import ErrorResponse, HealthResponse, SummarizeRequest, SummarizeResponse
from app.services.summarization_service import SummarizationService
from app.services.transcript_service import TranscriptService, TranscriptUnavailableError
from app.config.settings import settings


router = APIRouter()
transcript_service = TranscriptService()
summarization_service = SummarizationService()


@router.get("/", response_class=FileResponse)
@router.get("/index.html", response_class=FileResponse)
def index():
    """Serve the main index.html file"""
    static_dir = Path(__file__).resolve().parent.parent / "static"
    index_file = static_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail={"message": "index.html not found"})
    return FileResponse(index_file)


@router.get("/app.js", response_class=FileResponse)
def app_js():
    static_dir = Path(__file__).resolve().parent.parent / "static"
    js_file = static_dir / "app.js"
    if not js_file.exists():
        raise HTTPException(status_code=404, detail={"message": "app.js not found"})
    return FileResponse(js_file)


@router.get("/styles.css", response_class=FileResponse)
def styles_css():
    static_dir = Path(__file__).resolve().parent.parent / "static"
    css_file = static_dir / "styles.css"
    if not css_file.exists():
        raise HTTPException(status_code=404, detail={"message": "styles.css not found"})
    return FileResponse(css_file)


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@router.get("/api/health", response_model=HealthResponse)
def api_health():
    return HealthResponse(status="ok")


@router.post("/api/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """Summarize a YouTube video from its transcript."""
    try:
        if not request.url or len(request.url.strip()) < 8:
            raise ValueError("Please provide a valid YouTube URL")

        # Fetch transcript
        transcript = await transcript_service.fetch_transcript(request.url, request.language)

        # Summarize
        summary = await summarization_service.summarize_transcript(transcript.segments)

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

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc)},
        )
    except TranscriptUnavailableError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "message": str(exc),
                "fallback": "Choose a public video with captions, try another language, or check video availability.",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"message": "An unexpected error occurred. Please check the server logs."},
        )