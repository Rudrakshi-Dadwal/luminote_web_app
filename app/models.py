from pydantic import BaseModel, Field
from typing import List, Optional
from dataclasses import dataclass


# Data classes for internal processing
@dataclass
class TranscriptSegment:
    text: str
    start: float
    duration: float


@dataclass
class TranscriptResult:
    video_id: str
    language: str
    source: str
    segments: List[TranscriptSegment]

    @property
    def full_text(self) -> str:
        from app.utils import clean_text
        return clean_text(" ".join(segment.text for segment in self.segments))


# Pydantic models for API
class SummarizeRequest(BaseModel):
    url: str = Field(..., min_length=8, description="A YouTube video URL or video ID")
    language: str = Field(default="en", min_length=2, max_length=8, description="Preferred language code")


class TimestampItem(BaseModel):
    time: str
    seconds: float
    text: str


class SummarizeResponse(BaseModel):
    video_id: str
    language: str
    transcript_source: str
    model_used: str
    tldr: str
    bullets: List[str]
    timestamps: List[TimestampItem]
    transcript_characters: int
    fallback_suggestion: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: dict


class HealthResponse(BaseModel):
    status: str
