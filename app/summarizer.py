from __future__ import annotations

import os
import re
from collections import Counter

from app.transcript import TranscriptSegment
from app.utils import clean_text, format_timestamp


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "he", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to",
    "was", "we", "were", "will", "with", "you", "your", "they", "their", "our",
    "but", "if", "so", "not", "can", "about", "into", "more", "what", "when",
    "just", "like", "get", "got", "also", "been", "do", "did", "go", "going",
    "want", "know", "think", "see", "way", "even", "i", "me", "my", "us",
    "him", "her", "all", "then", "than", "here", "there", "where", "which",
    "who", "how", "very", "yeah", "okay", "right", "really", "actually",
    "gonna", "gotta", "kinda", "wanna",
}

TLDR_WORDS = 95
BULLET_WORDS = 18
NUM_BULLETS = 5
WINDOW_WORDS = 32


class SummarizationUnavailableError(RuntimeError):
    pass


def summarize_transcript(segments: list[TranscriptSegment]) -> dict:
    max_chars = int(os.getenv("MAX_TRANSCRIPT_CHARS", "18000"))
    text = _build_extractive_source(segments, max_chars=max_chars)

    windows = _rank_windows(text)
    tldr = _build_tldr(text, windows)
    bullets = _build_bullets(text, windows)

    return {
        "model_used": "local extractive summarizer",
        "tldr": tldr or "Could not generate a summary for this video.",
        "bullets": bullets,
        "timestamps": find_key_timestamps(segments),
    }


def _build_extractive_source(segments: list[TranscriptSegment], max_chars: int) -> str:
    windows: list[str] = []
    current: list[str] = []
    current_chars = 0

    for segment in segments:
        piece = _clean_transcript(segment.text)
        if not piece:
            continue
        if current and current_chars + len(piece) > 220:
            windows.append(" ".join(current))
            current = []
            current_chars = 0
        current.append(piece)
        current_chars += len(piece) + 1

    if current:
        windows.append(" ".join(current))

    return clean_text(" ".join(windows))[:max_chars]


