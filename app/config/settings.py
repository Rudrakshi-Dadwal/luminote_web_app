from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


load_dotenv()

TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}
CONFIG_WARNINGS: list[str] = []


def _warn(message: str) -> None:
    CONFIG_WARNINGS.append(message)


def _raw_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _get_str(name: str, default: str, *, allowed: set[str] | None = None) -> str:
    value = _raw_env(name)
    if value is None:
        return default
    if allowed and value not in allowed:
        _warn(f"{name}={value!r} is not supported; using {default!r}.")
        return default
    return value


def _get_optional_str(name: str, default: str | None = None) -> str | None:
    return _raw_env(name) or default


def _get_bool(name: str, default: bool) -> bool:
    value = _raw_env(name)
    if value is None:
        return default

    normalized = value.casefold()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False

    _warn(f"{name}={value!r} is not a valid boolean; using {default!r}.")
    return default


def _get_int(name: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    value = _raw_env(name)
    if value is None:
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        _warn(f"{name}={value!r} is not a valid integer; using {default}.")
        return default

    if minimum is not None and parsed < minimum:
        _warn(f"{name}={parsed} is below {minimum}; using {default}.")
        return default
    if maximum is not None and parsed > maximum:
        _warn(f"{name}={parsed} is above {maximum}; using {default}.")
        return default
    return parsed


@dataclass(frozen=True)
class Settings:
    # Server settings
    host: str = field(default_factory=lambda: _get_str("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: _get_int("PORT", 8000, minimum=1, maximum=65535))
    debug: bool = field(default_factory=lambda: _get_bool("DEBUG", False))

    # Transcript settings
    enable_whisper_fallback: bool = field(default_factory=lambda: _get_bool("ENABLE_WHISPER_FALLBACK", True))
    whisper_model: str = field(default_factory=lambda: _get_str("WHISPER_MODEL", "tiny"))
    max_transcript_chars: int = field(
        default_factory=lambda: _get_int("MAX_TRANSCRIPT_CHARS", 18000, minimum=1000, maximum=500000)
    )
    transcript_timeout: int = field(default_factory=lambda: _get_int("TRANSCRIPT_TIMEOUT", 30, minimum=1, maximum=300))

    # Gemini settings
    gemini_api_key: str = field(default_factory=lambda: _get_str("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: _get_str("GEMINI_MODEL", "gemini-2.5-flash"))
    max_chunk_tokens: int = field(default_factory=lambda: _get_int("MAX_CHUNK_TOKENS", 4000, minimum=500, maximum=32000))
    chunk_overlap: int = field(default_factory=lambda: _get_int("CHUNK_OVERLAP", 500, minimum=0, maximum=8000))

    # YouTube settings
    ytdlp_cookie_file: str | None = field(default_factory=lambda: _get_optional_str("YTDLP_COOKIE_FILE"))
    ytdlp_cookies_from_browser: str | None = field(default_factory=lambda: _get_optional_str("YTDLP_COOKIES_FROM_BROWSER"))

    def validate(self) -> list[str]:
        warnings = list(CONFIG_WARNINGS)

        if not self.gemini_api_key:
            warnings.append("GEMINI_API_KEY is not set; /api/summarize will not be able to use Gemini.")

        if self.chunk_overlap >= self.max_chunk_tokens:
            warnings.append("CHUNK_OVERLAP should be lower than MAX_CHUNK_TOKENS; chunking may be inefficient.")

        if self.ytdlp_cookie_file and not Path(self.ytdlp_cookie_file).exists():
            warnings.append(f"YTDLP_COOKIE_FILE={self.ytdlp_cookie_file!r} does not exist; cookie fallback will be skipped.")

        if self.ytdlp_cookies_from_browser:
            allowed_browsers = {"brave", "chrome", "chromium", "edge", "firefox", "opera", "safari", "vivaldi"}
            browser = self.ytdlp_cookies_from_browser.casefold()
            if browser not in allowed_browsers:
                warnings.append(
                    f"YTDLP_COOKIES_FROM_BROWSER={self.ytdlp_cookies_from_browser!r} may not be supported by yt-dlp."
                )

        return warnings

    def as_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "enable_whisper_fallback": self.enable_whisper_fallback,
            "whisper_model": self.whisper_model,
            "max_transcript_chars": self.max_transcript_chars,
            "transcript_timeout": self.transcript_timeout,
            "gemini_api_key": "***" if self.gemini_api_key else "",
            "gemini_model": self.gemini_model,
            "max_chunk_tokens": self.max_chunk_tokens,
            "chunk_overlap": self.chunk_overlap,
            "ytdlp_cookie_file": self.ytdlp_cookie_file,
            "ytdlp_cookies_from_browser": self.ytdlp_cookies_from_browser,
        }


settings = Settings()
