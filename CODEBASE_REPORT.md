# Sizzle (Petpooja AI Copilot) — Full Codebase Context Report

> **Purpose**: This document provides complete context of the Sizzle codebase so you can analyze what's built and suggest improvements.

---

## 1. Project Overview

**Sizzle** (internally "Petpooja AI Copilot") is a **Restaurant Revenue Intelligence & Voice Ordering** platform built during a 48-hour hackathon by a 4-person team.

**Core Value Proposition**: Fully offline — no external APIs, no LLMs. Everything runs locally with SQLite/PostgreSQL, faster-whisper for STT, and rule-based NLP.

**Two Main Modules**:
1. **Revenue Intelligence** — Analyzes menu profitability using BCG matrix classification, detects hidden stars, mines co-occurrence patterns for combo suggestions, and generates price optimization recommendations.
2. **Voice Ordering** — Accepts Hindi/Hinglish/English voice input, transcribes locally, parses intent + items + quantities + modifiers, builds orders with KOT (Kitchen Order Ticket) generation, and provides real-time upsell suggestions.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI + Uvicorn (REST API) |
| **ORM** | SQLAlchemy (PostgreSQL via Supabase / SQLite fallback) |
| **STT** | faster-whisper "small" model (local, CPU, ~244MB) |
| **NLP** | Rule-based (regex intent mapping + compound clause splitting, no external LLMs) |
| **Item Matching** | Hybrid: RapidFuzz fuzzy (0.4 weight) + Sentence-Transformer FAISS semantic vectors (0.6 weight) |
| **Semantic Model** | paraphrase-multilingual-MiniLM-L12-v2 (~420MB, multilingual, fully offline) |
| **Vector Search** | FAISS (faiss-cpu, IndexFlatIP cosine similarity, no server needed) |
| **VAD** | Silero VAD (torch.hub, filters noise before Whisper, fully local) |
| **Session Persistence** | Redis (preferred) → PostgreSQL fallback → in-memory fallback |
| **Combo Mining** | mlxtend FP-Growth (association rules) |
| **Data Processing** | Pandas + NumPy |
| **Frontend** | React 18 + React Router 6 (SPA) |
| **Bundler** | Vite |
| **HTTP Client** | Axios (with /api proxy to backend) |
| **Charts** | Recharts (scatter plot for BCG matrix) |
| **Styling** | Custom CSS dark theme (no UI framework) |

---

## 3. Database Schema (12 Tables)

### Categories
- `id`, `name`, `name_hi` (Hindi), `display_order`, `is_active`

### MenuItem
- `id`, `name`, `name_hi`, `description`, `aliases` (pipe-separated fuzzy search corpus, e.g. `"pnr tikka|panir tikka|tikka paneer"`), `category_id` (FK), `selling_price`, `food_cost`, `modifiers` (JSON: `{"spice_level": [...], "size": [...], "add_ons": [...]}`), `is_veg`, `is_available`, `is_bestseller`, `current_stock`, `tags` (JSON), `created_at`
- Computed properties: `contribution_margin` (price − cost), `margin_pct` ((CM / price) × 100)

### SaleTransaction
- `id`, `item_id` (FK), `order_id`, `quantity`, `unit_price`, `total_price`, `order_type` (dine_in / takeaway / delivery), `sold_at`

### Order
- `id`, `order_id` (unique), `order_number`, `total_amount`, `status` (building / confirmed / cancelled), `order_type`, `table_number`, `source` (voice / manual), `created_at`, `updated_at`

### OrderItem
- `id`, `order_id` (FK), `item_id` (FK), `quantity`, `unit_price`, `modifiers_applied` (JSON), `line_total`

### KOT (Kitchen Order Ticket)
- `id`, `kot_id` (format: `KOT-YYYYMMDD-XXXX`), `order_id` (FK), `items_summary` (JSON), `print_ready` (plain text for kitchen printer), `created_at`

### Staff
- `id`, `name`, `role` (waiter/cashier/manager/chef), `pin_hash`, `phone`, `is_active`, `created_at`

### RestaurantTable
- `id`, `table_number`, `capacity`, `section` (main/patio/private/bar), `status` (empty/occupied/reserved/cleaning), `current_order_id` (FK)

### Shift
- `id`, `name`, `started_at`, `ended_at`, `opened_by` (FK staff), `closed_by` (FK staff), `opening_cash`, `closing_cash`, `status` (open/closed)

