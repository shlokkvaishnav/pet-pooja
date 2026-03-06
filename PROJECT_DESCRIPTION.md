# Sizzle (Petpooja AI Copilot) — Complete Project Description

## 1. What This Project Is

**Sizzle** (internally "Petpooja AI Copilot") is a **Restaurant Revenue Intelligence & Voice Ordering** platform built during a 48-hour hackathon by a 4-person team. It's a full-stack web application with two core pillars:

1. **Revenue Intelligence** — Analyzes menu profitability using BCG matrix classification, detects hidden stars (high-margin but low-visibility items), mines co-occurrence patterns for AI-generated combo suggestions (FP-Growth association rules), and generates rule-based price optimization recommendations.

2. **Voice Ordering** — Accepts Hindi/Hinglish/English voice input, transcribes locally using faster-whisper, parses intent + items + quantities + modifiers via rule-based NLP, builds orders with KOT (Kitchen Order Ticket) generation, and provides real-time upsell suggestions.

**Key Design Principle**: Fully offline — no OpenAI, no cloud STT, no external APIs. Everything (Whisper STT, Silero VAD, SentenceTransformers, FAISS) runs locally on CPU.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3 — FastAPI + Uvicorn (REST API) |
| **ORM** | SQLAlchemy 2.0 (PostgreSQL via Supabase in prod / SQLite fallback for dev) |
| **STT** | faster-whisper `large-v3-turbo` model (local, CPU, ~809MB) |
| **VAD** | Silero VAD (via `torch.hub`, filters noise before Whisper) |
| **NLP** | Rule-based (regex intent mapping + compound clause splitting, no LLMs) |
| **Item Matching** | Hybrid: RapidFuzz fuzzy (0.4 weight) + SentenceTransformer FAISS semantic vectors (0.6 weight) |
| **Semantic Model** | `paraphrase-multilingual-MiniLM-L12-v2` (~420MB, multilingual, offline) |
| **Vector Search** | FAISS (`faiss-cpu`, `IndexFlatIP` cosine similarity) |
| **Session Persistence** | Redis (preferred) → PostgreSQL DB fallback → in-memory fallback |
| **Combo Mining** | mlxtend FP-Growth (association rules) |
| **Data Processing** | Pandas + NumPy |
| **Auth** | JWT (PyJWT) with PIN-based staff login + shift-aware token expiry |
| **Rate Limiting** | `slowapi` (per-IP) + custom sliding-window middleware |
| **Frontend** | React 18 + React Router 6 (SPA) |
| **Bundler** | Vite (dev port 3000, proxies `/api` → backend:8000) |
| **HTTP Client** | Axios |
| **Charts** | Recharts (Bar, Area, Pie, Scatter) |
| **Animations** | Framer Motion (BlurText), WebGL (OGL light rays) |
| **Styling** | Vanilla CSS dark theme with CSS custom properties (no UI framework) |
| **i18n** | Custom React context — English, Hindi, Marathi, Kannada, Gujarati (5 languages) |

---

## 3. Project Structure

