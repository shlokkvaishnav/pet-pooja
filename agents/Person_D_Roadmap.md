# 🗺️ Person D — Full 48-Hour Roadmap
## Database + Combo Engine + API Routes + Order Flow

> **✅ ALL PHASES COMPLETE** — Every file is fully implemented with zero TODOs or placeholders.

### Implementation Status Summary

| File | Status | Highlights |
|---|---|---|
| `models.py` | ✅ Done | 7 ORM models (Category, MenuItem, SaleTransaction, Order, OrderItem, KOT, ComboSuggestion) + computed properties |
| `database.py` | ✅ Done | SQLite engine, SessionLocal, get_db dependency |
| `seed_data.py` | ✅ Done | 60 items, 6 categories, 180 days of orders, all co-occurrence patterns |
| `sample_menu.json` | ✅ Done | Full Hindi names + thorough aliases + realistic pricing |
| `combo_engine.py` | ✅ Done | FP-Growth pipeline + pair-counting fallback |
| `upsell_engine.py` | ✅ Done | 2 strategies (combo-based + hidden star) + DB fallback |
| `order_builder.py` | ✅ Done | build_order (with GST) + generate_kot + save_order_to_db |
| `routes_revenue.py` | ✅ Done | 10 endpoints (7 primary + 3 legacy) with combo caching |
| `routes_voice.py` | ✅ Done | 6 endpoints with Pydantic validation |
| `main.py` | ✅ Done | Async lifespan, CORS, dual router mount, health checks |

---

> **You own the backbone of the entire project.** Nothing works without your DB, your routes, and your order flow. Prioritize ruthlessly.

---

## ⏰ Timeline Overview

| Block | Hours | What |
|---|---|---|
| Phase 0 | 0–2 | Setup with team |
| Phase 1A | 2–8 | DB + Seed Data (critical path) |
| Phase 1B | 8–16 | Combo Engine + Upsell Engine |
| Phase 1C | 16–24 | All API Routes + Order Flow |
| Phase 2 | 24–36 | Integration + Bug Fixes |
| Phase 3 | 36–42 | Bonus Features |
| Phase 4 | 42–48 | Demo Prep + Final Polish |

---

## 🟢 Phase 0 — Team Setup (Hours 0–2)

> All 4 people together.

- [x] Git repo init, folder structure, branches
- [x] FastAPI skeleton + React + Vite + Tailwind setup
- [x] Install all packages on your machine:
  ```
  pip install fastapi uvicorn sqlalchemy pydantic mlxtend rapidfuzz pandas numpy
  ```
- [x] Verify FastAPI hello world runs on `localhost:8000`
- [x] Create your branch: `git checkout -b feat/backend-d`
- [x] Set up the folder structure:
  ```
  backend/
  ├── main.py
  ├── models.py
  ├── database.py
  ├── data/
  │   └── seed_data.py
  ├── modules/
  │   ├── revenue/
  │   │   └── combo_engine.py
  │   └── voice/
  │       ├── upsell_engine.py
  │       └── order_builder.py
  └── api/
      ├── routes_revenue.py
      └── routes_voice.py
  ```

---

## 🔴 Phase 1A — Database + Seed Data (Hours 2–8) ⭐ CRITICAL PATH

> **Nothing else in the project works without this.** A, B, and C are all blocked on your DB and seed data. Ship this first.

### Hour 2–4: `models.py` + `database.py`

- [x] **`database.py`** — SQLAlchemy engine + session
  ```python
  # Key items:
  - SQLite engine: sqlite:///./petpooja.db
  - SessionLocal with autocommit=False, autoflush=False
  - get_db() dependency generator (yield session, finally close)
  - Base = declarative_base()
  ```