### ComboSuggestion
- `id`, `name`, `item_ids` (JSON array), `item_names` (JSON array), `individual_total`, `combo_price`, `discount_pct`, `expected_margin`, `confidence`, `lift`, `support`, `combo_score`, `created_at`

### Ingredient
- `id`, `name`, `unit` (g/kg/ml/L/pcs), `current_stock`, `reorder_level`, `cost_per_unit`, `is_active`, `created_at`
- Computed property: `is_low_stock` (current_stock ≤ reorder_level)

### MenuItemIngredient
- `id`, `menu_item_id` (FK), `ingredient_id` (FK), `quantity_used` (per serving)

### StockLog
- `id`, `ingredient_id` (FK), `change_qty`, `reason` (purchase/usage/waste/adjustment), `note`, `staff_id` (FK), `created_at`

### VoiceSession
- `id`, `session_id` (unique, indexed), `last_active` (Unix timestamp), `order_items` (JSON), `last_items` (JSON), `turn_count`, `confirmed`
- Used by the persistent session store (DB backend) — survives server restarts
- `to_dict()` / `from_dict()` helpers for backend serialization

---

## 4. Backend Architecture

### 4.1 Entry Point — `main.py`
- FastAPI app with CORS middleware (allows all origins for dev)
- Async lifespan context manager that loads `VoicePipeline` from DB at startup (builds menu search corpus once)
- Global exception handlers
- Router registration: `/api/revenue` and `/api/voice`

### 4.2 Database — `database.py`
- Reads `DATABASE_URL` from `.env` → connects to Supabase PostgreSQL
- Falls back to local SQLite at `backend/petpooja.db` if env var missing
- Connection pooling: pool_size=5, max_overflow=10, pool_pre_ping=True, recycle every 5 min

### 4.3 Synthetic Data — `generate_synthetic_data.py`
- Generates 60 menu items across 6 categories (Starters, Main Course, Breads, Rice & Biryani, Beverages, Desserts) with Hindi names and realistic aliases
- Creates 180 days of sales data (~21,000 transactions)
- Intentional co-occurrence patterns: Butter Naan + Dal Makhani (70%), Cold Drink + Biryani (60%)
- Weekend 1.5x multiplier, lunch/dinner time spikes
- Weighted popularity distribution designed to populate all 4 BCG quadrants

---

## 5. Voice Pipeline (7-Stage Architecture)

The voice pipeline is orchestrated by `pipeline.py` → class `VoicePipeline`. Each stage is a separate module:

### Stage 0: Voice Activity Detection (`vad.py`) — Preprocessing
- **Silero VAD** via `torch.hub` — fully local, no API calls
- Detects actual speech segments in audio before sending to Whisper
- Eliminates Whisper "hallucinations" from restaurant background noise (kitchen sounds, music, other conversations)
- Configurable thresholds via env vars: `VAD_THRESHOLD` (default 0.40), `VAD_MIN_SPEECH_SEC` (0.3s), `VAD_SPEECH_PAD_MS` (300ms), `VAD_MIN_TOTAL_SPEECH_SEC` (0.4s)
- `detect_speech_segments()` → list of `{start, end}` timestamps
- `extract_speech_audio()` → concatenates speech-only segments into cleaned WAV, returns metadata: `total_speech_sec`, `speech_ratio`, `has_speech`
- Short/empty audio rejected before STT — saves compute and prevents false transcripts

### Stage 1: Speech-to-Text (`stt.py`)
- Uses `faster-whisper` "small" model (runs locally on CPU, no API calls)
- Lazy-loads and caches model on first use
- Converts WebM/MP3/M4A → WAV 16kHz mono via ffmpeg
- VAD preprocessing filters noise before transcription
- Returns: transcript text, detected language, confidence score, VAD info

### Stage 2: Text Normalization (`normalizer.py`)
- Converts Devanagari Hindi characters → romanized equivalents (20+ character mappings)
- Replaces Hindi number words (ek, do, teen, char, paanch, etc.) → digits
- Removes filler words (umm, bhai, yaar, please, ok, etc.)
- Collapses whitespace

### Stage 3: Intent Classification (`intent_mapper.py`) — Compound-Aware
- Rule-based regex pattern matching, classifies into 6 intents:
  - **ORDER** — "want", "give", "order", "lao", "chahiye", "dena" + quantities
  - **CONFIRM** — "haan", "okay", "theek hai", "bilkul", "confirm", "done"
  - **CANCEL** — "cancel", "remove", "hatao", "nahi chahiye", "wrong"
  - **MODIFY** — "instead", "change", "badlo", "replace", "swap"
  - **REPEAT** — "repeat", "dobara", "same", "again"
  - **QUERY** — "what", "price", "menu", "available"
