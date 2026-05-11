from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse
from typing import List


YOUTUBE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def extract_video_id(value: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    candidate = value.strip()
    if YOUTUBE_ID_PATTERN.match(candidate):
        return candidate

    parsed = urlparse(candidate)

    # youtu.be short links
    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
        if YOUTUBE_ID_PATTERN.match(video_id):
            return video_id

    # youtube.com variants
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

        # Handle playlist URLs - extract first video if possible
        if path_parts and path_parts[0] == "playlist":
            # For playlists, we can't easily get a single video ID without API
            # Return error for now
            pass

    raise ValueError("Please enter a valid YouTube URL or 11-character video ID.")


def format_timestamp(seconds: float) -> str:
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def clean_text(text: str) -> str:
    """Clean text by normalizing whitespace and removing lightweight noise."""
    text = str(text or "")
    text = re.sub(r"[\u266a\u266b]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_transcript(text: str) -> str:
    """Remove common transcript artifacts while preserving sentence structure."""
    if not text:
        return ""

    text = str(text)
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\[.*?\]", " ", text)
    text = re.sub(r"\b(Music|Applause|Laughter|Singing|Chorus|Drums|Intro|Outro|Verse|Bridge|Hook)\b",
                  " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[\u266a\u266b]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_lyric_or_music_text(text: str, threshold: float = 0.38, min_words: int = 100) -> bool:
    """Detect transcripts that are likely lyric-heavy or repetitive music."""
    cleaned = clean_transcript(text)
    words = [word.lower() for word in cleaned.split() if word.isalpha()]
    if len(words) < min_words:
        return False

    unique_ratio = len(set(words)) / len(words)
    repetitive_score = 1 - unique_ratio
    if repetitive_score >= threshold:
        return True

    lyric_markers = re.search(r"\b(chorus|verse|repeat|singing|lyrics|hook|beat|rap|rapping|lyrics)\b",
                              cleaned, flags=re.IGNORECASE)
    return bool(lyric_markers)


def split_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    normalized = clean_text(text)
    if not normalized:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    sentences = [sentence.strip() for sentence in sentences if len(sentence.strip()) > 25]

    # Break oversized blocks
    refined: List[str] = []
    for sentence in sentences or [normalized]:
        refined.extend(_split_long_caption_block(sentence))

    return [sentence for sentence in refined if len(sentence) > 25]


def _split_long_caption_block(text: str, max_words: int = 26) -> List[str]:
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
    current: List[str] = []
    for word in words:
        current.append(word)
        if len(current) >= max_words:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks for summarization."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
        if start >= len(words):
            break

    return chunks
