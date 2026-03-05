"""
pipeline.py — Voice Pipeline Orchestrator
============================================
Loads menu data FROM DB at startup -> builds dynamic search corpus.
No hardcoded menu items anywhere. All processing is local.
"""

import uuid

from .stt import transcribe
from .normalizer import normalize
from .intent_mapper import classify_intent
from .item_matcher import build_search_corpus, extract_all_items
from .quantity_extractor import extract_quantities_for_items
from .modifier_extractor import extract_modifiers


# -- Stub functions for D's files (until D delivers them) --
def _stub_get_upsell_suggestions(*args, **kwargs):
    return []


def _stub_build_order(parsed_items, upsells_shown):
    subtotal = sum(i.get("line_total", 0) for i in parsed_items)
    return {
        "order_id": str(uuid.uuid4()),
        "items": parsed_items,
        "upsells_shown": upsells_shown,
        "subtotal": subtotal,
        "status": "pending",
    }


# Try importing D's real modules; fall back to stubs
try:
    from .upsell_engine import get_upsell_suggestions
except (ImportError, Exception):
    get_upsell_suggestions = _stub_get_upsell_suggestions

try:
    from .order_builder import build_order
except (ImportError, Exception):
    build_order = _stub_build_order


class VoicePipeline:
    def __init__(self, db_session, menu_items: list,
                 combo_rules: list = None, hidden_stars: list = None):
        """
        Loaded ONCE at app startup.

        menu_items: loaded FROM DATABASE -- this is what makes it dynamic.
        The search corpus is built from whatever is in the DB.
        Change the menu in DB -> pipeline auto-adapts.
        """
        self.db = db_session
        self.menu_items = menu_items
        # DYNAMIC: corpus built from DB menu items, not hardcoded
        self.corpus = build_search_corpus(menu_items)
        self.combo_rules = combo_rules or []
        self.hidden_stars = hidden_stars or []

    def process_text(self, text: str) -> dict:
        """Process text input (skips STT). For testing without audio."""
        return self._run_pipeline(text, original_transcript=text,
                                  detected_language="unknown")

    def process_audio(self, audio_path: str) -> dict:
        """Full pipeline: audio file -> structured order JSON."""
        stt_result = transcribe(audio_path)
        return self._run_pipeline(
            stt_result["transcript"],
            original_transcript=stt_result["transcript"],
            detected_language=stt_result["detected_language"],
        )

    def _run_pipeline(self, text, original_transcript, detected_language):
        # Stage 2: Normalize
        normalized = normalize(text)

        # Stage 3: Intent
        intent, matched_pattern = classify_intent(normalized)

        # Stage 4: Match items DYNAMICALLY against DB corpus
        matched_items = extract_all_items(normalized, self.corpus)

        # Stage 5: Quantities + Modifiers
        items_with_qty = extract_quantities_for_items(normalized, matched_items)

        items_with_modifiers = []
        for item in items_with_qty:
            # DYNAMIC: modifier cross-check uses DB item data
            mods = extract_modifiers(normalized, item["item_id"], self.menu_items)
            items_with_modifiers.append({**item, "modifiers": mods})

        # Enrich with menu data from DB (name, price)
        enriched_items = self._enrich_with_menu_data(items_with_modifiers)

        # Stage 6: Upsell (D's file)
        upsell_suggestions = []
        if enriched_items:
            try:
                upsell_suggestions = get_upsell_suggestions(
                    current_order_items=enriched_items,
                    menu_data=self.menu_items,
                    combo_rules=self.combo_rules,
                    hidden_stars=self.hidden_stars,
                )
            except Exception:
                upsell_suggestions = []

        # Stage 7: Build Order (D's file)
        order = None
        if enriched_items:
            try:
                order = build_order(enriched_items, upsell_suggestions)
            except Exception:
                order = _stub_build_order(enriched_items, upsell_suggestions)

        needs_clarification = (intent == "ORDER" and len(enriched_items) == 0)

        return {
            "transcript": original_transcript,
            "normalized": normalized,
            "detected_language": detected_language,
            "intent": intent,
            "items": enriched_items,
            "upsell_suggestions": upsell_suggestions,
            "order": order,
            "needs_clarification": needs_clarification,
        }

    def _enrich_with_menu_data(self, matched_items):
        """Adds name, price FROM DB to each matched item."""
        menu_map = {item.id: item for item in self.menu_items}
        enriched = []
        for match in matched_items:
            menu_item = menu_map.get(match["item_id"])
            if menu_item:
                enriched.append({
                    "item_id": match["item_id"],
                    "item_name": menu_item.name,
                    "quantity": match["quantity"],
                    "unit_price": menu_item.selling_price,
                    "line_total": match["quantity"] * menu_item.selling_price,
                    "modifiers": match["modifiers"],
                    "confidence": match["confidence"],
                })
        return enriched
