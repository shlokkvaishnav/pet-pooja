"""
modifier_extractor.py — Per-item Modifier Extraction
======================================================
Modifier PATTERNS are linguistic (common across all restaurants).
But allowed modifiers per item are loaded DYNAMICALLY from DB.
"""

import re
import json

# Linguistic patterns — common across all restaurants
MODIFIER_PATTERNS = {
    "spice_level": {
        "mild":   [r"\b(mild|no spice|bina mirch|kam teekha|less spicy|not spicy)\b"],
        "medium": [r"\b(medium|normal|theek|regular spice)\b"],
        "hot":    [r"\b(spicy|extra spicy|zyada teekha|hot|tez|bahut teekha|very spicy)\b"],
    },
    "size": {
        "small":  [r"\b(small|chota|half|chhota)\b"],
        "large":  [r"\b(large|bada|full|double|bara)\b"],
    },
    "add_ons": {
        "no_onion":      [r"\b(no onion|bina pyaz|without onion|pyaz mat)\b"],
        "no_garlic":     [r"\b(no garlic|bina lehsun|jain|without garlic)\b"],
        "extra_butter":  [r"\b(extra butter|zyada butter|more butter|butter add)\b"],
        "extra_cheese":  [r"\b(extra cheese|cheese add|zyada cheese)\b"],
        "no_sauce":      [r"\b(no sauce|bina sauce|dry)\b"],
    }
}


def extract_modifiers(text: str, item_id: int, menu_items: list) -> dict:
    """
    Extracts modifiers from transcript for a specific item.
    Cross-checks against item's allowed modifiers FROM THE DB.
    """
    text = text.lower()

    # DYNAMIC: Get allowed modifiers for this item from DB
    item = next((m for m in menu_items if m.id == item_id), None)
    allowed_modifiers = {}
    if item and hasattr(item, "modifiers") and item.modifiers:
        try:
            allowed_modifiers = json.loads(item.modifiers)
        except Exception:
            allowed_modifiers = {}

    result = {"spice_level": None, "size": None, "add_ons": []}

    # Spice level — most items accept spice preference
    for level, patterns in MODIFIER_PATTERNS["spice_level"].items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                result["spice_level"] = level
                break

    # Size — only if item supports it (checked from DB)
    if "size" in allowed_modifiers:
        for size, patterns in MODIFIER_PATTERNS["size"].items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    result["size"] = size
                    break

    # Add-ons
    for add_on, patterns in MODIFIER_PATTERNS["add_ons"].items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if add_on not in result["add_ons"]:
                    result["add_ons"].append(add_on)

    return result