```
pet-pooja/
│
├── package.json                         # Root: npm scripts proxy to frontend/
├── README.md                            # Quick start guide
├── CODEBASE_REPORT.md                   # Detailed codebase analysis document
├── PROJECT_DESCRIPTION.md               # This file
├── LICENSE
├── hero1.jpg, hero2.avif, hero3.png     # Landing page hero images
│
├── agents/                              # Team planning docs
│   ├── agent.md
│   ├── Person_B_Guide.md
│   ├── Person_C.md
│   ├── Person_D_Roadmap.md
│   └── Team_Division_Revised.md
│
├── backend/
│   ├── .env                             # DATABASE_URL (Supabase PostgreSQL)
│   ├── main.py                          # FastAPI app entry point + lifespan
│   ├── database.py                      # SQLAlchemy engine + session (PostgreSQL/SQLite)
│   ├── models.py                        # 13 ORM models (344 lines)
│   ├── requirements.txt                 # Python dependencies
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py                      # JWT auth + PIN login + shift-aware tokens
│   │   ├── rate_limit.py                # Sliding-window rate limiter middleware
│   │   ├── routes_revenue.py            # /api/revenue/* (16+ endpoints, 506 lines)
│   │   └── routes_voice.py              # /api/voice/* (6 endpoints, 228 lines)
│   │
│   ├── data/
│   │   ├── schema.sql                   # PostgreSQL DDL for 12+ tables
│   │   └── generate_synthetic_data.py   # Seeds 60 menu items + 180 days sales data
│   │
│   ├── modules/
│   │   ├── revenue/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py              # Main orchestrator + health score (150 lines)
│   │   │   ├── contribution_margin.py   # CM calculation + tier classification (62 lines)
│   │   │   ├── popularity.py            # Sales velocity + normalized scoring (83 lines)
│   │   │   ├── menu_matrix.py           # BCG quadrant classification (92 lines)
│   │   │   ├── hidden_stars.py          # High CM + low visibility detection (92 lines)
│   │   │   ├── combo_engine.py          # FP-Growth combo mining + scheduler (594 lines)
│   │   │   ├── price_optimizer.py       # Rule-based price recommendations (167 lines)
│   │   │   ├── advanced_analytics.py    # Cannibalization, waste, sensitivity (518 lines)
│   │   │   └── trend_analyzer.py        # WoW/MoM, elasticity, seasonal (526 lines)
│   │   │
│   │   └── voice/
│   │       ├── __init__.py
│   │       ├── pipeline.py              # 8-stage orchestrator (275 lines)
│   │       ├── stt.py                   # faster-whisper STT + ffmpeg (218 lines)
│   │       ├── vad.py                   # Silero VAD noise filtering (136 lines)
│   │       ├── normalizer.py            # Hindi/Hinglish text normalization (168 lines)
│   │       ├── intent_mapper.py         # Compound intent classification (177 lines)
│   │       ├── item_matcher.py          # Hybrid fuzzy+semantic matching (542 lines)
│   │       ├── quantity_extractor.py    # Multi-language qty extraction (92 lines)
│   │       ├── modifier_extractor.py    # Spice/size/add-on with target resolution (266 lines)
│   │       ├── upsell_engine.py         # Combo + hidden star upselling (207 lines)
│   │       ├── order_builder.py         # Order JSON + KOT + DB persistence (203 lines)
│   │       ├── session_store.py         # Multi-turn session (Redis/DB/memory) (320 lines)
│   │       ├── voice_config.py          # ~40 env-overridable params singleton (116 lines)
│   │       └── pipeline_errors.py       # Structured error taxonomy (152 lines)
│   │
│   ├── test_audio.py                    # Audio processing tests
│   ├── test_pipeline.py                 # Voice pipeline tests
│   ├── test_realdb.py                   # Real DB integration tests
│   ├── test_changes.py                  # Change validation tests
│   └── test_voice_config.py             # Config tests
│
├── frontend/
│   ├── index.html
│   ├── package.json                     # React 18, react-router-dom, axios, recharts, motion, ogl
│   ├── vite.config.js                   # Port 3000, /api proxy → :8000
│   │
│   ├── public/images/                   # Static assets
│   │
│   └── src/
│       ├── main.jsx                     # React DOM entry point
│       ├── App.jsx                      # Router + sidebar layout + nested routes
│       ├── index.css                    # Full dark theme CSS (1761 lines)
│       │
│       ├── api/
│       │   └── client.js                # Axios client with 20+ endpoint functions
│       │
│       ├── context/
│       │   ├── AuthContext.jsx          # localStorage auth with login/logout
│       │   └── LanguageContext.jsx      # i18n context (5 Indian languages)
│       │
│       ├── i18n/
│       │   └── translations.js          # ~70 keys × 5 languages
│       │
│       ├── pages/
│       │   ├── Landing.jsx              # Marketing page (hero slideshow, features, contact)
│       │   ├── AboutUs.jsx              # Company info, timeline, values
│       │   ├── Login.jsx                # PIN login with glassmorphic UI + WebGL background
│       │   ├── Login.css                # Dedicated login styles (317 lines)
│       │   ├── Dashboard.jsx            # KPIs, charts, 12+ analytics panels (525 lines)
│       │   ├── MenuAnalysis.jsx         # BCG scatter chart + filterable item table
│       │   ├── ComboEngine.jsx          # AI combos + price optimization
│       │   └── VoiceOrder.jsx           # Voice/text ordering with full order flow
│       │
│       └── components/
│           ├── Navbar.jsx               # Shared glassmorphic nav with language switcher
│           ├── MetricCard.jsx           # KPI display card
│           ├── MenuMatrix.jsx           # Recharts BCG scatter chart
│           ├── ItemTable.jsx            # Sortable/filterable data table
│           ├── ComboCard.jsx            # Combo recommendation card
│           ├── VoiceRecorder.jsx        # MediaRecorder mic button
│           ├── OrderSummary.jsx         # Parsed order display
│           ├── KOTTicket.jsx            # Kitchen ticket receipt UI
│           ├── BlurText.jsx             # Framer Motion blur-reveal text
│           ├── TypewriterText.jsx       # Typewriter cycling text
│           └── LightRays.jsx + .css     # WebGL animated light rays (OGL)
│
└── audio/                               # Audio test files
```

---

## 4. Database Schema (13 Tables)

