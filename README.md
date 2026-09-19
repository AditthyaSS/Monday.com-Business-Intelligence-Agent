# Skylark BI Agent

> **A conversational business-intelligence agent for founders.** Ask questions like *"How's our pipeline looking for the energy sector this quarter?"* and get live, data-quality-aware answers from your monday.com boards — no spreadsheet wrangling required.

Built as a hiring assignment for **Skylark Drones** (Full-Stack Engineer, AI & Agents).

**Live demo:** https://monday-com-business-intelligence-ag-six.vercel.app

---

## Table of Contents

1. [What it does](#what-it-does)
2. [Architecture](#architecture)
3. [Tech stack](#tech-stack)
4. [Key design decisions](#key-design-decisions)
5. [Monday.com configuration](#mondaycom-configuration)
6. [Local setup](#local-setup)
7. [Running tests](#running-tests)
8. [Deploying to Vercel](#deploying-to-vercel)
9. [AI tools used](#ai-tools-used)
10. [Known limitations & trade-offs](#known-limitations--trade-offs)
11. [Future roadmap: scaling, multi-agents & guardrails](#future-roadmap)

---

## What it does

The agent reads two monday.com boards **live** (read-only), cleans the messy data in Python, and answers natural-language questions with computed numbers + transparency notes.

**Sample questions it handles:**
- *"How's our open pipeline looking overall?"*
- *"What's our win rate by sector?"*
- *"How's the energy sector pipeline this quarter?"*
- *"How much have we billed vs collected on mining work orders?"*
- *"Give me a sector overview across deals and work orders."*
- *"Prepare a leadership update."*
- *"What's our data quality like?"*

Every answer includes:
- **Coverage** — e.g. "value present for 45 of 47 open deals"
- **Caveats** — e.g. "46 deals have close dates in the past"
- **Assumptions** — e.g. "Period: All time, status = Open only"
- **Data as of** timestamp
- **Trace panel** — which tool was called, with what params

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│   Chat UI · Status strip · Sample chips · Trace panel          │
└────────────────────────┬────────────────────────────────────────┘
                         │ POST /api/chat
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI  (app/main.py)                        │
│   Rate limit · Answer cache · Budget check · Data load          │
└────────┬───────────────────────────────────┬────────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐                ┌─────────────────────────────┐
│  BoardSource    │                │       Agent Loop            │
│  monday_api.py  │                │  loop.py · prompts.py       │
│  (read-only)    │                │  max 2 LLM calls/question   │
│  5-min cache    │                │  degraded mode fallback      │
└────────┬────────┘                └──────────┬──────────────────┘
         │ raw DataFrame                       │ tool calls
         ▼                                     ▼
┌─────────────────┐                ┌─────────────────────────────┐
│  Normalisation  │◄───────────────│    Tool Executor            │
│  deals.py       │                │    analytics/tools.py        │
│  workorders.py  │                │    pipeline_summary          │
│  common.py      │                │    work_order_summary        │
│  taxonomy.py    │                │    sector_overview           │
└─────────────────┘                │    leadership_brief          │
                                   │    data_quality_report       │
                                   └──────────┬──────────────────┘
                                              │
                                              ▼
                                   ┌─────────────────────────────┐
                                   │  LLM Provider (Gemini)      │
                                   │  gemini.py                  │
                                   │  Manual function calling     │
                                   │  Retry · fallback model      │
                                   └─────────────────────────────┘
```

### Two clean seams

| Seam | Interface | Current impl | Swap-to |
|---|---|---|---|
| `BoardSource` | `get_board(name) → Snapshot` | monday GraphQL API | MCP adapter, mock, CSV |
| `LLMProvider` | `generate(system, messages, tools) → LLMResponse` | Google Gemini | OpenAI, Anthropic, local |

### Core principle

> **Code cleans and calculates. The LLM only chooses tools and explains results.**

The LLM is never asked to do arithmetic over raw rows. Every number comes from pandas. The LLM gets a structured tool result and writes a paragraph.

---

## Tech stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, pandas, Pydantic v2, pydantic-settings |
| **LLM** | Google Gemini (`google-genai` SDK), manual function calling |
| **Data source** | monday.com GraphQL API (read-only) |
| **Frontend** | React 18, Vite, plain CSS (no framework) |
| **Deploy** | Vercel (Python serverless + React static) |
| **Tests** | pytest, FakeProvider (zero real LLM calls) |

---

## Key design decisions

### 1. Code computes, LLM narrates
Every analytics function returns `{data, coverage, caveats, assumptions_used, data_as_of}`. The LLM receives pre-computed numbers and writes the explanation. This makes answers verifiable, predictable, and cheap (few tokens).

### 2. Manual function calling (no LangChain)
The agent loop is ~150 lines of plain Python. It calls the model, parses tool calls from the response, executes them in Python, and injects results into the next message. This gives full control over call counting and error handling — critical for a 20-req/day free tier.

### 3. Tolerant data normalisation
Both boards have messy data: header rows pasted into data, duplicate rows, mixed date formats, blank values, status/stage conflicts. The normaliser handles all of this without touching the source, and reports exclusions in the quality report.

### 4. Degraded mode
When the Gemini quota is exhausted (or `LLM_DISABLED=1`), the app still answers every question using keyword routing — it picks the right analytics tool and formats the result without any LLM call. The UI shows ⚡ *Degraded mode* but never refuses to answer.

### 5. Missing values are excluded, not zeroed
A deal with no value is not treated as a ₹0 deal. Coverage is always reported: "value present for X of Y deals."

### 6. Indian fiscal year
Quarter logic uses April as FY start (Q1: Apr–Jun, Q2: Jul–Sep, Q3: Oct–Dec, Q4: Jan–Mar). Period labels include the FY year (e.g. "Q2 FY26-27").

---

## Monday.com configuration

### Boards required

| Board | Purpose | Board ID (env var) |
|---|---|---|
| **Deals** | CRM pipeline — open, won, dead deals | `DEALS_BOARD_ID` |
| **Work Orders** | Executed projects — billing, collections | `WORK_ORDERS_BOARD_ID` |

### How to find your Board IDs

1. Open the board in monday.com
2. Look at the URL: `https://app.monday.com/boards/XXXXXXXXXX`
3. The number is your Board ID

### Required column names (Deals board)

The normaliser uses tolerant matching (casefold + strip), so minor variations are OK:

| Canonical field | Accepted column names |
|---|---|
| Deal name | `Name`, `Deal Name`, `Deal Name Masked` |
| Owner | `Owner code`, `Owner` |
| Client code | `Client Code` |
| Status | `Deal Status` |
| Value | `Masked Deal value`, `Deal value` |
| Tentative close | `Tentative Close Date` |
| Actual close | `Close Date (A)`, `Close Date` |
| Stage | `Deal Stage` |
| Sector | `Sector/service`, `Sector` |

### Required column names (Work Orders board)

| Canonical field | Accepted column names |
|---|---|
| WO ID | `Serial #`, `Serial No` |
| Deal name | `Name`, `Deal Name Masked` |
| Client | `Customer Name Code`, `Client Code` |
| PO date | `Date of PO/LOI`, `PO Date` |
| Order amount (excl GST) | `Amount in Rupees (Excl of GST) (Masked)` |
| Order amount (incl GST) | `Amount in Rupees (Incl of GST) (Masked)` |
| Billed (excl GST) | `Billed Value in Rupees (Excl of GST.) (Masked)` |
| Collected (incl GST) | `Collected Amount in Rupees (Incl of GST.) (Masked)` |
| Receivable | `Amount Receivable (Masked)` |
| Sector | `Sector` |
| Execution status | `Execution Status` |
| WO Status | `WO Status (billed)`, `WO Status` |

### API token permissions

The monday.com token needs only **read** access:
- `boards:read`
- `items:read`

Go to **Profile → Developers → My Access Tokens** and generate a token with read-only scope.

---

## Local setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A monday.com account with the two boards imported
- A Google AI Studio API key (free tier works)

### 1. Clone and set up Python env

```bash
git clone https://github.com/AditthyaSS/Monday.com-Business-Intelligence-Agent.git
cd Monday.com-Business-Intelligence-Agent

python -m venv .venv
# Windows:
.venv\Scripts\pip install -r backend/requirements.txt
# macOS/Linux:
.venv/bin/pip install -r backend/requirements.txt
```

### 2. Create `.env`

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
MONDAY_API_TOKEN=your_monday_token_here
MONDAY_API_VERSION=2026-07
DEALS_BOARD_ID=your_deals_board_id
WORK_ORDERS_BOARD_ID=your_work_orders_board_id

GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.0-flash-lite
```

### 3. Run the backend

```bash
# With AI enabled (requires Gemini key):
cd backend
../.venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Without AI (degraded mode - no Gemini calls):
LLM_DISABLED=1 ../.venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Build and run the frontend

```bash
cd frontend
npm install
npm run dev        # dev server with hot reload (port 5173)
# OR
npm run build      # production build → frontend/dist/
```

Open http://localhost:5173 (dev) or http://localhost:8000 (served by FastAPI after build).

---

## Running tests

```bash
# From repo root:
.venv/Scripts/python -m pytest backend/tests/ -q

# Expected output:
# 43 passed in 1.4s
```

Tests use `FakeProvider` — zero real LLM or monday.com calls. All tests are deterministic.

**Test coverage:**
- `parse_number`, `parse_date` edge cases (blanks, suffixes, brackets)
- Taxonomy: sector synonyms, status/stage conflict detection
- Deals normalisation: junk exclusion, duplicate exclusion, flag detection
- Period boundaries: Indian FY quarters
- Analytics tools: pipeline counts, sector filter, concentration, no-data-in-period
- Work order summary: GST basis, sector filter
- Agent loop: 2-call flow, call cap enforcement, degraded mode, history trimming
- Prompt injection: deal names containing instructions are treated as data

---

## Deploying to Vercel

### One-time setup

1. Go to [vercel.com/new](https://vercel.com/new) → Import from GitHub
2. Select this repository
3. Framework: **Other**
4. Build command: `cd frontend && npm install && npm run build`
5. Output directory: `frontend/dist`
6. Add environment variables (see below)
7. Click **Deploy**

### Required environment variables

| Variable | Description |
|---|---|
| `MONDAY_API_TOKEN` | Your monday.com personal API token |
| `MONDAY_API_VERSION` | e.g. `2026-07` |
| `DEALS_BOARD_ID` | Numeric board ID |
| `WORK_ORDERS_BOARD_ID` | Numeric board ID |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `GEMINI_MODEL` | e.g. `gemini-2.0-flash-lite` |

### Optional variables (have safe defaults)

| Variable | Default | Description |
|---|---|---|
| `GLOBAL_LLM_CALLS_PER_DAY` | `16` | Daily Gemini call budget |
| `CACHE_TTL_SECONDS` | `300` | Monday data cache TTL |
| `LLM_DISABLED` | `0` | Set `1` to force degraded mode |

### Quota notes

- Free Gemini tier: ~200 requests/day
- Each question uses 2 LLM calls → ~100 questions/day with AI narration
- Beyond the daily budget: degraded mode kicks in automatically
- Same questions within 6 hours: served from cache (0 calls)

---

## AI tools used

| Tool | Used for |
|---|---|
| **Antigravity (Google Deepmind)** | Sprint build: normalisation, analytics, LLM layer, agent loop, FastAPI API, React frontend, tests |
| **Codex** | Phase 1: monday.com API client (sources/monday_api.py, tests) |
| **Google AI Studio** | Manual testing of Gemini model tool-calling behaviour |

All code is reviewed and understood. No AI-generated code was committed without verification. See `docs/AI_USAGE.md` for the full log.

---

## Known limitations & trade-offs

| Limitation | Why | Mitigation |
|---|---|---|
| ~100 AI questions/day free tier | Gemini free quota | Degraded mode always answers; answer cache; upgrade path to paid tier |
| In-memory state resets on cold start | Vercel serverless is stateless | Cache warms fast (~5s); stale cache indicator in UI |
| Data ends ~Apr 2026 | Monday.com data not yet updated | App shows "data as of" and warns when stale |
| No write access | Assignment constraint | Explicitly documented; read-only badge in UI |
| GST assumption: 18% | Standard Indian GST rate | Configurable via `gst_basis` param; disclosed in caveats |
| Sector synonyms are curated | LLM not used for synonym resolution | Synonym table in `taxonomy.py`; easy to extend |

---

## Future roadmap

### Scaling

| When | What |
|---|---|
| >100 users/day | Move from Vercel serverless to a container (Railway, Render, GCP Cloud Run) |
| >500 LLM calls/day | Upgrade to Gemini paid tier or add OpenAI as a provider |
| Real-time data | Replace 5-min cache with monday.com webhooks → push invalidation |
| Multi-board | The `BoardSource` seam is already abstracted; add boards via config |
| Shared state across instances | Add Redis for rate-limit counters, answer cache, and LLM budget tracking |

### Multi-agent architecture

The current design uses a single agent loop. A natural evolution:

```
Orchestrator Agent
├── Pipeline Analyst Agent     (specialised on Deals board)
├── Revenue Analyst Agent      (specialised on Work Orders / billing)
├── Sector Strategist Agent    (cross-board sector synthesis)
└── Data Quality Agent         (proactive anomaly detection)
```

Each sub-agent would:
- Have its own tool set and system prompt
- Return structured `{answer, confidence, caveats}` to the orchestrator
- Be swappable (different models for different tasks based on cost/capability)

Implementation path: keep the existing `LLMProvider` and `ToolExecutor` seams; wrap them in an `AgentRegistry`; add a routing layer that decides which sub-agent to invoke based on question intent classification.

### Guardrails

| Guardrail | Implementation |
|---|---|
| **Input validation** | Max 1,000 chars, role allowlist (already in place) |
| **Output validation** | Pydantic model on `/api/chat` response; numbers checked for plausibility |
| **Prompt injection defence** | Tool results are sandboxed in structured JSON; LLM instructed to treat data as data |
| **PII redaction** | Add a pre-processing step to strip client names before LLM context (client codes already used instead of names) |
| **Answer confidence** | Add a `confidence: low/medium/high` field to ToolResult; surface in UI |
| **Audit log** | Append each question + answer + tool trace to a time-series store (e.g. Supabase) for post-hoc review |
| **Model-level safety** | Gemini safety filters already applied; add topic classifier to reject non-BI questions before LLM call |
| **Rate limiting** | Per-IP sliding window (already in place); add global per-user daily quotas via JWT |

### Better explainability

- **Drill-down tool**: `find_records(filter)` → return top-10 matching deal/WO names
- **Chart generation**: add a `render_chart` tool that returns a Vega-Lite spec; frontend renders it
- **Trend over time**: add `trend_analysis(metric, periods)` tool for quarter-on-quarter comparisons
- **Proactive alerts**: daily digest email — "3 deals have close dates expiring this week"

---

*Built by Aditthya S — September 2026*
