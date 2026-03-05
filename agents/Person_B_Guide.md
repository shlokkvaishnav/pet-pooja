# 🎙️ Person B — Module 2: NLP Voice Pipeline
## Your Complete Build Guide (Dynamic Edition)

---

## What You Are Building

You are building the entire voice ordering system that runs **100% locally — zero external API calls**. A customer calls, speaks their order in English / Hindi / Hinglish, and your pipeline converts that into a confirmed structured order pushed to the PoS.

> ⚠️ **NO EXTERNAL AI APIs** — No OpenAI, no Google Speech, no cloud STT. Everything runs on your machine using `faster-whisper` (local Whisper model).

Your pipeline has 7 stages:

```
Audio File
    ↓
[1] STT — faster-whisper converts speech to raw text (LOCAL model)
    ↓
[2] Normalizer — cleans Hinglish, maps Hindi numbers, removes fillers
    ↓
[3] Intent Mapper — is this an ORDER? CONFIRM? CANCEL?
    ↓
[4] Item Matcher — "pnr tikka" → Paneer Tikka (DYNAMIC from DB menu)
    ↓
[5] Quantity + Modifier Extractor — "do", "extra spicy"
    ↓
[6] Upsell Engine — suggests add-ons (D writes this, you just call it)
    ↓
[7] Order Builder — structured JSON + KOT (D writes this, you just call it)
    ↓
Final Order JSON → PoS Push
```

Stages 1–5 + pipeline.py are entirely yours.
Stages 6–7 are written by D — you just call them inside pipeline.py.

---

## 🔧 What You Must Install on Your PC

These are **local** tools — no cloud APIs, no API keys, no internet needed at runtime.

### 1. Python packages
```bash
pip install faster-whisper rapidfuzz
```

### 2. ffmpeg (audio converter — required by STT)
```bash
# Windows — download from https://ffmpeg.org/download.html
# Extract, add the bin/ folder to your system PATH
# Verify: open new terminal and run:
ffmpeg -version

# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### 3. Whisper model (downloads automatically on first run)
```python
# Run this ONCE on good WiFi — downloads ~244MB model
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
# After this, it works fully offline forever
```

**What this gives you:**
| Tool | What it does | Runs where? |
|---|---|---|
| `faster-whisper` | Speech-to-Text (Whisper model) | 100% local on your CPU |
| `ffmpeg` | Converts browser audio (webm) → WAV | 100% local |
| `rapidfuzz` | Fuzzy string matching | 100% local, pure Python |

**No API keys. No internet at runtime. No cloud services.**

---

## Your Files — Complete List

```
backend/modules/voice/
    stt.py                    ← Speech-to-Text (local Whisper model)
    normalizer.py             ← text cleaning + Hindi number conversion
    intent_mapper.py          ← ORDER/CONFIRM/CANCEL classification
    item_matcher.py           ← fuzzy match spoken words → DB menu items
    quantity_extractor.py     ← extract quantities ("do" → 2)
    modifier_extractor.py     ← extract spice/size/add-ons
    pipeline.py               ← orchestrates everything above

backend/api/
    routes_voice.py           ← your API endpoints
```

---

## ⚡ KEY DESIGN PRINCIPLE: Dynamic, Not Hardcoded

**The pipeline reads everything from the database at startup.** The only hardcoded things are:
- Hindi number words (ek=1, do=2...) — these are a fixed language, not data
- Filler words to strip (umm, bhai, yaar...) — fixed linguistic patterns
- Modifier patterns (spicy, mild, no onion...) — fixed linguistic patterns

**Everything else is DYNAMIC from the DB:**
- Menu item names → loaded from `MenuItem.name` column
- Hindi names → loaded from `MenuItem.name_hi` column
- Fuzzy aliases → loaded from `MenuItem.aliases` column (pipe-separated)
- Allowed modifiers per item → loaded from `MenuItem.modifiers` column (JSON)
- Item prices → loaded from `MenuItem.selling_price` column
- Categories → loaded from `Category` table

**This means:**
- If the restaurant changes their menu → pipeline auto-adapts (reload from DB)
- If new items are added → they're immediately matchable
- No code changes needed when menu changes

---

## File 1 — `stt.py` (Speech-to-Text)

This is the first thing you write. The Whisper model runs **entirely on your CPU** — no API calls.

```python
"""
Speech-to-Text using faster-whisper — runs 100% locally.
No external API calls. Model loaded once, cached forever.
"""

import os
import subprocess
import logging

logger = logging.getLogger("petpooja.voice.stt")

