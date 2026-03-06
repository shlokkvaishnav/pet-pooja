"""
llm_brain.py — LLM-Enhanced NLP Layer (Hybrid Pipeline Brain)
===============================================================
Uses the existing Ollama/Qwen LLM as a second-pass processor
to handle cases where the rule-based pipeline (FAISS + regex) is
uncertain or fails.

This module does NOT replace the existing pipeline — it enhances it.
The fast rule-based system handles 80%+ of orders accurately. The LLM
kicks in ONLY for edge cases:

  1. UNKNOWN intent       → LLM classifies the intent
  2. Zero item matches    → LLM interprets what the user meant
  3. Disambiguation       → LLM picks the right item from alternatives
  4. Conversational refs  → LLM resolves "same again", "one more", "make it two"

Architecture:
  Rule-based (fast, 50-100ms) → falls back to LLM (slower, 500-2000ms) when uncertain.
  LLM output is POST-PROCESSED through FAISS to map names back to menu item IDs.

Usage:
    from modules.voice.llm_brain import llm_brain
    result = await llm_brain.resolve_unknown_intent(transcript, menu_items, session_items)
"""

import json
import logging
import re
from typing import Optional

import httpx

from .voice_config import cfg

logger = logging.getLogger("petpooja.voice.llm_brain")

# ── Prompts ──────────────────────────────────────────────────────

_INTENT_PROMPT = """\
You are a restaurant voice ordering assistant. Classify the customer's intent.

The customer said: "{transcript}"

Classify as EXACTLY one of:
- ORDER: customer wants to add items to their cart
- CANCEL: customer wants to remove items
- MODIFY: customer wants to change something about existing items (spice, size, etc.)
- CONFIRM: customer wants to finalize/place the order
- DONE: customer says they're finished ordering (but not yet confirming)
- QUERY: customer is asking a question about the menu
- REPEAT: customer wants the same thing again
- UNKNOWN: truly cannot determine intent

Also extract any item names or food references mentioned.

Respond ONLY in this JSON format, nothing else:
{{"intent": "ORDER", "items": ["butter naan", "dal makhani"], "reasoning": "brief reason"}}
"""

_ITEM_RECOVERY_PROMPT = """\
You are a restaurant voice ordering assistant. The speech recognition produced
this transcript but our menu search couldn't find matching items.

Transcript: "{transcript}"
Restaurant menu items: {menu_names}

The customer likely ordered food items. Extract what they probably said,
correcting for speech recognition errors and Hinglish/Hindi pronunciation.

Common issues:
- "chikan" = chicken, "pnr" = paneer, "naan" = naan, "biryani" variants
- Hindi food terms spoken in English or vice versa
- Whisper mis-transcribing accented speech

Respond ONLY in this JSON format:
{{"items": [{{"name": "closest menu item name", "quantity": 1, "confidence": 0.9}}], "reasoning": "brief explanation"}}

If you genuinely cannot find any food items in the transcript, return:
{{"items": [], "reasoning": "no food items detected"}}
"""

_DISAMBIGUATION_PROMPT = """\
You are a restaurant voice ordering assistant. The customer said something
that matches multiple menu items. Help pick the right one.

Customer said: "{transcript}"
Possible matches:
{alternatives}

Current cart: {cart_summary}

Based on the context and what the customer said, which item did they most likely mean?

Respond ONLY in this JSON format:
{{"chosen_item": "exact item name from the list", "reasoning": "brief reason"}}
"""

_CONTEXT_RESOLUTION_PROMPT = """\
You are a restaurant voice ordering assistant. The customer used a conversational
reference that needs context resolution.

Customer said: "{transcript}"
Current cart items: {cart_summary}
Previous turn items: {prev_items}

Resolve what the customer meant. Examples:
- "same again" / "wahi" = repeat last order
- "one more" / "ek aur" = add another of the last item
- "make it two" / "do kar do" = change quantity of last item to 2
- "double it" = double the quantity
- "that's fine" / "theek hai" = confirm

Respond ONLY in this JSON format:
{{"action": "add|modify_qty|repeat|confirm|unclear", "items": [{{"name": "item name", "quantity": 1}}], "reasoning": "brief reason"}}
"""


