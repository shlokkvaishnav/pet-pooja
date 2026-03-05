"""
stt.py — Speech-to-Text using faster-whisper
==============================================
Runs 100% locally — no external API calls.
Model loaded once on first use, cached forever.
Requires: pip install faster-whisper + ffmpeg installed.

Model selection (via WHISPER_MODEL env var):
  tiny          ~75MB   fastest, lowest accuracy
  base          ~145MB  fast, basic accuracy
  small         ~460MB  good balance (old default)
  medium        ~1.5GB  better accuracy
  large-v3-turbo ~809MB best balance — DEFAULT (fast + accurate)
  large-v3       ~3GB   highest accuracy, slowest on CPU
"""

import os
import subprocess
import shutil
import glob
import logging

logger = logging.getLogger("petpooja.voice.stt")

# Model name — override via WHISPER_MODEL env var
_WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3-turbo")


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
    """Load Whisper model on demand. Cached after first call.
    
    Auto-detects CUDA; falls back to CPU with int8 quantization.
    Model size controlled by WHISPER_MODEL env var (default: large-v3-turbo).
    """
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # Try CUDA first, fall back to CPU
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                device, compute_type = "cuda", "float16"
            else:
                device, compute_type = "cpu", "int8"
        except Exception:
            device, compute_type = "cpu", "int8"

        logger.info(
            "Loading faster-whisper model '%s' on %s (%s)...",
            _WHISPER_MODEL, device, compute_type
        )
        _model = WhisperModel(_WHISPER_MODEL, device=device, compute_type=compute_type)
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


# Romanized-Hindi + Indian-English prompt:
# Biases Whisper toward correct spellings even with Indian accents.
# Includes common mispronounced words (chicken, mutton, biryani, etc.)
# so the model learns the expected vocabulary before transcribing.
_INITIAL_PROMPT = (
    "Order for chicken biryani, mutton curry, paneer tikka, butter naan. "
    "Ek chicken biryani extra spicy aur do mango lassi chahiye. "
    "Bhaiya do paneer tikka aur ek butter naan dena. "
    "Teen roti aur dal makhani please. "
    "One chicken tikka masala, two garlic naan, and one gulab jamun. "
    "Dahi kebab, tandoori chicken, fish curry, prawn masala. "
    "Cold drink, masala chai, lassi, cold coffee. "
    "Boss ek gulab jamun aur masala chai dena. "
    "Half plate chicken, full plate mutton, chicken 65, chicken manchurian."
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
        language=None,                    # auto-detect language
        task="transcribe",
        vad_filter=True,                  # removes silent parts
        initial_prompt=_INITIAL_PROMPT,   # bias toward correct food vocabulary
        condition_on_previous_text=False, # prevents hallucination loops
        temperature=0.0,                  # deterministic — best for short commands
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
