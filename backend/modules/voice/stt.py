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

import asyncio
import os
import re
import subprocess
import shutil
import glob
import logging

from .voice_config import cfg

logger = logging.getLogger("petpooja.voice.stt")

# Model name — from centralized config (env-overridable)
_WHISPER_MODEL = cfg.WHISPER_MODEL

# ── Confidence threshold ──
# Below this, the system flags the transcript as low-confidence
# and asks the user to repeat rather than guessing wrong.
MIN_CONFIDENCE = cfg.STT_MIN_CONFIDENCE


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

# Lazy-loaded model — loaded on first transcribe() call or at startup via warmup()
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


def warmup():
    """Pre-load Whisper model at startup so the first request is fast."""
    logger.info("Warming up Whisper STT model...")
    _get_model()
    logger.info("Whisper STT model warm")


def convert_to_wav(input_path: str) -> str:
    """
    Browser MediaRecorder produces webm/opus.
    Whisper needs WAV 16kHz mono.
    Converts any audio format to WAV using ffmpeg (local tool).
    Synchronous version — used by the Whisper pipeline.
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


async def convert_to_wav_async(input_path: str) -> str:
    """
    Async version of convert_to_wav.
    Uses asyncio.create_subprocess_exec so the event loop can serve
    other requests while ffmpeg runs (important for concurrent voice orders).
    """
    output_path = input_path.rsplit(".", 1)[0] + "_converted.wav"
    ffmpeg_path = _find_ffmpeg()
    proc = await asyncio.create_subprocess_exec(
        ffmpeg_path, "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        output_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
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


# ── Text-based language re-detection ─────────────────────────────
# Whisper's audio-level detection is unreliable for short, mixed-language
# (Hinglish) utterances. This re-detects from the actual transcript text.

# Hindi/Hinglish markers — romanized Hindi words commonly used in orders
_HINDI_MARKERS = re.compile(
    r"\b("
    r"ek|do|teen|char|paanch|chhe|saat|aath|nau|das"
    r"|aur|ya|bhi|dena|lao|chahiye|de\s*do|milega|bhejo|rakh"
    r"|bhaiya|bhai|boss|yaar|ji"
    r"|haan|nahi|mat|theek|accha|bilkul|zaroor|sahi"
    r"|kya|kuch|koi|kitna|kaisa"
    r"|mujhe|mereko|humko|mujhko"
    r"|wala|wali|wale"
    r"|extra|zyada|kam|bina|thoda|bahut"
    r"|lekin|magar|par|phir|abhi"
    r"|hata|hatao|cancel|change|badlo"
    r"|masala|tikka|naan|roti|dal|paneer|biryani|lassi|chai"
    r"|kheer|raita|tandoori|kebab|makhani|gobhi|aloo|palak|shahi"
    r"|sabzi|sabji|dahi|gosht|chawal"
    r")\b",
    re.IGNORECASE,
)

# Gujarati romanized markers — words that distinguish Gujarati from Hindi
_GUJARATI_MARKERS = re.compile(
    r"\b("
    r"che|chhe|chhu|nathi|hoy|hato|hashe|hase"   # auxiliaries
    r"|joiye|joie|aapo|apo|aavo|karvo|karvu"       # verbs
    r"|tame|tamne|tamaro|tamari|amne|amaro"         # pronouns
    r"|kem|shu|kyare|kyan|ketlu|ketla"              # question words
    r"|saras|saru|majama|sambhalo"                  # adjectives/expressions
    r"|rotli|rotlo|thepla|dhokla|khandvi|fafda"     # Gujarati food
    r"|undhiyu|handvo|khakhra|gathiya|jalebi"       # more Gujarati food
    r"|bas\s*thai|puru|nakki|besi|besvu"            # common phrases
    r")\b",
    re.IGNORECASE,
)

# Marathi romanized markers — words that distinguish Marathi from Hindi
_MARATHI_MARKERS = re.compile(
    r"\b("
    r"aahe|aahes|aahet|naahi|naye|ashe"             # auxiliaries
    r"|mhanje|mhanun|kaay|kasa|kashi|kuthe"         # question/connectors
    r"|dya|ghya|sanga|sangaa|kara|lava|theva"       # verbs
    r"|amhi|tumhi|tumhala|aamhala|tyala|tila"       # pronouns
    r"|bhari|chhan|mast|ekdum"                       # adjectives
    r"|vada\s*pav|pav\s*bhaji|misal|puran\s*poli"   # Marathi food
    r"|thalipeeth|sabudana|poha|usal|modak"          # more Marathi food
    r"|jhale|zale|sampale|thik\s*aahe|chalel"       # common phrases
    r")\b",
    re.IGNORECASE,
)

# Gujarati script detection (Unicode block: 0A80-0AFF)
_GUJARATI_SCRIPT = re.compile(r"[\u0A80-\u0AFF]")

# Devanagari script detection (Unicode block: 0900-097F)
_DEVANAGARI_SCRIPT = re.compile(r"[\u0900-\u097F]")

# Kannada script detection (Unicode block: 0C80-0CFF)
_KANNADA_SCRIPT = re.compile(r"[\u0C80-\u0CFF]")

# Pure English markers — words that strongly suggest English intent
_ENGLISH_MARKERS = re.compile(
    r"\b("
    r"please|thank|want|give|order|need|would\s+like|can\s+i|get\s+me"
    r"|remove|cancel|change|add|confirm|yes|no|okay"
    r"|one|two|three|four|five|six|seven|eight|nine|ten"
    r"|chicken|butter|extra|spicy|without"
    r")\b",
    re.IGNORECASE,
)

# Supported Whisper language codes to our 5 languages
_WHISPER_LANG_MAP = {
    "en": "en", "english": "en",
    "hi": "hi", "hindi": "hi",
    "gu": "gu", "gujarati": "gu",
    "mr": "mr", "marathi": "mr",
    "kn": "kn", "kannada": "kn",
}


def _redetect_language(transcript: str, whisper_lang: str, whisper_confidence: float,
                       session_language: str = None) -> str:
    """
    Re-detect the language from the transcript text content.
    Overrides Whisper's audio-level detection when text evidence is strong.

    Args:
        session_language: Language from previous turns in this session.
                         Used as a tiebreaker when text evidence is ambiguous.

    Strategy:
    1. Native script present → use that script's language (definitive)
    2. Gujarati romanized markers → "gu"
    3. Marathi romanized markers → "mr"
    4. Hindi/Hinglish markers dominant → "hi"
    5. Pure English with high Whisper confidence → "en"
    6. Session language stickiness (if ambiguous, prefer session's language)
    7. Fall back to Whisper's detection if it maps to a supported language
    8. Otherwise default to "en"
    """
    if not transcript or not transcript.strip():
        return _WHISPER_LANG_MAP.get(whisper_lang, "en")

    text = transcript.strip()

    # 1. Native script detection (highest priority — definitive)
    gujarati_chars = len(_GUJARATI_SCRIPT.findall(text))
    devanagari_chars = len(_DEVANAGARI_SCRIPT.findall(text))
    kannada_chars = len(_KANNADA_SCRIPT.findall(text))

    if gujarati_chars > 3:
        return "gu"
    if kannada_chars > 3:
        return "kn"
    if devanagari_chars > 3:
        # Devanagari could be Hindi or Marathi; prefer Whisper's guess
        if whisper_lang in ("mr", "marathi"):
            return "mr"
        return "hi"

    # 2. Count romanized language-specific markers
    hindi_hits = len(_HINDI_MARKERS.findall(text))
    english_hits = len(_ENGLISH_MARKERS.findall(text))
    gujarati_hits = len(_GUJARATI_MARKERS.findall(text))
    marathi_hits = len(_MARATHI_MARKERS.findall(text))
    word_count = max(len(text.split()), 1)

    # 3. Gujarati/Marathi markers take priority (they are more specific)
    if gujarati_hits >= 2 and gujarati_hits > marathi_hits:
        return "gu"
    if marathi_hits >= 2 and marathi_hits > gujarati_hits:
        return "mr"
    # Even 1 hit + Whisper agreement is enough
    if gujarati_hits >= 1 and whisper_lang in ("gu", "gujarati"):
        return "gu"
    if marathi_hits >= 1 and whisper_lang in ("mr", "marathi"):
        return "mr"

    hindi_ratio = hindi_hits / word_count
    english_ratio = english_hits / word_count

    # 4. Strong Hindi/Hinglish signal → "hi"
    if hindi_hits >= 2 and hindi_ratio > english_ratio:
        return "hi"

    # Mixed — mostly Hindi markers present → "hi" (Hinglish is spoken as Hindi)
    if hindi_hits >= 1 and whisper_confidence < 0.8:
        # But if session language is gu/mr and Hindi markers are weak, prefer session
        if session_language in ("gu", "mr") and hindi_hits <= 2:
            return session_language
        return "hi"

    # 5. High-confidence Whisper with pure English text → trust Whisper
    if whisper_confidence >= 0.8 and english_ratio > 0.3 and hindi_hits == 0:
        return "en"

    # 6. Session language stickiness — when text is ambiguous, prefer session's language
    if session_language and session_language in ("hi", "gu", "mr", "kn", "en"):
        return session_language

    # 7. Map Whisper's language to our supported set
    mapped = _WHISPER_LANG_MAP.get(whisper_lang)
    if mapped:
        return mapped

    # 8. Default fallback: if Hindi markers at all, say "hi"
    if hindi_hits >= 1:
        return "hi"

    return "en"


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


# Per-language initial prompts — feed Whisper native-script priming so it
# transcribes in the correct script instead of defaulting to Hindi/Latin.
_LANGUAGE_PROMPTS = {
    "gu": (
        "gu-IN food order. "
        "ek paneer tikka aur do butter naan. "
        "ઓર્ડર: એક પનીર ટિક્કા, બે બટર નાન, ત્રણ ચા. "
        "ઉમેરો, કાઢો, ઓર્ડર, ઓક."
    ),
    "mr": (
        "mr-IN food order. "
        "ek paneer tikka ani do butter naan. "
        "ऑर्डर: एक पनीर टिक्का, दोन बटर नान, तीन चहा. "
        "जोडा, काढा, ऑर्डर, ठीक आहे."
    ),
    "kn": (
        "kn-IN food order. "
        "ondu paneer tikka mattu eradu butter naan. "
        "ಆರ್ಡರ್: ಒಂದು ಪನೀರ್ ಟಿಕ್ಕಾ, ಎರಡು ಬಟರ್ ನಾನ್, ಮೂರು ಚಹಾ. "
        "ಸೇರಿಸಿ, ತೆಗೆಯಿರಿ, ಆರ್ಡರ್."
    ),
    "hi": (
        "hi-IN food order. "
        "ek paneer tikka aur do butter naan chahiye. "
        "एक पनीर टिक्का, दो बटर नान, तीन चाय. "
        "जोड़ें, हटाएं, ऑर्डर, ठीक है."
    ),
    "en": _INITIAL_PROMPT,  # reuse existing English prompt
}


def transcribe(audio_path: str, language_hint: str = None) -> dict:
    """
    Full STT pipeline: audio file → VAD preprocessing → Whisper → confidence check.

    Args:
        audio_path: Path to the audio file.
        language_hint: ISO language code ('en','hi','gu','mr','kn') from a user-selected
                       language preference. Used to override the final detected_language
                       for TTS voice/template selection. Whisper still auto-detects so
                       that the transcript stays in romanized/Latin script (which the
                       pipeline's item matcher can process).

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
    import time as _time
    t0 = _time.perf_counter()
    wav_path = convert_to_wav(audio_path)
    t_convert = _time.perf_counter() - t0
    logger.info("⏱ ffmpeg convert in %.0fms", t_convert * 1000)

    # Step 2: VAD preprocessing — strip noise, keep only speech
    t_vad_start = _time.perf_counter()
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

    t_vad = _time.perf_counter() - t_vad_start
    logger.info("⏱ VAD preprocessing in %.0fms", t_vad * 1000)

    # Step 3: Whisper transcription on cleaned audio
    # IMPORTANT: Always use language=None so Whisper auto-detects and outputs
    # romanized/Latin-script text. If we pass language='gu'/'mr'/'kn', Whisper
    # outputs native script (e.g. Gujarati) which the item matcher cannot match
    # against English menu names. The language_hint is used ONLY for final
    # detected_language override (TTS voice/template selection).
    model = _get_model()
    t_whisper_start = _time.perf_counter()
    segments_gen, info = model.transcribe(
        transcribe_path,
        beam_size=cfg.STT_BEAM_SIZE,
        language=None,                    # always auto-detect for romanized output
        task="transcribe",
        vad_filter=cfg.STT_VAD_FILTER,    # we already did VAD externally
        initial_prompt=_INITIAL_PROMPT,   # romanized food vocabulary
        condition_on_previous_text=cfg.STT_CONDITION_ON_PREV,
        temperature=cfg.STT_TEMPERATURE,  # deterministic — best for short commands
    )

    # Step 4: Collect segments and compute confidence
    segments_list = list(segments_gen)
    t_whisper = _time.perf_counter() - t_whisper_start
    logger.info("⏱ Whisper transcribe in %.0fms (beam=%d, model=%s)",
                 t_whisper * 1000, cfg.STT_BEAM_SIZE, cfg.WHISPER_MODEL)
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

    # Step 6: Text-based language re-detection
    # If a language_hint was given, skip re-detection and trust the hint.
    whisper_lang = info.language
    whisper_conf = info.language_probability
    if language_hint and language_hint in ("en", "hi", "gu", "mr", "kn"):
        final_lang = language_hint
        logger.info("Language forced by hint: %s (Whisper guessed %s %.2f)",
                    language_hint, whisper_lang, whisper_conf)
    else:
        final_lang = _redetect_language(transcript.strip(), whisper_lang, whisper_conf)
    if final_lang != whisper_lang:
        logger.info(
            "Language override: Whisper=%s (%.2f) → text-detected=%s | '%s'",
            whisper_lang, whisper_conf, final_lang, transcript[:60],
        )

    return {
        "transcript": transcript.strip(),
        "detected_language": final_lang,
        "whisper_raw_language": whisper_lang,
        "language_confidence": round(whisper_conf, 3),
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