| Table | Purpose | Key Columns |
|---|---|---|
| `staff` | Restaurant employees | `name`, `role` (waiter/cashier/manager/chef), `pin_hash`, `is_active` |
| `categories` | Menu categories | `name`, `name_hi` (Hindi), `display_order` |
| `menu_items` | Menu items with pricing | `name`, `name_hi`, `aliases` (pipe-separated for fuzzy search), `selling_price`, `food_cost`, `modifiers` (JSONB), `is_veg`, `is_available`, `is_bestseller`, `current_stock`, `tags` (JSON) |
| `sale_transactions` | Historical sales | `item_id`, `order_id`, `quantity`, `unit_price`, `total_price`, `order_type`, `shift_id`, `sold_at` |
| `orders` | Order lifecycle | `order_id`, `status` (building→confirmed→cancelled), `order_type`, `table_number`, `staff_id`, `shift_id`, `source` (voice/manual) |
| `order_items` | Line items per order | `order_id`, `item_id`, `quantity`, `unit_price`, `modifiers_applied` (JSON), `line_total` |
| `kots` | Kitchen Order Tickets | `kot_id` (KOT-YYYYMMDD-XXXX), `order_id`, `items_summary` (JSON), `print_ready` (plain text for thermal printer) |
| `combo_suggestions` | FP-Growth combo cache | `item_ids`, `item_names`, `combo_price`, `discount_pct`, `lift`, `confidence`, `support`, `combo_score` |
| `restaurant_tables` | Table management | `table_number`, `capacity`, `section`, `status` (empty/occupied/reserved/cleaning) |
| `shifts` | Operational shifts | `opened_by`, `closed_by`, `opening_cash`, `closing_cash`, `status` (open/closed) |
| `ingredients` | Inventory tracking | `name`, `unit`, `current_stock`, `reorder_level`, `cost_per_unit` |
| `menu_item_ingredients` | Recipe BOM | `menu_item_id`, `ingredient_id`, `quantity_used` (per serving) |
| `stock_logs` | Inventory audit trail | `ingredient_id`, `change_qty`, `reason` (purchase/usage/waste/adjustment), `staff_id` |
| `voice_sessions` | Persistent voice sessions | `session_id`, `order_items` (JSON), `last_items` (JSON), `turn_count`, `confirmed` |

---

## 5. Voice Pipeline Architecture (8 Stages)

Orchestrated by `VoicePipeline` class in `pipeline.py`:

| Stage | Module | What It Does |
|---|---|---|
| **0** | `vad.py` | **Voice Activity Detection** — Silero VAD strips silence/noise, prevents Whisper hallucinations from restaurant background noise |
| **1** | `stt.py` | **Speech-to-Text** — faster-whisper `large-v3-turbo`, converts audio to 16kHz WAV via ffmpeg, returns transcript + confidence |
| **2** | `normalizer.py` | **Text Normalization** — Devanagari→romanized, Hindi number words→digits, phonetic corrections (~50 accent fixes), filler word removal |
| **3** | `intent_mapper.py` | **Intent Classification** — Regex patterns classify into ORDER/CANCEL/MODIFY/CONFIRM/REPEAT/QUERY. Compound-aware: splits at conjunctions then classifies each clause independently |
| **4** | `item_matcher.py` | **Item Matching** — Hybrid `0.4×RapidFuzz + 0.6×SentenceTransformer+FAISS`. Sliding window (3→2→1 word ngrams). Dynamic corpus from DB. Disambiguation when confidence < 85% |
| **5** | `quantity_extractor.py` | **Quantity Extraction** — Position-based (3 tokens before/4 after item). Hindi/Gujarati/Marathi/English number words. Default=1, max=50 |
| **6** | `modifier_extractor.py` | **Modifier Extraction** — Spice/size/add-ons with target resolution (explicit name / positional / proximity / global "everything") |
| **7** | `order_builder.py` | **Order Building** — JSON order + KOT generation + DB persistence. 5% GST tax. KOT formatted for 32-char thermal printers |
| **+** | `session_store.py` | **Session State** — Multi-turn cart accumulation. Redis→DB→memory fallback. Handles compound intents across turns |
| **+** | `upsell_engine.py` | **Upselling** — Combo-based (association rules) + hidden star promotion. Max 2 suggestions per order |
| **+** | `pipeline_errors.py` | **Error Recovery** — Typed StageResult objects with user-facing messages. Zero-match→top-3 suggestions. Ambiguous→"Did you mean X or Y?" |

### Voice Pipeline — Detailed Module Descriptions

#### `vad.py` — Voice Activity Detection
- Silero VAD via `torch.hub` — fully local, no API calls
- Detects actual speech segments before sending to Whisper, eliminating hallucinations from kitchen sounds, music, other conversations
- `detect_speech_segments()` → list of `{start, end}` timestamps
- `extract_speech_audio()` → concatenates speech-only segments into cleaned WAV
- Config: `VAD_THRESHOLD=0.40`, `VAD_MIN_SPEECH_SEC=0.3s`, `VAD_SPEECH_PAD_MS=300ms`

