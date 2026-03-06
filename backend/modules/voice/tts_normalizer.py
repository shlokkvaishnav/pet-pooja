"""
tts_normalizer.py — Text Normalization for TTS Input
=======================================================
Converts text that reads well into text that *speaks* well.
Runs between LLM/template text generation and the TTS engine.

Handles: currency, quantities, order IDs, small numbers,
symbols, acronyms, script conversion, menu item name protection,
and breathing punctuation.
"""

import re
import logging

logger = logging.getLogger("petpooja.voice.tts_normalizer")

# ── Small numbers → spoken words (1–20) ──────────────────────────
_NUM_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
    15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen", 20: "twenty",
}

# ── Acronyms to spell out ─────────────────────────────────────────
_ACRONYMS = {
    "KOT": "K O T",
    "GST": "G S T",
    "ID": "I D",
    "UPI": "U P I",
    "QR": "Q R",
}

# ── Script mapping for indic-transliteration ─────────────────────
_SCRIPT_MAP = {
    "hi": "DEVANAGARI",
    "mr": "DEVANAGARI",
    "gu": "GUJARATI",
    "kn": "KANNADA",
}


def _expand_currency(text: str) -> str:
    """₹340 → '340 rupees', ₹5.50 → '5 rupees 50 paise', Rs.340 → '340 rupees'."""
    # ₹ or Rs. with decimal
    text = re.sub(
        r"[₹](\d+)\.(\d{1,2})",
        lambda m: f"{m.group(1)} rupees {m.group(2)} paise",
        text,
    )
    # ₹ or Rs. without decimal
    text = re.sub(r"[₹](\d+)", r"\1 rupees", text)
    text = re.sub(
        r"Rs\.?\s*(\d+)\.(\d{1,2})",
        lambda m: f"{m.group(1)} rupees {m.group(2)} paise",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"Rs\.?\s*(\d+)", r"\1 rupees", text, flags=re.IGNORECASE)
    return text


def _expand_quantities(text: str) -> str:
    """Remove quantity markers: '2x', '×2', 'x2 Butter Naan' → '2'."""
    text = re.sub(r"(\d+)\s*[x×]", r"\1", text)
    text = re.sub(r"[x×]\s*(\d+)", r"\1", text)
    return text


