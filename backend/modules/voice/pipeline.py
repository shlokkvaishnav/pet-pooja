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
from .session_store import get_session, update_session, get_session_items


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

    def process_text(self, text: str, session_id: str = None) -> dict:
        """Process text input (skips STT). For testing without audio."""
        return self._run_pipeline(text, original_transcript=text,
                                  detected_language="unknown",
                                  session_id=session_id)

    def process_audio(self, audio_path: str, session_id: str = None) -> dict:
        """Full pipeline: audio file -> structured order JSON."""
        stt_result = transcribe(audio_path)
        return self._run_pipeline(
            stt_result["transcript"],
            original_transcript=stt_result["transcript"],
            detected_language=stt_result["detected_language"],
            session_id=session_id,
        )

    def _run_pipeline(self, text, original_transcript, detected_language,
                      session_id=None):
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

        # Stage 8: Session state — accumulate items across turns
        if session_id:
            update_session(session_id, enriched_items, intent)
            session_items = get_session_items(session_id)
            session_context = get_session(session_id)
        else:
            session_items = enriched_items
            session_context = None

        # Flag clarification needed: no items found OR any item has low confidence
        disambiguation_items = []
        for item in enriched_items:
            if item.get("needs_disambiguation"):
                disambiguation_items.append({
                    "item_name": item["item_name"],
                    "confidence": item["confidence"],
                    "alternatives": item.get("alternatives", []),
                })

        needs_clarification = (
            (intent == "ORDER" and len(enriched_items) == 0)
            or len(disambiguation_items) > 0
        )

        return {
            "transcript": original_transcript,
            "normalized": normalized,
            "detected_language": detected_language,
            "intent": intent,
            "items": enriched_items,
            "upsell_suggestions": upsell_suggestions,
            "order": order,
            "needs_clarification": needs_clarification,
            "disambiguation": disambiguation_items,
            "session_id": session_id,
            "session_items": session_items if session_id else None,
            "turn_count": session_context["turn_count"] if session_context else 0,
        }

    def _enrich_with_menu_data(self, matched_items):
        """Adds name, price FROM DB to each matched item."""
        menu_map = {item.id: item for item in self.menu_items}
        enriched = []
        for match in matched_items:
            menu_item = menu_map.get(match["item_id"])
            if menu_item:
                # Enrich alternatives with menu data
                alternatives = []
                for alt in match.get("alternatives", []):
                    alt_item = menu_map.get(alt["item_id"])
                    if alt_item:
                        alternatives.append({
                            "item_id": alt["item_id"],
                            "item_name": alt_item.name,
                            "confidence": alt["confidence"],
                            "unit_price": alt_item.selling_price,
                        })

                enriched.append({
                    "item_id": match["item_id"],
                    "item_name": menu_item.name,
                    "quantity": match["quantity"],
                    "unit_price": menu_item.selling_price,
                    "line_total": match["quantity"] * menu_item.selling_price,
                    "modifiers": match["modifiers"],
                    "confidence": match["confidence"],
                    "needs_disambiguation": match.get("needs_disambiguation", False),
                    "alternatives": alternatives,
                })
        return enriched


# ---------------------------------------------------------------------------
# Convenience wrapper — used by Person D's routes_voice.py
# ---------------------------------------------------------------------------
def process_voice_order(db, audio_path: str = None, text_input: str = None,
                        session_id: str = None) -> dict:
    """
    Standalone function that creates a VoicePipeline on the fly from DB
    and processes either audio or text input.
    """
    from models import MenuItem
    menu_items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
    pipeline = VoicePipeline(db_session=db, menu_items=menu_items)

    if audio_path:
        return pipeline.process_audio(audio_path, session_id=session_id)
    elif text_input:
        return pipeline.process_text(text_input, session_id=session_id)
    else:
        return {"error": "No audio_path or text_input provided", "items": []}
