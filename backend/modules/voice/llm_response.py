"""
llm_response.py — LLM-Powered Natural Response Generator
============================================================
Decides whether to use Qwen2.5:7B (via Ollama) for natural phrasing
or fall back to language-specific templates. Always returns speakable
text — never raises.

Usage:
    from modules.voice.llm_response import llm_generator
    spoken = await llm_generator.get_response_text(pipeline_result, "hi")
"""

import logging
import httpx

from .voice_config import cfg

logger = logging.getLogger("petpooja.voice.llm_response")

# ── System prompt for Qwen2.5:7B ─────────────────────────────────
SYSTEM_PROMPT = (
    "You are Sizzle, the voice of an AI restaurant ordering assistant in India. "
    "Your job is to generate spoken response text that will be converted to audio by a TTS engine.\n\n"
    "STRICT RULES — violating these breaks the system:\n"
    "1. Maximum 2 sentences. Hard limit: 25 words total. TTS clips longer responses.\n"
    "2. Match the customer's detected language exactly:\n"
    '   - "en"  → English\n'
    '   - "hi"  → Hinglish (romanized Hindi mixed with English food terms)\n'
    '   - "gu"  → Gujarati\n'
    '   - "mr"  → Marathi\n'
    '   - "kn"  → Kannada\n'
    "3. Never use symbols: no ₹, no ×, no %, no /. Write everything as spoken words.\n"
    "4. Never invent information. Use only what is in the provided order data.\n"
    "5. For 5+ items: summarize by count and category. Do not list all item names.\n"
    '   BAD:  "Added dal makhani, butter naan, coke, lassi, and gulab jamun."\n'
    '   GOOD: "Five items added — mains, bread, drinks, and a dessert. Kuch aur chahiye?"\n'
    "6. For upsells: sound like a genuine helpful suggestion, not a sales pitch.\n"
    "7. Output ONLY the spoken text. No JSON. No explanation. No quotation marks."
)