#### `stt.py` — Speech-to-Text
- faster-whisper `large-v3-turbo` (~809MB), lazy-loaded and cached on first use
- Converts WebM/MP3/M4A/OGG/FLAC → 16kHz WAV mono via ffmpeg
- CUDA auto-detected, falls back to CPU + int8 quantization
- Initial prompt biases Whisper toward romanized Hindi food vocabulary
- Returns: `{transcript, detected_language, language_confidence, transcription_confidence, is_low_confidence, segments, vad_info}`
- `warmup()` called at server startup to pre-load model

#### `normalizer.py` — Text Normalization
- Devanagari → romanized (70+ character mappings)
- Phonetic corrections: ~50 Indian-accent STT mishearing fixes (`"chikan"→"chicken"`, `"biriyani"→"biryani"`)
- Hindi number words (ek/do/teen/char/paanch + Gujarati/Marathi variants) → digits
- Filler word removal: ~40 words across all supported languages (`umm`, `bhai`, `yaar`, `please`, `ok`, etc.)

#### `intent_mapper.py` — Intent Classification
- Pure regex, no ML. Priority order: CANCEL > CONFIRM > MODIFY > REPEAT > QUERY > ORDER
- **Compound intents**: `"Cancel the naan but keep the dal"` → `[CANCEL(naan), ORDER(dal)]`
- Splits at: commas, semicolons, `but/lekin`, `and/aur`, `then/phir`, `instead`, etc.
- Only splits if both resulting clauses have ≥2 words (prevents false splits)

#### `item_matcher.py` — Hybrid Item Matching
- **Blend**: `final_score = 0.4 × RapidFuzz(token_sort_ratio) + 0.6 × FAISS(cosine)`
- Model: `paraphrase-multilingual-MiniLM-L12-v2` — handles English/Hindi/Hinglish/Devanagari natively
- FAISS `IndexFlatIP` built once at startup from all corpus entries (DB names + Hindi names + aliases)
- Sliding window: 3-word → 2-word → 1-word ngrams with per-size confidence thresholds (0.85/0.78/0.75)
- `rebuild_index(db)` endpoint to refresh after menu changes
- Graceful fallback to fuzzy-only if SentenceTransformer fails to load

#### `modifier_extractor.py` — Modifier Extraction with Target Resolution
- Categories: `spice_level` (mild/medium/hot), `size` (small/large), `add_ons` (no_onion, no_garlic, extra_butter, extra_cheese, no_sauce)
- **Target resolution priority**: Global ("everything/sab mein") → Explicit name ("make the biryani spicy") → Positional ("last one", "first one") → Proximity (nearest mentioned item) → Unresolved
- Cross-checks against `MenuItem.modifiers` JSONB from DB — only allows modifiers the item supports

#### `session_store.py` — Persistent Session Store
- **3-tier backend**: Redis (native TTL `SETEX`) → PostgreSQL `VoiceSession` table → in-memory `OrderedDict`
- 30-min timeout, max 500 sessions (prevents memory leaks)
- Cart mutations: `_apply_order()` merges/increments, `_apply_cancel()` removes/clears, `_apply_modify()` replaces, `_apply_modify_targeted()` applies per-item modifier
- `update_session_compound()` applies multiple intents sequentially

#### `pipeline_errors.py` — Structured Error Recovery
- `StageResult` dataclass: `{status, error_type, user_message, data, suggestions}`
- Properties: `is_ok`, `is_partial`, `is_failure`
- Error types: `ERR_NO_SPEECH`, `ERR_AUDIO_TOO_SHORT`, `ERR_LOW_CONFIDENCE_STT`, `ERR_STT_MODEL_ERROR`, `ERR_ZERO_MATCHES`, `ERR_AMBIGUOUS_MATCH`, `ERR_MODIFIER_UNSUPPORTED`, `ERR_ITEM_OUT_OF_STOCK`, `ERR_PIPELINE_STAGE_FAILED`
- User messages are displayed directly on the frontend

#### `voice_config.py` — Centralized Configuration Singleton
- `cfg = VoiceConfig()` — imported everywhere, all params env-overridable
- ~40 parameters grouped by module: STT, VAD, Item Matcher, Quantity, Order Builder, Session, Upsell

---

## 6. Revenue Intelligence Pipeline (8 Modules)

Orchestrated by `analyzer.py` → `run_full_analysis()`:

