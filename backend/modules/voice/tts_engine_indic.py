"""
tts_engine_indic.py — Edge TTS Engine (Microsoft Neural Voices)
=================================================================
Singleton that uses edge-tts for high-quality neural text-to-speech.
Supports English, Hindi, Gujarati, Marathi, and Kannada
with native neural voices per language. No model loading required —
uses Microsoft Edge's TTS service.

Usage:
    from modules.voice.tts_engine_indic import indic_engine
    mp3_bytes = indic_engine.synthesize("Got it! 2 Butter Naan added.", "en")
"""

import asyncio
import io
import time
import logging

from .voice_config import cfg

logger = logging.getLogger("petpooja.voice.tts_engine")

# ── Microsoft Edge Neural Voice IDs per language ──────────────────
_VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",      # Indian English female
    "hi": "hi-IN-SwaraNeural",       # Hindi female
    "gu": "gu-IN-DhwaniNeural",      # Gujarati female
    "mr": "mr-IN-AarohiNeural",      # Marathi female
    "kn": "kn-IN-SapnaNeural",       # Kannada female
}


class IndicTTSEngine:
    """Singleton TTS engine using edge-tts (Microsoft Edge neural voices).

    No heavy model loading — just an async call to Edge TTS service.
    Supports Indian English, Hindi, Gujarati, Marathi, Kannada.
    """

    _instance = None
    _warmup_time = None
    _ready = False
    _loop = None  # Dedicated event loop for sync→async bridge

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def warmup_time(self) -> float | None:
        return self._warmup_time

    def warmup(self) -> None:
        """Validate edge-tts is importable and run a quick test synthesis.
        Call this once at server startup."""
        start = time.time()

        try:
            import edge_tts  # noqa: F401
        except ImportError:
            logger.error("edge-tts not installed. Install with: pip install edge-tts")
            return

        # Run a quick test to verify connectivity
        try:
            test_audio = self._synthesize_sync("Hello.", "en")
            if test_audio and len(test_audio) > 100:
                self._warmup_time = round(time.time() - start, 1)
                self._ready = True
                logger.info(
                    f"Edge TTS ready (warmup: {self._warmup_time}s, "
                    f"test audio: {len(test_audio)} bytes)"
                )
            else:
                logger.error("Edge TTS warmup produced empty audio")
        except Exception as e:
            logger.error(f"Edge TTS warmup failed: {e}")

    async def _synthesize_async(self, text: str, language: str) -> bytes:
        """Async synthesis using edge-tts. Returns MP3 bytes."""
        import edge_tts

        voice = _VOICE_MAP.get(language, _VOICE_MAP["en"])
        communicate = edge_tts.Communicate(text, voice)

        mp3_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_buffer.write(chunk["data"])

        return mp3_buffer.getvalue()

    def _synthesize_sync(self, text: str, language: str) -> bytes:
        """Synchronous wrapper for _synthesize_async.
        Creates a new event loop if needed (safe for thread contexts)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an async context (e.g., FastAPI) —
            # use a thread to run a new event loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run, self._synthesize_async(text, language)
                )
                return future.result(timeout=30)
        else:
            return asyncio.run(self._synthesize_async(text, language))

    def synthesize(self, text: str, language: str) -> bytes:
        """Synthesize text to MP3 bytes.

        Args:
            text: Normalized text ready for TTS.
            language: Language code ("en", "hi", "gu", "mr", "kn").

        Returns:
            MP3 audio bytes.

        Raises:
            RuntimeError: If engine is not ready.
        """
        if not self._ready:
            raise RuntimeError("TTS engine not ready — call warmup() first")

        if not text or not text.strip():
            raise ValueError("Empty text provided to TTS")

        start = time.time()

        mp3_bytes = self._synthesize_sync(text, language)

        elapsed = round((time.time() - start) * 1000, 1)
        logger.info(
            f"TTS synthesized {len(text)} chars ({language}) → "
            f"{len(mp3_bytes)} bytes in {elapsed}ms"
        )

        return mp3_bytes

    async def synthesize_async(self, text: str, language: str) -> bytes:
        """Async version of synthesize — use this from async contexts
        (FastAPI route handlers) for better performance."""
        if not self._ready:
            raise RuntimeError("TTS engine not ready — call warmup() first")

        if not text or not text.strip():
            raise ValueError("Empty text provided to TTS")

        start = time.time()

        mp3_bytes = await self._synthesize_async(text, language)

        elapsed = round((time.time() - start) * 1000, 1)
        logger.info(
            f"TTS synthesized {len(text)} chars ({language}) → "
            f"{len(mp3_bytes)} bytes in {elapsed}ms"
        )

        return mp3_bytes

    def get_status(self) -> dict:
        """Return engine status for health endpoint."""
        return {
            "status": "ready" if self._ready else "not_loaded",
            "engine": "edge-tts",
            "voices": _VOICE_MAP,
            "languages": list(_VOICE_MAP.keys()),
            "warmup_time_s": self._warmup_time,
        }


# Module-level singleton
indic_engine = IndicTTSEngine()