- [x] **`models.py`** — All ORM models (7 models: Category, MenuItem, SaleTransaction, Order, OrderItem, KOT, ComboSuggestion)
  ```
  Category:
    - id, name, name_hi, display_order, is_active

  MenuItem:
    - id, category_id (FK), name, name_hi, description, aliases (pipe-separated string),
      selling_price, food_cost, modifiers (JSON string), is_veg,
      is_available (bool), is_bestseller, current_stock (nullable int), tags
    + contribution_margin and margin_pct computed properties

  SaleTransaction:
    - id, item_id (FK), order_id, quantity, unit_price, total_price, order_type, sold_at

  Order:
    - id (uuid), order_id, order_number, total_amount, status, order_type,
      table_number, source, created_at, updated_at

  OrderItem:
    - id, order_id (FK), item_id (FK), quantity, unit_price,
      modifiers_applied (JSON), line_total

  KOT:
    - id, kot_id (unique string), order_id (FK),
      items_summary (JSON), print_ready (text), created_at

  ComboSuggestion:
    - id, name, item_ids, item_names, individual_total, combo_price,
      discount_pct, expected_margin, support, confidence, lift, combo_score
  ```

- [x] Run `Base.metadata.create_all(engine)` and verify tables exist in SQLite viewer

### Hour 4–8: `data/seed_data.py` ⭐ MOST IMPORTANT FILE

> This file makes or breaks the demo. Bad data = bad charts = bad demo.

- [x] **6 categories**: Starters, Main Course (Veg), Main Course (Non-Veg), Breads, Rice & Biryani, Beverages
- [x] **60 menu items** with realistic data:
  - Every item needs: `name`, `name_hi`, `aliases`, `selling_price`, `food_cost`, `modifiers`
  - Aliases must include common misspellings and abbreviations (e.g., "paneer tikka" → "pnr tikka|panir tikka|tikka paneer")
- [x] **Margin distribution** — THIS IS CRUCIAL for Module 1:

  | Quadrant | Count | CM% Range | Sales Pattern |
  |---|---|---|---|
  | Stars | 20+ items | ≥ 65% CM | High popularity |
  | Hidden Stars | 12+ items | ≥ 65% CM | Low sales (< median) |
  | Workhorses | ~15 items | 40–65% CM | Medium-high sales |
  | Dogs | ~10 items | < 40% CM | Low sales |
  | Risk items | 8+ items | < 40% CM | HIGH sales (dangerous) |

- [x] **180 days of order history** (80–150 orders/day):
  - Butter Naan + Dal Makhani co-occur in **70%** of orders
  - Cold Drink + any Biryani co-occur in **60%** of orders
  - Weekend orders = **1.5x** weekday volume
  - Lunch spike: 12–3 PM, Dinner spike: 7–10 PM
  - Randomize but keep patterns consistent
- [x] **Run the seed script**, open the DB in SQLite viewer, verify:
  - Total items = 60
  - Total orders = ~18,000+ (180 days × ~100/day)
  - Co-occurrence patterns actually exist in the data
  - CM% distribution creates the right quadrants

### ⚠️ CHECKPOINT: Before moving on
> Push your branch. Tell Person A: "DB is ready, pull and test your algorithms." Person A is BLOCKED on you.

---

## 🟡 Phase 1B — Combo Engine + Upsell Engine (Hours 8–16)

### Hour 8–12: `modules/revenue/combo_engine.py` ⭐ HARDEST FILE

- [x] **Build basket matrix** from OrderItems:
  ```python
  # Each order = 1 row, each item = 1 column
  # Values MUST be boolean (True/False), NOT int (0/1)
  # fpgrowth will silently give wrong results with int
  ```
- [x] **Run FP-Growth**:
  ```python
  from mlxtend.frequent_patterns import fpgrowth, association_rules
  frequent = fpgrowth(basket_df, min_support=0.04, use_colnames=True)
  rules = association_rules(frequent, metric="lift", min_threshold=1.2)
  ```
- [x] **Filter rules**:
  - confidence ≥ 0.30
  - Single-item consequent only (no multi-item combos)
- [x] **Score each rule**:
  ```
  combo_score = lift × avg_cm_of_consequent × confidence
  ```
- [x] **Return top 20 combos** with: item names, confidence, lift, cm_gain, suggested bundle price
- [x] **Test**: Verify that Butter Naan + Dal Makhani shows up as a top combo (it should with 70% co-occurrence)

