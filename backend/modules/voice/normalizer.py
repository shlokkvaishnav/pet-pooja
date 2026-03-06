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


# ---------------------------------------------------------------------------
# Character-level Devanagari → Roman transliteration
# Fallback for words NOT covered by the word-level DEVANAGARI_MAP above.
# Produces approximate romanizations that downstream fuzzy + semantic
# matching can resolve to correct menu items.
# ---------------------------------------------------------------------------
_DEV_VOWELS_INDEP = {
    '\u0905': 'a', '\u0906': 'aa', '\u0907': 'i', '\u0908': 'ee',
    '\u0909': 'u', '\u090A': 'oo', '\u090F': 'e', '\u0910': 'ai',
    '\u0913': 'o', '\u0914': 'au', '\u090B': 'ri',
}
_DEV_MATRAS = {
    '\u093E': 'a', '\u093F': 'i', '\u0940': 'ee', '\u0941': 'u',
    '\u0942': 'oo', '\u0947': 'e', '\u0948': 'ai', '\u094B': 'o',
    '\u094C': 'au', '\u0943': 'ri',
}
_DEV_CONSONANTS = {
    '\u0915': 'k', '\u0916': 'kh', '\u0917': 'g', '\u0918': 'gh', '\u0919': 'ng',
    '\u091A': 'ch', '\u091B': 'chh', '\u091C': 'j', '\u091D': 'jh', '\u091E': 'ny',
    '\u091F': 't', '\u0920': 'th', '\u0921': 'd', '\u0922': 'dh', '\u0923': 'n',
    '\u0924': 't', '\u0925': 'th', '\u0926': 'd', '\u0927': 'dh', '\u0928': 'n',
    '\u092A': 'p', '\u092B': 'ph', '\u092C': 'b', '\u092D': 'bh', '\u092E': 'm',
    '\u092F': 'y', '\u0930': 'r', '\u0932': 'l', '\u0935': 'v',
    '\u0936': 'sh', '\u0937': 'sh', '\u0938': 's', '\u0939': 'h',
}
_DEV_NUKTA_MAP = {
    '\u0915\u093C': 'q', '\u0916\u093C': 'kh', '\u0917\u093C': 'gh',
    '\u091C\u093C': 'z', '\u0921\u093C': 'r', '\u0922\u093C': 'rh',
    '\u092B\u093C': 'f',
}
_DEV_DIGITS = {
    '\u0966': '0', '\u0967': '1', '\u0968': '2', '\u0969': '3', '\u096A': '4',
    '\u096B': '5', '\u096C': '6', '\u096D': '7', '\u096E': '8', '\u096F': '9',
}
_HALANT = '\u094D'
_NUKTA_CHAR = '\u093C'
_ANUSVARA = '\u0902'
_CHANDRABINDU = '\u0901'
_VISARGA = '\u0903'


def _is_devanagari(c: str) -> bool:
    return '\u0900' <= c <= '\u097F'


def _transliterate_remaining_devanagari(text: str) -> str:
    """
    Character-by-character Devanagari → Roman transliteration.
    Uses word-final schwa deletion: last consonant in a Devanagari
    word (before space / non-Devanagari / end) omits inherent 'a'.
    """
    result = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        # Non-Devanagari: pass through
        if not _is_devanagari(c):
            result.append(c)
            i += 1
            continue
        # Devanagari digit
        if c in _DEV_DIGITS:
            result.append(_DEV_DIGITS[c])
            i += 1
            continue
        # Nukta-modified consonant (e.g. ज़ = ज + ़)
        base = None
        if i + 1 < n and text[i + 1] == _NUKTA_CHAR:
            combo = c + _NUKTA_CHAR
            base = _DEV_NUKTA_MAP.get(combo, _DEV_CONSONANTS.get(c, ''))
            i += 2
        elif c in _DEV_CONSONANTS:
            base = _DEV_CONSONANTS[c]
            i += 1
        elif c in _DEV_VOWELS_INDEP:
            result.append(_DEV_VOWELS_INDEP[c])
            i += 1
            continue
        elif c in (_ANUSVARA, _CHANDRABINDU):
            result.append('n')
            i += 1
            continue
        elif c == _VISARGA:
            result.append('h')
            i += 1
            continue
        else:
            i += 1            # skip unknown Devanagari marks
            continue

        # --- Consonant post-processing: halant / matra / inherent vowel ---
        if i < n and text[i] == _HALANT:
            result.append(base)        # halant suppresses inherent vowel
            i += 1
        elif i < n and text[i] in _DEV_MATRAS:
            result.append(base + _DEV_MATRAS[text[i]])
            i += 1
        else:
            # Word-final schwa deletion: omit inherent 'a' at end of
            # Devanagari word (next char is space / non-Devanagari / end)
            at_word_end = (i >= n or not _is_devanagari(text[i]))
            result.append(base if at_word_end else base + 'a')

    return ''.join(result)


