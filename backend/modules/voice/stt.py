"""
stt.py — Speech-to-Text using faster-whisper
==============================================
Runs 100% locally — no external API calls.
Model loaded once on first use, cached forever.
Requires: pip install faster-whisper + ffmpeg installed.
"""

import os
import subprocess
import shutil
import glob
import logging

logger = logging.getLogger("petpooja.voice.stt")


def _find_ffmpeg() -> str:
    """Locate ffmpeg executable. Checks PATH first, then common Windows locations."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    # Common Windows install locations
    for pattern in [
        r"C:\ffmpeg*\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg*\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
    ]:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    raise FileNotFoundError(
        "ffmpeg not found. Install it: winget install Gyan.FFmpeg"
    )

# Lazy-loaded model — loaded on first transcribe() call
# This avoids crashes when testing text-only (no audio needed)
_model = None


def _get_model():
    """Load Whisper model on demand. Cached after first call."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading faster-whisper model (small)...")
        _model = WhisperModel("small", device="cpu", compute_type="int8")
        logger.info("Model loaded — runs fully offline from now on")
    return _model


def convert_to_wav(input_path: str) -> str:
    """
    Browser MediaRecorder produces webm/opus.
    Whisper needs WAV 16kHz mono.
    Converts any audio format to WAV using ffmpeg (local tool).
    """
    output_path = input_path.rsplit(".", 1)[0] + "_converted.wav"
    ffmpeg_path = _find_ffmpeg()
    subprocess.run([
        ffmpeg_path, "-y",        # -y = overwrite if exists
        "-i", input_path,
        "-ar", "16000",           # 16kHz sample rate
        "-ac", "1",               # mono channel
        output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


# Romanized-Hindi prompt: biases Whisper to output Latin script for Hinglish
_INITIAL_PROMPT = (
    "Bhaiya do paneer tikka aur ek butter naan dena. "
    "Ek chicken biryani extra spicy aur do mango lassi chahiye. "
    "Teen roti aur dal makhani please. "
    "Boss ek gulab jamun aur masala chai dena."
)


def transcribe(audio_path: str) -> dict:
    """
    Takes any audio file path.
    Returns transcript + detected language.
    language=None means Whisper auto-detects (handles EN, HI, Hinglish).
    initial_prompt biases Whisper toward romanized Hinglish output.
    """
    # Convert to WAV first (handles webm, mp3, m4a, etc.)
    wav_path = convert_to_wav(audio_path)

    model = _get_model()
    segments, info = model.transcribe(
        wav_path,
        beam_size=5,
        language=None,        # auto-detect language
        task="transcribe",
        vad_filter=True,      # removes silent parts
        initial_prompt=_INITIAL_PROMPT,  # bias toward romanized Hinglish
    )

    transcript = " ".join(segment.text.strip() for segment in segments)

    # Cleanup converted file
    if wav_path != audio_path and os.path.exists(wav_path):
        os.remove(wav_path)

    return {
        "transcript": transcript.strip(),
        "detected_language": info.language,         # "en", "hi", etc.
        "language_confidence": round(info.language_probability, 3),
    }
