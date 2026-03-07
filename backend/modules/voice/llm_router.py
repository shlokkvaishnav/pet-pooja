"""
llm_router.py — LLM-First Intent Router for the Voice Pipeline
================================================================
Replaces the regex-first pipeline with a single LLM call that receives:
  - The user's transcript
  - The full restaurant menu (names, prices, categories)
  - Current cart state, conversation context

And returns structured JSON:
  {
    "intent": "ORDER",
    "items": [{"name": "Chicken Biryani", "quantity": 2}],
    "query_answer": null
  }

Architecture:
  1. LLM Router (this module) runs FIRST — handles 95%+ of requests
  2. If LLM times out or fails → fall back to regex+FAISS (zero breakage)

The router naturally handles:
  - Intent classification (ORDER, CANCEL, MODIFY, CONFIRM, DONE, QUERY, REPEAT)
  - Item extraction (maps to exact menu names)
  - Disambiguation (picks the right variant from context)
  - Query answering ("what's the price of biryani?" → "₹280")
  - Conversational refs ("same again", "one more", "make it two")

Usage:
    from modules.voice.llm_router import llm_router
    result = llm_router.route(transcript, menu_items, session_items)
"""

import json
import logging
import re
from typing import Optional

import httpx

from .voice_config import cfg

logger = logging.getLogger("petpooja.voice.llm_router")


# ── System prompt — compact, structured, reliable ──────────────────────

_SYSTEM_PROMPT = """\
You are a restaurant voice ordering assistant that processes speech-to-text transcripts.
You MUST respond ONLY in valid JSON. No markdown, no explanations, no extra text.

Support: English, Hindi, Hinglish, Gujarati, Marathi, Kannada (romanized or native script).

Output format:
{"intent":"ORDER","items":[{"name":"exact menu item name","quantity":1}],"query_answer":null}

Rules:
- intent must be one of: ORDER, CANCEL, MODIFY, CONFIRM, DONE, QUERY, REPEAT, UNKNOWN
- For ORDER: extract items with quantities from the transcript. Match names EXACTLY to the menu list.
  Items are ALWAYS ADDED to the cart — never replace or remove existing cart items.
- For CANCEL: list items to remove. Empty items = cancel everything.
- For MODIFY: list items with modifications in "modify" field: {"name":"item","modify":"extra spicy"}
- For CONFIRM: items=[], the user is confirming/placing the order.
- For DONE: items=[], the user is finished ordering but not confirming yet.
- For QUERY: items=[], set query_answer to answer the user's question using the menu data.
- For REPEAT: items from the cart to repeat.
- If transcript is ambiguous between similar items, pick the most likely one. Do NOT leave it unresolved.
- Quantities: "do" / "two" = 2, "ek" / "one" = 1, "teen" / "three" = 3, etc. Default = 1.
- Fix speech recognition errors: "chikan" = chicken, "pnr" = paneer, "naan" = naan, "biriyani" = biryani."""


def _build_user_prompt(
    transcript: str,
    menu_summary: str,
    cart_summary: str,
    turn_count: int = 0,
    pending_disambiguation: dict = None,
    conversation_history: list = None,
) -> str:
    """Build the user prompt with context."""
    prompt = ""

    # Conversation history (last 5 turns for context)
    if conversation_history:
        recent = conversation_history[-5:]
        prompt += "Recent conversation:\n"
        for turn in recent:
            role = "Customer" if turn["role"] == "user" else "Agent"
            prompt += f"  {role}: {turn['text']}\n"
        prompt += "\n"

    # Pending disambiguation — critical context
    if pending_disambiguation:
        alts = pending_disambiguation.get("alternatives", [])
        alt_names = [a.get("item_name", "?") for a in alts]
        original = pending_disambiguation.get("original_item_name", "?")
        prompt += (
            f'CRITICAL: The agent asked "which {original}?" and the customer is answering. '
            f'Valid options are ONLY: {", ".join(alt_names)}. '
            f'Return intent=ORDER with items containing EXACTLY ONE item from that list — the one the customer chose. '
            f'Do NOT return any item that is not in the options list. Do NOT return CANCEL. '
            f'The cart already has other items — you are ONLY adding the chosen variant, never replacing the cart.\n\n'
        )

    prompt += f'Customer said: "{transcript}"\n\n'
    prompt += f"Restaurant menu:\n{menu_summary}\n\n"
    if cart_summary:
        prompt += f"Current cart: {cart_summary}\n"
    if turn_count > 0:
        prompt += f"(Turn {turn_count} of conversation)\n"
    prompt += "\nRespond with JSON only."
    return prompt


def _build_menu_summary(menu_items: list, max_items: int = 120) -> str:
    """Build a compact menu representation for the LLM context.

    Format: "Name (₹price, category)" — one per line.
    Truncated to max_items to keep prompt size manageable (~4KB).
    """
    lines = []
    for item in menu_items[:max_items]:
        if not item.name:
            continue
        cat = ""
        if hasattr(item, "category") and item.category and hasattr(item.category, "name"):
            cat = f", {item.category.name}"
        veg = ""
        if hasattr(item, "is_veg") and item.is_veg is not None:
            veg = " [V]" if item.is_veg else " [NV]"
        avail = ""
        if hasattr(item, "is_available") and not item.is_available:
            avail = " [UNAVAILABLE]"
        lines.append(f"- {item.name} (₹{item.selling_price}{cat}{veg}){avail}")

    return "\n".join(lines) if lines else "(no menu loaded)"


