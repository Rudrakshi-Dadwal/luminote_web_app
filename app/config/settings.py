from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Transcript settings
    enable_whisper_fallback: bool = True
    whisper_model: str = "tiny"
    max_transcript_chars: int = 18000
    transcript_timeout: int = 30

    # Gemini settings
    gemini_api_key: str
    gemini_model: str = "gemini-1.5-flash"
    max_chunk_tokens: int = 4000  # Gemini token limit per request
    chunk_overlap: int = 500

    # YouTube settings
    ytdlp_cookie_file: Optional[str] = None
    ytdlp_cookies_from_browser: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()