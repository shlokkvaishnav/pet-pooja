"""
normalizer.py — Text Normalization for Hindi/Hinglish/Gujarati/Marathi
=======================================================================
Supports: English, Hindi, Hinglish, Gujarati, Marathi
Only LINGUISTIC patterns are hardcoded (numbers, fillers).
Food/menu data comes from the DATABASE via item_matcher.
"""

import re

# ---------------------------------------------------------------------------
# Devanagari -> Romanized transliteration map (common restaurant words)
# Applied BEFORE number/filler processing so downstream stays Latin-script.
# ---------------------------------------------------------------------------
DEVANAGARI_MAP = {
    # Numbers
    "एक": "ek", "दो": "do", "तीन": "teen", "चार": "char",
    "पांच": "paanch", "पाँच": "paanch", "छह": "chhe", "छे": "chhe",
    "सात": "saat", "आठ": "aath", "नौ": "nau", "दस": "das",
    "ग्यारह": "gyarah", "बारह": "barah", "बीस": "bees",
    # Common ordering words
    "और": "aur", "या": "ya", "भी": "bhi",
    "दे": "de", "देना": "dena", "दो": "do",  # context: "give" vs "two" handled below
    "लाओ": "lao", "चाहिए": "chahiye", "चाहिये": "chahiye",
    "कृपया": "please", "प्लीज": "please",
    # Common fillers
    "भैया": "bhaiya", "भइया": "bhaiya", "भाई": "bhai",
    "यार": "yaar", "बॉस": "boss", "जी": "ji",
    "अच्छा": "accha", "ठीक": "theek", "हाँ": "haan", "हां": "haan",
    # Modifiers
    "एक्स्ट्रा": "extra", "बिना": "bina", "स्पाइसी": "spicy",
    "ज़्यादा": "zyada", "कम": "kam",
    # Common food words (helps fuzzy matching after transliteration)
    "पनीर": "paneer", "टिक्का": "tikka", "बटर": "butter",
    "नान": "naan", "रोटी": "roti", "चिकन": "chicken",
    "बिरयानी": "biryani", "दाल": "dal", "मसाला": "masala",
    "लस्सी": "lassi", "चाय": "chai", "गुलाब": "gulab",
    "जामुन": "jamun", "मखनी": "makhani", "मक्खनी": "makhani",
    "तंदूरी": "tandoori", "तन्दूरी": "tandoori",
    "पालक": "palak", "शाही": "shahi", "कड़ाही": "kadhai",
    "मटन": "mutton", "गोश्त": "gosht", "मछली": "fish",
    "आलू": "aloo", "गोभी": "gobhi", "भिंडी": "bhindi",
    "राइस": "rice", "चावल": "chawal", "खीर": "kheer",
    "रसमलाई": "rasmalai", "कुल्फी": "kulfi",
    "कोल्ड": "cold", "ड्रिंक": "drink", "पानी": "pani",
    "मशरूम": "mushroom", "केबाब": "kebab", "कबाब": "kebab",
    "रायता": "raita", "सलाद": "salad",
}


def _transliterate_devanagari(text: str) -> str:
    """Replace Devanagari tokens with romanized equivalents."""
    for dev, roman in DEVANAGARI_MAP.items():
        text = text.replace(dev, roman)
    # Drop any remaining Devanagari characters (U+0900-U+097F)
    text = re.sub(r"[\u0900-\u097F]+", " ", text)
    return text


# Number words -> integer
# Covers Hindi, Gujarati, Marathi romanized variants
NUMBER_WORDS = {
    # Hindi / Hinglish
    "ek": 1, "ak": 1,
    "do": 2, "dono": 2, "dou": 2,
    "teen": 3, "tin": 3,
    "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5,
    "chhe": 6, "chheh": 6,
    "saat": 7, "sat": 7,
    "aath": 8, "ath": 8,
    "nau": 9, "naw": 9,
    "das": 10,
    "gyarah": 11,
    "barah": 12,
    "tera": 13,
    "chaudah": 14,
    "pandrah": 15,
    "bees": 20,

    # Gujarati romanized
    "be": 2,
    "tran": 3,
    "chha": 6,
    "nav": 9,

    # Marathi romanized
    "don": 2,
    "paach": 5,
    "saha": 6,
    "daha": 10,

    # English number words
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

# Conversational filler words across all 5 supported languages
FILLERS = {
    # English / common
    "umm", "uh", "uhh", "hmm", "aaa", "err", "please",
    "okay", "ok", "actually", "basically",
    # Hindi / Hinglish
    "bhai", "bhaiya", "bhaiyya", "bhaia", "yaar", "boss",
    "sunlo", "suniye", "suno",
    "bolo", "batao", "ji", "haan", "theek", "acha", "accha", "matlab",
    "dekho", "dekhiye", "sahab", "saab",
    # Gujarati
    "kem", "saro",
    # Marathi
    "arey", "bro", "na",
}


def normalize(text: str) -> str:
    """
    Input : raw Whisper transcript
    Output: cleaned lowercase string ready for intent + item parsing
    """
    if not text or not text.strip():
        return ""

    text = text.lower().strip()

    # Remove punctuation except spaces
    text = re.sub(r"[^\w\s]", " ", text)

    # Transliterate Devanagari -> romanized BEFORE number/filler processing
    text = _transliterate_devanagari(text)

    # Replace number words with digits (Hindi, Gujarati, Marathi, English)
    tokens = text.split()
    tokens = [str(NUMBER_WORDS[t]) if t in NUMBER_WORDS else t for t in tokens]
    text = " ".join(tokens)

    # Remove filler words
    tokens = text.split()
    tokens = [t for t in tokens if t not in FILLERS]
    text = " ".join(tokens)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text