| Module | What It Does |
|---|---|
| `contribution_margin.py` | CM = Selling Price − Food Cost. Tiers: high (≥65%), medium (50-65%), low (<50%) |
| `popularity.py` | 30-day sales velocity. Normalized 0–1 using `mean×2` ceiling (robust, handles outliers like Butter Naan in 70% of orders). Tiers: high/medium/low |
| `menu_matrix.py` | BCG quadrant: ⭐Star (high margin + high pop), 🐴Plowhorse (low margin + high pop), 🧩Puzzle (high margin + low pop), 🐕Dog (low margin + low pop). Each gets actionable advice |
| `hidden_stars.py` | Top 70th percentile margin + bottom 30th percentile popularity. `opportunity_score = margin_pct/100 × (1−pop_score) × 100`. Actionable suggestions generated per item |
| `combo_engine.py` | FP-Growth association rules → combo bundles. `combo_score = lift×1.5 × avg_cm × confidence×2.0 × diversity_multiplier`. Dynamic discount 5–25%. Background 24h retraining scheduler. Category diversity bonus (1.5× for 3+ categories). Thread-safe |
| `price_optimizer.py` | Rule-based price nudges by BCG quadrant. Plowhorse→ increase, Dog→ increase to recover margin, Puzzle→ small decrease, Star→ hold. Prices rounded to ₹5 |
| `advanced_analytics.py` | Cannibalization detection (>20% decline after new item launch), price sensitivity simulation (5/8/10% increase scenarios), waste/void analysis, repeat customer estimation, menu complexity scoring (>7 items/category = alert), operational metrics (AOV, peak hours, order type breakdown) |
| `trend_analyzer.py` | WoW/MoM revenue changes, price elasticity estimation (from historical price changes), seasonal patterns (CV>0.5 over 6 months), BCG quadrant drift detection. Batch-optimized SQL queries |

### Revenue Pipeline — Detailed Algorithms

#### `analyzer.py` — Health Score Formula
```
Health Score (0–100):
  + Margin Component:   0–40 pts  (target: avg margin ≥ 60%)
  − Dog Penalty:        0–20 pts  (each Dog quadrant item penalizes)
  + Star Ratio:         0–25 pts  (% of items that are Stars)
  + Hidden Star Bonus:  0–15 pts  (revenue uplift potential)
```

#### `combo_engine.py` — Scoring & Pricing
```
combo_score = (lift × 1.5) × avg_cm_consequent × (confidence × 2.0) × diversity_multiplier
  diversity_multiplier = 1.5 (3+ categories), 1.2 (2 categories), 0.8 (same category)
combo_price = individual_total × (1 − discount_pct)
  discount range: 5–25% based on lift + avg margin
  price rounded to nearest ₹5
  floor: food_cost + ₹10 minimum profit
```

#### `trend_analyzer.py` — Trend Arrows
```
↑↑ > +10%  |  ↑ > +3%  |  → stable  |  ↓ < -3%  |  ↓↓ < -10%
```

---

## 7. API Endpoints

### Revenue (`/api/revenue/`) — All auth-gated
| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard` | KPIs: health score, avg margin, items at risk, uplift potential, operational metrics |
| GET | `/menu-matrix` | All items with BCG quadrant classification + summary |
| GET | `/hidden-stars` | High-margin underperformers with opportunity scores |
| GET | `/risks` | Low-margin high-volume items ranked by risk score |
| GET | `/combos` | FP-Growth combo recommendations (cached 5 min) |
| POST | `/combos/retrain` | Force retrain combo model (rate-limited 2/min) |
| GET | `/price-recommendations` | Rule-based pricing suggestions |
| GET | `/category-breakdown` | Per-category revenue and margin stats (single aggregated SQL query) |
| GET | `/trends` | Item + category + seasonal + quadrant drift trends |
| GET | `/wow-mom` | Week-over-week and month-over-month revenue changes |
| GET | `/price-elasticity` | Estimated price elasticity coefficients |
| GET | `/cannibalization` | Category cannibalization detection |
| GET | `/price-sensitivity` | Price increase simulation scenarios |
| GET | `/waste-analysis` | Waste + void rate analysis |
| GET | `/customer-returns` | Repeat customer estimation |
| GET | `/menu-complexity` | Per-category complexity scoring |
| GET | `/operational-metrics` | AOV, peak hours, order type distribution |
| GET | `/analyze`, `/margins`, `/popularity`, `/matrix`, `/pricing` | Legacy aliases |

### Voice (`/api/voice/`) — All auth-gated
| Method | Endpoint | Description |
|---|---|---|
| POST | `/transcribe` | Audio → transcript only (no order parsing), max 10MB, rate-limited 10/min |
| POST | `/process-audio` | Full pipeline: audio → parsed order + upsell, rate-limited 10/min |
| POST | `/process` | Text → full pipeline (no mic needed) |
| POST | `/confirm-order` | Save confirmed order + KOT to DB |
| GET | `/orders` | Paginated recent orders |
| POST | `/rebuild-index` | Force-rebuild FAISS semantic index after menu changes |
| POST | `/order` | Legacy backward-compatible endpoint |

### Auth — Public
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | PIN (4-6 digit, numeric) → JWT token + staff info |

### Health — Public
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check with pipeline status |
| GET | `/health` | Root health alias |

---

## 8. Backend — Core Files

### `main.py` — Application Entry Point
- FastAPI `v0.2.0` with async lifespan context manager
- **Startup sequence**: Create DB tables → Warmup Whisper → Warmup SentenceTransformer → Load VoicePipeline from DB → Start combo scheduler
- Rate limiter: `slowapi` (60 req/min default, env-overridable)
- CORS: configurable via `CORS_ORIGINS` env var, defaults to localhost:5173/3000
- Global exception handler: logs + returns `{"error": "Internal server error", "detail": ...}`
- Auth gated via `Depends(require_auth)` on both routers

### `database.py` — Database Connection
- Reads `DATABASE_URL` from `.env` → Supabase PostgreSQL
- Fallback to `backend/petpooja.db` (SQLite) if `DATABASE_URL` not set
- PostgreSQL: `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, `pool_recycle=300s`
- `get_db()` FastAPI dependency — yields session, always closes in `finally`

