"""
pipeline.py — Voice Pipeline Orchestrator
============================================
Loads menu data FROM DB at startup -> builds dynamic search corpus.
No hardcoded menu items anywhere. All processing is local.
"""

import time
import uuid
import logging

logger = logging.getLogger("petpooja.voice.pipeline")

from .stt import transcribe, _redetect_language
from .normalizer import normalize
from .intent_mapper import classify_intent, classify_intents, is_cancel_all
from .item_matcher import build_search_corpus, extract_all_items, get_alternatives
from .quantity_extractor import extract_quantities_for_items
from .modifier_extractor import extract_modifiers, extract_modifiers_with_target
from .session_store import (
    get_session, update_session, update_session_compound, get_session_items,
    get_session_language, set_session_language,
)
from .voice_config import cfg
from . import pipeline_errors as errs

# LLM brain — hybrid enhancement layer (lazy import to avoid circular deps)
try:
    from .llm_brain import llm_brain
except ImportError:
    llm_brain = None


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
    def __init__(self, menu_items: list,
                 combo_rules: list = None, hidden_stars: list = None):
        """
        Loaded ONCE at app startup.

        menu_items: loaded FROM DATABASE -- this is what makes it dynamic.
        The search corpus is built from whatever is in the DB.
        Change the menu in DB -> pipeline auto-adapts.
        """
        self.menu_items = menu_items
        # DYNAMIC: corpus built from DB menu items, not hardcoded
        self.corpus = build_search_corpus(menu_items)
        self._menu_map = {item.id: item for item in menu_items}
        self.combo_rules = combo_rules or []
        self.hidden_stars = hidden_stars or []

    def refresh_menu(self, menu_items: list, *, corpus: list | None = None):
        """Refresh menu items and rebuild corpus/map without re-instantiating."""
        self.menu_items = menu_items
        self.corpus = corpus or build_search_corpus(menu_items)
        self._menu_map = {item.id: item for item in menu_items}

    def process_text(self, text: str, session_id: str = None,
                     restaurant_id: int = None) -> dict:
        """Process text input (skips STT). For testing without audio."""
        # Reset LLM brain call budget for this pipeline run
        if llm_brain is not None:
            llm_brain.reset_call_budget()

        session_lang = get_session_language(session_id) if session_id else None
        lang = _redetect_language(text, "unknown", 0.0, session_language=session_lang)
        return self._run_pipeline(text, original_transcript=text,
                                  detected_language=lang,
                                  session_id=session_id,
                                  restaurant_id=restaurant_id)

    def process_audio(self, audio_path: str, session_id: str = None,
                      language_hint: str = None, restaurant_id: int = None) -> dict:
        """Full pipeline: audio file -> structured order JSON."""
        t0 = time.perf_counter()

        # Reset LLM brain call budget for this pipeline run
        if llm_brain is not None:
            llm_brain.reset_call_budget()

        try:
            t_stt_start = time.perf_counter()
            stt_result = transcribe(audio_path, language_hint=language_hint)
            t_stt = time.perf_counter() - t_stt_start
            logger.info("⏱ STT completed in %.1fms", t_stt * 1000)
        except FileNotFoundError:
            sr = errs.stt_model_error("ffmpeg not found")
            return self._error_response(sr, session_id=session_id)
        except RuntimeError as e:
            sr = errs.stt_model_error(str(e))
            return self._error_response(sr, session_id=session_id)

        # Apply session language stickiness: re-detect with session hint
        # Skip if user explicitly chose a language — the hint already locked it in STT.
        if session_id and not language_hint:
            session_lang = get_session_language(session_id)
            if session_lang:
                transcript = stt_result.get("transcript", "").strip()
                whisper_lang = stt_result.get("whisper_raw_language", stt_result.get("detected_language", "unknown"))
                whisper_conf = stt_result.get("language_confidence", 0.0)
                refined_lang = _redetect_language(transcript, whisper_lang, whisper_conf, session_language=session_lang)
                if refined_lang != stt_result["detected_language"]:
                    logger.info("Session language override: %s → %s", stt_result["detected_language"], refined_lang)
                    stt_result["detected_language"] = refined_lang

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
            restaurant_id=restaurant_id,
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
                      vad_info=None, restaurant_id=None):
        t_pipeline_start = time.perf_counter()
        stage_results = []   # list of StageResult.to_dict()
        user_messages = []   # list of user-facing strings

        # Stage 2: Normalize
        normalized = normalize(text)

        # Stage 3: Compound intent classification
        intent_results = classify_intents(normalized)
        primary_intent, matched_pattern = classify_intent(normalized)
        is_compound = len(intent_results) > 1

        # Stage 3b: LLM brain fallback for UNKNOWN intents
        # If the regex classifier couldn't determine intent, ask the LLM
        if (primary_intent == "UNKNOWN"
                and llm_brain is not None and llm_brain.enabled):
            try:
                llm_intent = llm_brain.resolve_unknown_intent_sync(
                    normalized, menu_items=self.menu_items,
                )
                if llm_intent and llm_intent["intent"] != "UNKNOWN":
                    resolved_intent = llm_intent["intent"]
                    logger.info("LLM brain rescued UNKNOWN → %s", resolved_intent)
                    primary_intent = resolved_intent
                    matched_pattern = f"llm:{resolved_intent.lower()}"
                    # Re-classify all UNKNOWN clauses with the LLM result
                    for ir in intent_results:
                        if ir["intent"] == "UNKNOWN":
                            ir["intent"] = resolved_intent
                            ir["matched_pattern"] = matched_pattern
                    is_compound = len(set(ir["intent"] for ir in intent_results)) > 1
            except Exception as e:
                logger.debug("LLM brain intent fallback failed: %s", e)

        # Stage 4-5: Process each clause independently
        all_enriched_items = []
        intent_actions = []

        menu_map = self._menu_map

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

                enriched = self._enrich_with_menu_data(clause_with_mods, restaurant_id=restaurant_id)

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

                # Zero match handling — different for ORDER vs CANCEL
                if not enriched:
                    if clause_intent == "ORDER":
                        # ORDER with no match → try LLM brain recovery first
                        llm_recovered = []
                        if llm_brain is not None and llm_brain.enabled:
                            try:
                                llm_recovered = llm_brain.recover_items_sync(
                                    clause, self.menu_items, self.corpus,
                                )
                            except Exception as e:
                                logger.debug("LLM brain item recovery failed: %s", e)

                        if llm_recovered:
                            # Map LLM-recovered items back to real menu items via name
                            name_to_item = {
                                item.name.lower(): item
                                for item in self.menu_items if item.name
                            }
                            for lr in llm_recovered:
                                db_item = name_to_item.get(lr["name"].lower())
                                if db_item:
                                    # Filter by restaurant if needed
                                    if (restaurant_id is not None
                                            and getattr(db_item, 'restaurant_id', None) is not None
                                            and db_item.restaurant_id != restaurant_id):
                                        continue
                                    enriched.append({
                                        "item_id": db_item.id,
                                        "item_name": db_item.name,
                                        "quantity": lr["quantity"],
                                        "unit_price": db_item.selling_price,
                                        "line_total": lr["quantity"] * db_item.selling_price,
                                        "modifiers": {},
                                        "confidence": lr["confidence"],
                                        "needs_disambiguation": False,
                                        "alternatives": [],
                                        "source": lr.get("source", "llm_recovery"),
                                    })
                            if enriched:
                                logger.info("LLM brain recovered %d items from zero-match clause", len(enriched))

                        if not enriched:
                            # Still no match → suggest fuzzy alternatives
                            fuzzy_suggestions = getattr(extract_all_items, "_last_fuzzy_suggestions", [])
                            if not fuzzy_suggestions:
                                fuzzy_suggestions = get_alternatives(clause, self.corpus, top_n=3)
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
                    elif clause_intent == "CANCEL":
                        # CANCEL with no specific items
                        if is_cancel_all(clause):
                            # "cancel everything" / "hata do sab" → clear all
                            pass  # _apply_cancel(session, []) clears cart
                        else:
                            # "cancel the xyz" where xyz wasn't matched
                            # → don't clear cart, ask for clarification
                            sr = errs.StageResult(
                                status=errs.PARTIAL,
                                error_type="cancel_item_not_found",
                                user_message="Which item should I remove? Please say the item name.",
                            )
                            stage_results.append(sr.to_dict())
                            user_messages.append(sr.user_message)
                            # Mark this CANCEL as needing clarification so we
                            # don't accidentally clear the entire cart
                            clause_intent = "_CANCEL_NEEDS_CLARIFY"

                # Ambiguous match: try LLM disambiguation first, then prompt user
                session_items_for_disambig = get_session_items(session_id) if session_id else []
                for item in enriched:
                    if item.get("needs_disambiguation"):
                        alternatives = item.get("alternatives", [])
                        # Try LLM to auto-resolve before asking user
                        if (alternatives and llm_brain is not None and llm_brain.enabled):
                            try:
                                all_options = [{"item_name": item["item_name"],
                                                "unit_price": item["unit_price"]}] + alternatives
                                chosen = llm_brain.resolve_disambiguation_sync(
                                    clause, all_options, session_items_for_disambig,
                                )
                                if chosen:
                                    # Find the chosen item in menu and replace
                                    chosen_db = next(
                                        (m for m in self.menu_items if m.name == chosen), None
                                    )
                                    if chosen_db:
                                        item["item_id"] = chosen_db.id
                                        item["item_name"] = chosen_db.name
                                        item["unit_price"] = chosen_db.selling_price
                                        item["line_total"] = item["quantity"] * chosen_db.selling_price
                                        item["confidence"] = 0.90
                                        item["needs_disambiguation"] = False
                                        item["alternatives"] = []
                                        item["source"] = "llm_disambiguation"
                                        logger.info("LLM auto-resolved disambiguation → %s", chosen)
                                        continue  # skip adding error prompt
                            except Exception as e:
                                logger.debug("LLM disambiguation failed: %s", e)

                        # LLM couldn't resolve or not available → prompt user
                        sr = errs.ambiguous_match(item["item_name"], alternatives)
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
                    [{**i, "modifiers": {}} for i in clause_with_qty],
                    restaurant_id=restaurant_id,
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
                # For REPEAT, UNKNOWN, DONE, QUERY — try LLM context resolution
                # Handles "same again", "one more", "double it", etc.
                if (clause_intent in ("REPEAT", "UNKNOWN")
                        and llm_brain is not None and llm_brain.enabled
                        and session_id):
                    try:
                        session_items = get_session_items(session_id)
                        ctx = llm_brain.resolve_context_sync(
                            clause,
                            session_items=session_items,
                            prev_items=session_items,  # Use session items as context
                        )
                        if ctx and ctx.get("action") in ("add", "repeat"):
                            # Map resolved items to menu items and add them
                            name_to_item = {
                                m.name.lower(): m
                                for m in self.menu_items if m.name
                            }
                            resolved_enriched = []
                            for ci in ctx.get("items", []):
                                db_item = name_to_item.get(ci["name"].lower())
                                if db_item:
                                    if (restaurant_id is not None
                                            and getattr(db_item, 'restaurant_id', None) is not None
                                            and db_item.restaurant_id != restaurant_id):
                                        continue
                                    qty = ci.get("quantity", 1)
                                    resolved_enriched.append({
                                        "item_id": db_item.id,
                                        "item_name": db_item.name,
                                        "quantity": qty,
                                        "unit_price": db_item.selling_price,
                                        "line_total": qty * db_item.selling_price,
                                        "modifiers": {},
                                        "confidence": 0.85,
                                        "needs_disambiguation": False,
                                        "alternatives": [],
                                        "clause_intent": "ORDER",
                                        "clause": clause,
                                        "source": "llm_context",
                                    })
                            if resolved_enriched:
                                all_enriched_items.extend(resolved_enriched)
                                intent_actions.append({
                                    "intent": "ORDER",
                                    "items": resolved_enriched,
                                    "modifier_updates": [],
                                })
                                # Override the primary intent since we resolved it
                                if primary_intent in ("REPEAT", "UNKNOWN"):
                                    primary_intent = "ORDER"
                                logger.info("LLM context resolution: %s → ORDER with %d items",
                                            clause_intent, len(resolved_enriched))
                                continue  # Skip adding the empty intent action
                        elif ctx and ctx.get("action") == "confirm":
                            intent_actions.append({
                                "intent": "CONFIRM",
                                "items": [],
                                "modifier_updates": [],
                            })
                            if primary_intent in ("REPEAT", "UNKNOWN"):
                                primary_intent = "CONFIRM"
                            continue
                    except Exception as e:
                        logger.debug("LLM context resolution failed: %s", e)

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
            # Store detected language for session stickiness
            set_session_language(session_id, detected_language)
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

        # Build a session-wide order from all accumulated items
        session_order = None
        if session_id and session_items:
            # Normalize items: ensure "name" key exists for generate_kot/save_order_to_db
            normalized_items = []
            for si in session_items:
                item_copy = dict(si)
                if "name" not in item_copy and "item_name" in item_copy:
                    item_copy["name"] = item_copy["item_name"]
                normalized_items.append(item_copy)

            s_subtotal = sum(i.get("line_total", 0) for i in normalized_items)
            session_order = {
                "order_id": session_id,
                "items": normalized_items,
                "item_count": len(normalized_items),
                "total_quantity": sum(i.get("quantity", 1) for i in normalized_items),
                "subtotal": round(s_subtotal, 2),
                "tax": round(s_subtotal * cfg.ORDER_TAX_RATE, 2),
                "total": round(s_subtotal * (1 + cfg.ORDER_TAX_RATE), 2),
                "order_type": "dine_in",
                "table_number": None,
                "status": "building",
            }

        # Deduplicate user messages while preserving order
        seen_msgs = set()
        unique_messages = []
        for msg in user_messages:
            if msg and msg not in seen_msgs:
                seen_msgs.add(msg)
                unique_messages.append(msg)

        t_nlp = time.perf_counter() - t_pipeline_start
        logger.info("⏱ NLP pipeline completed in %.1fms (intent=%s, items=%d)",
                     t_nlp * 1000, primary_intent, len(all_enriched_items))

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
            "session_order": session_order,
            "needs_clarification": needs_clarification,
            "disambiguation": disambiguation_items,
            "session_id": session_id,
            "session_items": session_items if session_id else None,
            "turn_count": session_context["turn_count"] if session_context else 0,
            "transcription_confidence": transcription_confidence,
            "vad_info": vad_info,
            "stage_results": stage_results,
            "user_messages": unique_messages,
            "timing_ms": round(t_nlp * 1000, 1),
        }

    def _enrich_with_menu_data(self, matched_items, restaurant_id: int = None):
        """Adds name, price FROM DB to each matched item.
        If restaurant_id is given, only items belonging to that restaurant are kept."""
        menu_map = self._menu_map
        enriched = []
        for match in matched_items:
            menu_item = menu_map.get(match["item_id"])
            if not menu_item:
                continue
            # Skip items not belonging to the current restaurant
            if restaurant_id is not None and getattr(menu_item, 'restaurant_id', None) is not None:
                if menu_item.restaurant_id != restaurant_id:
                    continue

            # Enrich alternatives with menu data (also filtered by restaurant)
            alternatives = []
            for alt in match.get("alternatives", []):
                alt_item = menu_map.get(alt["item_id"])
                if not alt_item:
                    continue
                if restaurant_id is not None and getattr(alt_item, 'restaurant_id', None) is not None:
                    if alt_item.restaurant_id != restaurant_id:
                        continue
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
    pipeline = VoicePipeline(menu_items=menu_items)

    if audio_path:
        return pipeline.process_audio(audio_path, session_id=session_id)
    elif text_input:
        return pipeline.process_text(text_input, session_id=session_id)
    else:
        return {"error": "No audio_path or text_input provided", "items": []}