# Lazy-loaded model — loaded on first transcribe() call
# This avoids crashes when testing text-only (no audio)
_model = None


def _get_model():
    """Load Whisper model on demand. Cached after first call."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading faster-whisper model (small)...")
        _model = WhisperModel("small", device="cpu", compute_type="int8")
        logger.info("Model loaded — runs fully offline from now on")
    return _model


def convert_to_wav(input_path: str) -> str:
    """
    Browser MediaRecorder produces webm/opus.
    Whisper needs WAV 16kHz mono.
    Converts any audio format to WAV using ffmpeg (local tool).
    """
    output_path = input_path.rsplit(".", 1)[0] + "_converted.wav"
    subprocess.run([
        "ffmpeg", "-y",           # -y = overwrite if exists
        "-i", input_path,
        "-ar", "16000",           # 16kHz sample rate
        "-ac", "1",               # mono channel
        output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


def transcribe(audio_path: str) -> dict:
    """
    Takes any audio file path.
    Returns transcript + detected language.

    language=None means Whisper auto-detects (handles EN, HI, Hinglish).
    """
    # Convert to WAV first (handles webm, mp3, m4a, etc.)
    wav_path = convert_to_wav(audio_path)

    model = _get_model()
    segments, info = model.transcribe(
        wav_path,
        beam_size=5,
        language=None,        # auto-detect language
        task="transcribe",
        vad_filter=True,      # removes silent parts
    )

    transcript = " ".join(segment.text.strip() for segment in segments)

    # Cleanup converted file
    if wav_path != audio_path and os.path.exists(wav_path):
        os.remove(wav_path)

    return {
        "transcript": transcript.strip(),
        "detected_language": info.language,         # "en", "hi", etc.
        "language_confidence": round(info.language_probability, 3),
    }
```

**Test it with a real audio file:**
```python
from modules.voice.stt import transcribe

result = transcribe("test_hindi.m4a")   # record yourself on phone
print(result)
# Expected: {"transcript": "do paneer tikka dena", "detected_language": "hi", ...}
```

**Common issues:**
- `ffmpeg not found` → install ffmpeg and restart terminal
- `Module not found: faster_whisper` → `pip install faster-whisper`
- First run downloads ~244MB model → needs WiFi once, then works offline

---

## File 2 — `normalizer.py`

Cleans raw Whisper transcript. These are **linguistic rules** (not database data) — Hindi number words and filler words are part of the language itself, not restaurant-specific.

```python
"""
Text normalization for Hindi/Hinglish transcripts.
Only LINGUISTIC patterns are hardcoded here (numbers, fillers).
Food aliases and menu data come from the DATABASE.
"""

import re

# Hindi/Urdu number words → integer
# These are LANGUAGE constants, not restaurant data
HINDI_NUMBERS = {
    "ek": 1, "ak": 1,
    "do": 2, "dono": 2, "dou": 2,
    "teen": 3, "tin": 3,
    "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5,
    "chhe": 6, "chheh": 6,
    "saat": 7, "sat": 7,
    "aath": 8, "ath": 8,
    "nau": 9, "naw": 9,
    "das": 10,
    "gyarah": 11,
    "barah": 12,
    "tera": 13,
    "chaudah": 14,
    "pandrah": 15,
    "bees": 20,
}

# Conversational filler words — LANGUAGE constants, not data
FILLERS = {
    "umm", "uh", "uhh", "hmm", "aaa", "err",
    "bhai", "yaar", "boss", "sunlo", "suniye",
    "bolo", "batao", "please", "ji", "haan ji",
    "theek", "okay", "ok", "acha", "accha",
    "actually", "basically", "matlab",
}


def normalize(text: str) -> str:
    """
    Input : raw Whisper transcript
    Output: cleaned lowercase string ready for intent + item parsing
    """
    if not text or not text.strip():
        return ""

    text = text.lower().strip()

    # Remove punctuation except spaces
    text = re.sub(r"[^\w\s]", " ", text)

    # Replace Hindi number words with digits
    tokens = text.split()
    tokens = [str(HINDI_NUMBERS[t]) if t in HINDI_NUMBERS else t for t in tokens]
    text = " ".join(tokens)

    # Remove filler words
    tokens = text.split()
    tokens = [t for t in tokens if t not in FILLERS]
    text = " ".join(tokens)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text
```

---

## File 3 — `intent_mapper.py`

Classifies what the customer is trying to do. Uses regex patterns on **common ordering phrases** — these are linguistic, not restaurant-specific.

```python
"""
Intent classification using regex patterns.
No AI models, no API calls — pure pattern matching.
"""

import re
from typing import Tuple

# Intent patterns — linguistic ordering phrases, not restaurant data
INTENT_PATTERNS = {
    "CONFIRM": [
        r"\b(yes|haan|ha|okay|ok|theek hai|sahi|bilkul|confirm|done|ho gaya|correct|right)\b",
    ],
    "CANCEL": [
        r"\b(cancel|remove|hatao|mat dena|nahi chahiye|wrong|galat|undo)\b",
    ],
    "MODIFY": [
        r"\b(without|bina|no |extra|zyada|kam|less|more|add|instead|change|badlo)\b",
        r"\b(spicy|mild|hot|medium|sweet|sugar free|no onion|no garlic|jain)\b",
    ],
    "REPEAT": [
        r"\b(repeat|dobara|phir se|again|same|wahi|wahi wala)\b",
    ],
    "QUERY": [
        r"\b(what|kya hai|kitna|how much|price|available|hai kya|menu|list)\b",
    ],
    "ORDER": [
        r"\b(want|give|order|lao|chahiye|dena|milega|dedo|lena|bhejo|pack)\b",
        r"\b(1|2|3|4|5|6|7|8|9|10)\s+\w+",
        r"\b(ek|do|teen|char|paanch)\s+\w+",
    ],
}


def classify_intent(text: str) -> Tuple[str, str]:
    """
    Returns (intent, matched_pattern)
    Priority: CONFIRM > CANCEL > MODIFY > REPEAT > QUERY > ORDER > UNKNOWN
    """
    if not text:
        return "UNKNOWN", ""

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return intent, match.group()

    return "UNKNOWN", ""
```

---

## File 4 — `item_matcher.py` ⭐ Most Critical File

**This is the DYNAMIC heart of the pipeline.** It builds its search corpus from the DATABASE, not from hardcoded lists. When the restaurant adds a new item to the DB, this file automatically matches it.

```python
"""
Dynamic fuzzy menu item matching.
Builds search corpus FROM THE DATABASE — nothing hardcoded.
Uses RapidFuzz for fuzzy string matching (local, no API).
"""

from rapidfuzz import process, fuzz
from typing import Optional


def build_search_corpus(menu_items: list) -> dict:
    """
    DYNAMICALLY builds search corpus from DB menu items.
    
    menu_items: list of MenuItem ORM objects loaded from database
    
    Returns: { "alias string" → item_id }
    
    Every item gets multiple searchable entries:
      - English name from DB (item.name)
      - Hindi name from DB (item.name_hi) 
      - Each pipe-separated alias from DB (item.aliases)
    
    When restaurant adds/changes menu items in DB,
    the corpus auto-updates on next server restart.
    """
    corpus = {}
    for item in menu_items:
        entries = []

        # English name from DB
        if item.name:
            entries.append(item.name.lower().strip())

        # Hindi name from DB
        if item.name_hi:
            entries.append(item.name_hi.strip())

        # All aliases from DB (pipe-separated)
        if hasattr(item, "aliases") and item.aliases:
            for alias in item.aliases.split("|"):
                alias = alias.strip().lower()
                if alias:
                    entries.append(alias)

        for entry in entries:
            if entry:
                corpus[entry] = item.id

    return corpus


def match_item(text: str, corpus: dict, threshold: int = 72) -> Optional[dict]:
    """
    Fuzzy match a spoken phrase against the dynamic corpus.
    Uses RapidFuzz WRatio scorer — handles:
      - word order differences ("tikka paneer" vs "paneer tikka")
      - partial matches ("dal" matching "dal makhani")
      - typos ("pnr tikka" → "paneer tikka")
    
    threshold=72 means 72% similarity required for a match.
    """
    if not text or not corpus:
        return None

    result = process.extractOne(
        text,
        corpus.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
    )

    if result:
        matched_key, score, _ = result
        return {
            "item_id": corpus[matched_key],
            "matched_as": matched_key,
            "confidence": round(score / 100, 3),
        }
    return None


def extract_all_items(text: str, corpus: dict) -> list:
    """
    Sliding window over transcript tokens.
    Tries 3-word, 2-word, then 1-word phrases.
    Returns all matched items (deduped by item_id, highest confidence wins).
    """
    if not text or not corpus:
        return []

    tokens = text.split()
    found = {}   # item_id → best match dict

    for window_size in [3, 2, 1]:
        for i in range(len(tokens) - window_size + 1):
            phrase = " ".join(tokens[i:i + window_size])

            # Skip pure numbers
            if phrase.strip().isdigit():
                continue

            match = match_item(phrase, corpus)
            if match:
                item_id = match["item_id"]
                if item_id not in found or match["confidence"] > found[item_id]["confidence"]:
                    found[item_id] = {**match, "position": i}

    return sorted(found.values(), key=lambda x: x["position"])
```

**Why this is dynamic:**
- `build_search_corpus()` reads from DB — add new menu items, they become matchable
- Aliases from DB — restaurant can add "pnr tikka" as alias for "Paneer Tikka" without code change
- Hindi names from DB — works for any restaurant's Hindi menu
- Fuzzy matching handles typos/accents the customer might use

---

## File 5 — `quantity_extractor.py`

```python
"""
Position-based quantity extraction.
Hindi numbers are LANGUAGE constants, not restaurant data.
"""

import re

HINDI_NUMBERS = {
    "ek": 1, "ak": 1,
    "do": 2, "dono": 2,
    "teen": 3, "tin": 3,
    "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5,
    "chhe": 6,
    "saat": 7, "sat": 7,
    "aath": 8, "ath": 8,
    "nau": 9,
    "das": 10,
}


def extract_quantity(text: str, item_position: int, tokens: list) -> int:
    """
    Looks for quantity in the 2 tokens BEFORE and 2 tokens AFTER
    the matched item's position in the token list.
    Default: 1.
    """
    start = max(0, item_position - 2)
    end = min(len(tokens), item_position + 3)
    window = tokens[start:end]

    for token in window:
        token = token.strip().lower()
        if token in HINDI_NUMBERS:
            return HINDI_NUMBERS[token]
        if token.isdigit():
            val = int(token)
            if 1 <= val <= 50:
                return val

    return 1


def extract_quantities_for_items(text: str, matched_items: list) -> list:
    """
    For each matched item, extract its quantity.
    """
    tokens = text.split()
    result = []
    for item in matched_items:
        qty = extract_quantity(text, item["position"], tokens)
        result.append({**item, "quantity": qty})
    return result
```

---

## File 6 — `modifier_extractor.py`

Modifier patterns are **linguistic** (spicy, mild, no onion are common across all restaurants). But the **allowed modifiers per item** come from the DB.

```python
"""
Per-item modifier extraction.
Modifier PATTERNS are linguistic, but allowed modifiers
per item are loaded DYNAMICALLY from DB.
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
```

---

## File 7 — `pipeline.py` (The Orchestrator)

**This is the main dynamic engine.** It loads menu data from the DB once at startup, builds its search corpus dynamically, and everything flows from there.

```python
"""
Voice Pipeline Orchestrator.
Loads menu data FROM DB at startup → builds dynamic search corpus.
No hardcoded menu items anywhere.
"""

