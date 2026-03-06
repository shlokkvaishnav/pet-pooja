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
    "DONE": [
        # English
        r"\b(done|that'?s?\s*it|that'?s?\s*all|that\s*will\s*be\s*all|enough|no\s*more|nothing\s*else|nothing\s*more|over|finish)\b",
        # Hindi / Hinglish (+ Whisper spelling variants for "bas")
        r"\b(bas|buss|bus|boss|bass|ho\s*gaya|ho\s*gya|hogaya|hogya|khatam|aur\s*nahi|aur\s*kuch\s*nahi|itna\s*hi|bas\s*kar|bus\s*kar|ho\s*gai|hogai)\b",
        # Gujarati romanized
        r"\b(bas\s*thai\s*gay?u|thayu|thai\s*gayu|aatle|puru|puro)\b",
        # Marathi romanized
        r"\b(jhale?|zhale?|bas\s*zale|sampale?|puro|zale|jhala)\b",
    ],
    "CONFIRM": [
        # English
        r"\b(yes|yeah|yep|yup|sure|okay|ok|confirm|correct|right|go\s*ahead|definitely|absolutely|place\s*(?:the\s*)?order)\b",
        # Hindi / Hinglish
        r"\b(haan|haa|ha\s+ji|haji|theek\s*hai|thik\s*hai|sahi|bilkul|pakka|kar\s*do|kardo|karo|laga\s*do|lagado|lagao|de\s*do|dedo)\b",
        # Hindi compound: "order kar do", "order laga do", "order de do"
        r"\border\s*(?:kar\s*do|kardo|karo|laga\s*do|lagado|lagao|de\s*do|dedo|place\s*kar)\b",
        # Gujarati romanized
        r"\b(haa|chale|chalse|karso|muki\s*d[oy]o?|muko)\b",
        # Marathi romanized ("ho" but not "ho gaya"/"ho gya")
        r"\bho\b(?!\s*g[ay])",
        r"\b(chalu\s*kar|lava|dya|ghya|order\s*dya|thik\s*aahe)\b",
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

    # 1. CONFIRM (explicit yes/confirm)
    for pattern in INTENT_PATTERNS["CONFIRM"]:
        match = re.search(pattern, text_lower)
        if match:
            return "CONFIRM", match.group()

    # 1b. DONE ("that's it", "bas", "ho gaya" — signals ordering is finished)
    for pattern in INTENT_PATTERNS["DONE"]:
        match = re.search(pattern, text_lower)
        if match:
            return "DONE", match.group()

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
    priority = ["CANCEL", "CONFIRM", "DONE", "MODIFY", "REPEAT", "QUERY", "ORDER", "UNKNOWN"]
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


# ── Cancel-all detection ──
_CANCEL_ALL_PATTERNS = [
    r"\b(everything|every\s+thing|all|sab|sab\s+kuch|sara|saara|poora|pura|complete)\b",
    r"\b(cancel\s+(?:the\s+)?order|order\s+cancel|reset|clear|start\s*over|shuru\s+se)\b",
    r"\b(don'?t\s+want\s+anything|kuch\s+nahi|nahi\s+chahiye\s+kuch|sab\s+hata\s+do)\b",
    r"\b(clear\s+(?:the\s+)?cart|empty\s+(?:the\s+)?cart|remove\s+(?:all|everything|sab))\b",
]


def is_cancel_all(text: str) -> bool:
    """Check if a cancel utterance means 'cancel everything / clear the order'."""
    text_lower = text.lower().strip()
    for pattern in _CANCEL_ALL_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


_ORDER_START = re.compile(
    r"""
    (?:now\s+)?                              # optional "now"
    (?:
        give\s+me
      | i\s+(?:want|need|would\s+like)
      | (?:mujhe|mujhko|mereko|humko)\s*(?:de(?:do|na)?|chahiye|lao)?
      | please\s+(?:give|get|bring)
      | (?:can|could)\s+(?:i|you)\s+(?:get|have|order)
      | let\s+me\s+(?:have|order|get)
      | i(?:'d|\s+would)\s+like
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _split_clauses(text: str) -> list[str]:
    """
    Split an utterance into clauses at conjunction/punctuation boundaries.
    Also splits at order-start phrases (e.g. "give me", "now give me")
    so non-food preamble doesn't contaminate item matching.

    Only splits if the result would yield multiple non-trivial fragments.
    """
    # --- Phase 0: split at order-start phrases ---
    # If "give me" / "now give me" etc. appears mid-sentence, treat it as
    # a clause boundary so everything before it (non-food chatter) is isolated.
    segments = [text.strip()]
    m = _ORDER_START.search(text)
    if m and m.start() > 3:       # at least a few chars of preamble before it
        preamble = text[:m.start()].strip()
        order_part = text[m.start():].strip()
        if preamble and order_part:
            segments = [preamble, order_part]

    # --- Phase 1: apply conjunction/punctuation splitting to each segment ---
    all_clauses: list[str] = []
    for seg in segments:
        parts = _CLAUSE_SPLITTERS.split(seg)
        clauses = [p.strip() for p in parts if p and p.strip()]
        if len(clauses) <= 1:
            all_clauses.append(seg.strip())
        else:
            substantial = [c for c in clauses if len(c.split()) >= 2]
            if len(substantial) < 2:
                all_clauses.append(seg.strip())
            else:
                all_clauses.extend(clauses)

    return all_clauses if all_clauses else [text.strip()]
