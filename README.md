# Sizzle — Restaurant Revenue & Voice Ordering

**Revenue intelligence, combo engine, and voice ordering** — runs locally with SQLite (or PostgreSQL via `DATABASE_URL`), faster-whisper STT, and optional Ollama for summaries.

---

## Project structure

```
sizzle/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLAlchemy (SQLite or Postgres)
│   ├── config.py            # Env-based config
│   ├── models.py            # ORM models
│   ├── requirements.txt
│   ├── seed_database.py     # Seed DB (run once)
│   ├── api/
│   │   ├── routes_auth.py   # Login, /me
│   │   ├── routes_ops.py    # Orders, tables, inventory, reports, settings
│   │   ├── routes_revenue.py# Dashboard, combos, pricing, analytics
│   │   └── routes_voice.py  # Transcribe, process, confirm order
│   └── modules/
│       ├── revenue/         # Analyzer, combo_engine, price_optimizer, etc.
│       └── voice/           # Pipeline, STT, item_matcher, order_builder, TTS
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── config.js        # VITE_* and app constants
│       ├── api/client.js
│       ├── pages/            # Dashboard, MenuAnalysis, ComboEngine, VoiceOrder, Orders, Tables, etc.
│       └── components/
│
└── README.md
```

---

## Quick start

### Backend

```bash
cd backend
pip install -r requirements.txt
python seed_database.py   # once, to create DB and sample data
python main.py
```

Server: `http://localhost:8000`. Without `DATABASE_URL`, SQLite is used (`backend/petpooja.db`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000` (Vite proxies `/api` to the backend).

---

## Main features

- **Revenue**: Dashboard, menu matrix, hidden stars, risks, combos, price recommendations, category breakdown, trends, advanced analytics.
- **Voice**: Record or type orders; STT (faster-whisper), item matching, modifiers, upsell; confirm order and save to DB.
- **Ops**: Orders, tables (book/settle/reserve), menu items, inventory, reports, settings.

---

## API overview

| Area        | Examples |
|------------|----------|
| Auth       | `POST /api/auth/login`, `GET /api/auth/me/{id}` |
| Ops        | `GET/POST/PATCH /api/ops/orders`, `GET/PATCH /api/ops/tables`, `GET /api/ops/settings`, `GET /api/ops/public-config` |
| Revenue    | `GET /api/revenue/dashboard`, `GET /api/revenue/combos`, `GET /api/revenue/price-recommendations`, … |
| Voice      | `POST /api/voice/transcribe`, `POST /api/voice/process`, `POST /api/voice/confirm-order` |

---

## Tech stack

| Layer   | Tech |
|--------|------|
| Backend | FastAPI, SQLAlchemy, SQLite / PostgreSQL |
| STT     | faster-whisper (local) |
| TTS     | Parler-TTS (optional) |
| LLM     | Optional Ollama for summaries |
| Frontend| React, Vite, Recharts |
