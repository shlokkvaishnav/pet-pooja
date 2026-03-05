"""
intent_mapper.py — Intent Classification
==========================================
Classifies customer intent using regex patterns.
No AI models, no API calls — pure pattern matching.
These are LINGUISTIC ordering phrases, not restaurant data.
"""

import re
from typing import Tuple

# Intent patterns — linguistic ordering phrases, not restaurant data
# Priority order: CONFIRM > CANCEL > MODIFY > REPEAT > QUERY > ORDER
INTENT_PATTERNS = {
    "CONFIRM": [
        r"\b(yes|haan|ha|okay|ok|theek hai|sahi|bilkul|confirm|done|ho gaya|correct|right)\b",
    ],
    "CANCEL": [
        r"\b(cancel|remove|hatao|mat dena|nahi chahiye|wrong|galat|undo)\b",
    ],
    "MODIFY": [
        r"\b(without|bina|no |extra|zyada|kam|less|more|add|instead|change|badlo)\b",
        r"\b(spicy|mild|hot|medium|sweet|sugar free|no onion|no garlic|jain)\b",
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


def classify_intent(text: str) -> Tuple[str, str]:
    """
    Returns (intent, matched_pattern)
    Priority: CONFIRM > CANCEL > MODIFY > REPEAT > QUERY > ORDER > UNKNOWN
    """
    if not text:
        return "UNKNOWN", ""

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return intent, match.group()

    return "UNKNOWN", ""