- **Compound intent support**: Splits utterances into clauses via conjunction/punctuation patterns ("but", "and", "aur", commas, "instead", "phir", etc.) and classifies each independently
  - "Cancel the naan but keep the dal" → `[CANCEL(naan), ORDER(dal)]`
  - "Make it extra spicy and add one raita" → `[MODIFY(biryani), ORDER(raita)]`
- `classify_intents()` → list of `{intent, matched_pattern, clause, clause_index}`
- `classify_intent()` → backward-compatible single-intent (priority: CANCEL > CONFIRM > MODIFY > REPEAT > QUERY > ORDER)
- Context-aware: modifier patterns don't steal intent when order signals present

### Stage 4: Item Matching (`item_matcher.py`) — Hybrid Fuzzy + Semantic
- **Fully dynamic** — builds search corpus from DB (MenuItem.name + name_hi + aliases)
- **Two-layer matching architecture**:
  1. **RapidFuzz** `token_sort_ratio` — fast character-level fuzzy matching (threshold 70)
  2. **Sentence-Transformer + FAISS** — semantic meaning vectors that rescue phonetic mishearings
- **Blend formula**: `final_score = 0.4 × fuzzy + 0.6 × semantic`
- **Semantic model**: `paraphrase-multilingual-MiniLM-L12-v2` (~420MB, downloads once, fully offline)
  - Multilingual: handles English, Hindi, Hinglish, Devanagari natively
  - "chikken" → embeds near "chicken" (phonetic shape preserved), far from "chikan" (embroidery)
  - "murgh", "चिकन", "chicken" handled as near-synonyms
