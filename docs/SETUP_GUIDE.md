# Sizzle — Complete Setup & Usage Guide

This guide walks you through **cloning the project**, **installing dependencies**, **configuring the environment**, **running the app**, and **using every feature** from scratch.

---

## Table of contents

1. [What you need (prerequisites)](#1-what-you-need-prerequisites)
2. [Clone the repository](#2-clone-the-repository)
3. [Backend setup](#3-backend-setup)
4. [Frontend setup](#4-frontend-setup)
5. [Running the application](#5-running-the-application)
6. [Using the application](#6-using-the-application)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. What you need (prerequisites)

### Required

| Tool | Version | Purpose |
|------|---------|--------|
| **Python** | 3.10 or 3.11 | Backend (FastAPI, voice pipeline, revenue modules) |
| **Node.js** | 18.x or 20.x (LTS) | Frontend (React, Vite) |
| **npm** | Comes with Node | Install frontend dependencies |
| **Git** | Any recent | Clone the repo |
| **PostgreSQL** | 14+ (or hosted) | Database. Use [Supabase](https://supabase.com) or [Neon](https://neon.tech) for a free hosted DB. |

### Optional (for full voice & AI)

| Tool | Purpose |
|------|--------|
| **Redis** | Session store for voice ordering (multi-turn cart). Without it, the app falls back to in-memory or DB-backed sessions. |
| **Ollama** + **Qwen** | LLM router and brain for voice (smarter intent and disambiguation). Without it, rule-based + FAISS still work. |
| **FFmpeg** | Used by the voice pipeline for audio conversion. If missing, some formats may fail. |

### One-time: PostgreSQL database

You need a **PostgreSQL** connection string. Easiest options:

- **Supabase:** Create a project at [supabase.com](https://supabase.com) → Settings → Database → Connection string (URI). Use the **pooler** URL (port 5432) for stability.
- **Neon:** Create a project at [neon.tech](https://neon.tech) → Connection string.

The app expects the database to exist; it will create tables and apply migrations on startup. You do **not** need to run SQL by hand for the default schema.

---

## 2. Clone the repository

```bash
git clone https://github.com/your-org/pet-pooja.git
cd pet-pooja
```

Replace `your-org/pet-pooja` with your actual repo URL if different.

---

## 3. Backend setup

### 3.1 Open a terminal in the project root, then go to the backend folder

```bash
cd backend
```

### 3.2 Create and activate a virtual environment

**Windows (PowerShell or CMD):**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your prompt.

### 3.3 Create and edit `.env`

Copy the example env file and set your values:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `backend/.env` in an editor and set at least:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | **Yes** | PostgreSQL connection string, e.g. `postgresql://user:password@host:5432/dbname`. Use `postgresql://` (not `postgres://`) for SQLAlchemy. |
| `REDIS_URL` | No | Redis URL for voice sessions, e.g. `redis://localhost:6379/0`. Omit to use in-memory/DB fallback. |
| `JWT_SECRET` | No | Secret for JWT (only if you enable auth). |
| `AUTH_ENABLED` | No | Set to `true` to require login. Default is `false` for local use. |

Optional voice/LLM (defaults work without these):

- `LLM_BASE_URL` — Ollama URL (default `http://localhost:11434`).
- `LLM_ROUTER_ENABLED` — Set to `false` to disable LLM router and use only rule-based + FAISS.
- `TTS_ENABLED` — Set to `false` to disable Edge TTS (responses will still show as text).

All supported variables are listed in `backend/.env.example`. Copy it to `backend/.env` and fill in at least `DATABASE_URL`.

### 3.4 Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, psycopg2, faster-whisper, sentence-transformers, faiss-cpu, edge-tts, redis, and other backend deps. First run may download models (e.g. Whisper, sentence-transformers); allow a few minutes and a stable internet connection.

### 3.5 Seed the database (first time or to add sample data)

From the `backend` directory:

```bash
python seed_database.py
```

This script **does not** drop or recreate tables. It **adds or reuses** data: restaurants, categories, menu items, ingredients, tables, and sample orders. Safe to run multiple times (get-or-create logic). Requires `DATABASE_URL` and an existing schema (tables are created on first `main.py` run or via your DB provider).

### 3.6 Start the backend server

```bash
python main.py
```

You should see something like:

- `Connecting to Supabase PostgreSQL: ...`
- `Uvicorn running on http://0.0.0.0:8000`

Leave this terminal open. The API and WebSocket will be at **http://localhost:8000**.

**Quick check:** Open http://localhost:8000/health in a browser. You should get a healthy JSON response.

---

## 4. Frontend setup

Use a **new terminal** (keep the backend running).

### 4.1 Go to the frontend folder

From the **project root**:

```bash
cd frontend
```

### 4.2 Install Node dependencies

```bash
npm install
```

### 4.3 Optional: frontend environment

By default, the frontend talks to the backend via Vite’s proxy at `/api` → `http://localhost:8000`. If your backend runs elsewhere, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### 4.4 Start the frontend dev server

```bash
npm run dev
```

You should see:

- `Local: http://localhost:5173/`

Open **http://localhost:5173** in your browser. The app will load and proxy API requests to the backend.

---

## 5. Running the application

### Option A: Two terminals (recommended during development)

1. **Terminal 1 — Backend:**  
   `cd backend` → activate venv → `python main.py`
2. **Terminal 2 — Frontend:**  
   `cd frontend` → `npm run dev`  
   Then open http://localhost:5173

### Option B: Windows one-command start

From the **project root** (where `start.bat` is):

```cmd
start.bat
```

This will:

- Start the backend in a new window (after killing anything on port 8000).
- Wait for the backend health check.
- Start the frontend in another window.
- Open http://localhost:3000 in your browser (if the script uses port 3000; otherwise check the frontend window for the URL).

Make sure you’ve already run backend setup (venv, `.env`, `pip install`, `seed_database.py` once) and `npm install` in `frontend` at least once.

---

## 6. Using the application

After logging in (if auth is enabled) or landing on the dashboard:

### 6.1 Dashboard

- **Route:** `/dashboard` or Home.
- **What it does:** Overview of today’s revenue, orders, average order value, and menu health.
- **Use:** Get a quick snapshot of the restaurant’s performance.

### 6.2 Menu analysis

- **Route:** `/dashboard/menu-analysis`.
- **What it does:** BCG-style matrix (Stars, Cash Cows, Question Marks, Dogs), contribution margins, and sortable item table.
- **Use:** See which items are high margin vs high volume and where to focus promotions or cuts.

### 6.3 Hidden stars

- **Route:** `/dashboard/hidden-stars`.
- **What it does:** Items with good contribution margin but lower visibility/sales.
- **Use:** Find underpromoted items worth pushing (specials, combos, staff recommendations).

### 6.4 Combo engine

- **Route:** `/dashboard/combos`.
- **What it does:** Suggests combos from order history (frequent itemsets) and shows item-level prices.
- **Use:** Create combo deals or bundles to increase average order value.

### 6.5 Voice order (same page)

- **Route:** `/dashboard/voice-order`.
- **What it does:** Record voice or type text; pipeline does STT → intent/item extraction → cart; you see live cart and can confirm.
- **Use:** Place an order by speaking (e.g. “Two butter naan, one dal makhani”) or by typing. Works with multiple languages.

### 6.6 Web call

- **Route:** `/dashboard/web-call`.
- **What it does:** Simulates a phone call in the browser: Start Call → speak → agent responds with TTS → add items → confirm order from the call.
- **Use:** Demo or use as a “call the restaurant” experience without a real phone line. Only the agent (lady) voice should speak; previous fixes ensure no duplicate voices when ending and starting a new call.

### 6.7 Orders

- **Route:** `/dashboard/orders`.
- **What it does:** List of orders; filter by status; view details.
- **Use:** Track and manage orders (e.g. pending, confirmed, settled).

### 6.8 Tables

- **Route:** `/dashboard/tables`.
- **What it does:** Floor plan of tables; seat a table, add items, settle.
- **Use:** Manage dine-in tables and link orders to tables.

### 6.9 Inventory

- **Route:** `/dashboard/inventory`.
- **What it does:** Ingredients and stock levels.
- **Use:** Monitor and update inventory for the restaurant.

### 6.10 Reports

- **Route:** `/dashboard/reports`.
- **What it does:** Revenue and performance reports over time.
- **Use:** Deeper analytics and exports if implemented.

### 6.11 Settings

- **Route:** `/dashboard/settings`.
- **What it does:** App/settings and preferences.
- **Use:** Configure restaurant or user options.

---

## 7. Troubleshooting

### Backend won’t start: `DATABASE_URL is not set`

- Create `backend/.env` from `backend/.env.example` and set `DATABASE_URL` to a valid PostgreSQL URI (`postgresql://...`).

### Backend: `ModuleNotFoundError` (e.g. `psycopg2`, `faster_whisper`)

- Ensure the virtual environment is activated and run `pip install -r requirements.txt` again from `backend`.

### Backend: schema / relation does not exist

- Run the backend once (`python main.py`); it runs migrations. If you use a fresh DB, ensure it’s empty or that you’re not pointing at the wrong database. Seed with `python seed_database.py` after tables exist.

### Seed: `duplicate key` or unique violation

- The seed script uses get-or-create logic. If you still see duplicates, you may have old rows with different constraints. Check the error for the table/column and fix or clear that table if you need a clean seed.

### Frontend: blank page or “Cannot GET /api/…”

- Ensure the backend is running on port 8000 and the frontend is using the dev server (Vite proxies `/api` to the backend). If you changed the backend port, set `VITE_API_BASE_URL` in `frontend/.env` accordingly.

### Voice: no speech recognition / STT not working

- Ensure `faster-whisper` is installed and that the first run has completed (model download). Check backend logs for Whisper/STT errors. On CPU, a smaller model (e.g. `small`) is used by default for speed.

### Voice: agent doesn’t speak (no TTS)

- If TTS is enabled, Edge TTS needs network access. If you disabled TTS, the UI will still show the agent’s text and you can use browser TTS or read it. Check `TTS_ENABLED` in backend config.

### Web call: two voices at once

- This was fixed so only the agent speaks. Ensure you’re on the latest code; clear any cached frontend build (`npm run dev` again or hard refresh).

### Port 8000 or 5173 already in use

- Stop the process using that port, or change the backend/frontend port in the backend `main.py` and in `frontend/vite.config.js` (and any proxy config).

---

## Summary checklist

- [ ] Python 3.10+ and Node 18+ installed  
- [ ] PostgreSQL (Supabase/Neon) created; `DATABASE_URL` in `backend/.env`  
- [ ] `backend`: venv created and activated, `pip install -r requirements.txt`, `python seed_database.py`, `python main.py`  
- [ ] `frontend`: `npm install`, `npm run dev`  
- [ ] Browser open to http://localhost:5173 (or the URL shown by Vite)  
- [ ] Optional: Redis for sessions; Ollama + Qwen for LLM voice; FFmpeg for audio  

For more on the voice pipeline, WebSocket stream, and calling design, see `docs/CALLING_IMPLEMENTATION_PLAN.md`.