### `models.py` — ORM Models (344 lines, 13 models)
All models use `_utcnow()` for timezone-aware timestamps.

| Model | Table | Notes |
|---|---|---|
| `Staff` | `staff` | Roles: waiter/cashier/manager/chef. PIN stored as SHA256 hash |
| `Category` | `categories` | Hindi name, display ordering |
| `MenuItem` | `menu_items` | Computed `contribution_margin` and `margin_pct` properties |
| `SaleTransaction` | `sale_transactions` | Analytics data source |
| `Order` | `orders` | Full lifecycle tracking |
| `OrderItem` | `order_items` | Line items with applied modifiers |
| `KOT` | `kots` | `print_ready` plain text for thermal printers |
| `ComboSuggestion` | `combo_suggestions` | FP-Growth result cache |
| `RestaurantTable` | `restaurant_tables` | Real-time table status |
| `Shift` | `shifts` | Cash session tracking |
| `Ingredient` | `ingredients` | `is_low_stock` computed property |
| `MenuItemIngredient` | `menu_item_ingredients` | Recipe BOM |
| `StockLog` | `stock_logs` | Inventory audit trail |
| `VoiceSession` | `voice_sessions` | `to_dict()` / `from_dict()` helpers |

### `api/auth.py` — JWT Authentication
- `create_token(staff_id, role, shift_end)` — expiry = min(shift_end, 8 hours hard cap)
- `verify_token(token)` — decodes JWT, raises 401 on expired/invalid
- `require_auth()` — when `AUTH_ENABLED=false` (default), returns dummy manager payload
- `require_role(*allowed_roles)` — factory returning role-gating dependency (403 if unauthorized)
- `authenticate_staff(pin, db)` — SHA256 PIN verification + JWT issuance

### `api/rate_limit.py` — Sliding Window Rate Limiter
- In-process, no Redis dependency for rate limiting
- Keys by `(client_ip, route_group)` where groups are `voice`, `revenue`, `default`
- Respects `X-Forwarded-For` for proxy deployments
- Defaults: voice=20 RPM, revenue=60 RPM, default=120 RPM

---

## 9. Frontend Architecture

### Routing (React Router v6)
```
/                    → Landing.jsx
/about               → AboutUs.jsx
/login               → Login.jsx
/dashboard           → DashboardLayout (sidebar + outlet)
  /dashboard         → Dashboard.jsx
  /dashboard/menu-analysis  → MenuAnalysis.jsx
  /dashboard/combos         → ComboEngine.jsx
  /dashboard/voice-order    → VoiceOrder.jsx
```

### Pages — Detailed

#### `Landing.jsx` — Public Marketing Page
- Hero: 3 image slideshow (5s interval), `BlurText` animated title, `TypewriterText` rotating tagline
- Sections: Navbar, hero split layout, infinite marquee of restaurant names, 4 feature cards (numbered), about preview with stats, CTA section, contact (email/phone/location), footer with link columns
- State: `activeSlide`, `fadeClass`, `titleLoaded`
- Fully i18n'd — all text via `t()` translation function

#### `Login.jsx` — Authentication Page
- Two `LightRays` WebGL components as background (mouse-follow enabled)
- Split layout: left (background image + branding), right (form)
- State: `email`, `password`, `loading`, `showPassword`, `error`
- Auth: Uses `useAuth().login()` — 1.2s simulated delay, stores in localStorage, navigates to `/dashboard`
- Note: Currently client-side only (no real PIN verification on frontend)

#### `Dashboard.jsx` — Analytics Hub (525 lines)
- Loads 12 API calls in parallel via `Promise.all` at mount
- 8 KPI MetricCards in 2 rows (Health Score, Avg Margin, Star Items, Hidden Stars, Total Items, Dog Items, Combo Suggestions, Price Actions)
- Collapsible health score breakdown panel
- Recharts `BarChart` (category CM%), `AreaChart` (peak hours), `PieChart` (revenue by category)
- Panels: hidden stars, risk items, quadrant drift alerts, WoW/MoM table, price elasticity table, cannibalization alerts, price sensitivity simulations, waste/void analysis, customer returns, menu complexity grid, seasonal patterns chart

