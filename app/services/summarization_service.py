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


class GeminiServiceError(RuntimeError):
    pass


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
        if style == "chunk":
            style_instruction = (
               """
Create a concise synthesis of this transcript section in 3-5 sentences.
Identify the main topic, meaningful subtopics, context, and conclusions.
Write in your own words and avoid transcript wording.
"""
            )
        else:
            style_instruction = (
                "Create a concise but complete overview of the full video in one polished paragraph. "
                "Explain what the video is about, what is discussed or taught, and the main conclusions. "
                "Adapt the length to the content size while staying focused and professional."
            )

        music_note = (
            "The transcript appears to be music- or lyric-heavy; focus only on observable meaning and avoid restating repeated lyrics.\n"
        ) if music_warning else ""

        prompt = f"""
You are an expert video content analyst.

Your job is to transform transcripts into meaningful summaries and insights.
Your primary goal is understanding, not extraction.

Rules:
1. Never copy transcript sentences verbatim unless absolutely necessary.
2. Never return transcript fragments as summaries.
3. Never write labels such as NOTE, SUMMARY, KEY POINTS, TRANSCRIPT, or IMPORTANT.
4. Ignore filler words, repeated phrases, greetings, advertisements, sponsorships, and unrelated chatter.
5. Analyze the entire transcript before writing.
6. Identify the video's main topic and all major subtopics.
7. Understand context rather than repeating words.
8. If multiple topics are discussed, include all significant topics in proportion to their importance.
9. Focus on concepts explained, lessons taught, stories shared, opinions expressed, announcements made, conclusions reached, recommendations given, and important events discussed.
10. Rewrite everything in clear professional language.

{music_note}{style_instruction}

Return only the summary paragraph. Do not use bullet points, headings, labels, quotes, or JSON.

Transcript:
{text}
"""
        response = await self._generate_with_retry(
            prompt,
            max_output_tokens=700,
            operation="Gemini summarization",
        )
        result = getattr(response, "text", "").strip()
        if not result:
            raise GeminiServiceError("Gemini returned an empty summary.")
        return result

    async def _generate_bullets_gemini(self, text: str) -> List[str]:
        """Generate 3-5 meaningful bullet points from the transcript."""
        prompt = (
            f"""
You are an expert video content analyst.

Analyze the entire transcript and extract only the most meaningful takeaways.

Rules:
- Base every point strictly on transcript content.
- Ignore filler speech, repetition, greetings, advertisements, sponsorships, and unrelated chatter.
- Focus on concepts, lessons, stories, opinions, announcements, conclusions, recommendations, and important events.
- Each point must be a complete idea that helps someone understand the video without watching it.
- Do not copy transcript wording.
- Do not create points for minor details.
- Return a maximum of 10 points.
- Return only bullet points with no heading, label, or introduction.

Transcript:
{text}
"""
        )

        response = await self._generate_with_retry(
            prompt,
            max_output_tokens=220,
            operation="Gemini bullet generation",
        )
        bullets = self._parse_bullet_lines(getattr(response, "text", ""))
        if bullets:
            return bullets[:10]
        return self._fallback_bullets(text)

    async def _generate_with_retry(self, prompt: str, *, max_output_tokens: int, operation: str):
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.15,
                            max_output_tokens=max_output_tokens,
                            top_p=0.9,
                        ),
                    ),
                )
            except Exception as exc:
                last_error = exc
                logger.warning("%s failed on attempt %s/2: %s", operation, attempt + 1, exc)
                if attempt == 0:
                    await asyncio.sleep(1)

        raise GeminiServiceError(f"{operation} failed after retry: {last_error}") from last_error

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
            bullet = self._limit_words(bullet.rstrip(". "), 32)
            if bullet not in bullets:
                bullets.append(bullet)

        return bullets

    def _fallback_bullets(self, text: str, limit: int = 3) -> List[str]:
        """Return non-verbatim fallback points when model extraction is unavailable."""
        fallback = [
            "Reliable takeaways could not be generated from the available transcript.",
            "The transcript may be too short, noisy, repetitive, or lacking clear structure.",
            "A clearer spoken-video transcript should produce stronger insights.",
        ]
        return fallback[:limit]

    def _limit_words(self, text: str, max_words: int) -> str:
        words = clean_text(text).split()
        if len(words) <= max_words:
            return " ".join(words).rstrip(". ")
        return " ".join(words[:max_words]).rstrip(". ") + "..."

    def _format_output(self, summary_text: str, bullets: List[str], music_warning: bool) -> str:
        """Return the final summary paragraph without labels or embedded bullet sections."""
        return summary_text.strip()

    def _simple_summary(self, text: str, segments: List[TranscriptSegment]) -> dict:
        """Handle short transcripts with a professional fallback."""
        bullets = self._fallback_bullets(text, limit=2)
        return {
            "model_used": settings.gemini_model,
            "tldr": "The video is too brief to support a detailed summary, but it appears to contain a short spoken segment with limited context.",
            "bullets": bullets,
            "timestamps": self._find_key_timestamps(segments),
        }

    def _empty_summary(self) -> dict:
        """Return empty summary structure."""
        return {
            "model_used": settings.gemini_model,
            "tldr": "Summary generation failed.",
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

        
