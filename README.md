# Sizzle — AI Copilot for Restaurants

<div align="center">

**Revenue intelligence, voice ordering, and real-time operations — in one dashboard.**

*Multi-language • Offline-capable STT • Web & voice ordering • BCG-style menu analytics*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)

</div>

---

## What is Sizzle?

**Sizzle** is an AI-powered restaurant copilot that helps owners and staff:

- **Understand their menu** — BCG-style matrix, contribution margins, hidden stars, and combo suggestions.
- **Take orders by voice** — Multilingual (English, Hindi, Hinglish, Gujarati, Marathi, Kannada), with real-time STT and natural responses.
- **Run the floor** — Tables, live orders, inventory, and reports in one place.
- **Improve margins** — Data-driven pricing and upsell recommendations.

Built for **hackathons and production**: PostgreSQL (Supabase), optional Redis, optional Ollama for smarter voice, and a single-command start script for Windows.

---

## Features

| Area | Capabilities |
|------|--------------|
| **Revenue intelligence** | Full pipeline: margins, popularity, BCG matrix, hidden stars, combo mining, price optimizer. |
| **Voice ordering** | faster-whisper STT, rule-based + LLM fallback, disambiguation (“which biryani?”), session cart, Edge TTS (Indian languages). |
| **Web call** | Browser-based “phone call” UI: stream audio over WebSocket, agent speaks back, confirm order from the call. |
| **Operations** | Tables (floor plan, seat, settle), orders list, inventory, reports. |
| **Frontend** | Dark theme, i18n (EN/HI/GU/MR/KN), dashboard, menu analysis, combo engine, voice order, Web call, settings. |

---

## Tech stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, SQLAlchemy, PostgreSQL (Supabase / Neon), Redis (optional) |
| **Voice STT** | faster-whisper (local, offline-capable) |
| **Voice NLP** | Rule-based + FAISS semantic matching; optional Ollama (Qwen) for router/brain |
| **Voice TTS** | Edge TTS (Microsoft neural voices, Indian languages) |
| **Frontend** | React 18, Vite 6, React Router, Recharts, Motion |

---

## Quick start

**Prerequisites:** Python 3.10+, Node.js 18+, PostgreSQL (e.g. Supabase).  
**Detailed setup:** see **[Setup & usage guide](docs/SETUP_GUIDE.md)**.

```bash
# 1. Clone
git clone https://github.com/your-org/pet-pooja.git
cd pet-pooja

# 2. Backend
cd backend
cp .env.example .env   # edit: set DATABASE_URL (and optional REDIS_URL, etc.)
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python seed_database.py  # seed data (get-or-create, safe to re-run)
python main.py           # → http://localhost:8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev              # → http://localhost:5173
```

**Windows one-liner:** from project root, run `start.bat` to start backend + frontend and open the app.

---

## Project structure

```
pet-pooja/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLAlchemy + PostgreSQL
│   ├── models.py            # ORM models
│   ├── seed_database.py     # Seed data (restaurants, menu, orders)
│   ├── api/
│   │   ├── routes_auth.py   # Login / JWT
│   │   ├── routes_ops.py    # Tables, orders, inventory
│   │   ├── routes_revenue.py # Revenue & combo API
│   │   └── routes_voice.py  # Voice + WebSocket stream
│   └── modules/
│       ├── revenue/         # Analyzer, margins, matrix, combos, pricing
│       └── voice/           # STT, pipeline, LLM router, TTS, session store
├── frontend/
│   └── src/
│       ├── pages/           # Dashboard, MenuAnalysis, ComboEngine, VoiceOrder, WebCall, Tables, Orders, …
│       ├── components/      # MetricCard, MenuMatrix, VoiceRecorder, OrderSummary, …
│       └── api/             # client.js, useVoiceStream.js
├── docs/
│   ├── SETUP_GUIDE.md       # Full setup and usage
│   └── CALLING_IMPLEMENTATION_PLAN.md
├── start.bat                # Windows: start backend + frontend
└── README.md
```

---

## API overview

- **Health:** `GET /health`
- **Auth:** `POST /api/auth/login`, JWT on protected routes
- **Revenue:** `GET /api/revenue/analyze`, `/matrix`, `/hidden-stars`, `/combos`, `/pricing`
- **Operations:** `GET/POST /api/ops/tables`, `/api/ops/orders`, settle, inventory
- **Voice:** `POST /api/voice/process`, `/process-audio`, `GET /api/voice/stream` (WebSocket)

---

## Configuration

- **Backend:** `backend/.env` — `DATABASE_URL` (required), `REDIS_URL` (optional), `JWT_SECRET`, `AUTH_ENABLED`, voice/LLM options (see `docs/SETUP_GUIDE.md`).
- **Frontend:** `frontend/.env` or Vite env — `VITE_API_BASE_URL` (default `/api` with dev proxy).

---

## License

See [LICENSE](LICENSE) for details.