def _expand_order_ids(text: str) -> str:
    """ORD-20250306-0042 → 'order 42', KOT-20250306-0012 → 'K O T 12'."""
    text = re.sub(
        r"ORD-\d{8}-0*(\d+)",
        r"order \1",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"KOT-\d{8}-0*(\d+)",
        r"K O T \1",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _expand_small_numbers(text: str, language: str = "en") -> str:
    """Convert lone small quantities (1–20) to words in spoken context.
    Only for English — other languages let TTS read digits natively."""
    if language != "en":
        return text  # Hindi TTS reads "2" as "do", Gujarati as "be", etc.

    def _replace_num(m):
        n = int(m.group(0))
        if n in _NUM_WORDS:
            return _NUM_WORDS[n]
        return m.group(0)

    # Match standalone numbers 1–20 that aren't followed by 'rupees' or 'paise'
    text = re.sub(r"\b([1-9]|1[0-9]|20)\b(?!\s*(?:rupees|paise|rupee))", _replace_num, text)
    return text


def _expand_symbols(text: str) -> str:
    """%→'percent', &→'and'."""
    text = text.replace("%", " percent")
    text = text.replace("&", " and ")
    # Clean up double spaces
    text = re.sub(r"\s{2,}", " ", text)
    return text


def _expand_acronyms(text: str) -> str:
    """KOT → 'K O T', GST → 'G S T' etc."""
    for acr, expansion in _ACRONYMS.items():
        text = re.sub(rf"\b{acr}\b", expansion, text)
    return text


def _protect_menu_items(text: str, pipeline_result: dict) -> tuple[str, dict]:
    """Replace menu item names with placeholders before script conversion.
    Returns (text_with_placeholders, placeholder_map)."""
    placeholder_map = {}
    items = pipeline_result.get("items", [])
    # Also check session_items for accumulated cart
    session_items = pipeline_result.get("session_items") or []

    # Collect unique item names
    item_names = set()
    for item in items:
        name = item.get("item_name")
        if name:
            item_names.add(name)
    for item in session_items:
        name = item.get("item_name")
        if name:
            item_names.add(name)

    # Also protect upsell suggestion names
    for upsell in pipeline_result.get("upsell_suggestions", []):
        name = upsell.get("name") or upsell.get("suggestion_text")
        if name:
            item_names.add(name)

    # Sort by length (longest first) to prevent partial replacements
    sorted_names = sorted(item_names, key=len, reverse=True)

    for idx, name in enumerate(sorted_names):
        placeholder = f"__ITEM_{idx}__"
        if name in text:
            text = text.replace(name, placeholder)
            placeholder_map[placeholder] = name

    return text, placeholder_map


def _restore_menu_items(text: str, placeholder_map: dict) -> str:
    """Restore menu item names from placeholders."""
    for placeholder, name in placeholder_map.items():
        text = text.replace(placeholder, name)
    return text


def _convert_script(text: str, language: str) -> str:
    """Convert romanized text to native script for Indian languages.
    Uses indic-transliteration library."""
    target_script = _SCRIPT_MAP.get(language)
    if not target_script:
        return text

    try:
        from indic_transliteration import sanscript

        script_enum = getattr(sanscript, target_script, None)
        if script_enum is None:
            return text

        # Only transliterate if the text appears to be romanized
        # (i.e., mostly ASCII characters)
        ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
        if ascii_ratio < 0.5:
            # Already in native script
            return text

        return sanscript.transliterate(text, sanscript.ITRANS, script_enum)
    except ImportError:
        logger.warning("indic-transliteration not installed — skipping script conversion")
        return text
    except Exception as e:
        logger.warning(f"Script conversion failed for '{language}': {e}")
        return text


def _add_breathing_punctuation(text: str) -> str:
    """Add natural pauses for TTS.
    - Comma after opening acknowledgment
    - Period at end if not already punctuated
    """
    # Add comma after common opening phrases if none exists
    openers = [
        "Got it", "Perfect", "Done", "Sure", "Okay", "OK",
        "Ji haan", "Theek hai", "Bilkul", "Zaroor",
    ]
    for opener in openers:
        # Match opener at start followed by a space (no comma already)
        pattern = rf"^({re.escape(opener)})(\s)"
        text = re.sub(pattern, r"\1,\2", text, flags=re.IGNORECASE)

    # Ensure text ends with punctuation
    text = text.strip()
    if text and text[-1] not in ".!?।":
        text += "."

    return text


def normalize(text: str, language: str, pipeline_result: dict) -> str:
    """
    Main normalization entry point.

    Args:
        text: The spoken text to normalize (from LLM or template).
        language: Detected language code ("en", "hi", "gu", "mr", "kn").
        pipeline_result: Full pipeline result dict for menu item extraction.

    Returns:
        Normalized text ready for TTS engine input.
    """
    if not text:
        return text

    # Step 1: Currency expansion (before number conversion)
    text = _expand_currency(text)

    # Step 2: Quantity markers
    text = _expand_quantities(text)

    # Step 3: Order ID simplification
    text = _expand_order_ids(text)

    # Step 4: Symbols
    text = _expand_symbols(text)

    # Step 5: Acronyms
    text = _expand_acronyms(text)

    # Step 6: Small numbers to words (after currency so "340 rupees" stays)
    # Only for English — non-English TTS voices read digits natively
    text = _expand_small_numbers(text, language)

    # Step 7: Script conversion — DISABLED
    # Templates already output native scripts for gu/mr/kn and romanized
    # Hindi for hi. ITRANS conversion garbles casual romanized Hindi.
    # The TTS engine handles voice selection based on text script instead.

    # Step 8: Breathing punctuation
    text = _add_breathing_punctuation(text)

    return text.strip()
