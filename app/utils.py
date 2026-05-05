from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


YOUTUBE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def extract_video_id(value: str) -> str:
    candidate = value.strip()
    if YOUTUBE_ID_PATTERN.match(candidate):
        return candidate

    parsed = urlparse(candidate)

    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
        if YOUTUBE_ID_PATTERN.match(video_id):
            return video_id

    if parsed.hostname and "youtube.com" in parsed.hostname:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if YOUTUBE_ID_PATTERN.match(video_id):
                return video_id

        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts and path_parts[0] in {"shorts", "embed", "live"}:
            video_id = path_parts[1] if len(path_parts) > 1 else ""
            if YOUTUBE_ID_PATTERN.match(video_id):
                return video_id

    raise ValueError("Please enter a valid YouTube URL or 11-character video ID.")


def format_timestamp(seconds: float) -> str:
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    normalized = clean_text(text)
    if not normalized:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    sentences = [sentence.strip() for sentence in sentences if len(sentence.strip()) > 25]

    # Caption text often has poor punctuation, so break oversized blocks into smaller units.
    refined: list[str] = []
    for sentence in sentences or [normalized]:
        refined.extend(_split_long_caption_block(sentence))

    return [sentence for sentence in refined if len(sentence) > 25]


def _split_long_caption_block(text: str, max_words: int = 26) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    words = text.split()
    if len(words) <= max_words:
        return [text]

    parts = re.split(r"(?<=[,;:])\s+", text)
    if 1 < len(parts) <= 8:
        chunks = [clean_text(part) for part in parts if len(clean_text(part)) > 25]
        if chunks:
            return chunks

    chunks = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if len(current) >= max_words:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks
