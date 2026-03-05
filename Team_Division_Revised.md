# 👥 Team Division — PetPooja Hackathon
## 4 People | Phases Only

---

## Role Assignment

| Person | Role |
|---|---|
| **A** | Module 1 — Analysis Algorithms |
| **B** | Module 2 — NLP Voice Pipeline |
| **C** | Frontend — All Pages & Components |
| **D** | Database + Combo Engine + API Routes + Order Flow |

---

## Sleep

A + C sleep together. B + D sleep together, 3 hours later.
At no point are all 4 sleeping simultaneously.

---

## Phase 0 — Everyone Together (do this first, all 4)

- Git repo init, folder structure, branches
- FastAPI skeleton + React + Vite + Tailwind setup
- **Download Whisper "small" model right now on good WiFi** (B does this — 244MB, do not skip)
- Install and verify all packages work on everyone's machine
- Run a quick sanity check: FastAPI says hello, React renders, Whisper loads

---

## Phase 1 — Core Build (parallel, all 4 working independently)

---

### Person A — Module 1 Algorithms

Files you own and write from scratch:

**`modules/revenue/contribution_margin.py`**
- `calculate_cm(items_df)` — adds `cm_absolute`, `cm_percent`, `cm_class` to dataframe
- Classification: high (≥65%), medium (40–65%), low (<40%)

**`modules/revenue/popularity.py`**
- `score_popularity(order_items_df, days=30)` — normalized 0–100 score per item
- Formula: 40% units sold + 35% order frequency + 25% revenue generated
- Classification: star (≥70), regular (35–70), slow (<35)

**`modules/revenue/menu_matrix.py`**
- `classify_quadrant(cm_percent, popularity_score, cm_median, pop_median)` → STAR / HIDDEN_STAR / WORKHORSE / DOG
- `get_full_matrix(db)` → every menu item with quadrant assigned

**`modules/revenue/hidden_stars.py`**
- Filter: CM% > mean + 1 std dev AND popularity < median − 0.5 std dev
- Add `estimated_monthly_uplift` per item
- Add `recommendation` string per item
- `flag_risk_items(df)` — risk score formula, flags items where high volume meets low margin

**`modules/revenue/price_optimizer.py`**
- Rule-based recommendations per quadrant
- WORKHORSE: suggest price increase to hit 45% CM target
- HIDDEN STAR: no price change, visibility problem not pricing
- DOG: raise to category average or recommend removal
- STAR: check if below category 75th percentile, suggest small increase

**`modules/revenue/analyzer.py`**
- Single orchestrator: `get_full_analysis(db, days=30)`
- Calls all 4 modules above, returns one clean combined dict
- This is what the API calls — A owns this entry point

---

### Person B — Module 2 NLP Pipeline

Files you own and write from scratch:

**`modules/voice/stt.py`**
- Load `WhisperModel("small", device="cpu", compute_type="int8")` at module level — NOT inside a function
- `transcribe(audio_path)` → `{transcript, detected_language, confidence}`
- ffmpeg helper: convert WebM/MP3/M4A → WAV 16kHz mono before passing to Whisper
- **Test this first with a real recorded audio before writing anything else**

**`modules/voice/normalizer.py`**
- Hindi number words → digits (ek=1, do=2 ... das=10, bees=20)
- Hinglish food aliases dict ("pani"→"water", "roti"→"chapati", "thanda"→cold drinks category, etc.)
- Filler word removal ("umm", "bhai", "yaar", "acha", "sunlo", "bolo")
- `normalize(text)` → cleaned lowercase string

**`modules/voice/intent_mapper.py`**
- Regex pattern dict for: ORDER / MODIFY / CONFIRM / CANCEL / QUERY / REPEAT
- `classify_intent(text)` → intent string
- Fallback → "UNKNOWN" if nothing matches

**`modules/voice/item_matcher.py`**
- `build_search_corpus(menu_items)` → dict mapping every alias/hindi_name/name → item_id
- `match_item(token, corpus, threshold=72)` using RapidFuzz `WRatio` scorer
- Sliding window: try 1-word, 2-word, 3-word ngrams from transcript tokens
- Return highest confidence match across all windows
- Test with intentionally broken inputs: "pnr tikka", "dl makhni", "panir", "bttr nn"