- **FAISS index**: `IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity)
  - Built once at startup from all corpus entries
  - Queried per match in milliseconds
- Sliding window approach: 3-word → 2-word → 1-word ngrams to extract all items
- Confidence thresholds per window size: 3-word (0.85), 2-word (0.78), 1-word (0.75)
- Extensive SKIP_WORDS list (English + Hindi + Hinglish + Devanagari fillers)
- `get_alternatives()` merges fuzzy + semantic candidates, deduplicates by item_id, re-ranks by hybrid score
- Disambiguation flag when confidence < 85%
- Graceful degradation: falls back to fuzzy-only if semantic model/FAISS fails to load

### Stage 5: Quantity Extraction (`quantity_extractor.py`)
- Position-based: looks 3 tokens before/after each matched item position
- Supports Hindi numbers (ek=1, do=2, teen=3...), English words (one, two, three...), plain digits
- Default quantity: 1

### Stage 6: Modifier Extraction (`modifier_extractor.py`) — With Target Resolution
- Extracts spice level (mild/medium/hot), size (small/large), add-ons (no_onion, no_garlic, extra_butter, extra_cheese, no_sauce)
- Supports both Devanagari and romanized Hindi patterns
- Cross-checks against `MenuItem.modifiers` JSON from DB — only allows modifiers the item actually supports
- **Target resolution**: determines WHICH item a modifier applies to:
  - **Explicit name**: "make the biryani extra spicy" → biryani
  - **Positional last**: "make the last one spicy" → most recently added item
  - **Positional first**: "first one mild" → first item in current turn
  - **Proximity**: "paneer tikka extra spicy" → nearest mentioned item
  - **Global**: "everything mild" / "sab mein" → all items in cart
- `extract_modifiers_with_target()` used by pipeline for MODIFY intents with compound clause support

### Stage 7: Order Building (`order_builder.py`)
- `build_order()` — creates full order JSON with UUID, item details, subtotal, 5% GST tax
- `generate_kot()` — Kitchen Order Ticket with formatted items, modifiers, notes; KOT ID: `KOT-YYYYMMDD-XXXX`
- `save_order_to_db()` — writes Order + OrderItem + KOT rows in a single DB transaction

### Supporting: Session Store (`session_store.py`) — Persistent
- **3-tier persistence** with automatic backend detection:
  1. **Redis** (preferred) — fast, multi-worker safe, native 30-min TTL via `SETEX`. Set `REDIS_URL` env var.
  2. **Database** (fallback) — uses existing SQLAlchemy engine, persists to `voice_sessions` table. Survives server restarts. Auto-creates table on first use.
  3. **In-memory** (last resort) — original `OrderedDict` behavior with warning log. Used only when neither Redis nor DB is available.
- 30-minute timeout, max 500 sessions (prevents memory leaks)
- Handles ORDER/CANCEL/MODIFY/CONFIRM intents across turns
- **Compound intent support**: `update_session_compound()` applies multiple intents sequentially ("cancel naan, add roti")
- Accumulates cart items across multiple voice inputs
- Server restart no longer loses active carts (with Redis or DB backend)
- Multi-worker deployment (Gunicorn + Uvicorn workers) safe with Redis backend

### Supporting: Structured Error Recovery (`pipeline_errors.py`)
- Every pipeline stage returns a `StageResult` dataclass with `status` (success/partial/failure), `error_type`, `user_message`, `suggestions`
- **Error taxonomy with user-facing recovery messages**:
  - STT: no speech detected, audio too short, low confidence, model error
  - Item matching: zero matches (with top-3 fuzzy suggestions), ambiguous match ("Did you mean X or Y?")
  - Modifiers: unsupported modifier for item
  - Stock: item out of stock / insufficient quantity
  - Pipeline: generic stage failure
- Factory helpers: `stt_no_speech()`, `zero_item_matches()`, `ambiguous_match()`, `item_out_of_stock()`, etc.
- Pipeline collects `stage_results` and `user_messages` lists throughout processing — frontend displays them directly
- Transforms silent failures into recoverable interactions

### Supporting: Upsell Engine (`upsell_engine.py`)
- Two strategies:
  1. **Combo-based**: if antecedent items in cart AND consequent not → suggest combo
  2. **Hidden star promotion**: top 3 hidden stars not in cart → "Chef's Special"
- Scores by: lift × margin × confidence
- Max 2 suggestions per order (prevents overwhelm)
- Fallback: top-margin items if no pattern matches

---

## 6. Revenue Intelligence Pipeline (6 Modules)

Orchestrated by `analyzer.py` → `run_full_analysis()` which calls all sub-modules:

### 6.1 Contribution Margin (`contribution_margin.py`)
- For each MenuItem: CM = Selling Price − Food Cost
- Margin % = (CM / Price) × 100
- Tier classification: **high** (≥65%), **medium** (50–65%), **low** (<50%)
- Returns sorted by margin_pct descending

### 6.2 Popularity / Sales Velocity (`popularity.py`)
- Total quantity sold in last 30 days
- Daily velocity = total_qty / 30
- Popularity score normalized 0–1 using mean × 2 as ceiling (robust normalization, prevents outliers from skewing)
- Tier: **high** (≥0.6), **medium** (0.3–0.6), **low** (<0.3)

### 6.3 BCG Menu Matrix (`menu_matrix.py`)
- Classifies each item on 2 axes: margin (threshold: 60%) × popularity (threshold: 0.4)
  - **⭐ Star** — high margin, high popularity → "Protect and promote"
  - **🐴 Plowhorse** — low margin, high popularity → "Increase price or reduce cost"
  - **🧩 Puzzle** — high margin, low popularity → "Boost visibility, upsell"
  - **🐕 Dog** — low margin, low popularity → "Consider removing"
- Thresholds are customizable

### 6.4 Hidden Stars Detection (`hidden_stars.py`)
- Filters: margin_pct > 70th percentile AND popularity_score < 30th percentile
- Computes `opportunity_score` = (margin_pct / 100) × (1 − popularity_score) × 100
- Generates actionable suggestions per item:
  - Feature as daily special
  - Train staff to recommend
  - Consider small discount if margin > 70%
  - Add menu photos if low visibility

### 6.5 Combo Engine (`combo_engine.py`) — ML-powered
- Builds boolean basket matrix (order × item) from SaleTransaction data
- Runs **FP-Growth** algorithm (mlxtend): min_support=0.04, min_confidence=0.30, min_lift=1.2
- Filters for single-item consequents
- Scores: `combo_score = lift × avg_cm_consequent × confidence`
- Suggests bundle price with 10% discount
- Persists results to ComboSuggestion table
- Fallback pair counting if FP-Growth yields no rules
- Thread-safe caching (5-minute TTL)

### 6.6 Price Optimizer (`price_optimizer.py`)
- Rule-based recommendations per BCG quadrant:
  - **Plowhorse**: increase price → target 65% margin
  - **Dog**: remove or increase price + bundle
  - **Puzzle**: hold price, focus visibility
  - **Star**: hold price, maintain quality
- Prices rounded to nearest ₹5
- Priority levels: critical → high → medium → low

---

## 7. API Endpoints

### Revenue Intelligence (`/api/revenue/`)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard` | KPI metrics (health score, avg margin, items at risk, uplift potential) |
| GET | `/menu-matrix` | All items with quadrant classification |
| GET | `/hidden-stars` | High-margin underperforming items with opportunity scores |
| GET | `/risks` | Low-margin high-volume items with risk scoring |
| GET | `/combos` | FP-Growth combo recommendations (cached 5 min) |
| GET | `/price-recommendations` | Rule-based price adjustment suggestions |
| GET | `/category-breakdown` | Per-category revenue and margin stats |
| GET | `/analyze` | Full analysis pipeline (legacy) |
| GET | `/margins`, `/popularity`, `/matrix`, `/pricing` | Legacy individual endpoints |