class LLMResponseGenerator:
    """Singleton that generates natural spoken text from pipeline results."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Decision Logic ────────────────────────────────────────────

    def should_use_llm(self, pipeline_result: dict) -> bool:
        """Determine if LLM should be called instead of using a template.

        Returns True when templates would produce unnatural output:
        - 5+ matched items (too long to list by name)
        - QUERY intent (customer asking about a dish)
        - Upsell suggestions present (need persuasive framing)
        - Ambiguous match with 3+ options
        - Partial order (some matched, some unrecognized)
        """
        if not cfg.LLM_ENABLED:
            return False

        items = pipeline_result.get("items", [])
        intent = pipeline_result.get("intent", "")
        upsells = pipeline_result.get("upsell_suggestions", [])
        disambiguation = pipeline_result.get("disambiguation", [])
        stage_results = pipeline_result.get("stage_results", [])

        # 5+ items — too many to list naturally
        if len(items) >= cfg.LLM_MIN_ITEMS_FOR_SUMMARY:
            return True

        # Customer asking about a dish — needs descriptive answer
        if intent == "QUERY":
            return True

        # Upsell — needs persuasive framing
        if upsells:
            return True

        # 3+ disambiguation options — hard to template naturally
        if len(disambiguation) >= 3:
            return True

        # Partial order — some matched, some failed
        has_items = len(items) > 0
        has_errors = any(
            sr.get("error_type") == "zero_item_matches"
            for sr in stage_results
        )
        if has_items and has_errors:
            return True

        return False

    # ── LLM Call ──────────────────────────────────────────────────

    async def generate(self, pipeline_result: dict, detected_language: str) -> str:
        """Call Qwen2.5:7B via Ollama for natural phrasing.
        Falls back to template on any error or timeout."""
        try:
            user_prompt = self._build_user_prompt(pipeline_result, detected_language)

            async with httpx.AsyncClient(timeout=cfg.LLM_TIMEOUT_SEC) as client:
                resp = await client.post(
                    f"{cfg.LLM_BASE_URL}/api/generate",
                    json={
                        "model": cfg.LLM_MODEL,
                        "prompt": user_prompt,
                        "system": SYSTEM_PROMPT,
                        "stream": False,
                        "options": {
                            "temperature": cfg.LLM_TEMPERATURE,
                            "num_predict": cfg.LLM_MAX_TOKENS,
                        },
                    },
                )
                resp.raise_for_status()
                text = resp.json().get("response", "").strip()

                if text:
                    # Strip quotation marks the LLM sometimes wraps output in
                    text = text.strip('"\'')
                    return text

        except httpx.TimeoutException:
            logger.info("LLM timed out (%.1fs) — using template", cfg.LLM_TIMEOUT_SEC)
        except Exception as e:
            logger.warning(f"LLM call failed: {e} — using template")

        return self._fallback_template(pipeline_result, detected_language)

    # ── Prompt Builder ────────────────────────────────────────────

    def _build_user_prompt(self, pipeline_result: dict, detected_language: str) -> str:
        """Construct the user prompt from pipeline result data."""
        items = pipeline_result.get("items", [])
        intent = pipeline_result.get("intent", "UNCLEAR")
        upsells = pipeline_result.get("upsell_suggestions", [])
        disambiguation = pipeline_result.get("disambiguation", [])
        order = pipeline_result.get("order")

        # Determine situation
        if len(items) >= cfg.LLM_MIN_ITEMS_FOR_SUMMARY:
            situation = "complex_order_echo"
        elif upsells:
            situation = "upsell_suggestion"
        elif intent == "QUERY":
            situation = "query_response"
        elif len(disambiguation) >= 3:
            situation = "ambiguous_multi_option"
        else:
            situation = "partial_order_with_unrecognized"

        # Build item summary
        item_parts = []
        for item in items:
            name = item.get("item_name", "unknown")
            qty = item.get("quantity", 1)
            item_parts.append(f"{qty} {name}")
        item_summary = ", ".join(item_parts) if item_parts else "no items matched"

        # Extra context
        extra = []
        if upsells:
            upsell_names = [u.get("name") or u.get("suggestion_text", "") for u in upsells]
            extra.append(f"Upsell suggestions: {', '.join(upsell_names)}")
        if disambiguation:
            for d in disambiguation:
                alts = [a.get("item_name", "") for a in d.get("alternatives", [])]
                extra.append(f"Ambiguous: '{d.get('item_name')}' — options: {', '.join(alts)}")
        if order and order.get("subtotal"):
            extra.append(f"Subtotal: {order['subtotal']} rupees")

        extra_context = "; ".join(extra) if extra else "none"

        return (
            f"Situation: {situation}\n"
            f"Order data: {item_summary}\n"
            f"Customer language: {detected_language}\n"
            f"Context: {extra_context}\n"
            f"Generate the spoken response:"
        )

    # ── Template Fallbacks ────────────────────────────────────────

    def _fallback_template(self, pipeline_result: dict, lang: str) -> str:
        """Generate a template-based response. Always returns something."""
        items = pipeline_result.get("items", [])
        intent = pipeline_result.get("intent", "UNCLEAR")
        order = pipeline_result.get("order")
        disambiguation = pipeline_result.get("disambiguation", [])
        stage_results = pipeline_result.get("stage_results", [])

        # Check for specific error types
        for sr in stage_results:
            err = sr.get("error_type")
            if err == "no_speech_detected":
                return self._t_no_speech(lang)
            if err == "audio_too_short":
                return self._t_audio_short(lang)

        # Intent-based templates
        if intent == "ORDER":
            if len(items) == 0:
                return self._t_no_match(lang)
            if len(items) >= cfg.LLM_MIN_ITEMS_FOR_SUMMARY:
                return self._t_order_many(lang, len(items))
            return self._t_order(lang, items)

        if intent == "CANCEL":
            item_name = items[0]["item_name"] if items else "the item"
            return self._t_cancel(lang, item_name)

        if intent == "MODIFY":
            if items:
                item_name = items[0]["item_name"]
                mods = items[0].get("modifiers", {})
                modifier_str = ", ".join(mods.get("applied", [])) if mods.get("applied") else "as requested"
                return self._t_modify(lang, item_name, modifier_str)
            return self._t_modify(lang, "the item", "as requested")

        if intent == "CONFIRM":
            total = order.get("subtotal", 0) if order else 0
            return self._t_confirm(lang, total)

        # Disambiguation
        if disambiguation and len(disambiguation) <= 2:
            d = disambiguation[0]
            alts = d.get("alternatives", [])
            if alts:
                opt_a = d.get("item_name", "option 1")
                opt_b = alts[0].get("item_name", "option 2")
                return self._t_disambiguation(lang, opt_a, opt_b)

        # Fallback
        return self._t_no_speech(lang)

    # ── Template Strings per Language ─────────────────────────────

    @staticmethod
    def _t_order(lang: str, items: list) -> str:
        names = ", ".join(
            f"{i.get('quantity', 1)} {i.get('item_name', '')}" for i in items
        )
        templates = {
            "en": f"Got it! {names}. Anything else?",
            "hi": f"Ji haan! {names} add kar diya. Aur kuch chahiye?",
            "gu": f"{names} ઉમેરી દીધું. બીજું કંઈ જોઈએ?",
            "mr": f"{names} जोडले. आणखी काही हवे का?",
            "kn": f"{names} ಸೇರಿಸಲಾಗಿದೆ. ಇನ್ನೇನಾದರೂ ಬೇಕೇ?",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_order_many(lang: str, count: int) -> str:
        templates = {
            "en": f"Perfect, {count} items added to your order.",
            "hi": f"{count} cheezein cart mein add ho gayi.",
            "gu": f"{count} વસ્તુઓ ઉમેરાઈ. બીજું કંઈ જોઈએ?",
            "mr": f"{count} वस्तू जोडल्या. आणखी काही?",
            "kn": f"{count} ವಸ್ತುಗಳನ್ನು ಸೇರಿಸಲಾಗಿದೆ.",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_cancel(lang: str, item_name: str) -> str:
        templates = {
            "en": f"Removed {item_name} from your order.",
            "hi": f"{item_name} hata diya.",
            "gu": f"{item_name} દૂર કર્યું.",
            "mr": f"{item_name} काढले.",
            "kn": f"{item_name} ತೆಗೆದುಹಾಕಲಾಗಿದೆ.",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_modify(lang: str, item_name: str, modifier: str) -> str:
        templates = {
            "en": f"Updated — {item_name} will be {modifier}.",
            "hi": f"{item_name} {modifier} kar diya.",
            "gu": f"{item_name} {modifier} કર્યું.",
            "mr": f"{item_name} {modifier} केले.",
            "kn": f"{item_name} {modifier} ಮಾಡಲಾಗಿದೆ.",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_confirm(lang: str, total: float) -> str:
        total_str = str(int(total)) if total == int(total) else str(total)
        templates = {
            "en": f"Order confirmed! Total is {total_str} rupees. Sent to kitchen.",
            "hi": f"Order confirm ho gaya! Total {total_str} rupees. Kitchen ko bhej diya.",
            "gu": f"ઓર્ડર કન્ફર્મ! કુલ {total_str} રૂપિયા. રસોડામાં મોકલ્યું.",
            "mr": f"ऑर्डर कन्फर्म! एकूण {total_str} रुपये. स्वयंपाकघरात पाठवले.",
            "kn": f"ಆರ್ಡರ್ ದೃಢಪಡಿಸಲಾಗಿದೆ! ಒಟ್ಟು {total_str} ರೂಪಾಯಿ. ಅಡುಗೆಮನೆಗೆ ಕಳುಹಿಸಲಾಗಿದೆ.",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_disambiguation(lang: str, opt_a: str, opt_b: str) -> str:
        templates = {
            "en": f"Did you mean {opt_a} or {opt_b}?",
            "hi": f"{opt_a} chahiye ya {opt_b}?",
            "gu": f"{opt_a} જોઈએ છે કે {opt_b}?",
            "mr": f"{opt_a} हवे की {opt_b}?",
            "kn": f"{opt_a} ಬೇಕೇ ಅಥವಾ {opt_b}?",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_no_speech(lang: str) -> str:
        templates = {
            "en": "I didn't catch that. Could you speak again?",
            "hi": "Samajh nahi aaya. Dobara bolein?",
            "gu": "સમજ ન પડ્યું. ફરીથી બોલો.",
            "mr": "कळले नाही. पुन्हा सांगा.",
            "kn": "ಅರ್ಥವಾಗಲಿಲ್ಲ. ಮತ್ತೆ ಹೇಳಿ.",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_audio_short(lang: str) -> str:
        templates = {
            "en": "That was too short. Please say your full order.",
            "hi": "Thoda aur bolein, please.",
            "gu": "થોડું વધુ બોલો.",
            "mr": "थोडे अधिक बोला.",
            "kn": "ಸ್ವಲ್ಪ ಹೆಚ್ಚು ಮಾತನಾಡಿ.",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_no_match(lang: str) -> str:
        templates = {
            "en": "I couldn't find that on the menu. Could you try again?",
            "hi": "Ye menu mein nahi mila. Dobara try karein?",
            "gu": "મેનુમાં મળ્યું નહીં. ફરી પ્રયત્ન કરો.",
            "mr": "मेनूमध्ये सापडले नाही. पुन्हा प्रयत्न करा.",
            "kn": "ಮೆನುವಿನಲ್ಲಿ ಕಂಡುಬರಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
        }
        return templates.get(lang, templates["en"])

    @staticmethod
    def _t_out_of_stock(lang: str, item_name: str) -> str:
        templates = {
            "en": f"{item_name} is not available right now. Can I suggest something else?",
            "hi": f"{item_name} abhi available nahi hai. Kuch aur suggest karoon?",
            "gu": f"{item_name} હાલમાં ઉપલબ્ધ નથી. બીજું કંઈ સૂચવું?",
            "mr": f"{item_name} सध्या उपलब्ध नाही. दुसरे काही सुचवू का?",
            "kn": f"{item_name} ಈಗ ಲಭ್ಯವಿಲ್ಲ. ಬೇರೆ ಏನಾದರೂ ಸೂಚಿಸಲೇ?",
        }
        return templates.get(lang, templates["en"])

    # ── Public Entry Point ────────────────────────────────────────

    async def get_response_text(self, pipeline_result: dict, detected_language: str) -> str:
        """Public entry point. Always returns speakable text — never raises."""
        lang = detected_language if detected_language in ("en", "hi", "gu", "mr", "kn") else "en"
        try:
            if self.should_use_llm(pipeline_result):
                return await self.generate(pipeline_result, lang)
            return self._fallback_template(pipeline_result, lang)
        except Exception as e:
            logger.warning(f"Response text generation failed: {e}")
            return self._t_no_speech(lang)


# Module-level singleton
llm_generator = LLMResponseGenerator()