def _transliterate_devanagari(text: str) -> str:
    """
    Two-pass Devanagari transliteration:
      1. Word-level: replace known words/phrases from DEVANAGARI_MAP
         (longest match first to prevent partial replacements)
      2. Character-level: transliterate any remaining Devanagari chars
    """
    # Pass 1 — word/phrase level (longest first to avoid partial matches)
    for dev, roman in sorted(DEVANAGARI_MAP.items(),
                             key=lambda x: len(x[0]), reverse=True):
        text = text.replace(dev, roman)
    # Pass 2 — character-level fallback for anything not in the map
    text = _transliterate_remaining_devanagari(text)
    return text


# ---------------------------------------------------------------------------
# Phonetic correction map — common Indian-accent / STT mishearings
# ---------------------------------------------------------------------------
# Applied AFTER Devanagari transliteration, BEFORE fuzzy matching.
# Maps whole-word phonetic variants to standard English food spellings.
# Only maps words that are clearly food-related; avoids overcorrecting.
PHONETIC_CORRECTIONS = {
    # Chicken variants
    "chikan": "chicken", "chiken": "chicken", "chikken": "chicken",
    "chikn": "chicken", "chickan": "chicken", "chikin": "chicken",
    "chkin": "chicken", "chickn": "chicken", "chekin": "chicken",
    "murgh": "chicken", "murg": "chicken",
    # Mutton variants
    "mutan": "mutton", "muton": "mutton", "muten": "mutton",
    "mattan": "mutton", "gosht": "mutton",
    # Paneer variants
    "paner": "paneer", "panir": "paneer", "pneer": "paneer",
    "pnir": "paneer", "panee": "paneer", "paneera": "paneer",
    # Biryani variants
    "biriyani": "biryani", "briyani": "biryani", "biryni": "biryani",
    "biriani": "biryani", "bryani": "biryani", "biriyanee": "biryani",
    # Naan variants
    "nan": "naan", "naaan": "naan",
    # Roti variants
    "rotee": "roti", "rooti": "roti", "rodi": "roti", "rodi": "roti",
    "rothi": "roti",
    # Tikka variants
    "tika": "tikka", "teeka": "tikka", "tikkah": "tikka",
    # Dal variants
    "daal": "dal", "dhal": "dal",
    # Kebab variants
    "kabab": "kebab", "kabob": "kebab", "kebob": "kebab",
    "kabeb": "kebab",
    # Masala variants
    "masale": "masala", "msala": "masala", "masla": "masala",
    # Curry variants
    "kari": "curry", "karri": "curry",
    # Lassi variants
    "lasi": "lassi", "lassee": "lassi",
    # Chai variants
    "chay": "chai", "chae": "chai",
    # Tandoori variants
    "tanduri": "tandoori", "tanduri": "tandoori", "tndoori": "tandoori",
    # Makhani variants
    "makhni": "makhani", "makni": "makhani", "makhane": "makhani",
    # Kulfi variants
    "kulfee": "kulfi",
}

_PHONETIC_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(PHONETIC_CORRECTIONS, key=len, reverse=True)) + r")\b"
)


def _apply_phonetic_corrections(text: str) -> str:
    """Replace phonetic variants with standard food spellings (whole-word only)."""
    return _PHONETIC_RE.sub(lambda m: PHONETIC_CORRECTIONS[m.group(0)], text)


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
    # Hindi ordering verbs (transliterated from Devanagari)
    "karna", "karana", "karo", "kar",
    "dijiye", "kijiye", "banao", "lagao",
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
    # Preserve Devanagari (U+0900-097F) and Gujarati (U+0A80-0AFF) blocks
    # so matras / vowel signs survive for transliteration
    text = re.sub(r"[^\w\s\u0900-\u097F\u0A80-\u0AFF]", " ", text)

    # Transliterate Devanagari -> romanized BEFORE number/filler processing
    text = _transliterate_devanagari(text)

    # Apply phonetic corrections for Indian-accent STT mishearings
    # e.g. "chikan" → "chicken", "biriyani" → "biryani"
    text = _apply_phonetic_corrections(text)

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
