from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from requests import RequestException
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApiException,
)

from app.config.settings import settings
from app.models import TranscriptResult, TranscriptSegment
from app.utils import clean_text, extract_video_id


logger = logging.getLogger(__name__)


class TranscriptService:
    def __init__(self):
        self.timeout = settings.transcript_timeout

    async def fetch_transcript(self, url_or_id: str, language: str = "en") -> TranscriptResult:
        """Fetch transcript with comprehensive fallback strategy."""
        video_id = extract_video_id(url_or_id)
        preferred_languages = list(dict.fromkeys([language, "en", "en-US", "en-GB"]))

        # Try YouTube Transcript API first
        try:
            result = await self._fetch_from_youtube_api(video_id, preferred_languages)
            if result:
                return result
        except Exception as e:
            logger.warning(f"YouTube API failed for {video_id}: {e}")

        # Try yt-dlp fallback
        try:
            result = await self._fetch_from_ytdlp(video_id, preferred_languages)
            if result:
                return result
        except Exception as e:
            logger.warning(f"yt-dlp fallback failed for {video_id}: {e}")

        # Try Whisper fallback
        try:
            result = await self._fetch_from_whisper(video_id, preferred_languages[0])
            if result:
                return result
        except Exception as e:
            logger.warning(f"Whisper fallback failed for {video_id}: {e}")

        raise TranscriptUnavailableError("No transcript could be retrieved for this video.")

    async def _fetch_from_youtube_api(self, video_id: str, preferred_languages: List[str]) -> Optional[TranscriptResult]:
        """Fetch transcript using youtube-transcript-api."""
        try:
            transcript_list = await asyncio.get_event_loop().run_in_executor(
                None, YouTubeTranscriptApi.list_transcripts, video_id
            )
        except Exception as e:
            logger.warning(f"Failed to list transcripts for {video_id}: {e}")
            return None

        # Try manual captions
        try:
            transcript = transcript_list.find_manually_created_transcript(preferred_languages)
            raw_segments = await asyncio.get_event_loop().run_in_executor(None, transcript.fetch)
            return self._build_result(video_id, raw_segments, transcript.language_code, "YouTube captions")
        except NoTranscriptFound:
            pass

        # Try auto-generated captions
        try:
            transcript = transcript_list.find_generated_transcript(preferred_languages)
            raw_segments = await asyncio.get_event_loop().run_in_executor(None, transcript.fetch)
            return self._build_result(video_id, raw_segments, transcript.language_code, "YouTube auto-generated captions")
        except NoTranscriptFound:
            pass

        # Try any available transcript
        try:
            transcript = transcript_list.find_transcript(preferred_languages)
            raw_segments = await asyncio.get_event_loop().run_in_executor(None, transcript.fetch)
            source = "YouTube auto-generated captions" if transcript.is_generated else "YouTube captions"
            return self._build_result(video_id, raw_segments, transcript.language_code, source)
        except NoTranscriptFound:
            pass

        # Try translated transcripts
        for transcript in transcript_list:
            if transcript.is_translatable:
                try:
                    translated = transcript.translate(preferred_languages[0])
                    raw_segments = await asyncio.get_event_loop().run_in_executor(None, translated.fetch)
                    return self._build_result(video_id, raw_segments, translated.language_code,
                                             f"Translated captions from {transcript.language_code}")
                except Exception:
                    continue

        return None

    async def _fetch_from_ytdlp(self, video_id: str, preferred_languages: List[str]) -> Optional[TranscriptResult]:
        """Fetch transcript using yt-dlp."""
        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            return None

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Build yt-dlp options with fallbacks
        options_list = self._build_ytdlp_options()

        for options in options_list:
            try:
                with YoutubeDL(options) as ydl:
                    info = await asyncio.get_event_loop().run_in_executor(
                        None, ydl.extract_info, video_url, False
                    )

                subtitle_sources = [
                    (info.get("subtitles") or {}, "YouTube captions via yt-dlp"),
                    (info.get("automatic_captions") or {}, "YouTube auto-generated captions via yt-dlp"),
                ]

                for subtitle_map, label in subtitle_sources:
                    candidate = self._pick_subtitle_track(subtitle_map, preferred_languages)
                    if not candidate:
                        continue
                    language_code, formats = candidate
                    for fmt in self._rank_subtitle_formats(formats):
                        try:
                            raw_segments = await self._download_subtitle_segments(fmt["url"], fmt.get("ext", ""))
                            if raw_segments:
                                return self._build_result(video_id, raw_segments, language_code, label)
                        except Exception as e:
                            logger.warning(f"Subtitle download failed for {video_id}: {e}")
                            continue

            except Exception as e:
                logger.warning(f"yt-dlp failed with options {options}: {e}")
                continue

        return None

    async def _fetch_from_whisper(self, video_id: str, language: str) -> Optional[TranscriptResult]:
        """Fetch transcript using Whisper."""
        if not settings.enable_whisper_fallback:
            return None

        if not shutil.which("ffmpeg"):
            logger.warning("Whisper fallback skipped: ffmpeg not installed")
            return None

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.warning("faster-whisper not installed")
            return None

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            from yt_dlp import YoutubeDL
        except ImportError:
            return None

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

            # Add cookie options if available
            if settings.ytdlp_cookie_file:
                ytdlp_options["cookiefile"] = settings.ytdlp_cookie_file
            elif settings.ytdlp_cookies_from_browser:
                ytdlp_options["cookiesfrombrowser"] = (settings.ytdlp_cookies_from_browser,)

            try:
                with YoutubeDL(ytdlp_options) as ydl:
                    info = await asyncio.get_event_loop().run_in_executor(
                        None, ydl.extract_info, video_url, True
                    )
                    downloaded_path = Path(ydl.prepare_filename(info))

                if not downloaded_path.exists():
                    return None

                # Load Whisper model
                model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")

                # Transcribe
                segments, info = await asyncio.get_event_loop().run_in_executor(
                    None, model.transcribe, str(downloaded_path), {"language": language if len(language) == 2 else None}
                )

                raw_segments = []
                for segment in segments:
                    text = clean_text(segment.text)
                    if not text:
                        continue
                    raw_segments.append({
                        "text": text,
                        "start": segment.start,
                        "duration": segment.end - segment.start,
                    })

                if raw_segments:
                    detected_language = info.language or language
                    return self._build_result(video_id, raw_segments, detected_language,
                                            f"Whisper transcription ({settings.whisper_model})")

            except Exception as e:
                logger.warning(f"Whisper transcription failed for {video_id}: {e}")

        return None

    def _build_ytdlp_options(self) -> List[dict]:
        """Build yt-dlp options with cookie fallbacks."""
        base_options = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "listsubtitles": False,
        }

        attempts = [base_options.copy()]

        if settings.ytdlp_cookie_file and Path(settings.ytdlp_cookie_file).exists():
            option = base_options.copy()
            option["cookiefile"] = settings.ytdlp_cookie_file
            attempts.append(option)

        if settings.ytdlp_cookies_from_browser:
            browsers = [settings.ytdlp_cookies_from_browser]
            for browser in browsers:
                option = base_options.copy()
                option["cookiesfrombrowser"] = (browser,)
                attempts.append(option)

        return attempts

    def _pick_subtitle_track(self, subtitle_map: dict, preferred_languages: List[str]) -> Optional[Tuple[str, List[dict]]]:
        """Pick the best subtitle track."""
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

    def _rank_subtitle_formats(self, formats: List[dict]) -> List[dict]:
        """Rank subtitle formats by preference."""
        preferred = {"json3": 0, "srv3": 1, "srv2": 2, "srv1": 3, "vtt": 4, "ttml": 5}
        return sorted(formats, key=lambda item: preferred.get(str(item.get("ext", "")).lower(), 99))

    async def _download_subtitle_segments(self, url: str, extension: str) -> List[dict]:
        """Download and parse subtitle segments."""
        response = await asyncio.get_event_loop().run_in_executor(
            None, requests.get, url, {"timeout": self.timeout}
        )
        response.raise_for_status()
        ext = extension.lower()
        if ext == "json3":
            return self._parse_json3_segments(response.text)
        if ext in {"srv3", "srv2", "srv1", "ttml", "xml"}:
            return self._parse_xml_segments(response.text)
        return self._parse_vtt_segments(response.text)

    def _parse_json3_segments(self, payload: str) -> List[dict]:
        data = json.loads(payload)
        events = data.get("events", [])
        segments = []
        for event in events:
            if "segs" not in event:
                continue
            text = "".join(seg.get("utf8", "") for seg in event.get("segs", []))
            if clean_text(text):
                segments.append({
                    "text": text,
                    "start": float(event.get("tStartMs", 0)) / 1000.0,
                    "duration": float(event.get("dDurationMs", 0)) / 1000.0,
                })
        return segments

    def _parse_xml_segments(self, payload: str) -> List[dict]:
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

    def _parse_vtt_segments(self, payload: str) -> List[dict]:
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
                start = self._parse_vtt_timestamp(start_text)
                end = self._parse_vtt_timestamp(end_text.split(" ")[0])
                duration = max(end - start, 0.0)
                segments.append({"text": text, "start": start, "duration": duration})
        return segments

    def _parse_vtt_timestamp(self, value: str) -> float:
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

    def _build_result(self, video_id: str, raw_segments: List[dict], language: str, source: str) -> TranscriptResult:
        """Build TranscriptResult from raw segments."""
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
            raise TranscriptUnavailableError("Transcript was found but contained no readable text.")

        return TranscriptResult(
            video_id=video_id,
            language=language,
            source=source,
            segments=segments,
        )


class TranscriptUnavailableError(RuntimeError):
    pass