def _clean_transcript(text: str) -> str:
    text = re.sub(r"[\u266a\u266b]", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _keyword_frequencies(text: str) -> Counter:
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return Counter(word for word in words if word not in STOP_WORDS)


def _word_windows(words: list[str], size: int, step: int) -> list[tuple[int, str]]:
    if not words:
        return []

    if len(words) <= size:
        return [(0, " ".join(words))]

    windows = []
    for start in range(0, len(words) - size + 1, max(step, 1)):
        windows.append((start, " ".join(words[start:start + size])))
    return windows


def _rank_windows(text: str) -> list[tuple[float, int, str]]:
    words = text.split()
    if not words:
        return []

    frequencies = _keyword_frequencies(text)
    windows = _word_windows(words, size=WINDOW_WORDS, step=max(WINDOW_WORDS // 2, 1))
    ranked = []
    for pos, chunk in windows:
        score = _score_window(chunk, frequencies)
        # Prefer early overview windows slightly so the notes start with the main idea.
        position_bias = 1.0 - (pos / max(len(words), 1)) * 0.18
        ranked.append((score * position_bias, pos, chunk))
    ranked.sort(reverse=True)
    return ranked


def _score_window(chunk: str, frequencies: Counter) -> float:
    chunk_words = re.findall(r"[a-zA-Z]{3,}", chunk.lower())
    if not chunk_words:
        return 0.0
    score = sum(frequencies.get(word, 0) for word in chunk_words if word not in STOP_WORDS)
    return score / len(chunk_words)


def _build_tldr(text: str, ranked_windows: list[tuple[float, int, str]]) -> str:
    words = text.split()
    if not words:
        return ""

    if len(words) <= TLDR_WORDS:
        return _to_summary_sentence(" ".join(words), max_words=TLDR_WORDS)

    frequencies = _keyword_frequencies(text)
    if not frequencies:
        return _to_summary_sentence(" ".join(words[:TLDR_WORDS]), max_words=TLDR_WORDS)

    top_chunks = []
    used_positions = []
    for _, pos, chunk in ranked_windows:
        if any(abs(pos - existing) < WINDOW_WORDS for existing in used_positions):
            continue
        top_chunks.append(chunk)
        used_positions.append(pos)
        if len(top_chunks) >= 3:
            break

    combined = clean_text(" ".join(top_chunks))
    return _to_summary_sentence(combined, max_words=TLDR_WORDS)


def _build_bullets(text: str, ranked_windows: list[tuple[float, int, str]]) -> list[str]:
    words = text.split()
    if not words:
        return []

    selected: list[tuple[int, str]] = []
    min_gap = WINDOW_WORDS
    for _, pos, chunk in ranked_windows:
        if len(selected) >= NUM_BULLETS:
            break
        if any(abs(pos - existing_pos) < min_gap for existing_pos, _ in selected):
            continue
        selected.append((pos, chunk))

    selected.sort(key=lambda item: item[0])

    bullets = []
    seen = set()
    for _, chunk in selected:
        bullet = _to_bullet(chunk, max_words=BULLET_WORDS)
        fingerprint = re.sub(r"[^a-z0-9]+", "", bullet.lower())[:120]
        if fingerprint and fingerprint not in seen:
            bullets.append(bullet)
            seen.add(fingerprint)

    if len(bullets) < min(3, NUM_BULLETS):
        fallback_chunks = _word_windows(words, size=BULLET_WORDS, step=BULLET_WORDS)
        for _, chunk in fallback_chunks:
            bullet = _to_bullet(chunk, max_words=BULLET_WORDS)
            fingerprint = re.sub(r"[^a-z0-9]+", "", bullet.lower())[:120]
            if fingerprint and fingerprint not in seen:
                bullets.append(bullet)
                seen.add(fingerprint)
            if len(bullets) >= min(3, NUM_BULLETS):
                break

    return bullets


def find_key_timestamps(segments: list[TranscriptSegment], count: int = 5) -> list[dict]:
    if not segments:
        return []

    windows: list[tuple[float, str]] = []
    current_text: list[str] = []
    window_start = segments[0].start
    window_size = 45.0

    for segment in segments:
        if segment.start - window_start > window_size and current_text:
            windows.append((window_start, clean_text(" ".join(current_text))))
            current_text = []
            window_start = segment.start
        current_text.append(segment.text)

    if current_text:
        windows.append((window_start, clean_text(" ".join(current_text))))

    frequencies = _keyword_frequencies(" ".join(text for _, text in windows))
    scored = []
    for start, text in windows:
        score = _score_window(text, frequencies)
        scored.append((score, start, text))

    top = sorted(scored, reverse=True)[:count]
    top.sort(key=lambda item: item[1])

    return [
        {
            "time": format_timestamp(start),
            "seconds": round(start, 2),
            "text": _shorten(text, 140),
        }
        for _, start, text in top
    ]


def _to_summary_sentence(text: str, max_words: int) -> str:
    text = _cleanup_phrase(text)
    words = text.split()
    compact = " ".join(words[:max_words])
    compact = re.sub(r"\s+", " ", compact).strip(" ,;:-")
    return compact.rstrip(".,;:") + "."


def _to_bullet(text: str, max_words: int) -> str:
    text = _cleanup_phrase(text)
    words = text.split()
    compact = " ".join(words[:max_words])
    compact = re.sub(r"\s+", " ", compact).strip(" ,;:-")
    compact = compact[0:1].upper() + compact[1:] if compact else compact
    return compact.rstrip(".,;:") + "."


def _cleanup_phrase(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"\b(um|uh|okay|yeah|so|now|well|like)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(and|but|so|because|then)\s+", "", text, flags=re.IGNORECASE)
    return text


def _shorten(text: str, limit: int) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit - 3].rsplit(" ", 1)[0] + "..."
