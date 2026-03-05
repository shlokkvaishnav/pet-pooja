"""
quantity_extractor.py — Position-based Quantity Extraction
===========================================================
Hindi numbers are LANGUAGE constants, not restaurant data.
"""

import re

HINDI_NUMBERS = {
    # Hindi / Hinglish
    "ek": 1, "ak": 1,
    "do": 2, "dono": 2,
    "teen": 3, "tin": 3,
    "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5,
    "chhe": 6,
    "saat": 7, "sat": 7,
    "aath": 8, "ath": 8,
    "nau": 9,
    "das": 10,
    # Gujarati romanized
    "be": 2, "tran": 3, "chha": 6, "nav": 9,
    # Marathi romanized
    "don": 2, "paach": 5, "saha": 6, "daha": 10,
    # English
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    # Devanagari (fallback if transliteration missed in normalizer)
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4,
    "पांच": 5, "पाँच": 5, "छह": 6, "छे": 6,
    "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
}


def extract_quantity(text: str, item_position: int, tokens: list) -> int:
    """
    Looks for quantity in the 2 tokens BEFORE and 2 tokens AFTER
    the matched item's position in the token list.
    Default: 1.
    """
    start = max(0, item_position - 2)
    end = min(len(tokens), item_position + 3)
    window = tokens[start:end]

    for token in window:
        token = token.strip().lower()
        if token in HINDI_NUMBERS:
            return HINDI_NUMBERS[token]
        if token.isdigit():
            val = int(token)
            if 1 <= val <= 50:
                return val

    return 1


def extract_quantities_for_items(text: str, matched_items: list) -> list:
    """For each matched item, extract its quantity."""
    tokens = text.split()
    result = []
    for item in matched_items:
        qty = extract_quantity(text, item["position"], tokens)
        result.append({**item, "quantity": qty})
    return result