### Hour 12–16: `modules/voice/upsell_engine.py`

- [x] **Strategy 1 — Combo-based upsell**:
  ```
  If antecedent items ⊆ current cart AND consequent NOT in cart → suggest combo
  ```
- [x] **Strategy 2 — Hidden star promotion**:
  ```
  Top 3 hidden stars NOT already in cart → "Chef's Special" upsell
  ```
- [x] Score all suggestions, **return max 2** (never overwhelm customer)
- [x] Test with sample cart: `["Dal Makhani"]` → should suggest Butter Naan

### Hour 12–16 (parallel): `modules/voice/order_builder.py`

- [x] `build_order(parsed_items, upsells_shown)`:
  - Generate UUID for order
  - Calculate line totals and subtotal
  - Attach any accepted upsells
  - Return full order JSON (includes GST calculation)
- [x] `generate_kot(order)`:
  - Generate `kot_id` (format: `KOT-YYYYMMDD-XXXX`)
  - Format items with modifiers for kitchen display
  - Create `print_ready` text string (plain text version)
- [x] `save_order_to_db(order, db)`:
  - Write Order row
  - Write OrderItem rows
  - Write KOT row
  - Use transaction (commit at end, rollback on error)

---

## 🔵 Phase 1C — All API Routes (Hours 16–24)

### Hour 16–20: `api/routes_revenue.py` — 7 endpoints

- [x] `GET /api/revenue/dashboard`
  - Returns: total_revenue, avg_cm_percent, items_at_risk_count, uplift_potential
  - Calls Person A's `analyzer.get_full_analysis(db)`

- [x] `GET /api/revenue/menu-matrix`
  - Returns: all items with quadrant, cm_percent, popularity_score
  - Used by C's scatter chart

- [x] `GET /api/revenue/hidden-stars`
  - Returns: hidden star items with estimated_monthly_uplift, recommendation

- [x] `GET /api/revenue/risks`
  - Returns: risk items with risk_score, risk_level

- [x] `GET /api/revenue/combos`
  - Returns: top 20 combos from combo_engine
  - Cached for 5 minutes

- [x] `GET /api/revenue/price-recommendations`
  - Returns: items with current price, recommended price, reason

- [x] `GET /api/revenue/category-breakdown`
  - Returns: per-category stats (item count, avg CM%, total revenue)

- [x] `GET /api/revenue/analyze` (legacy — full analysis)
- [x] `GET /api/revenue/margins` (legacy — margins only)
- [x] `GET /api/revenue/popularity` (legacy — popularity only)

### Hour 20–24: `api/routes_voice.py` — 5 endpoints

- [x] `POST /api/voice/transcribe`
  - Accepts: audio file (multipart form)
  - Returns: `{transcript, detected_language, confidence}`
  - Calls Person B's `stt.transcribe()`

- [x] `POST /api/voice/process-audio`
  - Accepts: audio file (multipart form)
  - Returns: full pipeline result `{transcript, intent, order, upsell_suggestions}`
  - Calls `app.state.pipeline.process_audio()`

- [x] `POST /api/voice/process`
  - Accepts: `{text: string}` JSON body (Pydantic validated)
  - Returns: same as above but from text input
  - Used for testing without microphone

- [x] `POST /api/voice/confirm-order`
  - Accepts: `{order: {...}}` JSON body (Pydantic validated)
  - Calls `save_order_to_db()`, returns `{order_id, kot}`

- [x] `GET /api/voice/orders`
  - Returns: recent orders list (last 50), sorted by created_at desc

- [x] `POST /api/voice/order` (legacy endpoint)

### Hour 20–24 (parallel): `main.py`

- [x] FastAPI app initialization with async lifespan context manager
- [x] Startup event: load VoicePipeline into `app.state.pipeline`
- [x] Mount both routers:
  ```python
  app.include_router(routes_revenue.router, prefix="/api/revenue")
  app.include_router(routes_voice.router, prefix="/api/voice")
  ```