**`modules/voice/quantity_extractor.py`**
- Look 2 tokens before + 1 token after matched item position
- Check Hindi number words + plain digits
- Default: 1

**`modules/voice/modifier_extractor.py`**
- Pattern dict: spice_level (mild/medium/hot), size (small/large), add_ons (no onion, extra butter, jain, etc.)
- Cross-check against item's allowed modifiers from DB
- `extract_modifiers(text, item_id, menu_items)` → `{spice_level, size, add_ons}`

**`modules/voice/pipeline.py`**
- `VoicePipeline` class — `__init__` loads menu corpus once
- `process_audio(audio_path)` → calls STT → normalize → intent → match → qty → modifiers → upsell → build order
- `process_text(text)` → same but skips STT (for testing without audio)
- Returns: `{transcript, intent, order, upsell_suggestions, needs_clarification}`

---

### Person C — Frontend

Files you own and write from scratch:

**`src/api/client.js`**
- Axios instance pointing to `localhost:8000`
- One exported function per API endpoint
- Uniform error handling

**`src/pages/Dashboard.jsx`**
- Calls `GET /api/revenue/dashboard`
- 4 MetricCards: Total Revenue | Avg CM% | Items At Risk | Uplift Potential
- Bar chart (Recharts): CM% per category
- Two quick-view lists: top 3 hidden stars + top 3 risk items

**`src/pages/MenuAnalysis.jsx`**
- ScatterChart (Recharts): X=popularity, Y=CM%, dot color=quadrant, dot size=units sold
- Tooltip on hover: item name, CM%, quadrant, action recommendation
- Right panel: filterable + sortable table with quadrant/category filters
- Color: Star=green, Hidden Star=purple, Workhorse=amber, Dog=gray
- Quadrant legend with count per quadrant

**`src/pages/ComboEngine.jsx`**
- Card grid: each combo shows "If orders X → suggest Y"
- Confidence bar, lift badge, CM gain shown per card
- Price recommendations table below with color-coded priority

**`src/pages/VoiceOrder.jsx`**
- Record button (MediaRecorder Web API) + status text + language badge
- Transcript display box
- Parsed order table: items, qty, unit price, line total, subtotal
- Upsell suggestion banner
- Confirm + Discard buttons
- KOT ticket display after confirm (kot_id, timestamp, items, modifiers)

**`src/components/`**
- `MetricCard.jsx` — icon + big number + label + up/down delta
- `VoiceRecorder.jsx` — handles recording state, sends audio to API
- `OrderSummary.jsx` — live order table
- `KOTTicket.jsx` — formatted kitchen ticket UI
- `ComboCard.jsx` — single combo display
- `ItemTable.jsx` — reusable sortable table

---

### Person D — Database + Combo Engine + API Routes + Order Flow

This is a full, heavy workload. You own the data layer, the hardest ML file, all API surface, and the complete order flow.

**`models.py`**
- All SQLAlchemy ORM models: Category, MenuItem, Order, OrderItem, KOT
- MenuItem must include: `name`, `name_hi`, `aliases` (pipe-separated), `selling_price`, `food_cost`, `modifiers` (JSON string)

**`database.py`**
- SQLAlchemy engine, SessionLocal, `get_db` dependency

**`data/seed_data.py`** ⭐ most important file in the project
- 60 menu items across 6 categories with realistic Hindi names + aliases
- Food costs that create: 12+ hidden stars (high CM%, low sales), 8+ risk items (low CM%, high sales), 20+ star items
- 180 days of orders, 80–150/day with realistic patterns:
  - Butter Naan appears with Dal Makhani in 70% of orders
  - Cold Drink appears with any biryani in 60% of orders
  - Weekend orders 1.5x weekday
  - Lunch (12–3pm) and dinner (7–10pm) spikes
- Run this, open SQLite viewer, manually verify the data looks right

**`modules/revenue/combo_engine.py`** ⭐ hardest file in Module 1
- Build boolean basket matrix from order_items (each order = 1 row, each item = 1 column)
- Run `fpgrowth(basket_df, min_support=0.04, use_colnames=True)` — basket MUST be boolean not int
- Run `association_rules(frequent_itemsets, metric="lift", min_threshold=1.2)`
- Filter: confidence ≥ 0.30, single-item consequent only
- Score each rule: `combo_score = lift × avg_cm_of_consequent × confidence`
- Return top 20 combos with item names, confidence, lift, cm_gain, suggested bundle price

