"""
modifier_extractor.py — Per-item Modifier Extraction with Target Resolution
=============================================================================
Modifier PATTERNS are linguistic (common across all restaurants).
But allowed modifiers per item are loaded DYNAMICALLY from DB.

Target resolution: determines WHICH item a modifier applies to:
    - Explicit name:  "make the biryani extra spicy"  → biryani
    - Positional:     "make the last one spicy"        → most recent item
    - Proximity:      "paneer tikka extra spicy"       → paneer tikka (nearest)
    - Global:         "everything mild"                → all items
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

# ── Target resolution patterns ──
# "all / everything / sab" → apply to every item
_GLOBAL_PATTERNS = [
    r"\b(everything|all|sab|sabhi|sab\s+mein|har\s+ek|dono)\b",
]
# "last / previous / pehle wala" → most recently added item
_POSITIONAL_LAST = [
    r"\b(last|previous|pehle\s+wala|upar\s+wala|abhi\s+wala|that\s+one|woh\s+wala)\b",
]
# "first / pehla" → first item in current turn
_POSITIONAL_FIRST = [
    r"\b(first|pehla|first\s+one|pehle\s+wala)\b",
]


def _detect_modifier_target(text: str, item_names: list[str]) -> dict:
    """
    Determine which item(s) a modifier clause targets.

    Returns:
        {
            "target_type": "explicit" | "last" | "first" | "global" | "proximity" | "unresolved",
            "target_name": str | None,       # matched item name (for explicit/proximity)
            "target_index": int | None,       # for positional (0-based into current items list)
            "applies_to_all": bool,
        }
    """
    text_lower = text.lower()

    # 1. Global: "everything extra spicy", "sab mein mild"
    for pattern in _GLOBAL_PATTERNS:
        if re.search(pattern, text_lower):
            return {
                "target_type": "global",
                "target_name": None,
                "target_index": None,
                "applies_to_all": True,
            }

    # 2. Positional: "last one spicy", "pehle wala mild"
    for pattern in _POSITIONAL_LAST:
        if re.search(pattern, text_lower):
            return {
                "target_type": "last",
                "target_name": None,
                "target_index": -1,
                "applies_to_all": False,
            }
    for pattern in _POSITIONAL_FIRST:
        if re.search(pattern, text_lower):
            return {
                "target_type": "first",
                "target_name": None,
                "target_index": 0,
                "applies_to_all": False,
            }

    # 3. Explicit name: check if any known item name appears in the text
    #    Sort by name length descending so "paneer tikka" matches before "paneer"
    for name in sorted(item_names, key=len, reverse=True):
        if name.lower() in text_lower:
            return {
                "target_type": "explicit",
                "target_name": name,
                "target_index": None,
                "applies_to_all": False,
            }

    # 4. Unresolved — caller should use proximity or default heuristic
    return {
        "target_type": "unresolved",
        "target_name": None,
        "target_index": None,
        "applies_to_all": False,
    }


def extract_modifiers(text: str, item_id: int, menu_items: list) -> dict:
    """
    Extracts modifiers from transcript for a specific item.
    Cross-checks against item's allowed modifiers FROM THE DB.

    Returns dict with keys: spice_level, size, add_ons, warnings.
    warnings: list of {"modifier", "item_name", "reason"} for unsupported mods.

    This is the per-item extraction (called once per matched item).
    For target-aware extraction across a clause, use extract_modifiers_with_target().
    """
    text = text.lower()

    # DYNAMIC: Get allowed modifiers for this item from DB
    item = next((m for m in menu_items if m.id == item_id), None)
    item_name = item.name if item else "this item"
    allowed_modifiers = {}
    if item and hasattr(item, "modifiers") and item.modifiers:
        try:
            allowed_modifiers = json.loads(item.modifiers)
        except Exception:
            allowed_modifiers = {}

    result = {"spice_level": None, "size": None, "add_ons": [], "warnings": []}

    # Spice level — most items accept spice preference
    for level, patterns in MODIFIER_PATTERNS["spice_level"].items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Check if item explicitly restricts spice levels
                if "spice_level" in allowed_modifiers and level not in allowed_modifiers["spice_level"]:
                    result["warnings"].append({
                        "modifier": level,
                        "item_name": item_name,
                        "reason": "unsupported",
                    })
                else:
                    result["spice_level"] = level
                break

    # Size — only if item supports it (checked from DB)
    size_requested = None
    for size, patterns in MODIFIER_PATTERNS["size"].items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                size_requested = size
                break
        if size_requested:
            break

    if size_requested:
        if "size" in allowed_modifiers:
            result["size"] = size_requested
        else:
            result["warnings"].append({
                "modifier": f"{size_requested} size",
                "item_name": item_name,
                "reason": "unsupported",
            })

    # Add-ons
    for add_on, patterns in MODIFIER_PATTERNS["add_ons"].items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Check if item restricts add-ons
                if "add_ons" in allowed_modifiers and add_on not in allowed_modifiers["add_ons"]:
                    result["warnings"].append({
                        "modifier": add_on.replace("_", " "),
                        "item_name": item_name,
                        "reason": "unsupported",
                    })
                elif add_on not in result["add_ons"]:
                    result["add_ons"].append(add_on)

    return result


def extract_modifiers_with_target(
    clause: str,
    matched_items: list[dict],
    menu_items: list,
    session_items: list[dict] | None = None,
) -> list[dict]:
    """
    Extract modifiers from a clause AND resolve which item(s) they apply to.

    Args:
        clause:         The text clause (potentially just the MODIFY part of a compound utterance)
        matched_items:  Items matched in the CURRENT turn [{"item_id", "item_name", ...}, ...]
        menu_items:     Full menu item list from DB (for allowed modifier cross-check)
        session_items:  Items already in the cart from previous turns (for "last one" resolution)

    Returns list of:
        {
            "item_id": int,
            "item_name": str,
            "modifiers": {...},
            "target_type": str,       # how the target was resolved
        }
    """
    # Build list of all known item names for target detection
    all_names = [i.get("item_name", "") for i in matched_items]
    if session_items:
        all_names.extend(i.get("item_name", "") for i in session_items)
    # Deduplicate while preserving order
    seen = set()
    unique_names = []
    for n in all_names:
        if n and n not in seen:
            seen.add(n)
            unique_names.append(n)

    target_info = _detect_modifier_target(clause, unique_names)

    # Combine current + session items for resolution
    all_items = list(matched_items)
    if session_items:
        all_items.extend(session_items)

    if not all_items:
        return []

    results = []

    if target_info["applies_to_all"]:
        # Global: apply modifiers to every item
        for item in all_items:
            mods = extract_modifiers(clause, item["item_id"], menu_items)
            results.append({
                "item_id": item["item_id"],
                "item_name": item.get("item_name", ""),
                "modifiers": mods,
                "target_type": "global",
            })

    elif target_info["target_type"] == "explicit":
        # Explicit name match
        target_name = target_info["target_name"].lower()
        for item in all_items:
            if item.get("item_name", "").lower() == target_name:
                mods = extract_modifiers(clause, item["item_id"], menu_items)
                results.append({
                    "item_id": item["item_id"],
                    "item_name": item.get("item_name", ""),
                    "modifiers": mods,
                    "target_type": "explicit",
                })
                break

    elif target_info["target_type"] in ("last", "first"):
        # Positional
        idx = target_info["target_index"]
        target_list = session_items if session_items else matched_items
        if target_list:
            try:
                item = target_list[idx]
                mods = extract_modifiers(clause, item["item_id"], menu_items)
                results.append({
                    "item_id": item["item_id"],
                    "item_name": item.get("item_name", ""),
                    "modifiers": mods,
                    "target_type": target_info["target_type"],
                })
            except IndexError:
                pass

    elif target_info["target_type"] == "unresolved":
        # Proximity heuristic: if there's exactly one item in this clause's
        # matched_items, it's almost certainly the target. Otherwise, apply
        # to the most recently mentioned item.
        if len(matched_items) == 1:
            item = matched_items[0]
            mods = extract_modifiers(clause, item["item_id"], menu_items)
            results.append({
                "item_id": item["item_id"],
                "item_name": item.get("item_name", ""),
                "modifiers": mods,
                "target_type": "proximity",
            })
        elif matched_items:
            # Apply to last item in the clause (nearest mention)
            item = matched_items[-1]
            mods = extract_modifiers(clause, item["item_id"], menu_items)
            results.append({
                "item_id": item["item_id"],
                "item_name": item.get("item_name", ""),
                "modifiers": mods,
                "target_type": "proximity",
            })
        elif session_items:
            # No items in this clause — fall back to last session item
            item = session_items[-1]
            mods = extract_modifiers(clause, item["item_id"], menu_items)
            results.append({
                "item_id": item["item_id"],
                "item_name": item.get("item_name", ""),
                "modifiers": mods,
                "target_type": "last_session",
            })

    return results