import uuid
from .stt import transcribe
from .normalizer import normalize
from .intent_mapper import classify_intent
from .item_matcher import build_search_corpus, extract_all_items
from .quantity_extractor import extract_quantities_for_items
from .modifier_extractor import extract_modifiers


# ── Stub functions for D's files (until D delivers them) ──
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
        
        menu_items: loaded FROM DATABASE — this is what makes it dynamic.
        The search corpus is built from whatever is in the DB.
        Change the menu in DB → pipeline auto-adapts.
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
        """Full pipeline: audio file → structured order JSON."""
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
```

---

## File 8 — `routes_voice.py`

```python
"""
Voice API endpoints.
All processing happens locally — no external API calls.
"""

import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db

router = APIRouter()


def get_pipeline(db: Session = Depends(get_db)):
    """Get pipeline from app state (loaded at startup with DB data)."""
    from main import app
    return app.state.voice_pipeline


class TextInput(BaseModel):
    text: str


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Audio file → transcript text only. Uses local Whisper model."""
    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        from modules.voice.stt import transcribe
        return transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)


@router.post("/process-audio")
async def process_audio(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Audio file → full pipeline result."""
    pipeline = get_pipeline(db)
    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        return pipeline.process_audio(tmp_path)
    finally:
        os.unlink(tmp_path)


