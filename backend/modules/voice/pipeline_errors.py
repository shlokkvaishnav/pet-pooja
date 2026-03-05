"""
pipeline_errors.py — Structured Error Taxonomy for Voice Pipeline
===================================================================
Every pipeline stage returns a StageResult. Failures produce user-facing
recovery messages instead of propagating silently as empty results.

Error types and their user messages are defined here so the frontend
can display them directly without interpreting error codes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Status enum (not using enum.Enum to keep JSON-serializable) ──
SUCCESS = "success"
PARTIAL = "partial"      # stage worked but with caveats (e.g., low confidence)
FAILURE = "failure"


# ── Error types ──
# STT
ERR_NO_SPEECH = "no_speech_detected"
ERR_AUDIO_TOO_SHORT = "audio_too_short"
ERR_LOW_CONFIDENCE_STT = "low_confidence_stt"
ERR_STT_MODEL_ERROR = "stt_model_error"

# Item matching
ERR_ZERO_MATCHES = "zero_item_matches"
ERR_AMBIGUOUS_MATCH = "ambiguous_match"

# Modifiers
ERR_MODIFIER_UNSUPPORTED = "modifier_unsupported"

# Stock
ERR_ITEM_OUT_OF_STOCK = "item_out_of_stock"

# Pipeline-level
ERR_PIPELINE_STAGE_FAILED = "pipeline_stage_failed"


# ── User-facing messages (English + Hinglish) ──
# The frontend should display user_message directly.
USER_MESSAGES = {
    ERR_NO_SPEECH: "Could not hear clearly, please try again.",
    ERR_AUDIO_TOO_SHORT: "Audio was too short — please speak a bit longer.",
    ERR_LOW_CONFIDENCE_STT: "Didn't catch that clearly — could you repeat?",
    ERR_STT_MODEL_ERROR: "Voice recognition is temporarily unavailable. Please type your order.",
    ERR_ZERO_MATCHES: "Didn't recognize that item — did you mean {suggestions}?",
    ERR_AMBIGUOUS_MATCH: "Did you mean {option_a} or {option_b}?",
    ERR_MODIFIER_UNSUPPORTED: "{modifier} is not available for {item_name}.",
    ERR_ITEM_OUT_OF_STOCK: "{item_name} is currently unavailable.",
    ERR_PIPELINE_STAGE_FAILED: "Something went wrong — please try again.",
}


def _get_message(error_type: str, **kwargs) -> str:
    """Format a user message, filling in any placeholders."""
    template = USER_MESSAGES.get(error_type, USER_MESSAGES[ERR_PIPELINE_STAGE_FAILED])
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


@dataclass
class StageResult:
    """
    Structured result from any pipeline stage.

    Attributes:
        status:       "success" | "partial" | "failure"
        error_type:   machine-readable error code (None if success)
        user_message:  human-readable message for the frontend (None if success)
        data:         the stage's actual output (whatever it normally returns)
        suggestions:  recovery suggestions (fuzzy matches, alternatives, etc.)
    """
    status: str = SUCCESS
    error_type: str | None = None
    user_message: str | None = None
    data: dict | list | str | None = None
    suggestions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "error_type": self.error_type,
            "user_message": self.user_message,
            "suggestions": self.suggestions,
        }

    @property
    def is_ok(self) -> bool:
        return self.status == SUCCESS

    @property
    def is_partial(self) -> bool:
        return self.status == PARTIAL

    @property
    def is_failure(self) -> bool:
        return self.status == FAILURE


# ── Factory helpers for common error cases ──

def stt_no_speech() -> StageResult:
    return StageResult(
        status=FAILURE,
        error_type=ERR_NO_SPEECH,
        user_message=_get_message(ERR_NO_SPEECH),
    )


def stt_too_short() -> StageResult:
    return StageResult(
        status=FAILURE,
        error_type=ERR_AUDIO_TOO_SHORT,
        user_message=_get_message(ERR_AUDIO_TOO_SHORT),
    )


def stt_low_confidence(transcript: str, confidence: float) -> StageResult:
    return StageResult(
        status=PARTIAL,
        error_type=ERR_LOW_CONFIDENCE_STT,
        user_message=_get_message(ERR_LOW_CONFIDENCE_STT),
        data={"transcript": transcript, "confidence": confidence},
    )


def stt_model_error(detail: str = "") -> StageResult:
    return StageResult(
        status=FAILURE,
        error_type=ERR_STT_MODEL_ERROR,
        user_message=_get_message(ERR_STT_MODEL_ERROR),
        data={"detail": detail} if detail else None,
    )


def zero_item_matches(normalized_text: str, top_suggestions: list) -> StageResult:
    names = ", ".join(s.get("matched_as", s.get("item_name", "?"))
                      for s in top_suggestions[:3]) or "something else"
    return StageResult(
        status=FAILURE,
        error_type=ERR_ZERO_MATCHES,
        user_message=_get_message(ERR_ZERO_MATCHES, suggestions=names),
        data={"input": normalized_text},
        suggestions=top_suggestions,
    )


def ambiguous_match(item_name: str, alternatives: list) -> StageResult:
    alt_names = [a.get("item_name", a.get("matched_as", "?")) for a in alternatives[:3]]
    option_a = alt_names[0] if alt_names else "?"
    option_b = alt_names[1] if len(alt_names) > 1 else "something else"
    return StageResult(
        status=PARTIAL,
        error_type=ERR_AMBIGUOUS_MATCH,
        user_message=_get_message(ERR_AMBIGUOUS_MATCH, option_a=option_a, option_b=option_b),
        data={"matched_item": item_name},
        suggestions=alternatives,
    )


def modifier_unsupported(modifier: str, item_name: str) -> StageResult:
    return StageResult(
        status=PARTIAL,
        error_type=ERR_MODIFIER_UNSUPPORTED,
        user_message=_get_message(ERR_MODIFIER_UNSUPPORTED, modifier=modifier, item_name=item_name),
        data={"modifier": modifier, "item_name": item_name},
    )


def item_out_of_stock(item_name: str, item_id: int) -> StageResult:
    return StageResult(
        status=PARTIAL,
        error_type=ERR_ITEM_OUT_OF_STOCK,
        user_message=_get_message(ERR_ITEM_OUT_OF_STOCK, item_name=item_name),
        data={"item_name": item_name, "item_id": item_id},
    )


def stage_success(data=None) -> StageResult:
    return StageResult(status=SUCCESS, data=data)