#### `MenuAnalysis.jsx` — BCG Analysis
- 4 clickable quadrant summary cards act as toggle filters
- `MenuMatrix` Recharts scatter chart (color-coded by quadrant)
- `ItemTable` with category + quadrant filters, sortable, shows trend arrows
- Enriches items with trend data from second API call

#### `ComboEngine.jsx` — AI Combos
- Discount % slider/input, "Retrain Model" button with separate loading state
- `ComboCard` grid
- Price recommendations table with quadrant-based strategies

#### `VoiceOrder.jsx` — Full Voice Ordering Flow
- `sessionId` via `useRef` (persists across renders, random UUID on mount)
- Supports both audio (`VoiceRecorder` → `transcribeAudio`) and text input (`submitTextOrder`)
- Displays: transcript → normalized text → detected language → intent → session state
- Matched items table: name, quantity, price, confidence badge (color-coded), modifiers, stock warnings
- Disambiguation card when confidence < threshold
- Full cart accumulation display across turns
- `OrderSummary` + `KOTTicket` shown side by side after order parsing
- Upsell suggestions banner
- Confirm Order → calls `confirmOrder` → clears local state (not session)
- New Order → generates new `sessionId`
- Error handling: specific messages for 503 (STT unavailable) and 422 (unrecognized)

### Components — Detailed

| Component | Key Props | What It Renders |
|---|---|---|
| `Navbar` | — | Glassmorphic nav, scroll-based transparency, language dropdown (5 langs), auth-aware CTA |
| `MetricCard` | `label, value, suffix, color, icon` | KPI card with large number + emoji |
| `MenuMatrix` | `items[]` | Recharts ScatterChart, color by quadrant, custom tooltip |
| `ItemTable` | `items[], categoryFilter, quadrantFilter` | Sortable table, click-to-sort, quadrant tags, popularity bars, trend arrows |
| `ComboCard` | `combo{}` | Association rule display, confidence bar, pricing/discount breakdown |
| `VoiceRecorder` | `onRecorded(blob)` | Circular mic button, MediaRecorder API, `audio/webm` output, pulse animation while recording |
| `OrderSummary` | `order{}` | Order ID, line items (qty × name, veg/non-veg badge, modifiers, line total), subtotal → GST 5% → total |
| `KOTTicket` | `kot{}` | Monospace receipt: KOT ID, order type, table, timestamp, items with modifiers, "PETPOOJA AI COPILOT" footer |
| `BlurText` | `text, delay, animateBy, direction` | Framer Motion word/char blur-to-clear reveal, IntersectionObserver triggered |
| `TypewriterText` | `baseText, words[], typeDelay, deleteDelay` | Types base text then cycles through words with cursor |
| `LightRays` | `raysOrigin, raysColor, followMouse, ...` | WebGL GLSL shader light rays via OGL, `pointer-events: none` overlay |

### State Management
- Local `useState` per page (no Redux/Zustand)
- `AuthContext` — `isLoggedIn` flag in localStorage, `login()` / `logout()` methods
- `LanguageContext` — `language` persisted in localStorage, `t(key)` translation function with English fallback

### Styling
- `index.css` (1761 lines): CSS custom properties, dark theme
- Key variables: `--bg: #000`, `--accent: #d4291f`, `--orange: #ff6b35`
- Dashboard: 240px fixed sidebar + scrollable main content
- Landing: glassmorphic navbar, marquee animations, CSS grid/flex layouts
- Login: separate `Login.css` (317 lines) — 40px border-radius glassmorphic card, conic-gradient logo, gradient submit button, pill inputs
- No UI framework (no Tailwind, no MUI, no shadcn)

### i18n
- 5 languages: `en`, `hi` (Hindi), `mr` (Marathi), `kn` (Kannada), `gu` (Gujarati)
- ~70 keys per language covering: navbar, hero, features, about, CTA, contact, footer, about page, login page
- `hero_tagline_words` is an array for `TypewriterText` cycling
- Dashboard analytics pages are English-only (not yet translated)

---

## 10. Synthetic Data Design

`generate_synthetic_data.py` creates realistic, BCG-aligned test data:
- **60 menu items** across 6 categories (Starters, Main Course, Breads, Rice & Biryani, Beverages, Desserts) with Hindi names and aliases
- **180 days** of sales data (~21,000 transactions, ~110 orders/day)
- **Intentional co-occurrence patterns**: Butter Naan + Dal Makhani (70%), Cold Drink + Biryani (60%)
- **Temporal patterns**: Weekend 1.5× multiplier, lunch (12–3pm) + dinner (7–10pm) spikes
- **BCG-aligned weights**: bestsellers→high popularity, high-margin non-bestsellers→low popularity (Puzzle), dogs→very low popularity
- **Batch inserts**: 5000 rows per flush for performance
- CLI: `python data/generate_synthetic_data.py [--reset] [--days N]`

---

## 11. Key Design Decisions

