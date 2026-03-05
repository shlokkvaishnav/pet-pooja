"""
stt.py — Speech-to-Text using faster-whisper + Silero VAD
===========================================================
Runs 100% locally — no external API calls.
Model loaded once on first use, cached forever.

Pipeline:
1. Convert any audio to 16kHz mono WAV (ffmpeg)
2. VAD preprocessing: strip silence/noise, keep speech-only segments
3. Whisper transcription on cleaned audio
4. Per-segment confidence scoring with minimum threshold

Model selection (via WHISPER_MODEL env var):
  tiny          ~75MB   fastest, lowest accuracy
  base          ~145MB  fast, basic accuracy
  small         ~460MB  good balance (old default)
  medium        ~1.5GB  better accuracy
  large-v3-turbo ~809MB best balance — DEFAULT (fast + accurate)
  large-v3       ~3GB   highest accuracy, slowest on CPU

Requires: pip install faster-whisper torch + ffmpeg installed.
"""

import os
import subprocess
import shutil
import glob
import logging

logger = logging.getLogger("petpooja.voice.stt")

# Model name — override via WHISPER_MODEL env var
_WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3-turbo")

# ── Confidence threshold ──
# Below this, the system flags the transcript as low-confidence
# and asks the user to repeat rather than guessing wrong.
MIN_CONFIDENCE = float(os.getenv("STT_MIN_CONFIDENCE", "0.45"))


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


def _compute_segment_confidence(segments_list: list) -> tuple[str, float, list]:
    """
    Collect segments, compute per-segment avg_logprob, and derive
    an overall confidence score.

    Returns: (transcript, overall_confidence, segment_details)
    """
    segment_details = []
    all_text_parts = []
    weighted_sum = 0.0
    total_duration = 0.0

    for seg in segments_list:
        text = seg.text.strip()
        if not text:
            continue
        duration = seg.end - seg.start
        # avg_logprob is log-probability; convert to 0-1 range
        # typical range: -1.0 (bad) to 0.0 (perfect)
        prob = min(1.0, max(0.0, 1.0 + seg.avg_logprob))

        all_text_parts.append(text)
        weighted_sum += prob * duration
        total_duration += duration
        segment_details.append({
            "text": text,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "confidence": round(prob, 3),
            "no_speech_prob": round(seg.no_speech_prob, 3),
        })

    transcript = " ".join(all_text_parts)
    overall_confidence = (weighted_sum / total_duration) if total_duration > 0 else 0.0

    return transcript, round(overall_confidence, 3), segment_details


def transcribe(audio_path: str) -> dict:
    """
    Full STT pipeline: audio file → VAD preprocessing → Whisper → confidence check.

    Returns:
        {
            "transcript": str,
            "detected_language": str,
            "language_confidence": float,
            "transcription_confidence": float,   # 0.0-1.0 overall score
            "is_low_confidence": bool,            # True = ask user to repeat
            "segments": [...],                    # per-segment detail
            "vad_info": {...},                    # VAD preprocessing stats
        }
    """
    # Step 1: Convert to WAV
    wav_path = convert_to_wav(audio_path)

    # Step 2: VAD preprocessing — strip noise, keep only speech
    vad_info = None
    transcribe_path = wav_path  # default: send full WAV to Whisper

    try:
        from .vad import extract_speech_audio
        vad_output_path = wav_path.rsplit(".", 1)[0] + "_vad.wav"
        vad_info = extract_speech_audio(wav_path, vad_output_path)

        if not vad_info["has_speech"]:
            # No speech detected — return early with explicit flag
            _cleanup(wav_path)
            return {
                "transcript": "",
                "detected_language": "unknown",
                "language_confidence": 0.0,
                "transcription_confidence": 0.0,
                "is_low_confidence": True,
                "low_confidence_reason": "no_speech_detected",
                "segments": [],
                "vad_info": vad_info,
            }

        # Use cleaned (speech-only) audio for Whisper
        transcribe_path = vad_output_path

    except Exception as e:
        logger.warning("VAD preprocessing failed, using raw audio: %s", e)
        vad_info = {"error": str(e), "has_speech": True}

    # Step 3: Whisper transcription on cleaned audio
    model = _get_model()
    segments_gen, info = model.transcribe(
        transcribe_path,
        beam_size=5,
        language=None,                    # auto-detect language
        task="transcribe",
        vad_filter=False,                 # we already did VAD externally
        initial_prompt=_INITIAL_PROMPT,   # bias toward correct food vocabulary
        condition_on_previous_text=False, # prevents hallucination loops
        temperature=0.0,                  # deterministic — best for short commands
    )

    # Step 4: Collect segments and compute confidence
    segments_list = list(segments_gen)
    transcript, overall_confidence, segment_details = _compute_segment_confidence(segments_list)

    # Step 5: Confidence gating
    is_low_confidence = overall_confidence < MIN_CONFIDENCE or not transcript.strip()
    low_confidence_reason = None
    if is_low_confidence:
        if not transcript.strip():
            low_confidence_reason = "empty_transcript"
        else:
            low_confidence_reason = "below_threshold"
        logger.warning(
            "Low-confidence transcript (%.2f < %.2f): '%s'",
            overall_confidence, MIN_CONFIDENCE, transcript[:80],
        )

    # Cleanup temp files (NOT the original audio!)
    _cleanup(wav_path)
    if transcribe_path != wav_path:
        _cleanup(transcribe_path)

    return {
        "transcript": transcript.strip(),
        "detected_language": info.language,
        "language_confidence": round(info.language_probability, 3),
        "transcription_confidence": overall_confidence,
        "is_low_confidence": is_low_confidence,
        "low_confidence_reason": low_confidence_reason,
        "segments": segment_details,
        "vad_info": vad_info,
    }


def _cleanup(*paths):
    """Remove temporary files, ignoring source audio."""
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
