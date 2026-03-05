"""
intent_mapper.py — Intent Classification
==========================================
Classifies customer intent using context-aware regex patterns.
No AI models, no API calls — pure pattern matching.
These are LINGUISTIC ordering phrases, not restaurant data.
"""

import re
from typing import Tuple

# Intent patterns — linguistic ordering phrases, not restaurant data
INTENT_PATTERNS = {
    "CONFIRM": [
        r"\b(yes|haan|ha|okay|ok|theek hai|sahi|bilkul|confirm|done|ho gaya|correct|right)\b",
    ],
    "CANCEL": [
        r"\b(cancel|remove|hatao|mat dena|nahi chahiye|wrong|galat|undo)\b",
    ],
    "MODIFY": [
        r"\b(instead|change|badlo|replace|swap)\b",
    ],
    "REPEAT": [
        r"\b(repeat|dobara|phir se|again|same|wahi|wahi wala)\b",
    ],
    "QUERY": [
        r"\b(what|kya hai|kitna|how much|price|available|hai kya|menu|list)\b",
    ],
    "ORDER": [
        r"\b(want|give|order|lao|chahiye|dena|milega|dedo|lena|bhejo|pack)\b",
        r"\b(1|2|3|4|5|6|7|8|9|10)\s+\w+",
        r"\b(ek|do|teen|char|paanch)\s+\w+",
    ],
}

# Modifier keywords that should NOT steal intent from ORDER
# These are valid inside an ORDER sentence ("2 paneer tikka extra spicy")
_MODIFIER_PATTERNS = [
    r"\b(without|bina|no |extra|zyada|kam|less|more|add)\b",
    r"\b(spicy|mild|hot|medium|sweet|sugar free|no onion|no garlic|jain)\b",
]


def _has_order_signals(text: str) -> bool:
    """Check if text contains ORDER-intent signals (ordering verbs or quantity+item patterns)."""
    for pattern in INTENT_PATTERNS["ORDER"]:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _has_modifier_only(text: str) -> bool:
    """Check if text ONLY has modifier keywords, no order signals."""
    for pattern in _MODIFIER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def classify_intent(text: str) -> Tuple[str, str]:
    """
    Returns (intent, matched_pattern)

    Context-aware priority:
    - CONFIRM/CANCEL checked first (explicit user actions)
    - If ORDER signals are present alongside modifiers → ORDER wins
    - MODIFY only wins if there are NO order signals (pure modification request)
    - REPEAT/QUERY checked before ORDER fallback
    """
    if not text:
        return "UNKNOWN", ""

    text_lower = text.lower()

    # 1. Check CONFIRM — explicit confirmation always wins
    for pattern in INTENT_PATTERNS["CONFIRM"]:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return "CONFIRM", match.group()

    # 2. Check CANCEL — explicit cancel always wins
    for pattern in INTENT_PATTERNS["CANCEL"]:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return "CANCEL", match.group()

    # 3. Context-aware: if order signals exist, modifiers don't steal intent
    has_order = _has_order_signals(text_lower)
    has_modifier = _has_modifier_only(text_lower)

    # If BOTH order + modifier signals → ORDER (user is ordering WITH modifiers)
    if has_order and has_modifier:
        for pattern in INTENT_PATTERNS["ORDER"]:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                return "ORDER", match.group()

    # 4. MODIFY only if NO order signals present (pure modification)
    if has_modifier and not has_order:
        for pattern in _MODIFIER_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                return "MODIFY", match.group()

    # 5. REPEAT
    for pattern in INTENT_PATTERNS["REPEAT"]:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return "REPEAT", match.group()

    # 6. QUERY
    for pattern in INTENT_PATTERNS["QUERY"]:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return "QUERY", match.group()

    # 7. ORDER (fallback — quantity+item patterns, ordering verbs)
    if has_order:
        for pattern in INTENT_PATTERNS["ORDER"]:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                return "ORDER", match.group()

    return "UNKNOWN", ""
