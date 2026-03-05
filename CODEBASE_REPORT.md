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
| **NLP** | Rule-based (regex intent mapping, no external LLMs) |
| **Fuzzy Matching** | RapidFuzz (token_sort_ratio, 80% threshold) |
| **Combo Mining** | mlxtend FP-Growth (association rules) |
| **Data Processing** | Pandas + NumPy |
| **Frontend** | React 18 + React Router 6 (SPA) |
| **Bundler** | Vite |
| **HTTP Client** | Axios (with /api proxy to backend) |
| **Charts** | Recharts (scatter plot for BCG matrix) |
| **Styling** | Custom CSS dark theme (no UI framework) |

---

## 3. Database Schema (7 Tables)

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

### ComboSuggestion
- `id`, `name`, `item_ids` (JSON array), `item_names` (JSON array), `individual_total`, `combo_price`, `discount_pct`, `expected_margin`, `confidence`, `lift`, `support`, `times_co_ordered`, `association_rule` (JSON), `is_active`, `created_at`

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

### Stage 1: Speech-to-Text (`stt.py`)
- Uses `faster-whisper` "small" model (runs locally on CPU, no API calls)
- Lazy-loads and caches model on first use
- Converts WebM/MP3/M4A → WAV 16kHz mono via ffmpeg
- Returns: transcript text, detected language, confidence score

### Stage 2: Text Normalization (`normalizer.py`)
- Converts Devanagari Hindi characters → romanized equivalents (20+ character mappings)
- Replaces Hindi number words (ek, do, teen, char, paanch, etc.) → digits
- Removes filler words (umm, bhai, yaar, please, ok, etc.)
- Collapses whitespace

### Stage 3: Intent Classification (`intent_mapper.py`)
- Rule-based regex pattern matching, classifies into 6 intents:
  - **ORDER** — "want", "give", "order", "lao", "chahiye", "dena" + quantities
  - **CONFIRM** — "haan", "okay", "theek hai", "bilkul", "confirm", "done"
  - **CANCEL** — "cancel", "remove", "hatao", "nahi chahiye", "wrong"
  - **MODIFY** — "extra", "change", "without", "spicy", "mild", "no onion"
  - **REPEAT** — "repeat", "dobara", "same", "again"
  - **QUERY** — "what", "price", "menu", "available"
- Context-aware priority: modifiers don't steal intent when order signals present

### Stage 4: Item Matching (`item_matcher.py`)
- **Fully dynamic** — builds search corpus from DB (MenuItem.name + name_hi + aliases)
- Uses RapidFuzz `token_sort_ratio` for fuzzy matching (80% threshold)
- Sliding window approach: 3-word → 2-word → 1-word ngrams to extract all items from transcript
- Returns matched items with confidence scores
- `get_alternatives()` for disambiguation when confidence < 85%

### Stage 5: Quantity Extraction (`quantity_extractor.py`)
- Position-based: looks 3 tokens before/after each matched item position
- Supports Hindi numbers (ek=1, do=2, teen=3...), English words (one, two, three...), plain digits
- Default quantity: 1

### Stage 6: Modifier Extraction (`modifier_extractor.py`)
- Extracts spice level (mild/medium/hot), size (small/large), add-ons (no_onion, no_garlic, extra_butter, extra_cheese, no_sauce)
- Supports both Devanagari and romanized Hindi patterns
- Cross-checks against `MenuItem.modifiers` JSON from DB — only allows modifiers the item actually supports

### Stage 7: Order Building (`order_builder.py`)
- `build_order()` — creates full order JSON with UUID, item details, subtotal, 5% GST tax
- `generate_kot()` — Kitchen Order Ticket with formatted items, modifiers, notes; KOT ID: `KOT-YYYYMMDD-XXXX`
- `save_order_to_db()` — writes Order + OrderItem + KOT rows in a single DB transaction

### Supporting: Session Store (`session_store.py`)
- In-memory session management for multi-turn conversations
- 30-minute timeout, max 500 sessions (prevents memory leaks)
- Thread-safe, handles ORDER/CANCEL/MODIFY/CONFIRM intents across turns
- Accumulates cart items across multiple voice inputs

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

1. **Fully offline** — No OpenAI, no cloud STT, no external APIs. faster-whisper runs on CPU locally.
2. **Dynamic menu matching** — Item matcher reads entirely from DB, no hardcoded menu items. Adding items to DB automatically makes them matchable.
3. **Multi-turn sessions** — Voice ordering supports accumulating items across multiple voice inputs with session persistence and 30-min timeout.
4. **Hindi/Hinglish first** — Devanagari transliteration, Hindi number words, Hindi filler word removal, Hindi aliases in DB.
5. **Rule-based NLP** — No LLMs. Intent classification via regex, quantity via positional parsing, modifiers via pattern matching. Fast, deterministic, predictable.
6. **FP-Growth for combos** — Real ML (association rule mining) instead of simple co-occurrence counting, with fallback if data is insufficient.
7. **BCG matrix for menu** — Standard restaurant industry framework (Star/Plowhorse/Puzzle/Dog) adapted to automatic classification.
8. **Thread-safe caching** — Combo results cached 5 min, session store has max 500 sessions to prevent memory leaks.

---

## 11. Current State

- All files are implemented and functional (no stubs/TODOs)
- Built in a 48-hour hackathon by a 4-person team
- PostgreSQL via Supabase for production, SQLite fallback for local dev
- Tests exist: `test_audio.py`, `test_pipeline.py`, `test_realdb.py`
- No CI/CD pipeline
- No Docker configuration
- No authentication/authorization
- CORS is fully open (allows all origins)

---

## 12. File Count Summary

| Area | Files |
|---|---|
| Backend core | 4 (main, database, models, requirements) |
| Backend API routes | 3 (init, routes_revenue, routes_voice) |
| Backend data | 2 (schema.sql, generate_synthetic_data) |
| Voice modules | 10 (init + 9 modules) |
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
