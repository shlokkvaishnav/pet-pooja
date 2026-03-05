"""
intent_mapper.py — Compound Intent Classification
====================================================
Splits utterances into clauses and classifies each independently.
Handles real restaurant speech like:
    "Cancel the naan but keep the dal"        → [CANCEL(naan), ORDER(dal)]
    "Make the biryani extra spicy and add one raita" → [MODIFY(biryani), ORDER(raita)]
    "Remove paneer tikka, add chicken tikka instead" → [CANCEL(paneer tikka), ORDER(chicken tikka)]

No AI models, no API calls — clause splitting + regex pattern matching.
"""

import re
from typing import Tuple

# ── Clause-splitting patterns ──
# These conjunctions/punctuation typically separate independent instructions.
_CLAUSE_SPLITTERS = re.compile(
    r"""
      \s*[,;]\s*                              # comma or semicolon
    | \s+(?:but|lekin|magar|par)\s+           # adversative conjunctions
    | \s+(?:and|aur|or|ya)\s+                 # additive / alternative
    | \s+(?:also|bhi)\s+                      # additive
    | \s+(?:then|phir|uske\s+baad)\s+         # sequential
    | \s+(?:instead|ki\s+jagah)\s+            # replacement marker
    """,
    re.IGNORECASE | re.VERBOSE,
)

# ── Intent patterns — linguistic ordering phrases ──
INTENT_PATTERNS = {
    "CONFIRM": [
        r"\b(yes|haan|ha|okay|ok|theek hai|sahi|bilkul|confirm|done|ho gaya|correct|right)\b",
    ],
    "CANCEL": [
        r"\b(cancel|remove|hatao|hata\s+do|mat\s+dena|nahi\s+chahiye|wrong|galat|undo|nikal)\b",
    ],
    "MODIFY": [
        r"\b(instead|change|badlo|replace|swap|ki\s+jagah)\b",
    ],
    "REPEAT": [
        r"\b(repeat|dobara|phir\s+se|again|same|wahi|wahi\s+wala)\b",
    ],
    "QUERY": [
        r"\b(what|kya\s+hai|kitna|how\s+much|price|available|hai\s+kya|menu|list)\b",
    ],
    "ORDER": [
        r"\b(want|give|order|lao|chahiye|dena|milega|dedo|lena|bhejo|pack|add|keep|rakh)\b",
        r"\b(?:1|2|3|4|5|6|7|8|9|10)\s+\w+",
        r"\b(?:ek|do|teen|char|paanch)\s+\w+",
    ],
}

# Modifier keywords that should NOT steal intent from ORDER
_MODIFIER_PATTERNS = [
    r"\b(without|bina|no |extra|zyada|kam|less|more|add)\b",
    r"\b(spicy|mild|hot|medium|sweet|sugar\s+free|no\s+onion|no\s+garlic|jain)\b",
]