def _build_cart_summary(session_items: list) -> str:
    """Build a compact cart representation."""
    if not session_items:
        return "empty"
    parts = []
    for s in session_items:
        name = s.get("item_name", s.get("name", "?"))
        qty = s.get("quantity", 1)
        parts.append(f"{qty}× {name}")
    return ", ".join(parts)


class LLMRouter:
    """Singleton LLM-first intent router.

    One LLM call replaces:
    - regex intent classification
    - FAISS/fuzzy item extraction
    - disambiguation resolution
    - query answering

    Falls back gracefully to None if disabled, timed out, or failed.
    The pipeline then uses the existing regex+FAISS path.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._client: Optional[httpx.Client] = None
            inst._warmed_up = False
            cls._instance = inst
            # Warm up the model in a background thread so first real call is fast
            inst._warm_up()
        return cls._instance

    @property
    def enabled(self) -> bool:
        return cfg.LLM_ROUTER_ENABLED and cfg.LLM_ENABLED

    def _warm_up(self):
        """Pre-load the LLM model into memory with a trivial request."""
        if not self.enabled:
            return
        import threading
        def _do_warmup():
            try:
                client = self._get_client()
                client.post(
                    f"{cfg.LLM_BASE_URL}/api/generate",
                    json={
                        "model": cfg.LLM_ROUTER_MODEL,
                        "prompt": "hi",
                        "system": "Reply OK",
                        "stream": False,
                        "options": {"num_predict": 5},
                    },
                    timeout=30.0,
                )
                self._warmed_up = True
                logger.info("LLM Router model %s warmed up", cfg.LLM_ROUTER_MODEL)
            except Exception as e:
                logger.debug("LLM Router warm-up failed (non-critical): %s", e)
        threading.Thread(target=_do_warmup, daemon=True).start()

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=30.0,  # generous for cold starts
                limits=httpx.Limits(max_connections=4),
            )
        return self._client

    def route(
        self,
        transcript: str,
        menu_items: list,
        session_items: list = None,
        turn_count: int = 0,
        pending_disambiguation: dict = None,
        conversation_history: list = None,
    ) -> Optional[dict]:
        """Route a transcript through the LLM in a single call.

        Returns:
            {
                "intent": "ORDER",
                "items": [{"name": "Chicken Biryani", "quantity": 2}],
                "query_answer": "Chicken Biryani costs 280",  # only for QUERY
            }
            or None on failure/timeout.
        """
        if not self.enabled:
            return None

        if not transcript or not transcript.strip():
            return None

        try:
            menu_summary = _build_menu_summary(menu_items)
            cart_summary = _build_cart_summary(session_items)

            user_prompt = _build_user_prompt(
                transcript=transcript.strip(),
                menu_summary=menu_summary,
                cart_summary=cart_summary,
                turn_count=turn_count,
                pending_disambiguation=pending_disambiguation,
                conversation_history=conversation_history,
            )

            client = self._get_client()
            request_json = {
                "model": cfg.LLM_ROUTER_MODEL,
                "prompt": user_prompt,
                "system": _SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": cfg.LLM_ROUTER_MAX_TOKENS,
                },
            }

            # Try up to 2 times: first with normal timeout, then with 2x timeout
            result = None
            for attempt in range(2):
                attempt_timeout = cfg.LLM_ROUTER_TIMEOUT_SEC * (2 if attempt > 0 else 1)
                try:
                    resp = client.post(
                        f"{cfg.LLM_BASE_URL}/api/generate",
                        json=request_json,
                        timeout=attempt_timeout,
                    )
                    resp.raise_for_status()
                    result = self._parse_response(resp.json())
                    if result:
                        break
                    else:
                        logger.warning("LLM Router: parse failed on attempt %d", attempt + 1)
                except httpx.TimeoutException:
                    logger.warning(
                        "LLM Router timed out (attempt %d, %.1fs timeout) for: '%s'",
                        attempt + 1, attempt_timeout, transcript[:60],
                    )
                except Exception as e:
                    logger.warning(
                        "LLM Router error (attempt %d): %s for: '%s'",
                        attempt + 1, e, transcript[:60],
                    )
                    break  # Don't retry on non-timeout errors

            if result:
                logger.info(
                    "LLM Router: '%s' -> intent=%s items=%s",
                    transcript[:60],
                    result.get("intent"),
                    [i.get("name") for i in result.get("items", [])],
                )
            return result

        except Exception as e:
            logger.warning("LLM Router unexpected failure: %s", e)
            return None

    @staticmethod
    def _parse_response(data: dict) -> Optional[dict]:
        """Parse the raw Ollama response into a structured result."""
        raw = data.get("response", "").strip()
        if not raw:
            return None

        # Strip markdown code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw)
            if match:
                try:
                    parsed = json.loads(match.group())
                except json.JSONDecodeError:
                    return None
            else:
                return None

        # Validate intent
        intent = parsed.get("intent", "").upper()
        valid_intents = {"ORDER", "CANCEL", "MODIFY", "CONFIRM", "DONE", "QUERY", "REPEAT", "UNKNOWN"}
        if intent not in valid_intents:
            return None

        # Normalize items
        items = parsed.get("items", [])
        if not isinstance(items, list):
            items = []

        normalized_items = []
        for item in items:
            if isinstance(item, dict) and item.get("name"):
                normalized_items.append({
                    "name": str(item["name"]).strip(),
                    "quantity": max(1, min(int(item.get("quantity", 1)), 50)),
                    "modify": item.get("modify"),  # for MODIFY intent
                })

        return {
            "intent": intent,
            "items": normalized_items,
            "query_answer": parsed.get("query_answer"),
        }


# Module-level singleton
llm_router = LLMRouter()
