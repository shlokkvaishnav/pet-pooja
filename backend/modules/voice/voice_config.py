"""
voice_config.py — Centralized Configuration for the Voice Pipeline
=====================================================================
Every tunable parameter in the voice pipeline reads from here.
All values are overridable via environment variables — no code
changes needed to tune for a specific restaurant environment.

Usage in other modules:
    from .voice_config import cfg

    threshold = cfg.ITEM_MATCH_FUZZY_THRESHOLD
"""

import os


def _env(key: str, default, cast=None):
    """Read an env var with optional type casting."""
    val = os.getenv(key)
    if val is None:
        return default
    if cast is not None:
        return cast(val)
    return val


def _env_float(key: str, default: float) -> float:
    return _env(key, default, float)


def _env_int(key: str, default: int) -> int:
    return _env(key, default, int)


def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes")


class VoiceConfig:
    """
    All voice pipeline tuning parameters in one place.
    Override any value by setting the corresponding env var.

    Grouped by module for clarity.
    """

    # ─── STT (stt.py) ────────────────────────────────────────────
    WHISPER_MODEL: str            = _env("WHISPER_MODEL", "large-v3-turbo")
    STT_MIN_CONFIDENCE: float     = _env_float("STT_MIN_CONFIDENCE", 0.45)
    STT_BEAM_SIZE: int            = _env_int("STT_BEAM_SIZE", 5)
    STT_TEMPERATURE: float        = _env_float("STT_TEMPERATURE", 0.0)
    STT_VAD_FILTER: bool          = _env_bool("STT_VAD_FILTER", False)
    STT_CONDITION_ON_PREV: bool   = _env_bool("STT_CONDITION_ON_PREV", False)

    # ─── VAD (vad.py) ────────────────────────────────────────────
    VAD_THRESHOLD: float          = _env_float("VAD_THRESHOLD", 0.40)
    VAD_MIN_SPEECH_SEC: float     = _env_float("VAD_MIN_SPEECH_SEC", 0.3)
    VAD_SPEECH_PAD_MS: int        = _env_int("VAD_SPEECH_PAD_MS", 300)
    VAD_MIN_TOTAL_SPEECH_SEC: float = _env_float("VAD_MIN_TOTAL_SPEECH_SEC", 0.4)
    VAD_SAMPLE_RATE: int          = _env_int("VAD_SAMPLE_RATE", 16000)

    # ─── Item Matcher (item_matcher.py) ───────────────────────────
    ITEM_MATCH_FUZZY_WEIGHT: float    = _env_float("ITEM_MATCH_FUZZY_WEIGHT", 0.4)
    ITEM_MATCH_SEMANTIC_WEIGHT: float = _env_float("ITEM_MATCH_SEMANTIC_WEIGHT", 0.6)
    ITEM_MATCH_SEMANTIC_MODEL: str    = _env("ITEM_MATCH_SEMANTIC_MODEL",
                                             "paraphrase-multilingual-MiniLM-L12-v2")
    ITEM_MATCH_FUZZY_THRESHOLD: int   = _env_int("ITEM_MATCH_FUZZY_THRESHOLD", 70)
    ITEM_MATCH_DISAMBIGUATION: float  = _env_float("ITEM_MATCH_DISAMBIGUATION", 0.85)
    ITEM_MATCH_MIN_TOKEN_LEN: int     = _env_int("ITEM_MATCH_MIN_TOKEN_LEN", 2)
    ITEM_MATCH_MIN_SINGLE_WORD: int   = _env_int("ITEM_MATCH_MIN_SINGLE_WORD", 4)
    ITEM_MATCH_ENCODE_BATCH: int      = _env_int("ITEM_MATCH_ENCODE_BATCH", 64)
    ITEM_MATCH_FAISS_TOP_K: int       = _env_int("ITEM_MATCH_FAISS_TOP_K", 20)
    ITEM_MATCH_ALT_CUTOFF: int        = _env_int("ITEM_MATCH_ALT_CUTOFF", 50)
    ITEM_MATCH_ALT_TOP_N: int         = _env_int("ITEM_MATCH_ALT_TOP_N", 3)
    # Minimum confidence per sliding-window size (3-word, 2-word, 1-word)
    ITEM_MATCH_MIN_CONF_3W: float     = _env_float("ITEM_MATCH_MIN_CONF_3W", 0.85)
    ITEM_MATCH_MIN_CONF_2W: float     = _env_float("ITEM_MATCH_MIN_CONF_2W", 0.78)
    ITEM_MATCH_MIN_CONF_1W: float     = _env_float("ITEM_MATCH_MIN_CONF_1W", 0.75)

    # ─── Quantity Extractor (quantity_extractor.py) ────────────────
    QTY_WINDOW_BEFORE: int        = _env_int("QTY_WINDOW_BEFORE", 3)
    QTY_WINDOW_AFTER: int         = _env_int("QTY_WINDOW_AFTER", 4)
    QTY_DEFAULT: int              = _env_int("QTY_DEFAULT", 1)
    QTY_MAX_VALID: int            = _env_int("QTY_MAX_VALID", 50)

    # ─── Order Builder (order_builder.py) ─────────────────────────
    ORDER_TAX_RATE: float         = _env_float("ORDER_TAX_RATE", 0.05)
    ORDER_KOT_WIDTH: int          = _env_int("ORDER_KOT_WIDTH", 32)

    # ─── Session Store (session_store.py) ─────────────────────────
    SESSION_MAX_COUNT: int        = _env_int("SESSION_MAX_COUNT", 500)
    SESSION_TIMEOUT_SEC: int      = _env_int("SESSION_TIMEOUT_SEC", 1800)

    # ─── Upsell Engine (upsell_engine.py) ─────────────────────────
    UPSELL_MAX_SUGGESTIONS: int   = _env_int("UPSELL_MAX_SUGGESTIONS", 2)
    UPSELL_HIDDEN_STAR_WEIGHT: float = _env_float("UPSELL_HIDDEN_STAR_WEIGHT", 0.5)
    UPSELL_HIDDEN_STARS_POOL: int = _env_int("UPSELL_HIDDEN_STARS_POOL", 5)
    UPSELL_MIN_MARGIN_PCT: float  = _env_float("UPSELL_MIN_MARGIN_PCT", 55.0)
    UPSELL_RELATED_ORDERS_LIMIT: int = _env_int("UPSELL_RELATED_ORDERS_LIMIT", 500)
    UPSELL_CO_ITEMS_LIMIT: int    = _env_int("UPSELL_CO_ITEMS_LIMIT", 20)
    UPSELL_FALLBACK_MARGIN: float = _env_float("UPSELL_FALLBACK_MARGIN", 60.0)


# Module-level singleton — import this everywhere
cfg = VoiceConfig()
