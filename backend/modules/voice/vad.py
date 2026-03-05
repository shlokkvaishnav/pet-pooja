"""
vad.py — Voice Activity Detection preprocessing (Silero VAD)
==============================================================
Detects actual speech segments in audio before sending to Whisper.
Runs fully local on CPU — no external API calls.

This eliminates:
- Whisper "hallucinations" caused by restaurant background noise
- Wasted compute on silence / music / kitchen clatter
- False transcripts from non-speech audio

Requires: pip install torch (silero-vad ships inside torch.hub)
"""

import logging
import os
import struct
import wave

import torch

logger = logging.getLogger("petpooja.voice.vad")

# ── Silero VAD model (loaded once, cached) ──
_vad_model = None
_vad_utils = None

# ── Tuning knobs (env-overridable) ──
# Minimum speech duration to keep (seconds). Filters out clicks/taps.
MIN_SPEECH_DURATION = float(os.getenv("VAD_MIN_SPEECH_SEC", "0.3"))
# Silence padding around each speech segment (seconds). Prevents clipping.
SPEECH_PAD_MS = int(os.getenv("VAD_SPEECH_PAD_MS", "300"))
# VAD threshold — higher = stricter (0.0-1.0). Default tuned for noisy restaurants.
VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.40"))
# Minimum total speech needed to consider the audio valid (seconds).
MIN_TOTAL_SPEECH = float(os.getenv("VAD_MIN_TOTAL_SPEECH_SEC", "0.4"))

_SAMPLE_RATE = 16000  # Silero VAD requires 16kHz


def _load_vad():
    """Load Silero VAD model on first use. Thread-safe via GIL."""
    global _vad_model, _vad_utils
    if _vad_model is None:
        logger.info("Loading Silero VAD model...")
        _vad_model, _vad_utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )
        logger.info("Silero VAD loaded — runs fully offline")
    return _vad_model, _vad_utils


def _read_wav_as_tensor(wav_path: str) -> torch.Tensor:
    """Read a 16kHz mono WAV file into a float32 torch tensor."""
    with wave.open(wav_path, "rb") as wf:
        assert wf.getnchannels() == 1, "WAV must be mono"
        assert wf.getframerate() == _SAMPLE_RATE, "WAV must be 16kHz"
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
    samples = struct.unpack(f"<{n_frames}h", raw)
    tensor = torch.tensor(samples, dtype=torch.float32) / 32768.0
    return tensor


def _write_wav_from_tensor(tensor: torch.Tensor, out_path: str):
    """Write a float32 tensor back to a 16kHz mono WAV file."""
    int_samples = (tensor * 32767).clamp(-32768, 32767).to(torch.int16)
    raw = struct.pack(f"<{len(int_samples)}h", *int_samples.tolist())
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(raw)


def detect_speech_segments(wav_path: str) -> list[dict]:
    """
    Run VAD on a 16kHz mono WAV file.

    Returns list of speech segments:
        [{"start": 0.5, "end": 2.3}, {"start": 4.1, "end": 6.0}, ...]

    Each segment represents continuous speech with padding applied.
    """
    model, utils = _load_vad()
    get_speech_timestamps = utils[0]

    audio = _read_wav_as_tensor(wav_path)

    speech_timestamps = get_speech_timestamps(
        audio,
        model,
        threshold=VAD_THRESHOLD,
        sampling_rate=_SAMPLE_RATE,
        min_speech_duration_ms=int(MIN_SPEECH_DURATION * 1000),
        speech_pad_ms=SPEECH_PAD_MS,
    )

    segments = []
    for ts in speech_timestamps:
        segments.append({
            "start": ts["start"] / _SAMPLE_RATE,
            "end": ts["end"] / _SAMPLE_RATE,
        })

    return segments


def extract_speech_audio(wav_path: str, output_path: str) -> dict:
    """
    Preprocess audio: detect speech, concatenate speech-only segments,
    write cleaned WAV for Whisper.

    Returns:
        {
            "output_path": str,         # path to cleaned WAV
            "speech_segments": [...],   # detected segments
            "total_speech_sec": float,  # total speech duration
            "total_audio_sec": float,   # original audio length
            "speech_ratio": float,      # speech / total
            "has_speech": bool,         # enough speech to transcribe?
        }
    """
    segments = detect_speech_segments(wav_path)
    audio = _read_wav_as_tensor(wav_path)
    total_audio_sec = len(audio) / _SAMPLE_RATE

    if not segments:
        logger.warning("VAD found no speech in audio (%.1fs)", total_audio_sec)
        return {
            "output_path": None,
            "speech_segments": [],
            "total_speech_sec": 0.0,
            "total_audio_sec": total_audio_sec,
            "speech_ratio": 0.0,
            "has_speech": False,
        }

    # Concatenate speech segments into a single clean tensor
    speech_chunks = []
    for seg in segments:
        start_sample = int(seg["start"] * _SAMPLE_RATE)
        end_sample = int(seg["end"] * _SAMPLE_RATE)
        speech_chunks.append(audio[start_sample:end_sample])

    speech_audio = torch.cat(speech_chunks)
    total_speech_sec = len(speech_audio) / _SAMPLE_RATE

    has_speech = total_speech_sec >= MIN_TOTAL_SPEECH

    if has_speech:
        _write_wav_from_tensor(speech_audio, output_path)
        logger.info(
            "VAD: kept %.1fs speech from %.1fs audio (%d segments, %.0f%% speech)",
            total_speech_sec, total_audio_sec,
            len(segments), (total_speech_sec / total_audio_sec) * 100,
        )
    else:
        logger.warning(
            "VAD: only %.2fs speech found (min=%.1fs) — too short",
            total_speech_sec, MIN_TOTAL_SPEECH,
        )

    return {
        "output_path": output_path if has_speech else None,
        "speech_segments": segments,
        "total_speech_sec": round(total_speech_sec, 2),
        "total_audio_sec": round(total_audio_sec, 2),
        "speech_ratio": round(total_speech_sec / total_audio_sec, 3) if total_audio_sec > 0 else 0.0,
        "has_speech": has_speech,
    }
