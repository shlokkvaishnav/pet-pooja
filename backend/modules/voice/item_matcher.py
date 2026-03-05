"""
item_matcher.py — Fuzzy Menu Item Matching
============================================
Matches spoken/typed food item names against the menu database
using alias lookup + RapidFuzz fuzzy matching with sliding window.

Handles misspellings, abbreviations, Hindi names, and partial matches.
"""

import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from models import MenuItem

logger = logging.getLogger("petpooja.voice.matcher")

# Try to import rapidfuzz — fall back to basic matching if unavailable
try:
    from rapidfuzz import fuzz, process as rfprocess
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    logger.warning("rapidfuzz not installed — falling back to basic matching")


def build_search_corpus(menu_items: list) -> dict:
    """
    Build a search corpus mapping every alias/hindi_name/name → item dict.

    Args:
        menu_items: List of MenuItem ORM objects

    Returns:
        Dict mapping lowercase string → {item_id, name, name_hi, selling_price, ...}
    """
    corpus = {}

    for item in menu_items:
        item_data = {
            "item_id": item.id,
            "name": item.name,
            "name_hi": item.name_hi or "",
            "selling_price": item.selling_price,
            "food_cost": item.food_cost,
            "is_veg": item.is_veg,
            "modifiers": item.modifiers or {},
            "category_id": item.category_id,
        }

        # Primary name
        corpus[item.name.lower()] = item_data

        # Hindi name
        if item.name_hi:
            corpus[item.name_hi.lower()] = item_data

        # Pipe-separated aliases
        if item.aliases:
            for alias in item.aliases.split("|"):
                alias = alias.strip().lower()
                if alias:
                    corpus[alias] = item_data

    return corpus


def match_item(token: str, corpus: dict, threshold: int = 72) -> Optional[dict]:
    """
    Match a single token/phrase against the corpus using RapidFuzz WRatio.

    Args:
        token: Text to match (lowercased)
        corpus: Search corpus from build_search_corpus()
        threshold: Minimum match score (0–100), default 72

    Returns:
        Best matching item dict with match_score, or None
    """
    token = token.strip().lower()
    if not token:
        return None

    # Exact match first
    if token in corpus:
        result = corpus[token].copy()
        result["match_score"] = 100
        result["matched_term"] = token
        return result

    # Fuzzy match
    if HAS_RAPIDFUZZ:
        corpus_keys = list(corpus.keys())
        match = rfprocess.extractOne(
            token,
            corpus_keys,
            scorer=fuzz.WRatio,
            score_cutoff=threshold,
        )
        if match:
            matched_key, score, _ = match
            result = corpus[matched_key].copy()
            result["match_score"] = round(score, 1)
            result["matched_term"] = matched_key
            return result
    else:
        # Basic substring fallback
        for key, item_data in corpus.items():
            if token in key or key in token:
                result = item_data.copy()
                result["match_score"] = 75
                result["matched_term"] = key
                return result

    return None


def match_items(db: Session, text: str) -> list[dict]:
    """
    Match menu items from a normalized text string using sliding window
    n-gram approach (1-word, 2-word, 3-word).

    Args:
        db: Database session
        text: Normalized input text

    Returns:
        List of matched item dicts [{item_id, name, name_hi, selling_price, match_score, ...}]
    """
    # Load menu and build corpus
    menu_items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
    if not menu_items:
        logger.warning("No available menu items found")
        return []

    corpus = build_search_corpus(menu_items)

    # Tokenize
    tokens = text.lower().split()
    if not tokens:
        return []

    matched = []
    matched_item_ids = set()
    used_positions = set()

    # Sliding window: try 3-word, then 2-word, then 1-word ngrams
    # Longer matches take priority (more specific)
    for window_size in [3, 2, 1]:
        for i in range(len(tokens) - window_size + 1):
            # Skip positions already consumed by a previous match
            positions = set(range(i, i + window_size))
            if positions & used_positions:
                continue

            ngram = " ".join(tokens[i : i + window_size])
            result = match_item(ngram, corpus, threshold=72)

            if result and result["item_id"] not in matched_item_ids:
                result["token_position"] = i
                result["token_length"] = window_size
                matched.append(result)
                matched_item_ids.add(result["item_id"])
                used_positions |= positions

    # Sort by position in text (preserve order of mention)
    matched.sort(key=lambda x: x.get("token_position", 0))

    logger.info(f"Matched {len(matched)} items from text: '{text[:80]}...'")
    return matched