class LLMBrain:
    """Singleton LLM-enhanced NLP processor for edge cases.

    Performance notes:
    - Uses a persistent httpx client (no connection overhead per call)
    - Each pipeline run gets a "call budget" (cfg.LLM_BRAIN_MAX_CALLS)
      to prevent sequential LLM call chains from blowing up latency
    - Tighter timeout (cfg.LLM_BRAIN_TIMEOUT_SEC) than the response LLM
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._sync_client: Optional[httpx.Client] = None
            inst._async_client: Optional[httpx.AsyncClient] = None
            inst._call_budget = 0  # reset per pipeline run
            cls._instance = inst
        return cls._instance

    @property
    def enabled(self) -> bool:
        return cfg.LLM_ENABLED

    # ── Call budget management (reset by pipeline per run) ────────

    def reset_call_budget(self):
        """Reset the call budget at the start of each pipeline run."""
        self._call_budget = 0

    def _budget_ok(self) -> bool:
        """Check if we can still make LLM calls this pipeline run."""
        return self._call_budget < cfg.LLM_BRAIN_MAX_CALLS

    def _use_budget(self):
        self._call_budget += 1

    # ── Persistent HTTP clients ───────────────────────────────────

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                timeout=cfg.LLM_BRAIN_TIMEOUT_SEC + 0.5,
                limits=httpx.Limits(max_connections=2),
            )
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                timeout=cfg.LLM_BRAIN_TIMEOUT_SEC + 0.5,
                limits=httpx.Limits(max_connections=2),
            )
        return self._async_client

    async def _call_llm(self, prompt: str, max_tokens: int = None) -> Optional[dict]:
        """Call Ollama LLM and parse JSON response (async). Returns None on failure."""
        if not self.enabled or not self._budget_ok():
            return None
        self._use_budget()
        if max_tokens is None:
            max_tokens = cfg.LLM_BRAIN_MAX_TOKENS

        try:
            client = self._get_async_client()
            resp = await client.post(
                f"{cfg.LLM_BASE_URL}/api/generate",
                json=self._llm_payload(prompt, max_tokens),
            )
            resp.raise_for_status()
            return self._parse_llm_response(resp.json())

        except httpx.TimeoutException:
            logger.debug("LLM brain timed out (%.1fs)", cfg.LLM_BRAIN_TIMEOUT_SEC)
            return None
        except json.JSONDecodeError as e:
            logger.debug("LLM brain returned invalid JSON: %s", e)
            return None
        except Exception as e:
            logger.debug("LLM brain call failed: %s", e)
            return None

    def _call_llm_sync(self, prompt: str, max_tokens: int = None) -> Optional[dict]:
        """Call Ollama LLM and parse JSON response (sync). Returns None on failure."""
        if not self.enabled or not self._budget_ok():
            return None
        self._use_budget()
        if max_tokens is None:
            max_tokens = cfg.LLM_BRAIN_MAX_TOKENS

        try:
            client = self._get_sync_client()
            resp = client.post(
                f"{cfg.LLM_BASE_URL}/api/generate",
                json=self._llm_payload(prompt, max_tokens),
            )
            resp.raise_for_status()
            return self._parse_llm_response(resp.json())

        except httpx.TimeoutException:
            logger.debug("LLM brain timed out (%.1fs)", cfg.LLM_BRAIN_TIMEOUT_SEC)
            return None
        except json.JSONDecodeError as e:
            logger.debug("LLM brain returned invalid JSON: %s", e)
            return None
        except Exception as e:
            logger.debug("LLM brain call failed: %s", e)
            return None

    @staticmethod
    def _llm_payload(prompt: str, max_tokens: int) -> dict:
        return {
            "model": cfg.LLM_MODEL,
            "prompt": prompt,
            "system": (
                "You are a precise JSON-only responder. "
                "Output ONLY valid JSON. No explanations, no markdown, no extra text. "
                "Support English, Hindi, Hinglish, Gujarati, Marathi, Kannada."
            ),
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": max_tokens,
            },
        }

    @staticmethod
    def _parse_llm_response(data: dict) -> Optional[dict]:
        raw = data.get("response", "").strip()
        # Strip markdown code fences if LLM wraps in ```json
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    # ── 1. Intent Classification Fallback ────────────────────────

    async def resolve_unknown_intent(
        self,
        transcript: str,
        menu_items: list = None,
    ) -> Optional[dict]:
        """
        When regex intent classifier returns UNKNOWN, ask the LLM.

        Returns: {"intent": str, "items": [str], "reasoning": str} or None
        """
        prompt = _INTENT_PROMPT.format(transcript=transcript)
        result = await self._call_llm(prompt)
        return self._validate_intent_result(result)

    def resolve_unknown_intent_sync(
        self,
        transcript: str,
        menu_items: list = None,
    ) -> Optional[dict]:
        """Sync version of resolve_unknown_intent."""
        prompt = _INTENT_PROMPT.format(transcript=transcript)
        result = self._call_llm_sync(prompt)
        return self._validate_intent_result(result)

    @staticmethod
    def _validate_intent_result(result: Optional[dict]) -> Optional[dict]:
        if result and "intent" in result:
            intent = result["intent"].upper()
            valid_intents = {"ORDER", "CANCEL", "MODIFY", "CONFIRM", "DONE", "QUERY", "REPEAT", "UNKNOWN"}
            if intent in valid_intents:
                result["intent"] = intent
                logger.info("LLM brain resolved UNKNOWN intent → %s (reason: %s)",
                            intent, result.get("reasoning", ""))
                return result
        return None

    # ── 2. Zero-Match Item Recovery ──────────────────────────────

    async def recover_items(
        self,
        transcript: str,
        menu_items: list,
        corpus: dict,
    ) -> list[dict]:
        """
        When FAISS finds zero matches, ask the LLM to interpret the transcript
        and map it to actual menu items.

        Returns list of {"name": str, "quantity": int, "confidence": float}
        with name being a menu item name, or empty list.
        """
        menu_names = list({item.name for item in menu_items if item.name})
        if len(menu_names) > 80:
            menu_names = menu_names[:80]

        prompt = _ITEM_RECOVERY_PROMPT.format(
            transcript=transcript,
            menu_names=json.dumps(menu_names, ensure_ascii=False),
        )

        result = await self._call_llm(prompt, max_tokens=200)
        return self._validate_recovered_items(result, menu_names)

    def recover_items_sync(
        self,
        transcript: str,
        menu_items: list,
        corpus: dict,
    ) -> list[dict]:
        """Sync version of recover_items."""
        menu_names = list({item.name for item in menu_items if item.name})
        if len(menu_names) > 80:
            menu_names = menu_names[:80]

        prompt = _ITEM_RECOVERY_PROMPT.format(
            transcript=transcript,
            menu_names=json.dumps(menu_names, ensure_ascii=False),
        )

        result = self._call_llm_sync(prompt, max_tokens=200)
        return self._validate_recovered_items(result, menu_names)

    @staticmethod
    def _validate_recovered_items(result: Optional[dict], menu_names: list) -> list[dict]:
        if not result or not result.get("items"):
            return []

        menu_name_lower = {name.lower(): name for name in menu_names}
        validated = []
        for item in result["items"]:
            name = item.get("name", "").strip()
            qty = item.get("quantity", 1)
            conf = item.get("confidence", 0.7)

            # Try exact match first
            if name.lower() in menu_name_lower:
                validated.append({
                    "name": menu_name_lower[name.lower()],
                    "quantity": max(1, min(qty, 50)),
                    "confidence": min(conf, 0.95),
                    "source": "llm_recovery",
                })
            else:
                # Try substring match
                for mn_lower, mn_original in menu_name_lower.items():
                    if name.lower() in mn_lower or mn_lower in name.lower():
                        validated.append({
                            "name": mn_original,
                            "quantity": max(1, min(qty, 50)),
                            "confidence": min(conf * 0.85, 0.85),
                            "source": "llm_recovery_fuzzy",
                        })
                        break

        if validated:
            logger.info("LLM brain recovered %d items: %s (reason: %s)",
                        len(validated),
                        [v["name"] for v in validated],
                        result.get("reasoning", ""))

        return validated

    # ── 3. Disambiguation Resolution ─────────────────────────────

    async def resolve_disambiguation(
        self,
        transcript: str,
        alternatives: list[dict],
        session_items: list = None,
    ) -> Optional[str]:
        """
        When FAISS returns multiple close matches, ask LLM to pick the right one.

        Returns the chosen item name, or None.
        """
        alt_text, cart_summary = self._format_disambiguation_context(alternatives, session_items)
        prompt = _DISAMBIGUATION_PROMPT.format(
            transcript=transcript,
            alternatives=alt_text,
            cart_summary=cart_summary,
        )
        result = await self._call_llm(prompt)
        return self._validate_disambiguation_result(result, alternatives)

    def resolve_disambiguation_sync(
        self,
        transcript: str,
        alternatives: list[dict],
        session_items: list = None,
    ) -> Optional[str]:
        """Sync version of resolve_disambiguation."""
        alt_text, cart_summary = self._format_disambiguation_context(alternatives, session_items)
        prompt = _DISAMBIGUATION_PROMPT.format(
            transcript=transcript,
            alternatives=alt_text,
            cart_summary=cart_summary,
        )
        result = self._call_llm_sync(prompt)
        return self._validate_disambiguation_result(result, alternatives)

    @staticmethod
    def _format_disambiguation_context(alternatives, session_items):
        alt_text = "\n".join(
            f"- {a.get('item_name', a.get('name', '?'))} (Rs {a.get('unit_price', '?')})"
            for a in alternatives
        )
        cart_summary = "empty"
        if session_items:
            cart_summary = ", ".join(
                f"{s.get('quantity', 1)}x {s.get('item_name', s.get('name', '?'))}"
                for s in session_items
            )
        return alt_text, cart_summary

    @staticmethod
    def _validate_disambiguation_result(result, alternatives) -> Optional[str]:
        if not result or not result.get("chosen_item"):
            return None
        chosen = result["chosen_item"]
        alt_names = {
            a.get("item_name", a.get("name", "")).lower(): a.get("item_name", a.get("name"))
            for a in alternatives
        }
        if chosen.lower() in alt_names:
            logger.info("LLM brain resolved disambiguation → '%s' (reason: %s)",
                        chosen, result.get("reasoning", ""))
            return alt_names[chosen.lower()]
        # Fallback: partial match
        for name_lower, name_original in alt_names.items():
            if chosen.lower() in name_lower or name_lower in chosen.lower():
                logger.info("LLM brain resolved disambiguation (partial) → '%s'", name_original)
                return name_original
        return None

    # ── 4. Conversational Context Resolution ─────────────────────

    async def resolve_context(
        self,
        transcript: str,
        session_items: list = None,
        prev_items: list = None,
    ) -> Optional[dict]:
        """
        Resolve conversational references like "same again", "one more",
        "make it two", "double it".

        Returns: {"action": str, "items": [{"name": str, "quantity": int}]} or None
        """
        cart_summary, prev_summary = self._format_context_summaries(session_items, prev_items)
        prompt = _CONTEXT_RESOLUTION_PROMPT.format(
            transcript=transcript,
            cart_summary=cart_summary,
            prev_items=prev_summary,
        )
        result = await self._call_llm(prompt)
        return self._validate_context_result(result)

    def resolve_context_sync(
        self,
        transcript: str,
        session_items: list = None,
        prev_items: list = None,
    ) -> Optional[dict]:
        """Sync version of resolve_context."""
        cart_summary, prev_summary = self._format_context_summaries(session_items, prev_items)
        prompt = _CONTEXT_RESOLUTION_PROMPT.format(
            transcript=transcript,
            cart_summary=cart_summary,
            prev_items=prev_summary,
        )
        result = self._call_llm_sync(prompt)
        return self._validate_context_result(result)

    @staticmethod
    def _format_context_summaries(session_items, prev_items):
        cart_summary = "empty"
        if session_items:
            cart_summary = ", ".join(
                f"{s.get('quantity', 1)}x {s.get('item_name', s.get('name', '?'))}"
                for s in session_items
            )
        prev_summary = "none"
        if prev_items:
            prev_summary = ", ".join(
                f"{p.get('quantity', 1)}x {p.get('item_name', p.get('name', '?'))}"
                for p in prev_items
            )
        return cart_summary, prev_summary

    @staticmethod
    def _validate_context_result(result) -> Optional[dict]:
        if result and result.get("action") in ("add", "modify_qty", "repeat", "confirm"):
            logger.info("LLM brain resolved context → action=%s, items=%s (reason: %s)",
                        result["action"], result.get("items", []),
                        result.get("reasoning", ""))
            return result
        return None


# Module-level singleton
llm_brain = LLMBrain()
