import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.models import SummarizeRequest, SummarizeResponse
from app.services.summarization_service import GeminiServiceError, SummarizationService
from app.services.transcript_service import TranscriptService, TranscriptUnavailableError


router = APIRouter()
logger = logging.getLogger(__name__)
transcript_service = TranscriptService()
summarization_service = SummarizationService()


@router.post("/api/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """Summarize a YouTube video from its transcript."""
    try:
        if not request.url or len(request.url.strip()) < 8:
            raise ValueError("Please provide a valid YouTube URL")

        transcript = await fetch_transcript_with_retry(request.url, request.language)

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
    except GeminiServiceError as exc:
        logger.exception("Gemini API failure")
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Gemini API failed while generating the summary.",
                "fallback": "Check GEMINI_API_KEY, quota, model name, and internet access, then try again.",
            },
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected summarize failure")
        raise HTTPException(
            status_code=500,
            detail={"message": "An unexpected error occurred. Please check the server logs."},
        ) from exc


async def fetch_transcript_with_retry(url: str, language: str):
    last_error: TranscriptUnavailableError | None = None
    for attempt in range(2):
        try:
            return await transcript_service.fetch_transcript(url, language)
        except TranscriptUnavailableError as exc:
            last_error = exc
            logger.warning("Transcript fetch failed on attempt %s/2: %s", attempt + 1, exc)
            if attempt == 0:
                await asyncio.sleep(1)

    raise last_error or TranscriptUnavailableError("No transcript could be retrieved for this video.")