### Voice Ordering (`/api/voice/`)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/transcribe` | Local STT only (audio → text) |
| POST | `/process-audio` | Full pipeline: audio → parsed order |
| POST | `/process` | Text input (for testing without mic) |
| POST | `/confirm-order` | Save order to DB (Pydantic-validated) |
| GET | `/orders` | Paginated recent orders list |
| POST | `/order` | Legacy endpoint |

---

## 8. Frontend Architecture

### Pages (4 routes)
1. **Dashboard** (`/`) — 4×2 grid of KPI MetricCards (Health Score, Avg Margin, Stars, Hidden Stars, Total Items, Dogs, Combos, Price Actions) + quick-view cards for Top 5 Stars and Top 5 Hidden Stars
2. **Menu Analysis** (`/menu-analysis`) — 4 clickable quadrant cards, Recharts ScatterChart (BCG matrix visualization), sortable ItemTable with quadrant filter
3. **Combo Engine** (`/combos`) — 2-column grid of ComboCards showing item names, prices, discounts, expected margins, co-order stats
4. **Voice Order** (`/voice-order`) — Full voice ordering interface:
   - VoiceRecorder (circular button with pulse animation) + TextInput
   - Parsed input display: transcript, normalized, intent, language, session ID
   - Matched items table with color-coded confidence badges
   - Disambiguation card for low-confidence matches
   - Full cart display (session accumulation across turns)
   - OrderSummary + KOTTicket side-by-side
   - Upsell suggestions banner
   - Confirm Order + New Order buttons
   - Error handling for STT failures

### Components (7 reusable)
- **MetricCard** — KPI card with emoji icon, big number, suffix, color
- **MenuMatrix** — Recharts 2×2 scatter chart (X: popularity, Y: margin%, colored by quadrant)
- **ItemTable** — Sortable table (name + Hindi name, category, price ₹, margin % color-coded, popularity progress bar, quadrant badge, action text)
- **ComboCard** — Combo details with items, pricing breakdown, co-order stats
- **VoiceRecorder** — MediaRecorder API, mic permissions, gradient-styled record button
- **OrderSummary** — Order ID, item rows (qty × name, veg/non-veg badge, modifiers, line total), subtotal, GST 5%, total
- **KOTTicket** — Monospace receipt-style: KOT ID, order type, table, timestamp, items with modifiers, "PETPOOJA AI COPILOT" footer

