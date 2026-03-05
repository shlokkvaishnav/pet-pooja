"""
pipeline.py — Voice Pipeline Orchestrator
============================================
Loads menu data FROM DB at startup -> builds dynamic search corpus.
No hardcoded menu items anywhere. All processing is local.
"""

import uuid
import logging

logger = logging.getLogger("petpooja.voice.pipeline")

from .stt import transcribe
from .normalizer import normalize
from .intent_mapper import classify_intent, classify_intents
from .item_matcher import build_search_corpus, extract_all_items, get_alternatives
from .quantity_extractor import extract_quantities_for_items
from .modifier_extractor import extract_modifiers, extract_modifiers_with_target
from .session_store import (
    get_session, update_session, update_session_compound, get_session_items,
)
from . import pipeline_errors as errs


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
        try:
            stt_result = transcribe(audio_path)
        except FileNotFoundError:
            sr = errs.stt_model_error("ffmpeg not found")
            return self._error_response(sr, session_id=session_id)
        except RuntimeError as e:
            sr = errs.stt_model_error(str(e))
            return self._error_response(sr, session_id=session_id)

        # Hard-abort only when there's truly nothing to work with
        # (no speech detected or completely empty transcript).
        # For "below_threshold" confidence, still attempt item extraction —
        # accented / mixed-language audio often has low avg_logprob
        # but produces a perfectly usable transcript.
        if stt_result.get("is_low_confidence"):
            reason = stt_result.get("low_confidence_reason", "unknown")
            if reason in ("no_speech_detected", "empty_transcript"):
                sr = (errs.stt_no_speech() if reason == "no_speech_detected"
                      else errs.stt_too_short())
                return self._error_response(
                    sr, session_id=session_id,
                    transcript=stt_result.get("transcript", ""),
                    detected_language=stt_result.get("detected_language", "unknown"),
                    transcription_confidence=stt_result.get("transcription_confidence", 0.0),
                    vad_info=stt_result.get("vad_info"),
                )
            # below_threshold — proceed with extraction, flag advisory
            logger.info(
                "Low STT confidence (%.2f) — proceeding with extraction anyway",
                stt_result.get("transcription_confidence", 0.0),
            )

        return self._run_pipeline(
            stt_result["transcript"],
            original_transcript=stt_result["transcript"],
            detected_language=stt_result["detected_language"],
            session_id=session_id,
            transcription_confidence=stt_result.get("transcription_confidence"),
            vad_info=stt_result.get("vad_info"),
        )

    def _error_response(self, stage_result: errs.StageResult, *,
                        session_id=None, transcript="",
                        detected_language="unknown",
                        transcription_confidence=0.0,
                        vad_info=None) -> dict:
        """Build a full pipeline response dict from a failed StageResult."""
        return {
            "transcript": transcript,
            "normalized": "",
            "detected_language": detected_language,
            "intent": "UNCLEAR",
            "intents": [],
            "is_compound": False,
            "items": [],
            "upsell_suggestions": [],
            "order": None,
            "needs_clarification": True,
            "disambiguation": [],
            "session_id": session_id,
            "session_items": get_session_items(session_id) if session_id else None,
            "turn_count": (get_session(session_id) or {}).get("turn_count", 0) if session_id else 0,
            "transcription_confidence": transcription_confidence,
            "vad_info": vad_info,
            "stage_results": [stage_result.to_dict()],
            "user_messages": [stage_result.user_message] if stage_result.user_message else [],
        }

    def _run_pipeline(self, text, original_transcript, detected_language,
                      session_id=None, transcription_confidence=None,
                      vad_info=None):
        stage_results = []   # list of StageResult.to_dict()
        user_messages = []   # list of user-facing strings

        # Stage 2: Normalize
        normalized = normalize(text)

        # Stage 3: Compound intent classification
        intent_results = classify_intents(normalized)
        primary_intent, matched_pattern = classify_intent(normalized)
        is_compound = len(intent_results) > 1

        # Stage 4-5: Process each clause independently
        all_enriched_items = []
        intent_actions = []

        menu_map = {item.id: item for item in self.menu_items}

        for ir in intent_results:
            clause = ir["clause"]
            clause_intent = ir["intent"]

            if clause_intent in ("ORDER", "CANCEL"):
                clause_matched = extract_all_items(clause, self.corpus)
                clause_with_qty = extract_quantities_for_items(clause, clause_matched)

                clause_with_mods = []
                for item in clause_with_qty:
                    mods = extract_modifiers(clause, item["item_id"], self.menu_items)
                    # Collect modifier warnings
                    for w in mods.get("warnings", []):
                        sr = errs.modifier_unsupported(w["modifier"], w["item_name"])
                        stage_results.append(sr.to_dict())
                        user_messages.append(sr.user_message)
                    clause_with_mods.append({**item, "modifiers": mods})

                enriched = self._enrich_with_menu_data(clause_with_mods)

                # Check stock availability for ORDER items
                if clause_intent == "ORDER":
                    for item in enriched:
                        db_item = menu_map.get(item["item_id"])
                        if db_item and not db_item.is_available:
                            sr = errs.item_out_of_stock(item["item_name"], item["item_id"])
                            stage_results.append(sr.to_dict())
                            user_messages.append(sr.user_message)
                            item["out_of_stock"] = True
                        elif db_item and db_item.current_stock is not None and db_item.current_stock < item.get("quantity", 1):
                            sr = errs.item_out_of_stock(item["item_name"], item["item_id"])
                            stage_results.append(sr.to_dict())
                            user_messages.append(sr.user_message)
                            item["out_of_stock"] = True

                # Zero match: generate recovery suggestions
                if clause_intent == "ORDER" and not enriched:
                    fuzzy_suggestions = getattr(extract_all_items, "_last_fuzzy_suggestions", [])
                    if not fuzzy_suggestions:
                        fuzzy_suggestions = get_alternatives(clause, self.corpus, top_n=3)
                    # Enrich suggestions with item names from DB
                    enriched_suggestions = []
                    for s in fuzzy_suggestions:
                        db_item = menu_map.get(s["item_id"])
                        enriched_suggestions.append({
                            **s,
                            "item_name": db_item.name if db_item else s.get("matched_as", "?"),
                        })
                    sr = errs.zero_item_matches(clause, enriched_suggestions)
                    stage_results.append(sr.to_dict())
                    user_messages.append(sr.user_message)

                # Ambiguous match: generate active prompts
                for item in enriched:
                    if item.get("needs_disambiguation"):
                        sr = errs.ambiguous_match(item["item_name"], item.get("alternatives", []))
                        stage_results.append(sr.to_dict())
                        user_messages.append(sr.user_message)

                for item in enriched:
                    item["clause_intent"] = clause_intent
                    item["clause"] = clause

                all_enriched_items.extend(enriched)
                intent_actions.append({
                    "intent": clause_intent,
                    "items": enriched,
                    "modifier_updates": [],
                })

            elif clause_intent == "MODIFY":
                session_items = get_session_items(session_id) if session_id else []
                clause_matched = extract_all_items(clause, self.corpus)
                clause_with_qty = extract_quantities_for_items(clause, clause_matched)
                clause_items = self._enrich_with_menu_data(
                    [{**i, "modifiers": {}} for i in clause_with_qty]
                )

                modifier_updates = extract_modifiers_with_target(
                    clause=clause,
                    matched_items=clause_items,
                    menu_items=self.menu_items,
                    session_items=session_items,
                )

                # Collect modifier warnings from targeted extraction
                for mu in modifier_updates:
                    for w in mu.get("modifiers", {}).get("warnings", []):
                        sr = errs.modifier_unsupported(w["modifier"], w.get("item_name", mu.get("item_name", "this item")))
                        stage_results.append(sr.to_dict())
                        user_messages.append(sr.user_message)
                    mu["clause_intent"] = "MODIFY"
                    mu["clause"] = clause

                intent_actions.append({
                    "intent": "MODIFY",
                    "items": [],
                    "modifier_updates": modifier_updates,
                })

            elif clause_intent == "CONFIRM":
                intent_actions.append({
                    "intent": "CONFIRM",
                    "items": [],
                    "modifier_updates": [],
                })

            else:
                intent_actions.append({
                    "intent": clause_intent,
                    "items": [],
                    "modifier_updates": [],
                })

        # Items from ORDER clauses only (for upsell + order building)
        order_items = [i for i in all_enriched_items
                       if i.get("clause_intent") == "ORDER" and not i.get("out_of_stock")]

        # Stage 6: Upsell (D's file)
        upsell_suggestions = []
        if order_items:
            try:
                upsell_suggestions = get_upsell_suggestions(
                    current_order_items=order_items,
                    menu_data=self.menu_items,
                    combo_rules=self.combo_rules,
                    hidden_stars=self.hidden_stars,
                )
            except Exception:
                upsell_suggestions = []

        # Stage 7: Build Order (D's file)
        order = None
        if order_items:
            try:
                order = build_order(order_items, upsell_suggestions)
            except Exception:
                order = _stub_build_order(order_items, upsell_suggestions)

        # Stage 8: Session state
        if session_id:
            if is_compound:
                update_session_compound(session_id, intent_actions)
            else:
                update_session(session_id, all_enriched_items, primary_intent)
            session_items = get_session_items(session_id)
            session_context = get_session(session_id)
        else:
            session_items = all_enriched_items
            session_context = None

        # Flag clarification needed
        disambiguation_items = []
        for item in all_enriched_items:
            if item.get("needs_disambiguation"):
                disambiguation_items.append({
                    "item_name": item["item_name"],
                    "confidence": item["confidence"],
                    "alternatives": item.get("alternatives", []),
                })

        needs_clarification = (
            (primary_intent == "ORDER" and len(order_items) == 0)
            or len(disambiguation_items) > 0
            or any(sr.get("status") == "failure" for sr in stage_results)
        )

        # Deduplicate user messages while preserving order
        seen_msgs = set()
        unique_messages = []
        for msg in user_messages:
            if msg and msg not in seen_msgs:
                seen_msgs.add(msg)
                unique_messages.append(msg)

        return {
            "transcript": original_transcript,
            "normalized": normalized,
            "detected_language": detected_language,
            "intent": primary_intent,
            "intents": [
                {"intent": ir["intent"], "clause": ir["clause"]}
                for ir in intent_results
            ],
            "is_compound": is_compound,
            "items": all_enriched_items,
            "upsell_suggestions": upsell_suggestions,
            "order": order,
            "needs_clarification": needs_clarification,
            "disambiguation": disambiguation_items,
            "session_id": session_id,
            "session_items": session_items if session_id else None,
            "turn_count": session_context["turn_count"] if session_context else 0,
            "transcription_confidence": transcription_confidence,
            "vad_info": vad_info,
            "stage_results": stage_results,
            "user_messages": unique_messages,
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
