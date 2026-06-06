from __future__ import annotations

import logging
import re
from urllib.parse import parse_qs, urlparse, urlunparse
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

YOUTUBE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def extract_video_id(value: str) -> str:
    """
    Extract YouTube video ID from various URL formats.
    
    Supports:
    - Direct video IDs: abc123def45
    - youtube.com/watch?v=ID
    - youtu.be/ID
    - youtu.be/?v=ID
    - youtube.com/shorts/ID
    - youtube.com/embed/ID
    - youtube.com/live/ID
    - URLs with timestamps: &t=45s
    - URLs with query params: &list=...
    """
    if not value:
        raise ValueError("URL cannot be empty")
    
    candidate = value.strip()
    logger.debug(f"Extracting video ID from: {candidate[:100]}")
    
    # Check if it's already a valid video ID
    if YOUTUBE_ID_PATTERN.match(candidate):
        logger.debug(f"Input is a valid video ID: {candidate}")
        return candidate
    
    # Normalize URL: add protocol if missing
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    
    try:
        parsed = urlparse(candidate)
    except Exception as e:
        logger.error(f"URL parsing failed: {e}")
        raise ValueError("Invalid URL format")
    
    hostname = parsed.hostname or ""
    
    # youtu.be short links (various formats)
    if "youtu.be" in hostname:
        logger.debug(f"Detected youtu.be short link")
        # Try path first: youtu.be/ID
        video_id = parsed.path.strip("/").split("/")[0]
        if YOUTUBE_ID_PATTERN.match(video_id):
            logger.debug(f"Extracted from path: {video_id}")
            return video_id
        
        # Try query parameter: youtu.be/?v=ID
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if YOUTUBE_ID_PATTERN.match(video_id):
            logger.debug(f"Extracted from query param: {video_id}")
            return video_id
    
    # youtube.com variants
    if "youtube.com" in hostname:
        logger.debug(f"Detected youtube.com URL")
        
        # Standard watch URL: youtube.com/watch?v=ID&t=...
        if "watch" in parsed.path or "watch" in parsed.query:
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if YOUTUBE_ID_PATTERN.match(video_id):
                logger.debug(f"Extracted from /watch query: {video_id}")
                return video_id
        
        # Shorts, embed, live: youtube.com/shorts/ID
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            video_id = path_parts[1]
            if YOUTUBE_ID_PATTERN.match(video_id):
                logger.debug(f"Extracted from /{path_parts[0]}: {video_id}")
                return video_id
        
        # Fallback: try first path segment if it's a valid ID
        if path_parts and YOUTUBE_ID_PATTERN.match(path_parts[0]):
            logger.debug(f"Extracted from first path segment: {path_parts[0]}")
            return path_parts[0]
    
    logger.error(f"Could not extract video ID from: {candidate[:100]}")
    raise ValueError(
        "Invalid YouTube URL. Please provide:\n"
        "- A YouTube URL (youtube.com/watch?v=...)\n"
        "- A short URL (youtu.be/...)\n"
        "- A video ID (11 characters)"
    )


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
