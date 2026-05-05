from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    url: str = Field(..., min_length=8, description="A YouTube video URL or video ID")
    language: str = Field(default="en", min_length=2, max_length=8)


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
    bullets: list[str]
    timestamps: list[TimestampItem]
    transcript_characters: int
    fallback_suggestion: str | None = None