- [x] CORS middleware (allow all origins for dev)
- [x] `GET /health` and `GET /api/health` endpoints
- [x] Test ALL endpoints in Swagger UI (`/docs`)

---

## 🟣 Phase 2 — Integration (Hours 24–36)

> Work WITH the team. This is where things break.

### Hour 24–28: Wire upsell into pipeline

- [x] Connect `upsell_engine` into Person B's `pipeline.py`
  - After item matching + qty extraction, call `get_upsell_suggestions()`
  - Append results to pipeline output
- [x] Test full pipeline: audio → transcript → parsed order → upsell suggestions → KOT

### Hour 28–32: Fix JSON shape mismatches with Person C

- [x] Meet with C, compare expected vs actual JSON shapes for every endpoint
- [x] Fix any field name mismatches, missing fields, wrong types
- [x] Common issues to watch for:
  - C expects `camelCase`, you return `snake_case` → pick one and be consistent
  - C expects arrays, you return objects (or vice versa)
  - Null vs missing fields
  - Date format differences

### Hour 32–36: End-to-end testing with Person A

- [x] Test all 7 revenue endpoints with real DB data in Swagger UI
- [x] Verify scatter plot data makes sense (check quadrant distribution)
- [x] Verify combo results include expected pairs (Naan + Dal, Biryani + Cold Drink)
- [x] Fix any calculation bugs Person A finds

---

## 🟤 Phase 3 — Bonus Features (Hours 36–42)

> **You lead this phase.** Only do these if Phase 2 is solid.

- [x] **Modifier handling** — verify modifier_extractor is properly wired into pipeline, modifiers show on KOT
- [x] **Auto KOT display** — KOT is already generated, confirm it renders in C's UI
- [x] **Ambiguity clarification** — when match confidence is 60–72%, return `needs_clarification: true` + candidate options
- [x] Add `current_stock` column to MenuItem — already present in models.py

---

## ⚫ Phase 4 — Demo Prep (Hours 42–48)

> All 4 together.

- [x] Full dry run of the demo (1 presents, 3 watch)
- [x] Fix anything that breaks
- [x] **Write README.md** with:
  - Project overview
  - Setup instructions (pip install, seed DB, run backend, run frontend)
  - API documentation summary
  - Architecture diagram (text-based is fine)
- [x] Record backup video of working demo
- [x] Final `git push`

---

## 🚨 Priority Rules

### If running out of time — cut in this order:

| Cut FIRST (nice-to-have) | NEVER cut (must demo) |
|---|---|
| Price recommendations endpoint | Voice demo working end-to-end |
| Inventory signals | Combo recommendations with real data |
| Ambiguity clarification | KOT generated after voice order |
| Regional language support | All revenue dashboard endpoints |
| Category breakdown endpoint | Seed data with correct patterns |

### Your personal "never cut" list: ✅ ALL COMPLETE
1. ✅ `models.py` + `database.py` — DONE (7 models + engine/session/get_db)
2. ✅ `seed_data.py` — DONE (60 items, 180 days, all co-occurrence patterns)
3. ✅ `combo_engine.py` — DONE (FP-Growth + fallback pair counting)
4. ✅ `routes_voice.py` — DONE (6 endpoints with Pydantic validation)
5. ✅ `order_builder.py` — DONE (build_order + generate_kot + save_order_to_db)

---

## 💤 Sleep Schedule Reminder

> You sleep with Person B, **3 hours after** A + C sleep.

- When A + C go to sleep → you and B have 3 more productive hours
- Use this time for: testing, bug fixes, integration with B's pipeline
- When you wake up → A + C have been working for 3 hours already, check their PRs

---

## 📋 Quick Dependency Map

```
Person A needs from you: DB + seed data (ASAP)
Person B needs from you: upsell_engine, order_builder (Phase 2)
Person C needs from you: all API routes returning correct JSON (Phase 1C)
You need from Person A: analyzer.py functions (for revenue routes)
You need from Person B: pipeline.py, stt.py (for voice routes)
```

> **Golden rule: Ship seed_data.py in the first 6 hours. Everything else can be iterated.**
