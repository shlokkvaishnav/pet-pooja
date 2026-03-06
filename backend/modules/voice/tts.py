"""
tts.py - TTS orchestrator.

Single entry point used by routes_voice.py. It ties together:
1. llm_response.py for spoken text generation
2. tts_normalizer.py for speech-friendly normalization
3. tts_engine_indic.py for actual synthesis
"""

import base64
import logging

from . import tts_normalizer
from .llm_response import llm_generator
from .tts_engine_indic import indic_engine

logger = logging.getLogger("petpooja.voice.tts")

SUPPORTED_LANGS = {"en", "hi", "gu", "mr", "kn"}


class TTSOrchestrator:
    """Generate spoken text, normalize it, and synthesize audio."""

    def _ensure_engine_ready(self) -> bool:
        """Warm the engine lazily so TTS still works if startup warmup was skipped."""
        if indic_engine.is_ready:
            return True

        try:
            indic_engine.warmup()
        except Exception as exc:
            logger.warning("TTS engine warmup failed on demand: %s", exc)

        return indic_engine.is_ready

    async def get_audio_response(self, pipeline_result: dict, detected_language: str) -> dict:
        """
        Generate spoken audio for a pipeline result.

        Returns:
            {
                "audio_b64": str | None,
                "spoken_text": str | None,
                "language": str,
            }
        """
        lang = detected_language if detected_language in SUPPORTED_LANGS else "en"

        try:
            spoken_text = await llm_generator.get_response_text(pipeline_result, lang)
            if not spoken_text:
                logger.warning("No spoken text generated - skipping TTS")
                return {"audio_b64": None, "spoken_text": None, "language": lang}

            normalized = tts_normalizer.normalize(spoken_text, lang, pipeline_result)

            if not self._ensure_engine_ready():
                logger.warning("TTS engine is not ready - returning text only")
                return {"audio_b64": None, "spoken_text": spoken_text, "language": lang}

            audio_bytes = await indic_engine.synthesize_async(normalized, lang)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            return {
                "audio_b64": audio_b64,
                "spoken_text": spoken_text,
                "language": lang,
            }
        except Exception as exc:
            logger.warning("TTS pipeline failed: %s", exc)
            return {"audio_b64": None, "spoken_text": None, "language": lang}

    async def speak_text(self, text: str, language: str) -> dict:
        """
        Synthesize arbitrary text for the /speak endpoint.

        Returns:
            { "audio_b64": str | None, "text": str }
        """
        lang = language if language in SUPPORTED_LANGS else "en"

        try:
            normalized = tts_normalizer.normalize(text, lang, {})

            if not self._ensure_engine_ready():
                logger.warning("TTS engine is not ready for /speak")
                return {"audio_b64": None, "text": text}

            audio_bytes = await indic_engine.synthesize_async(normalized, lang)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            return {"audio_b64": audio_b64, "text": text}
        except Exception as exc:
            logger.warning("speak_text failed: %s", exc)
            return {"audio_b64": None, "text": text}


tts_orchestrator = TTSOrchestrator()
