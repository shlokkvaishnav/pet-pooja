# 🧑‍💻 Person C: Frontend Lead (PetPooja Hackathon)

## Role Overview
**Role:** Frontend — All Pages & Components  
**Sleep Schedule:** Sleeps at the same time as Person A.

---

## 🚀 Phase 0: Everyone Together
- Git repo init, folder structure, branches
- FastAPI skeleton + React + Vite + Tailwind setup
- Install and verify all packages work on your machine
- Run a quick sanity check: React renders properly

---

## 💻 Phase 1: Core Build (Independent Work)

You own all the frontend pages, components, and the API client. You must write these from scratch.

### API Client
**`src/api/client.js`**
- Axios instance pointing to `localhost:8000`
- One exported function per API endpoint
- Uniform error handling

### Pages
**`src/pages/Dashboard.jsx`**
- Calls `GET /api/revenue/dashboard`
- **4 MetricCards:** Total Revenue | Avg CM% | Items At Risk | Uplift Potential
- **Bar chart (Recharts):** CM% per category
- **Two quick-view lists:** top 3 hidden stars + top 3 risk items

**`src/pages/MenuAnalysis.jsx`**
- **ScatterChart (Recharts):** X=popularity, Y=CM%, dot color=quadrant, dot size=units sold
- **Tooltip on hover:** item name, CM%, quadrant, action recommendation
- **Right panel:** filterable + sortable table with quadrant/category filters
- **Color Coding:** Star=green, Hidden Star=purple, Workhorse=amber, Dog=gray
- **Legend:** Quadrant legend with count per quadrant

**`src/pages/ComboEngine.jsx`**
- **Card grid:** each combo shows "If orders X → suggest Y"
- **Details:** Confidence bar, lift badge, CM gain shown per card
- **Price recommendations table:** positioned below with color-coded priority

**`src/pages/VoiceOrder.jsx`**
- **Recording UI:** Record button (MediaRecorder Web API) + status text + language badge
- **Display:** Transcript display box
- **Order Table:** Parsed items, qty, unit price, line total, subtotal
- **Upsell:** Upsell suggestion banner
- **Actions:** Confirm + Discard buttons
- **Ticket:** KOT ticket display after confirm (kot_id, timestamp, items, modifiers)

### Components
**`src/components/`**
- `MetricCard.jsx` — icon + big number + label + up/down delta
- `VoiceRecorder.jsx` — handles recording state, sends audio to API
- `OrderSummary.jsx` — live order table
- `KOTTicket.jsx` — formatted kitchen ticket UI
- `ComboCard.jsx` — single combo display
- `ItemTable.jsx` — reusable sortable table

---

## 🔗 Phase 2: Integration
- Work with Person D to fix any JSON shape mismatches between backend responses and frontend.
- Connect the voice page to Person B's live API endpoints.

---

## ✨ Phase 3: Bonus Features (If Time Remains)
- **Auto KOT display:** The KOT is already generated, just confirm it renders flawlessly in your UI.
- **Ambiguity clarification:** Add a disambiguation UI (e.g. dropdowns or modals) when the pipeline returns `needs_clarification: true` + options.

---

## 🎯 Phase 4: Demo Prep
- Participate in full dry runs together. (1 person presents, 3 watch and note issues).
- Fix anything on the frontend that breaks during the dry run.

---
**Summary Ownership at a Glance:**
`C owns → all frontend pages + all components + api/client.js`
