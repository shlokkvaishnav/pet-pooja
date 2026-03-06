"""
tts.py — TTS Orchestrator
============================
Single entry point called by routes_voice.py. Ties together:
  1. llm_response.py  — generates natural spoken text
  2. tts_normalizer.py — normalizes text for TTS engine
  3. tts_engine_indic.py — synthesizes audio

Returns { audio_b64, spoken_text, language }. Never raises —
degrades gracefully to None on any failure.

Usage:
    from modules.voice.tts import tts_orchestrator
    result = await tts_orchestrator.get_audio_response(pipeline_result, "hi")
"""

import base64
import logging

from .voice_config import cfg
from .llm_response import llm_generator
from . import tts_normalizer
from .tts_engine_indic import indic_engine

logger = logging.getLogger("petpooja.voice.tts")


class TTSOrchestrator:
    """Orchestrates LLM text generation → normalization → TTS synthesis."""

    async def get_audio_response(
        self, pipeline_result: dict, detected_language: str
    ) -> dict:
        """
        Generate spoken audio for a pipeline result.

        Args:
            pipeline_result: Full pipeline output dict from VoicePipeline.
            detected_language: Language code ("en", "hi", "gu", "mr", "kn").

        Returns:
            {
                "audio_b64": str | None,    # base64-encoded MP3
                "spoken_text": str | None,  # the text that was spoken
                "language": str,            # language used
            }

        Never raises — degrades gracefully to None values on failure.
        """
        lang = detected_language if detected_language in ("en", "hi", "gu", "mr", "kn") else "en"

        try:
            # Step 1: Generate natural response text (LLM or template)
            spoken_text = await llm_generator.get_response_text(pipeline_result, lang)

            if not spoken_text:
                logger.warning("No spoken text generated — skipping TTS")
                return {"audio_b64": None, "spoken_text": None, "language": lang}

            # Step 2: Normalize for TTS (symbols, scripts, item name protection)
            normalized = tts_normalizer.normalize(spoken_text, lang, pipeline_result)

            # Step 3: Synthesize to audio
            if not indic_engine.is_ready:
                logger.warning("TTS engine not ready — returning text only")
                return {"audio_b64": None, "spoken_text": spoken_text, "language": lang}

            audio_bytes = await indic_engine.synthesize_async(normalized, lang)

            # Step 4: Encode to base64
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            return {
                "audio_b64": audio_b64,
                "spoken_text": spoken_text,
                "language": lang,
            }

        except Exception as e:
            logger.warning(f"TTS pipeline failed: {e}")
            return {"audio_b64": None, "spoken_text": None, "language": lang}

    async def speak_text(self, text: str, language: str) -> dict:
        """
        Synthesize arbitrary text to audio (for /speak endpoint).

        Args:
            text: Text to speak.
            language: Language code.

        Returns:
            { "audio_b64": str | None, "text": str }
        """
        lang = language if language in ("en", "hi", "gu", "mr", "kn") else "en"

        try:
            # Normalize (pass empty pipeline_result since no menu context)
            normalized = tts_normalizer.normalize(text, lang, {})

            if not indic_engine.is_ready:
                return {"audio_b64": None, "text": text}

            audio_bytes = await indic_engine.synthesize_async(normalized, lang)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            return {"audio_b64": audio_b64, "text": text}

        except Exception as e:
            logger.warning(f"speak_text failed: {e}")
            return {"audio_b64": None, "text": text}


# Module-level singleton
tts_orchestrator = TTSOrchestrator()
