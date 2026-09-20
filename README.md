# Skylark BI Agent

> **A conversational business-intelligence agent for founders.** Ask questions like *"How's our pipeline looking for the energy sector this quarter?"* and get live, data-quality-aware answers from your monday.com boards — with zero spreadsheet wrangling and transparent data caveats.

Built as a hiring assignment for **Skylark Drones** (Full-Stack Engineer, AI & Agents).

- **Live Application:** [https://monday-com-business-intelligence-ag-six.vercel.app](https://monday-com-business-intelligence-ag-six.vercel.app)
- **Backend Service (Render):** [https://monday-com-business-intelligence-agent-wirr.onrender.com/api/health](https://monday-com-business-intelligence-agent-wirr.onrender.com/api/health)
- **Interactive API Documentation:** [https://monday-com-business-intelligence-agent-wirr.onrender.com/api/docs](https://monday-com-business-intelligence-agent-wirr.onrender.com/api/docs)
- **Source Repository:** [https://github.com/AditthyaSS/Monday.com-Business-Intelligence-Agent](https://github.com/AditthyaSS/Monday.com-Business-Intelligence-Agent)

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Current Architecture](#current-architecture)
3. [Key Engineering Principles](#key-engineering-principles)
4. [Implemented Features](#implemented-features)
5. [Monday.com Setup](#mondaycom-setup)
6. [Local Setup Guide](#local-setup-guide)
7. [Important API Endpoints](#important-api-endpoints)
8. [Automated Testing](#automated-testing)
9. [Error Handling & Resilience](#error-handling--resilience)
10. [Security & Privacy](#security--privacy)
11. [Production Deployment](#production-deployment)
12. [Project Structure](#project-structure)
13. [Documentation & Decision Logs](#documentation--decision-logs)
14. [Troubleshooting](#troubleshooting)
15. [Submission & Evaluation Guide](#submission--evaluation-guide)

---

## What It Does

The agent queries two live monday.com boards (**Deals** and **Work Orders**) in **read-only** mode via GraphQL, standardizes and normalizes the messy operational data in Python with pandas, and answers natural-language business questions with exact computations, coverage statistics, and data-quality caveats.

### Example Questions Supported
* *"How is our open pipeline looking overall?"*
* *"Which sectors have the highest open pipeline?"*
* *"How much have we billed vs collected on mining work orders?"*
* *"What operational issues should leadership be aware of?"*
* *"What should leadership know from the current deals and work orders?"*
* *"What is our overall data quality like?"*

### Every Response Surfacing
* **Exact Computed Metrics:** Pre-calculated in pandas (e.g. ₹67.2 Cr open pipeline, realization rates, concentration ratios).
* **Coverage Metrics:** Discloses missing data (e.g., *"Value present for 45 of 47 open deals; missing excluded from totals"*).
* **Data-Quality Caveats:** Flags operational anomalies (e.g., deals with close dates in the past, conflicting status/stage tags, top-3 concentration risks).
* **Assumptions Used:** Clearly states filter criteria, period boundaries, and GST treatment.
* **Audit Trace Panel:** Detailed inspectable trace in the UI indicating which tool was called and with which parameters.

---

## Current Architecture

The production application is decoupled into a high-performance **Vercel Edge static frontend** and a dedicated **Render FastAPI backend**.

```text
User / Browser
  │
  ▼
https://monday-com-business-intelligence-ag-six.vercel.app
  │
  ├────────────────────────┬────────────────────────────────┐
  │ GET /                  │ /api/*                         │
  ▼                        ▼                                │
Vercel CDN            Vercel Edge Rewrite                   │
(React 18 + Vite)     (vercel.json reverse proxy)           │
                           │                                │
                           ▼                                │
                   Render Web Service                       │
                   (FastAPI on Linux Uvicorn)               │
                   https://...onrender.com                  │
                           │                                │
                           ├────────────────────────────────┤
                           ▼                                ▼
                 Monday.com GraphQL API            Google Gemini API
                 (Read-Only Board Fetch)           (Tool Narration)
```

### Internal Execution Pipeline

```text
FastAPI Request (/api/chat)
  │
  ▼
In-Memory Cache & Rate Limiting Check
  │
  ▼
Monday.com GraphQL Fetch (Deals & Work Orders)
  │
  ▼
Data Normalization & Anomaly Detection (pandas)
  │
  ▼
Deterministic Analytics Engine (tools.py)
  │
  ├─► [AI Available]: Gemini Agent Loop (Selects Tools -> Receives Data -> Narrates)
  │
  └─► [Quota / Offline]: Deterministic Fallback Mode (Keyword Routing -> Direct Output)
  │
  ▼
Structured Founder-Friendly Response (Answer + Trace + Coverage + Caveats)
```

---

## Key Engineering Principles

1. **Code Cleans and Calculates; LLM Only Narrates:**
   The language model is **never** asked to perform arithmetic or sum currency over raw rows. All sums, averages, quarter boundaries, and realization ratios are strictly computed by deterministic Python functions. The LLM receives structured tool results and translates them into an executive summary.
2. **Never Treat Missing as Zero:**
   A deal with an empty value is reported as *"Value present for 45 of 47 deals; missing excluded from totals"*. Missing values are never silently converted to ₹0 or fabricated.
3. **No CSV / Excel Files at Runtime:**
   Monday.com is the sole system of record. The `.xlsx` files in `data/` serve strictly as offline reference datasets. Every live response originates from live monday.com GraphQL API calls.
4. **Resilient Degraded Mode:**
   When Google Gemini rate limits (5 RPM / daily free budget) are hit, or if `LLM_DISABLED=1` is configured, the application does not crash. It automatically switches to **Deterministic Mode**, executing the analytics tools and formatting the exact pandas results with an alert badge.
5. **Two Clean Architectural Seams:**
   * `BoardSource`: Abstracted in `backend/app/sources/base.py` (implemented via `monday_api.py`; easily swappable for mock tests or future integrations).
   * `LLMProvider`: Abstracted in `backend/app/llm/base.py` (implemented via `gemini.py`; easily swappable for OpenAI or Claude).

---

## Implemented Features

| Feature | Description | Implementation File |
| :--- | :--- | :--- |
| **Open Pipeline Analysis** | Stage breakdown, total open value, count, and top-3 deal concentration analysis. | `backend/app/analytics/tools.py` (`pipeline_summary`) |
| **Work Order Realization** | Order value, billed amounts, collected amounts, outstanding receivables, and collection realization percentage. | `backend/app/analytics/tools.py` (`work_order_summary`) |
| **Sector Overview** | Synthesizes deal pipeline and work order execution grouped by industry sector. | `backend/app/analytics/tools.py` (`sector_overview`) |
| **Leadership Brief** | Cross-board executive synthesis highlighting top risks, cash flow, stalled work orders, and high-value deals. | `backend/app/analytics/tools.py` (`leadership_brief`) |
| **Data Quality Reporting** | Identifies duplicate deals, unparseable values, past close dates, missing sectors, and status/stage conflicts. | `backend/app/analytics/tools.py` (`data_quality_report`) |
| **Fiscal Year Periods** | Standard Indian Fiscal Year calculations (Q1: Apr–Jun, Q2: Jul–Sep, Q3: Oct–Dec, Q4: Jan–Mar). | `backend/app/analytics/periods.py` |
| **Degraded Mode Fallback** | Instant keyword-routed tool execution ensuring 100% uptime when LLM quota is exhausted. | `backend/app/agent/loop.py` |
| **Bring Your Own Key (BYOK)** | Allows users to supply their personal Gemini API key in the UI settings to bypass shared daily limits. | `frontend/src/components/SettingsModal.jsx` |
| **Full Audit Trace** | Interactive expandable drawer detailing exact tool parameters, coverage ratios, and caveats for transparency. | `frontend/src/components/TraceDrawer.jsx` |

---

## Monday.com Setup

The application reads from two separate boards on monday.com:

1. **Deals Board:** Contains sales pipeline data (deals, status, masked value, close dates, stages, and sectors).
2. **Work Orders Board:** Contains execution records (serial numbers, client codes, PO dates, order amounts, billed values, and collections).

### Configuration Steps

1. In monday.com, open each board and retrieve the numeric **Board ID** from the URL:
   `https://<workspace>.monday.com/boards/<BOARD_ID>`
2. Generate a Personal API Token from **Profile → Developers → My Access Tokens** with read-only scopes (`boards:read`, `items:read`).
3. Set the following variables in your `.env` file:
   ```env
   MONDAY_API_TOKEN=your_monday_api_token_here
   MONDAY_API_VERSION=2024-01
   DEALS_BOARD_ID=1234567890
   WORK_ORDERS_BOARD_ID=0987654321
   ```
*(Note: All access is strictly **READ-ONLY**. The backend only sends GraphQL queries and will never execute GraphQL mutations).*

---

## Local Setup Guide

### Prerequisites
* **Python 3.11+** (`python --version`)
* **Node.js 18+** & **npm** (`node --version`)
* **Git**
* **monday.com API Token** with Deals & Work Orders board IDs
* **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

---

### Step 1: Clone Repository
```bash
git clone https://github.com/AditthyaSS/Monday.com-Business-Intelligence-Agent.git
cd Monday.com-Business-Intelligence-Agent
```

---

### Step 2: Set Up Python Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:
```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

---

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` in the project root:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your configuration:

| Variable | Required | Description |
| :--- | :--- | :--- |
| `MONDAY_API_TOKEN` | Yes | Monday.com Personal Access Token (read-only). |
| `MONDAY_API_VERSION` | Yes | Monday API version (e.g. `2024-01` or `2026-07`). |
| `DEALS_BOARD_ID` | Yes | Numeric Board ID for Deals. |
| `WORK_ORDERS_BOARD_ID` | Yes | Numeric Board ID for Work Orders. |
| `GEMINI_API_KEY` | Optional | Google AI Studio Gemini API Key (if omitted, app runs in deterministic mode). |
| `GEMINI_MODEL` | Optional | Primary model (e.g. `gemini-2.0-flash-lite` or `gemini-2.5-flash`). |
| `GEMINI_FALLBACK_MODEL` | Optional | Secondary fallback model when primary is unavailable. |
| `CACHE_TTL_SECONDS` | Optional | Cache duration for Monday board data (default: `300` seconds / 5 min). |
| `ANSWER_CACHE_TTL_SECONDS`| Optional | Cache duration for repeated queries (default: `21600` seconds / 6 hrs). |
| `GLOBAL_LLM_CALLS_PER_DAY` | Optional | Daily budget cap to prevent quota overrun (default: `16`). |
| `RATE_LIMIT_PER_MIN` | Optional | Rate limit per IP address per minute (default: `4`). |
| `TODAY_OVERRIDE` | Optional | Freeze reference date for deterministic testing (e.g. `2026-04-01`). |
| `LLM_DISABLED` | Optional | Set to `1` to run in offline deterministic mode without LLM calls. |

---

### Step 4: Run Backend Locally
From the repository root with your virtual environment active:

```bash
uvicorn app.main:app --reload --app-dir backend --port 8000
```

The FastAPI backend will start on **`http://localhost:8000`**.

---

### Step 5: Run Frontend Locally
In a **second terminal window**:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server will start on **`http://localhost:5173`**.

> **How Local Proxying Works:**
> `frontend/vite.config.js` is pre-configured with a development proxy that forwards all relative `/api/*` requests from Vite (`http://localhost:5173`) to FastAPI (`http://localhost:8000`). No CORS configuration or frontend code changes are needed.

---

### Step 6: Quick Local Verification

Open a new terminal or browser tab to verify local services:

```bash
# 1. Check Backend Health
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}

# 2. Check Monday.com Board Connectivity & Cache
curl http://localhost:8000/api/data-status

# 3. Interactive Swagger UI Documentation
# Open in browser: http://localhost:8000/api/docs

# 4. Open Full Application in Browser
# Open in browser: http://localhost:5173
```

---

## Important API Endpoints

All endpoints are hosted by FastAPI in `backend/app/main.py`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | **`/api/health`** | Lightweight health check returning `{"status": "ok"}`. |
| `GET` | **`/api/data-status`** | Returns live item counts, board sync status, cache age, and data quality warnings. |
| `POST` | **`/api/chat`** | Accepts conversational messages `{"messages": [{"role": "user", "content": "..."}]}` and returns analytics results + LLM narration. |
| `GET` | **`/api/docs`** | Interactive OpenAPI / Swagger UI test interface. |
| `GET` | **`/api/openapi.json`**| Raw OpenAPI 3.1 JSON schema. |
| `GET` | **`/redoc`** | Alternative ReDoc API documentation. |

---

## Automated Testing

The repository contains 53 automated unit and integration tests verifying parsers, taxonomy mappings, Indian FY quarter rules, pandas analytics calculations, error resilience, and degraded mode execution.

Tests run against a deterministic `FakeProvider` — **zero live API or LLM calls are made during test execution**.

```bash
# Run test suite from repository root
pytest backend/tests -v
```

Expected output:
```text
======================= 53 passed, 3 warnings in 14.24s =======================
```

---

## Error Handling & Resilience

| Scenario | Handled Behavior |
| :--- | :--- |
| **Monday.com Service Down / 5xx** | Returns HTTP 502 with friendly message. If a cached snapshot exists, serves cached data with a visible `stale_cache` notice. |
| **Monday.com Auth / Token Failure** | Returns HTTP 502 without leaking credentials or internal stack traces. |
| **Monday.com Rate Limit (429)** | Respects `Retry-After` header; serves cached data if available; avoids retrying fatal auth errors. |
| **Gemini Quota Exhausted / 429** | Transparently degrades to deterministic pandas calculation (`"degraded": true`). The user receives verified data without failure. |
| **Invalid Request / Empty Question** | Returns HTTP 400 with helpful guidance (`"Please enter a valid question"`). |
| **Spam / Rapid Clicking** | Per-IP sliding-window rate limiter returns HTTP 429 with retry duration. |

---

## Security & Privacy

* **Strictly Read-Only:** The monday.com integration only performs GraphQL queries (`boards`, `items_page`). Mutations are blocked at both code and API token levels.
* **Environment-Isolated Secrets:** `MONDAY_API_TOKEN` and `GEMINI_API_KEY` reside exclusively in server-side environment variables.
* **Never Committed:** `.env` is listed in `.gitignore`. `.env.example` contains only empty variable templates.
* **Zero Client-Side Exposure:** No third-party API keys or Render backend URLs are compiled into client JavaScript bundles.
* **Prompt Injection Defense:** Raw table rows are not passed into prompt text; tool results are pre-calculated in pandas and passed via structured parameters.

---

## Production Deployment

| Component | Platform | URL / Configuration |
| :--- | :--- | :--- |
| **Frontend** | **Vercel** | [https://monday-com-business-intelligence-ag-six.vercel.app](https://monday-com-business-intelligence-ag-six.vercel.app) |
| **Backend** | **Render** | [https://monday-com-business-intelligence-agent-wirr.onrender.com](https://monday-com-business-intelligence-agent-wirr.onrender.com) |
| **Proxy Routing** | `vercel.json` | Transparent edge rewrite: `/api/:path*` &rarr; Render origin |

### How Production Routing Works
1. When a user navigates to `/`, Vercel serves the compiled React Single-Page Application from `frontend/dist`.
2. When the frontend sends requests to `/api/health`, `/api/data-status`, or `/api/chat`, Vercel’s edge layer rewrites the request to the live Render FastAPI backend according to `vercel.json`:
   ```json
   {
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://monday-com-business-intelligence-agent-wirr.onrender.com/api/:path*"
       }
     ]
   }
   ```
3. The user's browser stays on the submitted Vercel URL with no cross-origin cookies or CORS complications.

---

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── agent/             # Conversational agent loop & tool orchestration
│   │   ├── analytics/         # Deterministic pandas calculations (pipeline, WO, sectors)
│   │   ├── llm/               # LLM provider interface & Google Gemini implementation
│   │   ├── normalize/         # Data cleaning, taxonomy mapping & quality reporting
│   │   ├── sources/           # Monday.com GraphQL API client & snapshot models
│   │   ├── config.py          # Pydantic settings & environment configuration
│   │   └── main.py            # FastAPI entry point & API route handlers
│   ├── requirements.txt       # Backend Python dependencies
│   └── tests/                 # 53 pytest automated unit and integration tests
├── frontend/
│   ├── src/                   # React components (Chat UI, TraceDrawer, StatusStrip, Modals)
│   ├── package.json           # Frontend dependencies (React 18, Lucide icons, etc.)
│   └── vite.config.js         # Vite configuration with local development proxy
├── data/                      # Offline reference Excel spreadsheets (not used at runtime)
├── docs/                      # Architectural decisions, data notes, and AI usage logs
│   ├── AI_USAGE.md
│   ├── DATA_NOTES.md
│   ├── DECISIONS.md
│   └── PROGRESS.md
├── .env.example               # Template for environment variables
├── .gitignore                 # Git ignore rules (secrets, venv, node_modules)
├── vercel.json                # Vercel reverse-proxy configuration to Render
└── README.md                  # Complete project documentation
```

---

## Documentation & Decision Logs

* [docs/DECISIONS.md](docs/DECISIONS.md) — Architectural trade-offs, why LangChain was rejected, Indian fiscal year conventions, and quota management strategies.
* [docs/DATA_NOTES.md](docs/DATA_NOTES.md) — Comprehensive anomaly audit of the monday.com Deals and Work Orders boards (inconsistent status values, missing fields, duplicate deals).
* [docs/PROGRESS.md](docs/PROGRESS.md) — Build log covering phase completion and testing milestones.
* [docs/AI_USAGE.md](docs/AI_USAGE.md) — Transparent disclosure of AI assistance tools (Codex, Antigravity, Google AI Studio) in accordance with assignment guidelines.

---

## Development Commands

| Component | Command | Purpose |
| :--- | :--- | :--- |
| **Backend** | `uvicorn app.main:app --reload --app-dir backend --port 8000` | Start local FastAPI server with auto-reload |
| **Frontend** | `cd frontend && npm run dev` | Start local Vite development server on port 5173 |
| **Build Frontend** | `cd frontend && npm run build` | Compile production static assets to `frontend/dist` |
| **Tests** | `pytest backend/tests -v` | Run full automated test suite (53 tests) |

---

## Troubleshooting

### 1. Monday.com Connection Errors
* **Symptom:** Status strip displays *"Monday.com connection error"* or returns HTTP 502.
* **Fix:** Verify `MONDAY_API_TOKEN` has read permissions. Confirm `DEALS_BOARD_ID` and `WORK_ORDERS_BOARD_ID` match your workspace board URLs.

### 2. Gemini Quota Limits & Degraded Mode
* **Symptom:** UI displays ⚡ *Degraded mode* badge.
* **Fix:** The free tier shared quota has been reached. Answers will still be calculated accurately using the deterministic pandas engine. To resume AI narration, click the **Settings** gear icon in the UI and enter your personal Gemini API key (BYOK).

### 3. Vercel Frontend Loads, but `/api` Fails
* **Symptom:** The chat UI loads at `https://monday-com-business-intelligence-ag-six.vercel.app`, but status shows disconnected.
* **Fix:** Check if the Render backend is waking from sleep by visiting [https://monday-com-business-intelligence-agent-wirr.onrender.com/api/health](https://monday-com-business-intelligence-agent-wirr.onrender.com/api/health). Once Render responds with `{"status":"ok"}`, Vercel proxy requests will resolve immediately.

### 4. Stale Data Notice
* **Symptom:** Agent notes that *"Data ends around 2026-04-01"*.
* **Explanation:** This is an intentional transparency feature. The sample monday.com boards contain records concluding in April 2026; the agent correctly flags that dates in the past may reflect historical performance rather than future expectations.

---

## Submission & Evaluation Guide

* **Submitted Production URL:** [https://monday-com-business-intelligence-ag-six.vercel.app](https://monday-com-business-intelligence-ag-six.vercel.app)
* **GitHub Repository:** [https://github.com/AditthyaSS/Monday.com-Business-Intelligence-Agent](https://github.com/AditthyaSS/Monday.com-Business-Intelligence-Agent)

### Key Scenarios to Evaluate
1. **Pipeline Aggregation:** Click the chip *"How's our open pipeline looking overall?"*. Notice the pre-calculated ₹67.2 Cr total, 47 deals, and top-3 deal concentration warning.
2. **Realization & GST:** Ask *"How much have we billed vs collected on mining work orders?"*. Notice the breakdown of order values, billing realization %, and collection ratios.
3. **Data Quality Awareness:** Ask *"What is our data quality like?"*. The agent surfaces past-due tentative close dates, unassigned sectors, and duplicate serial numbers.
4. **Auditability:** Click the **Trace** button beneath any response to inspect the exact parameters passed to pandas and the underlying coverage disclosures.

---

✨ Crafted with curiosity, code, and a little creative thinking by Aditthya SS Varma, for Skylark. 🪽
