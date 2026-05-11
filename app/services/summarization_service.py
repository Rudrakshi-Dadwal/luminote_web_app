from __future__ import annotations

import asyncio
import logging
import re
from typing import List

import google.generativeai as genai

from app.config.settings import settings
from app.models import TranscriptSegment
from app.utils import clean_transcript, clean_text, format_timestamp, is_lyric_or_music_text


logger = logging.getLogger(__name__)


class SummarizationService:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    async def summarize_transcript(self, segments: List[TranscriptSegment]) -> dict:
        """Perform hierarchical summarization using Gemini API."""
        if not segments:
            return self._empty_summary()

        raw_text = " ".join(segment.text for segment in segments)
        cleaned_text = clean_transcript(raw_text)
        if not cleaned_text:
            return self._empty_summary()

        cleaned_text = cleaned_text[: settings.max_transcript_chars]
        if len(cleaned_text) < 100:
            return self._simple_summary(cleaned_text, segments)

        music_warning = is_lyric_or_music_text(cleaned_text)
        if music_warning:
            logger.info("Music or lyric-heavy transcript detected")

        estimated_tokens = len(cleaned_text) // 4
        if estimated_tokens <= settings.max_chunk_tokens:
            summary_text = await self._summarize_with_gemini(cleaned_text, style="full", music_warning=music_warning)
        else:
            chunk_summaries = []
            for chunk in self._chunk_by_tokens(cleaned_text, settings.max_chunk_tokens, settings.chunk_overlap):
                try:
                    chunk_summary = await self._summarize_with_gemini(chunk, style="chunk", music_warning=music_warning)
                    chunk_summaries.append(chunk_summary)
                except Exception as exc:
                    logger.warning("Chunk summarization failed: %s", exc)
                    chunk_summaries.append("Summary generation failed.")

            combined_chunks = "\n\n".join(chunk_summaries)
            if len(combined_chunks) // 4 > settings.max_chunk_tokens:
                final_summaries = []
                for chunk in self._chunk_by_tokens(combined_chunks, settings.max_chunk_tokens, settings.chunk_overlap):
                    final_summaries.append(await self._summarize_with_gemini(chunk, style="full", music_warning=music_warning))
                summary_text = " ".join(final_summaries)
            else:
                summary_text = await self._summarize_with_gemini(combined_chunks, style="full", music_warning=music_warning)

        bullets = await self._generate_bullets_gemini(cleaned_text)
        if not bullets:
            bullets = self._fallback_bullets(cleaned_text)

        formatted_summary = self._format_output(summary_text, bullets, music_warning)
        timestamps = self._find_key_timestamps(segments)

        return {
            "model_used": settings.gemini_model,
            "tldr": formatted_summary,
            "bullets": bullets,
            "timestamps": timestamps,
        }

    def _chunk_by_tokens(self, text: str, max_tokens: int, overlap: int) -> List[str]:
        """Chunk text by estimated token count."""
        words = text.split()
        chunks: List[str] = []
        start = 0

        while start < len(words):
            current_tokens = 0
            chunk_words: List[str] = []

            for word in words[start:]:
                token_estimate = max(1, len(word) // 4)
                if current_tokens + token_estimate > max_tokens and chunk_words:
                    break
                chunk_words.append(word)
                current_tokens += token_estimate

            if not chunk_words:
                break

            chunks.append(" ".join(chunk_words))
            start += max(len(chunk_words) - overlap, 1)

        return chunks

    async def _summarize_with_gemini(self, text: str, style: str, music_warning: bool = False) -> str:
        """Summarize text using Gemini AI with a professional prompt."""
        summary_goal = (
            "Summarize this transcript in a professional, concise way. "
            "Do not echo the transcript verbatim, and avoid listing repeated lyrics or filler phrases. "
            "Focus on the meaning, outcomes, and the most important insights."
        )

        if style == "chunk":
            style_instruction = (
                "Summarize this excerpt in 2-3 sentences. "
                "Capture the main point and key takeaway without repeating the text."
            )
        else:
            style_instruction = (
                "Summarize the full transcript in a polished paragraph of 4-6 sentences. "
                "Highlight the main message, practical results, and any notable conclusions."
            )

        music_note = (
            "This transcript appears to be music- or lyric-heavy; focus on observable meaning and do not restate repeated lyrics.\n"
        ) if music_warning else ""

        prompt = (
            f"You are a professional summarization assistant. {summary_goal}\n"
            f"{music_note}\n"
            "TRANSCRIPT:\n"
            f"{text}\n\n"
            "SUMMARY:\n"
        )

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.15,
                        max_output_tokens=450,
                        top_p=0.9,
                    ),
                ),
            )
            result = response.text.strip()
            return result or "Summary generation failed."
        except Exception as exc:
            logger.error("Gemini summarization failed: %s", exc)
            return "Summary generation failed."

    async def _generate_bullets_gemini(self, text: str) -> List[str]:
        """Generate 3-5 meaningful bullet points from the transcript."""
        prompt = (
            "You are a professional assistant. Extract 3 to 5 distinct key points from the transcript below. "
            "Avoid repetition, filler, and lyric noise. Return each key point on its own line starting with a dash.\n\n"
            "TRANSCRIPT:\n"
            f"{text}\n\n"
            "KEY POINTS:\n"
        )

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.15,
                        max_output_tokens=220,
                        top_p=0.9,
                    ),
                ),
            )
            bullets = self._parse_bullet_lines(response.text)
            if len(bullets) >= 3:
                return bullets[:5]
            return self._fallback_bullets(text)
        except Exception as exc:
            logger.error("Gemini bullet generation failed: %s", exc)
            return self._fallback_bullets(text)

    def _parse_bullet_lines(self, text: str) -> List[str]:
        """Extract clean bullet lines from Gemini output."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        bullets: List[str] = []
        for line in lines:
            match = re.match(r"^[\-•*\d\.\)\s]*(.+)$", line)
            if not match:
                continue
            bullet = match.group(1).strip()
            bullet = re.sub(r"\s+", " ", bullet)
            if len(bullet) < 15:
                continue
            if bullet.lower().startswith("summary"):
                continue
            if bullet not in bullets:
                bullets.append(bullet.rstrip(". "))

        return bullets

    def _fallback_bullets(self, text: str, limit: int = 3) -> List[str]:
        """Generate fallback bullets from transcript text when model output is weak."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        bullets: List[str] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 40:
                continue
            if sentence.lower().startswith("this transcript"):
                continue
            summary_line = sentence.rstrip(".;")
            if summary_line not in bullets:
                bullets.append(summary_line)
            if len(bullets) >= limit:
                break

        if not bullets:
            bullets = [
                "Summary generation failed.",
                "The transcript did not produce strong key points.",
                "Try a narrative or spoken-video transcript for best results.",
            ]

        return bullets

    def _format_output(self, summary_text: str, bullets: List[str], music_warning: bool) -> str:
        """Format the final response in a professional summary structure."""
        notice = (
            "NOTE: This transcript appears music- or lyric-heavy; the summary may be less precise.\n\n"
        ) if music_warning else ""

        bullet_section = "\n".join(f"- {point}" for point in bullets[:5]) if bullets else "- Summary generation failed."
        formatted = (
            f"SUMMARY:\n{summary_text.strip()}\n\n"
            f"KEY POINTS:\n{bullet_section}"
        )
        return notice + formatted

    def _simple_summary(self, text: str, segments: List[TranscriptSegment]) -> dict:
        """Handle short transcripts with a professional fallback."""
        bullets = self._fallback_bullets(text, limit=2)
        return {
            "model_used": settings.gemini_model,
            "tldr": self._format_output(text, bullets, music_warning=False),
            "bullets": bullets,
            "timestamps": self._find_key_timestamps(segments),
        }

    def _empty_summary(self) -> dict:
        """Return empty summary structure."""
        return {
            "model_used": settings.gemini_model,
            "tldr": "SUMMARY:\nSummary generation failed.\n\nKEY POINTS:\n- Summary generation failed.",
            "bullets": ["Summary generation failed."],
            "timestamps": [],
        }

    def _find_key_timestamps(self, segments: List[TranscriptSegment], count: int = 5) -> List[dict]:
        """Find key timestamps from transcript segments."""
        if not segments:
            return []

        candidates: List[tuple[float, str]] = []
        for segment in segments:
            text = clean_text(segment.text)
            if len(text) > 50:
                candidates.append((segment.start, text))

        candidates.sort(key=lambda item: item[0])
        selected = candidates[:count]

        return [
            {
                "time": format_timestamp(start),
                "seconds": round(start, 2),
                "text": text[:140] + "..." if len(text) > 140 else text,
            }
            for start, text in selected
        ]

        