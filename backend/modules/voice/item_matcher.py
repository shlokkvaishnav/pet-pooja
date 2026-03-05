"""
item_matcher.py — Dynamic Fuzzy Menu Item Matching
====================================================
Builds search corpus FROM THE DATABASE — nothing hardcoded.
Uses RapidFuzz for fuzzy string matching (local, no API).
"""

from rapidfuzz import process, fuzz
from typing import Optional

# Common words that shouldn't match on their own
SKIP_WORDS = {"aur", "and", "or", "ya", "bhi", "with", "dena", "lao",
              "chahiye", "please", "extra", "no", "one", "two", "the",
              "ka", "ki", "ke", "se", "me", "hai", "ho", "karo",
              "bhaiya", "bhaiyya", "bhaia", "bhai", "de", "do",
              "yaar", "boss", "ji", "haan", "ok", "okay",
              # Devanagari equivalents (fallback if transliteration missed)
              "और", "या", "भी", "देना", "दे", "लाओ", "चाहिए",
              "भैया", "भइया", "भाई", "जी", "हाँ", "हां"}


def build_search_corpus(menu_items: list) -> dict:
    """
    DYNAMICALLY builds search corpus from DB menu items.
    Returns: { "alias string" -> item_id }
    """
    corpus = {}
    for item in menu_items:
        entries = []
        if item.name:
            entries.append(item.name.lower().strip())
        if item.name_hi:
            entries.append(item.name_hi.strip())
        if hasattr(item, "aliases") and item.aliases:
            for alias in item.aliases.split("|"):
                alias = alias.strip().lower()
                if alias:
                    entries.append(alias)
        for entry in entries:
            if entry:
                corpus[entry] = item.id
    return corpus


# Confidence threshold below which we flag for disambiguation
DISAMBIGUATION_THRESHOLD = 0.85


def match_item(text: str, corpus: dict, threshold: int = 70) -> Optional[dict]:
    """Fuzzy match a spoken phrase against the dynamic corpus."""
    if not text or not corpus:
        return None

    text_clean = text.strip().lower()
    if text_clean in SKIP_WORDS or len(text_clean) < 2:
        return None

    # Use token_sort_ratio instead of WRatio
    # WRatio does partial matching (finds best substring) which causes
    # "paneer tikka" to match "paneer butter masala" at 85%.
    # token_sort_ratio requires ALL words to be present, just in any order.
    result = process.extractOne(
        text_clean,
        corpus.keys(),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
    )

    if result:
        matched_key, score, _ = result
        match_result = {
            "item_id": corpus[matched_key],
            "matched_as": matched_key,
            "confidence": round(score / 100, 3),
        }

        # If confidence is below disambiguation threshold, find alternatives
        if score / 100 < DISAMBIGUATION_THRESHOLD:
            alternatives = get_alternatives(text_clean, corpus, top_n=3)
            match_result["needs_disambiguation"] = True
            match_result["alternatives"] = alternatives
        else:
            match_result["needs_disambiguation"] = False
            match_result["alternatives"] = []

        return match_result
    return None


def get_alternatives(text: str, corpus: dict, top_n: int = 3) -> list:
    """Return top N fuzzy matches as disambiguation candidates."""
    results = process.extract(
        text.strip().lower(),
        corpus.keys(),
        scorer=fuzz.token_sort_ratio,
        limit=top_n,
        score_cutoff=60,
    )
    return [
        {
            "item_id": corpus[key],
            "matched_as": key,
            "confidence": round(score / 100, 3),
        }
        for key, score, _ in results
    ]


def extract_all_items(text: str, corpus: dict) -> list:
    """
    Sliding window over transcript tokens.
    Tries 3-word, 2-word, then 1-word phrases.
    Uses overlap prevention + minimum confidence per window size.
    """
    if not text or not corpus:
        return []

    tokens = text.split()
    found = {}           # item_id -> best match dict
    used_positions = set()

    # Minimum confidence per window size
    # Larger windows = more likely to be intentional, lower threshold OK
    # Single words = high false positive risk, need high threshold
    MIN_CONF = {3: 0.80, 2: 0.80, 1: 0.92}

    for window_size in [3, 2, 1]:
        min_confidence = MIN_CONF[window_size]

        for i in range(len(tokens) - window_size + 1):
            window_positions = set(range(i, i + window_size))
            if window_positions & used_positions:
                continue

            phrase = " ".join(tokens[i:i + window_size])
            if phrase.strip().isdigit():
                continue

            match = match_item(phrase, corpus)
            if match and match["confidence"] >= min_confidence:
                item_id = match["item_id"]
                if item_id not in found or match["confidence"] > found[item_id]["confidence"]:
                    found[item_id] = {**match, "position": i}
                    used_positions.update(window_positions)

    return sorted(found.values(), key=lambda x: x["position"])