def _has_order_signals(text: str) -> bool:
    for pattern in INTENT_PATTERNS["ORDER"]:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _has_modifier_only(text: str) -> bool:
    for pattern in _MODIFIER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _classify_single_clause(text: str) -> Tuple[str, str]:
    """Classify a single clause (no compound splitting). Returns (intent, matched_pattern)."""
    if not text or not text.strip():
        return "UNKNOWN", ""

    text_lower = text.lower().strip()

    # 1. CONFIRM
    for pattern in INTENT_PATTERNS["CONFIRM"]:
        match = re.search(pattern, text_lower)
        if match:
            return "CONFIRM", match.group()

    # 2. CANCEL
    for pattern in INTENT_PATTERNS["CANCEL"]:
        match = re.search(pattern, text_lower)
        if match:
            return "CANCEL", match.group()

    # 3. Context-aware ORDER vs MODIFY
    has_order = _has_order_signals(text_lower)
    has_modifier = _has_modifier_only(text_lower)

    if has_order and has_modifier:
        for pattern in INTENT_PATTERNS["ORDER"]:
            match = re.search(pattern, text_lower)
            if match:
                return "ORDER", match.group()

    if has_modifier and not has_order:
        for pattern in _MODIFIER_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                return "MODIFY", match.group()

    # 4. REPEAT
    for pattern in INTENT_PATTERNS["REPEAT"]:
        match = re.search(pattern, text_lower)
        if match:
            return "REPEAT", match.group()

    # 5. QUERY
    for pattern in INTENT_PATTERNS["QUERY"]:
        match = re.search(pattern, text_lower)
        if match:
            return "QUERY", match.group()

    # 6. ORDER fallback
    if has_order:
        for pattern in INTENT_PATTERNS["ORDER"]:
            match = re.search(pattern, text_lower)
            if match:
                return "ORDER", match.group()

    return "UNKNOWN", ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_intent(text: str) -> Tuple[str, str]:
    """
    Backward-compatible single-intent classifier.
    Returns the PRIMARY intent (first by priority) and its matched pattern.

    For compound intent support, use classify_intents() instead.
    """
    results = classify_intents(text)
    if not results:
        return "UNKNOWN", ""
    # Priority: CANCEL > CONFIRM > MODIFY > REPEAT > QUERY > ORDER > UNKNOWN
    priority = ["CANCEL", "CONFIRM", "MODIFY", "REPEAT", "QUERY", "ORDER", "UNKNOWN"]
    for p in priority:
        for r in results:
            if r["intent"] == p:
                return r["intent"], r["matched_pattern"]
    return results[0]["intent"], results[0]["matched_pattern"]


def classify_intents(text: str) -> list[dict]:
    """
    Compound-aware intent classifier.
    Splits the utterance into clauses and classifies each independently.

    Returns list of:
        {
            "intent": str,           # ORDER, CANCEL, MODIFY, etc.
            "matched_pattern": str,  # regex match that triggered the intent
            "clause": str,           # the text fragment this intent came from
            "clause_index": int,     # 0-based position in utterance
        }

    Examples:
        "Cancel the naan but keep the dal"
        → [
            {"intent": "CANCEL", "clause": "cancel the naan", ...},
            {"intent": "ORDER",  "clause": "keep the dal", ...},
          ]

        "Make it extra spicy and add one raita"
        → [
            {"intent": "MODIFY", "clause": "make it extra spicy", ...},
            {"intent": "ORDER",  "clause": "add one raita", ...},
          ]
    """
    if not text:
        return [{"intent": "UNKNOWN", "matched_pattern": "", "clause": "", "clause_index": 0}]

    clauses = _split_clauses(text)

    results = []
    for idx, clause in enumerate(clauses):
        intent, pattern = _classify_single_clause(clause)
        results.append({
            "intent": intent,
            "matched_pattern": pattern,
            "clause": clause.strip(),
            "clause_index": idx,
        })

    # Filter out UNKNOWN clauses that are just connective tissue,
    # unless ALL clauses are UNKNOWN.
    meaningful = [r for r in results if r["intent"] != "UNKNOWN"]
    if meaningful:
        results = meaningful

    return results


def _split_clauses(text: str) -> list[str]:
    """
    Split an utterance into clauses at conjunction/punctuation boundaries.
    Preserves clause text for downstream item matching.

    Only splits if the result would yield multiple non-trivial fragments.
    """
    parts = _CLAUSE_SPLITTERS.split(text)
    # Keep only non-empty, non-whitespace fragments
    clauses = [p.strip() for p in parts if p and p.strip()]

    # Don't split if it would produce only 1 clause (or empty)
    if len(clauses) <= 1:
        return [text.strip()]

    # Don't split if any fragment is too short to be meaningful (< 2 words)
    # unless we have at least 2 substantial clauses
    substantial = [c for c in clauses if len(c.split()) >= 2]
    if len(substantial) < 2:
        return [text.strip()]

    return clauses
