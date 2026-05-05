from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

import requests
from requests import RequestException
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TooManyRequests,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.utils import clean_text, extract_video_id


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
    segments: list[TranscriptSegment]

    @property
    def full_text(self) -> str:
        return clean_text(" ".join(segment.text for segment in self.segments))


class TranscriptUnavailableError(RuntimeError):
    pass


logger = logging.getLogger("luminote.transcript")


def fetch_transcript(url_or_id: str, language: str = "en") -> TranscriptResult:
    video_id = extract_video_id(url_or_id)
    preferred_languages = list(dict.fromkeys([language, "en", "en-US", "en-GB"]))

    try:
        transcript, source_language, source = _fetch_with_retries(video_id, preferred_languages)
        try:
            raw_segments = transcript.fetch()
        except (RequestException, CouldNotRetrieveTranscript, TooManyRequests) as exc:
            raise TranscriptUnavailableError(_friendly_transcript_error(exc)) from exc
        except Exception as exc:
            logger.exception("Unexpected transcript fetch failure for video %s", video_id)
            raise TranscriptUnavailableError("YouTube returned an unreadable transcript response for this video.") from exc
    except TranscriptUnavailableError as primary_error:
        logger.warning("Primary transcript fetch failed for %s: %s", video_id, primary_error)
        yt_dlp_result = _fetch_with_ytdlp(video_id, preferred_languages)
        if yt_dlp_result:
            source_language, source, raw_segments = yt_dlp_result
        else:
            whisper_result = _transcribe_with_whisper(video_id, preferred_languages[0])
            if not whisper_result:
                raise primary_error
            source_language, source, raw_segments = whisper_result

    segments = [
        TranscriptSegment(
            text=clean_text(item.get("text", "")),
            start=float(item.get("start", 0.0)),
            duration=float(item.get("duration", 0.0)),
        )
        for item in raw_segments
        if clean_text(item.get("text", ""))
    ]

    if not segments:
        raise TranscriptUnavailableError("Transcript was found, but it did not contain readable text.")

    return TranscriptResult(
        video_id=video_id,
        language=source_language,
        source=source,
        segments=segments,
    )


def _fetch_with_ytdlp(video_id: str, preferred_languages: list[str]):
    try:
        from yt_dlp import YoutubeDL
    except Exception:
        return None

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    for options in _build_ytdlp_attempts():
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(video_url, download=False)
        except Exception as exc:
            cookie_label = options.get("cookiefile") or options.get("cookiesfrombrowser") or "no cookies"
            logger.warning("yt-dlp transcript fallback failed for %s using %s: %s", video_id, cookie_label, exc)
            continue

        subtitle_sources = [
            (info.get("subtitles") or {}, "YouTube captions via yt-dlp"),
            (info.get("automatic_captions") or {}, "YouTube auto-generated captions via yt-dlp"),
        ]

        for subtitle_map, label in subtitle_sources:
            candidate = _pick_subtitle_track(subtitle_map, preferred_languages)
            if not candidate:
                continue
            language_code, formats = candidate
            for fmt in _rank_subtitle_formats(formats):
                try:
                    raw_segments = _download_subtitle_segments(fmt["url"], fmt.get("ext", ""))
                except Exception as exc:
                    logger.warning("Subtitle download failed for %s (%s): %s", video_id, language_code, exc)
                    continue
                if raw_segments:
                    return language_code, label, raw_segments

    return None


