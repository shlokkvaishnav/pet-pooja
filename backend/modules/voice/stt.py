"""
stt.py — Speech-to-Text using faster-whisper + Silero VAD
===========================================================
Runs 100% locally — no external API calls.

Pipeline:
1. Convert any audio to 16kHz mono WAV (ffmpeg)
2. VAD preprocessing: strip silence/noise, keep speech-only segments
3. Whisper transcription on cleaned audio
4. Per-segment confidence scoring with minimum threshold

Requires: pip install faster-whisper torch + ffmpeg installed.
"""

import os
import subprocess
import shutil
import glob
import logging

logger = logging.getLogger("petpooja.voice.stt")

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
            _cleanup(wav_path, audio_path)
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
        language=None,        # auto-detect language
        task="transcribe",
        vad_filter=False,     # we already did VAD externally
        initial_prompt=_INITIAL_PROMPT,
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

    # Cleanup temp files
    _cleanup(wav_path, audio_path)
    if transcribe_path != wav_path:
        _cleanup(transcribe_path, None)

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