**`modules/voice/upsell_engine.py`** — the bridge between Module 1 and Module 2
- `get_upsell_suggestions(current_order_items, menu_data, combo_rules, hidden_stars)`
- Strategy 1: if antecedent items ⊆ current cart AND consequent not in cart → combo upsell
- Strategy 2: top 3 hidden stars not already in cart → "chef's special" upsell
- Score all suggestions, return top 2 max (never overwhelm)

**`modules/voice/order_builder.py`**
- `build_order(parsed_items, upsells_shown)` → full order JSON with uuid, items, modifiers, subtotal
- `generate_kot(order)` → KOT dict with `kot_id`, formatted items, `print_ready` text string
- `save_order_to_db(order, db)` → writes Order + OrderItem rows + KOT row to DB

**`api/routes_revenue.py`** — all 7 revenue endpoints
- `GET /api/revenue/dashboard`
- `GET /api/revenue/menu-matrix`
- `GET /api/revenue/hidden-stars`
- `GET /api/revenue/risks`
- `GET /api/revenue/combos`
- `GET /api/revenue/price-recommendations`
- `GET /api/revenue/category-breakdown`

**`api/routes_voice.py`** — all voice endpoints
- `POST /api/voice/transcribe` — audio → transcript only
- `POST /api/voice/process-audio` — audio → full pipeline result
- `POST /api/voice/process` — text → full pipeline result
- `POST /api/voice/confirm-order` — save confirmed order → return order_id + KOT
- `GET /api/voice/orders` — recent orders list

**`main.py`**
- FastAPI app with startup event that loads VoicePipeline once into `app.state`
- Mount both routers
- CORS middleware
- Health check endpoint

---

## Phase 2 — Integration (after phase 1 is done)

- D wires upsell_engine into B's pipeline.py
- D + C fix any JSON shape mismatches between backend responses and frontend
- C connects voice page to B's live endpoints
- A + D test all revenue endpoints with real DB data in Swagger UI
- B tests all 3 demo scripts end to end:
  - English: "2 paneer tikka and 1 butter naan please"
  - Hindi: "Ek biryani dena aur do cold drink bhi"
  - Hinglish: "Bhai do paneer tikka extra spicy chahiye aur ek lassi"

---

## Phase 3 — Bonus Features (if time remains, D leads)

Priority order — do top ones first:

1. **Modifier handling** — verify modifier_extractor is properly wired into pipeline
2. **Auto KOT display** — KOT already generated, just confirm it renders in C's UI
3. **Ambiguity clarification** — pipeline returns `needs_clarification: true` + options when match confidence is 60–72%; C adds disambiguation UI
4. **Regional languages** — B adds Tamil/Telugu/Kannada food word aliases to normalizer (Whisper already supports it, zero model change)
5. **Inventory signals** — A adds `current_stock` column to MenuItem, hidden stars with low stock get double-flagged

---

## Phase 4 — Demo Prep (all 4 together)

- Full dry run: 1 person presents, 3 watch and note issues
- Fix anything that breaks in dry run
- D writes README with setup instructions
- Record a backup video of the working demo in case live demo fails
- Final git push

---

## Files Ownership at a Glance

```
A owns → contribution_margin, popularity, menu_matrix, hidden_stars, price_optimizer, analyzer
B owns → stt, normalizer, intent_mapper, item_matcher, quantity_extractor, modifier_extractor, pipeline
C owns → all frontend pages + all components + api/client.js
D owns → models, database, seed_data, combo_engine, upsell_engine, order_builder, routes_revenue, routes_voice, main.py
```

---

## If You're Running Out of Time — Cut This Order

| Cut first | Never cut |
|---|---|
| Price optimizer UI page | Voice demo working end-to-end |
| Regional languages | Menu Matrix scatter chart |
| Ambiguity clarification | Hidden stars with real numbers |
| Inventory signals | Combo recommendations |
| WebSocket real-time | KOT generated after voice order |