@router.post("/process")
async def process_text(body: TextInput, db: Session = Depends(get_db)):
    """Text → full pipeline result. For testing without audio."""
    pipeline = get_pipeline(db)
    return pipeline.process_text(body.text)


@router.post("/confirm-order")
async def confirm_order(order: dict, db: Session = Depends(get_db)):
    """Save confirmed order to DB. Returns order_id + KOT."""
    try:
        from modules.voice.order_builder import save_order_to_db
        return save_order_to_db(order, db)
    except ImportError:
        return {"status": "stub", "message": "Order saving not implemented yet"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_orders(limit: int = 20, db: Session = Depends(get_db)):
    """Recent confirmed voice orders."""
    from models import Order
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
    return [
        {
            "id": o.id,
            "order_id": o.order_id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "total": o.total,
            "status": o.status,
            "order_type": o.order_type,
        }
        for o in orders
    ]
```

---

## How Dynamic Loading Works (in main.py at startup)

D's `main.py` should load menu items from DB and pass them to your pipeline:

```python
# In main.py lifespan event — D writes this, but here's what it does:
from models import MenuItem
from modules.voice.pipeline import VoicePipeline

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    # DYNAMIC: Load menu from DATABASE
    db = SessionLocal()
    menu_items = db.query(MenuItem).filter(MenuItem.is_available == True).all()
    
    # Build pipeline with DB data — no hardcoded items
    app.state.voice_pipeline = VoicePipeline(
        db_session=db,
        menu_items=menu_items,     # ← from DB
        combo_rules=[],            # ← D fills this from combo_engine
        hidden_stars=[],           # ← A fills this from hidden_stars
    )
    
    print(f"Voice pipeline loaded with {len(menu_items)} menu items from DB")
    yield
    db.close()
```

---

## What D Needs to Provide (for your pipeline to match items)

For `item_matcher.py` to match any menu item, D's `MenuItem` model needs these columns:

```
MenuItem.name           = "Paneer Tikka"        ← English name
MenuItem.name_hi        = "पनीर टिक्का"         ← Hindi name (optional)
MenuItem.aliases        = "pnr tikka|panir"     ← pipe-separated fuzzy aliases
MenuItem.selling_price  = 350                   ← for order total calculation
MenuItem.modifiers      = '{"spice":["mild","medium","hot"]}'  ← allowed modifiers JSON
```

**The more aliases D adds to seed_data, the better your fuzzy matching works.**

---

## What's Hardcoded vs Dynamic — Summary

| Component | Hardcoded? | Why |
|---|---|---|
| Hindi number words (ek=1, do=2) | ✅ Hardcoded | Language constant — Hindi numbers don't change |
| Filler words (umm, bhai, yaar) | ✅ Hardcoded | Language constant — conversational noise |
| Intent patterns (ORDER, CANCEL) | ✅ Hardcoded | Linguistic patterns — ordering phrases |
| Modifier patterns (spicy, mild) | ✅ Hardcoded | Linguistic patterns — food modifier phrases |
| **Menu item names** | ❌ **From DB** | Restaurant-specific — changes per restaurant |
| **Hindi menu names** | ❌ **From DB** | Restaurant-specific |
| **Fuzzy aliases** | ❌ **From DB** | Restaurant-specific |
| **Item prices** | ❌ **From DB** | Restaurant-specific |
| **Allowed modifiers per item** | ❌ **From DB** | Item-specific |
| **Whisper STT model** | ❌ **Local model** | Runs on your CPU, no API |
| **Fuzzy matching (RapidFuzz)** | ❌ **Local library** | Runs in Python, no API |

---

## Demo Scripts — These Must Work

**Script 1 — English:**
> "I'd like 2 paneer tikka and 1 butter naan please"

**Script 2 — Hindi:**
> "Ek biryani dena aur do cold drink bhi chahiye"

**Script 3 — Hinglish with modifier:**
> "Bhai do paneer tikka extra spicy chahiye aur ek mango lassi"

All three should produce structured order JSON with items, quantities, modifiers, and subtotal.

---

## Common Bugs to Watch For

| Bug | Cause | Fix |
|---|---|---|
| Whisper loads slowly | Model loaded inside function | Use lazy `_get_model()` - loads once, caches |
| "file not found" on wav conversion | ffmpeg not installed | Install ffmpeg, verify with `ffmpeg -version` |
| Item not matched | No alias in DB for that spelling | Ask D to add alias to `MenuItem.aliases` in seed_data |
| Hindi numbers not converting | Normalization runs after matching | Always run `normalize()` before `extract_all_items()` |
| `get_upsell_suggestions` crashes | D's file not ready | Stub function handles this automatically |
| WebM audio upload fails | Browser sends WebM | ffmpeg conversion handles this in stt.py |
| No items match at all | Menu corpus empty | Check that main.py loads menu items at startup |
