# 🍽️ Petpooja AI Copilot

**Restaurant Revenue Intelligence & Voice Ordering** — v0.1.0

> Fully offline. No external APIs. Everything runs locally with SQLite, faster-whisper, and rule-based NLP.

---

## 📂 Project Structure

```
petpooja-copilot/
│
├── backend/
│   ├── main.py                        # FastAPI app entry point
│   ├── database.py                    # SQLAlchemy engine + session (SQLite)
│   ├── models.py                      # ORM models
│   ├── requirements.txt
│   │
│   ├── data/
│   │   ├── seed_data.py               # Mock data generator — RUN FIRST
│   │   ├── restaurant.db              # SQLite DB (auto-created)
│   │   └── sample_menu.json           # 34-item menu with Hindi names
│   │
│   ├── modules/
│   │   ├── revenue/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py            # Main orchestrator
│   │   │   ├── contribution_margin.py # CM calculation + tier classification
│   │   │   ├── popularity.py          # Sales velocity + scoring
│   │   │   ├── menu_matrix.py         # BCG quadrant classification
│   │   │   ├── hidden_stars.py        # High CM, low visibility detection
│   │   │   ├── combo_engine.py        # Frequent itemset combo mining
│   │   │   └── price_optimizer.py     # Rule-based price recommendations
│   │   │
│   │   └── voice/
│   │       ├── __init__.py
│   │       ├── pipeline.py            # Main orchestrator
│   │       ├── stt.py                 # faster-whisper STT (local)
│   │       ├── normalizer.py          # Hindi/Hinglish text normalization
│   │       ├── intent_mapper.py       # Rule-based intent classification
│   │       ├── item_matcher.py        # Fuzzy matching (rapidfuzz)
│   │       ├── quantity_extractor.py  # Qty from text (En/Hi/Hinglish)
│   │       ├── modifier_extractor.py  # Spice/size/add-on extraction
│   │       ├── upsell_engine.py       # Real-time upsell from co-occurrence
│   │       └── order_builder.py       # JSON order + KOT generator
│   │
│   └── api/
│       ├── routes_revenue.py          # /api/revenue/* endpoints
│       └── routes_voice.py            # /api/voice/* endpoints
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx                    # Router + sidebar layout
│       ├── main.jsx                   # React entry point
│       ├── index.css                  # Design system (dark theme)
│       ├── api/
│       │   └── client.js              # Axios API client
│       ├── pages/
│       │   ├── Dashboard.jsx          # Overview + key metrics
│       │   ├── MenuAnalysis.jsx       # BCG matrix + item table
│       │   ├── ComboEngine.jsx        # Combo recommendation cards
│       │   └── VoiceOrder.jsx         # Voice recorder + live order
│       └── components/
│           ├── MetricCard.jsx         # KPI cards
│           ├── MenuMatrix.jsx         # 2×2 BCG scatter chart
│           ├── ItemTable.jsx          # Sortable data table
│           ├── ComboCard.jsx          # Combo suggestion card
│           ├── VoiceRecorder.jsx      # Record button + mic access
│           ├── OrderSummary.jsx       # Live order display
│           └── KOTTicket.jsx          # Kitchen order ticket UI
│
└── README.md
```

## 🚀 Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt

# Seed the database (run once)
python data/seed_data.py

# Start the server
python main.py
```

Backend runs at `http://localhost:8000`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000` (proxies API to backend)

## 📡 API Endpoints

### Revenue Intelligence

| Endpoint | Description |
|---|---|
| `GET /api/revenue/analyze` | Full revenue analysis pipeline |
| `GET /api/revenue/margins` | Contribution margins for all items |
| `GET /api/revenue/popularity` | Sales velocity & popularity scores |
| `GET /api/revenue/matrix` | BCG quadrant classification |
| `GET /api/revenue/hidden-stars` | High-margin underperforming items |
| `GET /api/revenue/combos` | Combo recommendations |
| `GET /api/revenue/pricing` | Price optimization suggestions |

### Voice Ordering

| Endpoint | Description |
|---|---|
| `POST /api/voice/order` | Process audio file (multipart) |
| `POST /api/voice/order/text` | Process text order directly |

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite |
| STT | faster-whisper (local, offline) |
| NLP | Rule-based (no external LLMs) |
| Matching | rapidfuzz (fuzzy string matching) |
| Combos | Frequent itemset mining |
| Frontend | React + Vite + Recharts |

## 📄 License

See [LICENSE](LICENSE) for details.