def _build_ytdlp_attempts() -> list[dict]:
    base_options = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "listsubtitles": False,
    }

    attempts = [base_options.copy()]
    cookie_file = os.getenv("YTDLP_COOKIE_FILE", "").strip()
    if cookie_file:
        option = base_options.copy()
        option["cookiefile"] = cookie_file
        attempts.append(option)

    browser_env = os.getenv("YTDLP_COOKIES_FROM_BROWSER", "").strip()
    browsers = [browser_env] if browser_env else ["chrome", "edge", "brave", "firefox"]
    for browser in browsers:
        if not browser:
            continue
        option = base_options.copy()
        option["cookiesfrombrowser"] = (browser,)
        attempts.append(option)

    unique_attempts = []
    seen = set()
    for attempt in attempts:
        key = (
            attempt.get("cookiefile", ""),
            tuple(attempt.get("cookiesfrombrowser", ())),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_attempts.append(attempt)
    return unique_attempts


def _transcribe_with_whisper(video_id: str, language: str):
    if os.getenv("ENABLE_WHISPER_FALLBACK", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        return None

    if not shutil.which("ffmpeg"):
        logger.warning("Whisper fallback skipped for %s because ffmpeg is not installed.", video_id)
        return None

    try:
        from yt_dlp import YoutubeDL
        import whisper
    except Exception as exc:
        logger.warning("Whisper fallback dependencies unavailable for %s: %s", video_id, exc)
        return None

    model_name = os.getenv("WHISPER_MODEL", "tiny")
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    with tempfile.TemporaryDirectory(prefix="luminote_whisper_") as temp_dir:
        output_template = str(Path(temp_dir) / f"{video_id}.%(ext)s")
        ytdlp_options = {
            "format": "bestaudio/best",
            "skip_download": False,
            "quiet": True,
            "no_warnings": True,
            "outtmpl": output_template,
            "noplaylist": True,
        }

        for cookie_options in _build_ytdlp_attempts():
            download_options = ytdlp_options | {
                key: value
                for key, value in cookie_options.items()
                if key in {"cookiefile", "cookiesfrombrowser"}
            }
            try:
                with YoutubeDL(download_options) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    downloaded_path = Path(ydl.prepare_filename(info))
            except Exception as exc:
                cookie_label = download_options.get("cookiefile") or download_options.get("cookiesfrombrowser") or "no cookies"
                logger.warning("Whisper audio download failed for %s using %s: %s", video_id, cookie_label, exc)
                continue

            if not downloaded_path.exists():
                logger.warning("Whisper fallback could not find downloaded audio for %s", video_id)
                continue

            try:
                model = whisper.load_model(model_name)
                result = model.transcribe(str(downloaded_path), language=language if len(language) == 2 else None, fp16=False)
            except Exception as exc:
                logger.warning("Whisper transcription failed for %s with model %s: %s", video_id, model_name, exc)
                return None

            raw_segments = []
            for segment in result.get("segments", []):
                text = clean_text(segment.get("text", ""))
                if not text:
                    continue
                start = float(segment.get("start", 0.0))
                end = float(segment.get("end", start))
                raw_segments.append(
                    {
                        "text": text,
                        "start": start,
                        "duration": max(end - start, 0.0),
                    }
                )

            if raw_segments:
                detected_language = result.get("language") or language
                return detected_language, f"Local Whisper transcription ({model_name})", raw_segments

    return None


def _pick_subtitle_track(subtitle_map: dict, preferred_languages: list[str]):
    for language_code in preferred_languages:
        if language_code in subtitle_map:
            return language_code, subtitle_map[language_code]

    normalized_map = {code.lower(): (code, formats) for code, formats in subtitle_map.items()}
    for language_code in preferred_languages:
        match = normalized_map.get(language_code.lower())
        if match:
            return match

    for code, formats in subtitle_map.items():
        if code.lower().startswith("en"):
            return code, formats

    for code, formats in subtitle_map.items():
        return code, formats

    return None


def _rank_subtitle_formats(formats: list[dict]) -> list[dict]:
    preferred = {"json3": 0, "srv3": 1, "srv2": 2, "srv1": 3, "vtt": 4, "ttml": 5}
    return sorted(formats, key=lambda item: preferred.get(str(item.get("ext", "")).lower(), 99))


def _download_subtitle_segments(url: str, extension: str) -> list[dict]:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    ext = extension.lower()
    if ext == "json3":
        return _parse_json3_segments(response.text)
    if ext in {"srv3", "srv2", "srv1", "ttml", "xml"}:
        return _parse_xml_segments(response.text)
    return _parse_vtt_segments(response.text)


def _parse_json3_segments(payload: str) -> list[dict]:
    data = json.loads(payload)
    events = data.get("events", [])
    segments = []
    for event in events:
        if "segs" not in event:
            continue
        text = "".join(seg.get("utf8", "") for seg in event.get("segs", []))
        if clean_text(text):
            segments.append(
                {
                    "text": text,
                    "start": float(event.get("tStartMs", 0)) / 1000.0,
                    "duration": float(event.get("dDurationMs", 0)) / 1000.0,
                }
            )
    return segments


def _parse_xml_segments(payload: str) -> list[dict]:
    matches = re.findall(r'<text start="([^"]+)" dur="([^"]+)"[^>]*>(.*?)</text>', payload, flags=re.DOTALL)
    segments = []
    for start, duration, text in matches:
        text = (
            text.replace("&amp;", "&")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )
        text = re.sub(r"<[^>]+>", " ", text)
        if clean_text(text):
            segments.append({"text": text, "start": float(start), "duration": float(duration)})
    return segments


def _parse_vtt_segments(payload: str) -> list[dict]:
    blocks = re.split(r"\r?\n\r?\n+", payload)
    segments = []
    for block in blocks:
        lines = [line.strip("\ufeff") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if "-->" not in lines[0] and len(lines) > 1 and "-->" in lines[1]:
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        start_text, end_text = [part.strip() for part in lines[0].split("-->", 1)]
        text = " ".join(lines[1:])
        text = re.sub(r"<[^>]+>", " ", text)
        if clean_text(text):
            start = _parse_vtt_timestamp(start_text)
            end = _parse_vtt_timestamp(end_text.split(" ")[0])
            duration = max(end - start, 0.0)
            segments.append({"text": text, "start": start, "duration": duration})
    return segments


def _parse_vtt_timestamp(value: str) -> float:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours = "0"
        minutes, seconds = parts
    else:
        return 0.0
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _fetch_with_retries(video_id: str, preferred_languages: list[str]):
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            return _select_transcript(video_id, preferred_languages)
        except TooManyRequests as exc:
            last_error = exc
            wait_seconds = 1.5 * (attempt + 1)
            logger.warning("YouTube transcript rate limited; retrying in %.1fs", wait_seconds)
            time.sleep(wait_seconds)
        except (CouldNotRetrieveTranscript, RequestException) as exc:
            last_error = exc
            if attempt == 2:
                break
            wait_seconds = 1.0 * (attempt + 1)
            logger.warning("Could not retrieve transcript; retrying in %.1fs", wait_seconds)
            time.sleep(wait_seconds)
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
            last_error = exc
            break

    message = _friendly_transcript_error(last_error)
    raise TranscriptUnavailableError(message) from last_error


def _select_transcript(video_id: str, preferred_languages: list[str]):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    except (RequestException, CouldNotRetrieveTranscript, TooManyRequests, TranscriptsDisabled, VideoUnavailable) as exc:
        raise exc
    except Exception as exc:
        logger.exception("Unexpected transcript listing failure for video %s", video_id)
        raise TranscriptUnavailableError("YouTube did not return caption metadata for this video.") from exc

    try:
        transcript = transcript_list.find_manually_created_transcript(preferred_languages)
        return transcript, transcript.language_code, "YouTube captions"
    except NoTranscriptFound:
        pass

    try:
        transcript = transcript_list.find_generated_transcript(preferred_languages)
        return transcript, transcript.language_code, "YouTube auto-generated captions"
    except NoTranscriptFound:
        pass

    try:
        transcript = transcript_list.find_transcript(preferred_languages)
        source = "YouTube auto-generated captions" if transcript.is_generated else "YouTube captions"
        return transcript, transcript.language_code, source
    except NoTranscriptFound:
        pass

    for transcript in transcript_list:
        if transcript.is_translatable:
            translated = transcript.translate(preferred_languages[0])
            return translated, translated.language_code, f"Translated captions from {transcript.language_code}"

    raise TranscriptUnavailableError("No captions are available in the requested language or as a translatable fallback.")


def _friendly_transcript_error(exc: Exception | None) -> str:
    if isinstance(exc, TranscriptsDisabled):
        return "Captions are disabled by the video owner."
    if isinstance(exc, VideoUnavailable):
        return "This video is unavailable, private, age restricted, or region blocked."
    if isinstance(exc, NoTranscriptFound):
        return "No usable transcript was found for the requested language."
    if isinstance(exc, TooManyRequests):
        return "YouTube temporarily rate limited transcript requests. Wait a minute and try again."
    if isinstance(exc, RequestException):
        return "The backend could not reach YouTube to fetch captions, even after fallback attempts. Check your internet connection, firewall, or browser-cookie access."
    if isinstance(exc, TranscriptUnavailableError):
        return str(exc)
    return "Transcript is unavailable for this video."