1. **Fully offline** — No OpenAI, no cloud STT, no external APIs. faster-whisper, Silero VAD, sentence-transformers, and FAISS all run on CPU locally.
2. **Hybrid matching (0.4 fuzzy + 0.6 semantic)** — Phonetic mishearings like `"chikken"` rescued by semantic similarity even when edit distance fails. `"murgh"`, `"चिकन"`, `"chicken"` treated as near-synonyms.
3. **Dynamic menu from DB** — No hardcoded items. Adding to DB automatically makes items matchable and semantically indexed. `FAISS` index invalidated and rebuilt when menu changes.
4. **Multi-turn sessions with persistence** — Voice ordering accumulates cart across turns. Redis → DB → memory fallback chain. Multi-worker-safe with Redis.
5. **Hindi/Hinglish first** — Devanagari transliteration, Hindi number words, Hindi aliases, multilingual sentence-transformer.
6. **Compound intents** — `"Cancel the naan but keep the dal"` → `[CANCEL(naan), ORDER(dal)]`. Real clause splitting, not heuristics.
7. **Structured error recovery** — Every pipeline stage returns typed `StageResult` with user-facing recovery messages. Zero-match → top-3 suggestions. Ambiguous → disambiguation dialog.
8. **VAD preprocessing** — Silero VAD filters restaurant noise before Whisper, preventing hallucinations from kitchen sounds, music, background conversations.
9. **Rule-based NLP** — No LLMs for intent classification. Regex patterns with compound clause splitting. Fast, deterministic, predictable, no GPU required.
10. **FP-Growth for combos** — Real association rule mining (mlxtend), not simple co-occurrence counting. Category diversity bonus rewards cross-category bundles.
11. **BCG matrix** — Standard restaurant industry framework (Star/Plowhorse/Puzzle/Dog) adapted to automatic SQL-driven classification.
12. **Thread-safe caching** — Combo results cached 5 min with `threading.Lock`, session store max 500 sessions (LRU eviction), rate limiting per route group.
13. **Centralized config** — `voice_config.py` singleton with ~40 env-overridable parameters. Zero hardcoded magic numbers across voice modules.

---

## 12. How to Run

### Backend
```bash
cd backend
pip install -r requirements.txt

# Seed database (first time only)
python data/generate_synthetic_data.py

# Start server
python main.py
# → http://localhost:8000
# → Swagger docs: http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000 (proxies /api → :8000)
```

### Environment Variables (`backend/.env`)
```env
# Database (required for production; falls back to SQLite if missing)
DATABASE_URL=postgresql+psycopg2://user:pass@host:6543/postgres
SUPABASE_URL=https://your-project.supabase.co

# Auth (default: false = open access for development)
AUTH_ENABLED=false
JWT_SECRET=your-secret-key
JWT_DEFAULT_EXPIRY_HOURS=8

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Rate limiting
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_VOICE_RPM=20
RATE_LIMIT_REVENUE_RPM=60

# Session persistence (optional; falls back to DB, then memory)
REDIS_URL=redis://localhost:6379

# Voice pipeline tuning (all optional)
WHISPER_MODEL=large-v3-turbo
VAD_THRESHOLD=0.40
ITEM_MATCH_FUZZY_WEIGHT=0.4
ITEM_MATCH_SEMANTIC_WEIGHT=0.6
```

---

## 13. Current State

- **~46 code files, all implemented and functional** (no stubs or TODOs)
- **Built in a 48-hour hackathon** by a 4-person team
- **Production DB**: Supabase-hosted PostgreSQL (`aws-1-ap-southeast-2` region)
- **Dev fallback**: Local SQLite at `backend/petpooja.db`
- **Tests**: `test_audio.py`, `test_pipeline.py`, `test_realdb.py`, `test_changes.py`, `test_voice_config.py`

### What's Implemented
- Full voice ordering pipeline (VAD → STT → NLP → Matching → Order → KOT)
- Hybrid fuzzy + semantic item matching (SentenceTransformers + FAISS)
- Compound intent classification (clause splitting)
- Modifier target resolution (explicit/positional/proximity/global)
- Structured error taxonomy with user-facing recovery messages
- Persistent session store (Redis → DB → memory)
- FP-Growth combo mining with background scheduler
- BCG matrix + hidden stars + price optimizer + trend analysis + advanced analytics
- JWT auth with PIN-based staff login + shift-aware token expiry
- Per-IP rate limiting (slowapi + custom middleware)
- FAISS semantic index with `rebuild-index` endpoint
- 5-language i18n (en, hi, mr, kn, gu)
- WebGL light rays on login page
- Full dark-theme responsive React SPA

### Not Yet Implemented
- Local LLM for intent classification (Ollama/Qwen2 — still regex-only)
- Real backend auth validation on frontend (currently localStorage flag only)
- Docker / Docker Compose configuration
- CI/CD pipeline
- Menu CRUD endpoints (items must be added directly to DB currently)
- Table management UI
- Shift management UI
- Inventory tracking UI