### Styling
- Full custom dark theme CSS (no framework)
- CSS variables: orange (#ff6b35), green, blue, red, cyan, purple
- Layout: 240px fixed sidebar + scrollable main content
- Responsive: hides sidebar on mobile, adjusts grids

---

## 9. Synthetic Data Design

The `generate_synthetic_data.py` creates realistic test data:
- **60 menu items** across 6 categories with Hindi names and aliases
- **180 days** of sales data (~21,000 transactions)
- **Intentional patterns**:
  - Butter Naan + Dal Makhani co-occur 70% → shows as combo recommendation
  - Cold Drink + Biryani co-occur 60% → shows as combo recommendation
  - Weekend sales 1.5x higher
  - Lunch (12–3pm) and dinner (7–10pm) spikes
  - Weighted popularity distribution → all 4 BCG quadrants populated

---

## 10. Key Design Decisions

1. **Fully offline** — No OpenAI, no cloud STT, no external APIs. faster-whisper, Silero VAD, sentence-transformers, and FAISS all run on CPU locally.
2. **Hybrid matching** — Item matcher combines RapidFuzz fuzzy matching (0.4 weight) with sentence-transformer semantic vectors + FAISS (0.6 weight). Phonetic mishearings like "chikken" are rescued by semantic similarity even when edit distance fails.
3. **Dynamic menu matching** — Item matcher reads entirely from DB, no hardcoded menu items. Adding items to DB automatically makes them matchable and semantically indexed.
4. **Multi-turn sessions with persistence** — Voice ordering supports accumulating items across multiple voice inputs. Sessions persist across server restarts via Redis (preferred) or database fallback. Multi-worker safe.
5. **Hindi/Hinglish first** — Devanagari transliteration, Hindi number words, Hindi filler word removal, Hindi aliases in DB. The multilingual sentence-transformer handles "murgh", "चिकन", and "chicken" as near-synonyms natively.
6. **Compound intent handling** — Single utterances like "cancel the naan but keep the dal" are split into clauses and each classified independently.
7. **Structured error recovery** — Every pipeline stage returns typed `StageResult` objects with user-facing messages. Zero-match → top-3 suggestions. Ambiguous → "Did you mean X or Y?". Out of stock → explicit notification.
8. **VAD preprocessing** — Silero VAD filters restaurant noise before Whisper, preventing hallucinations from kitchen sounds, music, and background conversations.
9. **Rule-based NLP** — No LLMs for intent classification. Regex patterns with compound clause splitting. Fast, deterministic, predictable.
10. **FP-Growth for combos** — Real ML (association rule mining) instead of simple co-occurrence counting, with fallback if data is insufficient.
11. **BCG matrix for menu** — Standard restaurant industry framework (Star/Plowhorse/Puzzle/Dog) adapted to automatic classification.
12. **Thread-safe caching** — Combo results cached 5 min, session store has max 500 sessions to prevent memory leaks.
13. **Centralized voice config** — All tuning parameters (thresholds, weights, model names, limits) live in `voice_config.py` with env-var overrides. Zero hardcoded magic numbers across voice modules.

---

## 11. Current State

- All files are implemented and functional (no stubs/TODOs)
- Built in a 48-hour hackathon by a 4-person team
- PostgreSQL via Supabase for production, SQLite fallback for local dev
- Tests exist: `test_audio.py`, `test_pipeline.py`, `test_realdb.py`
- **Implemented since initial build**:
  - Hybrid fuzzy + semantic item matching (sentence-transformers + FAISS)
  - Silero VAD preprocessing for noise filtering
  - Compound intent classification (clause splitting)
  - Modifier target resolution (explicit/positional/proximity/global)
  - Structured error taxonomy with user-facing recovery messages
  - Persistent session store (Redis → DB → memory fallback)
  - VoiceSession DB model for session persistence
  - Centralized `voice_config.py` with ~45 env-overridable parameters (STT, VAD, matcher, upsell, sessions)
  - Staff, RestaurantTable, Shift, Ingredient, StockLog models
- **Not yet implemented**:
  - Local LLM for intent classification (Ollama/Qwen2/Phi-3 — still regex-only)
- No CI/CD pipeline
- No Docker configuration
- No authentication/authorization
- CORS configured via `CORS_ORIGINS` env var (defaults to localhost)

---

## 12. File Count Summary

| Area | Files |
|---|---|
| Backend core | 4 (main, database, models, requirements) |
| Backend API routes | 3 (init, routes_revenue, routes_voice) |
| Backend data | 2 (schema.sql, generate_synthetic_data) |
| Voice modules | 12 (init + 11 modules incl. vad.py, pipeline_errors.py, voice_config.py) |
| Revenue modules | 8 (init + 7 modules) |
| Frontend core | 5 (index.html, package.json, vite.config, main.jsx, App.jsx, index.css, client.js) |
| Frontend pages | 4 |
| Frontend components | 7 |
| Tests | 3 |
| **Total** | **~46 code files** |

---

## Questions for Claude

Given the full context above, please analyze and suggest:

1. **What are the biggest architectural improvements** that would make this production-ready?
2. **What features are missing** that a real-world restaurant POS AI copilot would need?
3. **What are the weakest points** in the current implementation (voice pipeline, revenue analytics, frontend UX, database design)?
4. **What would you prioritize** for a v2 roadmap if this had 2 more weeks of development?
5. **Any security, performance, or scalability concerns** with the current approach?
6. **What's impressive / well-done** that should be kept as-is?
