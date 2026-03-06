"""
quantity_extractor.py — Position-based Quantity Extraction
===========================================================
Hindi numbers are LANGUAGE constants, not restaurant data.
"""

import re

from .voice_config import cfg

HINDI_NUMBERS = {
    # Hindi / Hinglish (1-10) — all common Whisper romanization variants
    "ek": 1, "ak": 1, "aek": 1, "ikk": 1,
    "do": 2, "dono": 2, "doh": 2,
    "teen": 3, "tin": 3, "tiin": 3,
    "char": 4, "chaar": 4, "char": 4,
    "paanch": 5, "panch": 5, "paach": 5, "punch": 5,
    "chhe": 6, "cheh": 6, "che": 6, "chhah": 6, "chha": 6, "chhey": 6,
    "saat": 7, "sat": 7, "saath": 7,
    "aath": 8, "ath": 8, "aath": 8, "aat": 8, "aatt": 8,
    "nau": 9, "naw": 9, "no": 9,
    "das": 10, "dus": 10, "duss": 10,
    # Hindi 11-20
    "gyaarah": 11, "gyarah": 11, "gyara": 11,
    "baarah": 12, "barah": 12, "bara": 12,
    "terah": 13, "tera": 13,
    "chaudah": 14, "chauda": 14, "chodah": 14,
    "pandrah": 15, "pandra": 15,
    "solah": 16, "sola": 16,
    "satrah": 17, "satra": 17,
    "athaarah": 18, "atharah": 18, "athara": 18,
    "unnees": 19, "unnis": 19,
    "bees": 20, "bis": 20,
    # Gujarati romanized
    "be": 2, "tran": 3, "nav": 9,
    # Marathi romanized
    "don": 2, "saha": 6, "daha": 10,
    # English (1-20)
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    # Fractional / special
    "half": 0.5, "double": 2, "triple": 3,
    # Devanagari (fallback if transliteration missed in normalizer)
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4,
    "पांच": 5, "पाँच": 5, "छह": 6, "छे": 6,
    "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14,
    "पंद्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18,
    "उन्नीस": 19, "बीस": 20,
}

# Compound quantity patterns: "2-3", "2 to 3", "2 or 3"
_RANGE_PATTERN = re.compile(r"(\d+)\s*[-to]+\s*(\d+)")


def extract_quantity(text: str, item_position: int, tokens: list) -> int:
    """
    Looks for quantity in the 3 tokens BEFORE and 3 tokens AFTER
    the matched item's position in the token list.
    Default: 1.
    """
    start = max(0, item_position - cfg.QTY_WINDOW_BEFORE)
    end = min(len(tokens), item_position + cfg.QTY_WINDOW_AFTER)
    window = tokens[start:end]

    # Check for range pattern (e.g., "2-3 naan" -> use higher value)
    window_text = " ".join(window)
    range_match = _RANGE_PATTERN.search(window_text)
    if range_match:
        return int(range_match.group(2))  # Use the higher bound

    for token in window:
        token = token.strip().lower()
        if token in HINDI_NUMBERS:
            val = HINDI_NUMBERS[token]
            return int(val) if val >= 1 else 1
        if token.isdigit():
            val = int(token)
            if 1 <= val <= cfg.QTY_MAX_VALID:
                return val

    return cfg.QTY_DEFAULT


def extract_quantities_for_items(text: str, matched_items: list) -> list:
    """For each matched item, extract its quantity."""
    tokens = text.split()
    result = []
    for item in matched_items:
        qty = extract_quantity(text, item["position"], tokens)
        result.append({**item, "quantity": qty})
    return result
