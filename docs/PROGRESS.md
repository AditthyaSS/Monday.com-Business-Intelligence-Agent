# PROGRESS / HANDOFF LOG

Newest entry at the top of "Session log". Keep "Current state" always up to date.

## Current state
- **Active tool:** Antigravity (error handling & resilience)
- **Deadline:** 19 Sep 2026, 7:00 PM.
- **Phase:** COMPLETE — user-facing API error handling implemented across the board.
- **Backend:** FastAPI with structured error JSON format, sanitized user messages, HTTP status codes, degraded fallback.
- **Frontend:** React + Vite handling error cards, countdown timers, and retry actions without losing chat state.
- **Tests:** 53/53 passing (including full external error condition suite).
- **Deploy:** Vercel serverless ready.

## Next steps (post-sprint)
1. Deploy to Vercel: `vercel --prod` with env vars set in Vercel dashboard.
2. Test the 10 acceptance questions with real LLM (set GEMINI_MODEL in Vercel).
3. Write README.md (user handles, per AGENTS.md).

## Phase checklist (sprint build)
- [x] config.py (pydantic-settings, env auto-discovery)
- [x] sources/monday_api.py (already built, fixed syntax error)
- [x] normalize/common.py (parsers: number, date, text, client_id, fmt_inr)
- [x] normalize/taxonomy.py (sectors, statuses, synonyms)
- [x] normalize/deals.py (junk/dup exclusion, flags, QualityReport)
- [x] normalize/workorders.py (GST basis, anomaly flags, WOQualityReport)
- [x] analytics/periods.py (Indian FY quarters, period resolution)
- [x] analytics/tools.py (pipeline_summary, work_order_summary, sector_overview, data_quality_report, leadership_brief)
- [x] llm/base.py (LLMProvider protocol)
- [x] llm/gemini.py (Gemini SDK with manual function calling, retry, fallback)
- [x] agent/prompts.py (system prompt, tool declarations)
- [x] agent/loop.py (2-call LLM flow, degraded mode, keyword routing)
- [x] app/main.py (FastAPI: all endpoints, rate limiting, caching, static files)
- [x] api/index.py (Vercel serverless entry point)
- [x] vercel.json, .vercelignore, requirements.txt (root)
- [x] frontend/ (React + Vite: full chat UI, status strip, chips, trace panel)
- [x] tests/test_core.py (parsers, taxonomy, normalisation, periods, analytics, agent FakeProvider)
- [x] All 43 tests passing
- [x] Backend verified: /api/health, /api/data-status, /api/chat all return valid contract JSON

## Gotchas / things learned
- Work Orders sheet: header is on row 2 (row 1 blank) — monday strips this automatically.
- Deals sheet "Deal Name" column is "Name" in monday (item name stored separately).
- Work Orders column names are very long (e.g. "Amount in Rupees (Excl of GST) (Masked)").
- Duplicate detection used key columns matching; 16 exact dups found (not 12 as in DATA_NOTES — difference due to which columns used for dedup).
- Data ends April 2026 (tentative close dates go to Apr 2026); today is Sep 2026 — stale_cache=true is correct.
- `%-d` strftime not supported on Windows; use `lstrip("0")` instead.
- Uvicorn from backend/ dir needs to find .env in parent — config.py walks up to find it.
- MondayComplexityError must not be retried (unlike other MondayError); needs to raise immediately for page-size halving to work.
- Per-instance in-memory state: rate limits, LLM call counter, answer cache, data cache are all in-memory and reset on Vercel cold start. This is documented (see DECISIONS.md D_SPRINT).

## Session log
### Session Claude UI & Situational Error Handling (Antigravity, 2026-09-19)
- Redesigned the entire frontend into a Claude-inspired interface matching user reference:
  - Collapsible left sidebar with `+ New chat`, navigation links, pinned queries, chat history, and founder profile.
  - Serene warm-paper aesthetic (`#FAF9F5`), terracotta sunburst mark (`#CC5A2B`), and serif greeting ("Evening, how are things?").
  - Floating centered input capsule with toolbar (`+`, `Chat`, `Sonnet 3.5`, mic, waveform, and send arrow).
  - Quick action suggestion pills in Claude hand-drawn style (`Write`, `Learn`, `Code`, `Life stuff`, `Claude's choice`).
- Integrated vector Lottie animations from `frontend/assets`:
  - `chatbot.json`: Interactive chatbot avatar and general conversation visual.
  - `sleep.json`: Cooldown / rate-limit / Monday coffee break animation.
  - `404 error page with cat.json`: Gateway 404 / network / error handling animation.
- Replaced all bitmap images with pure SVGs in Claude hand-drawn style (Icons8 Claude hand-drawn reference).
- Implemented the user's exact situational error messages table across all 16 error and warning cases.
- All 53 pytest unit tests pass cleanly. Frontend build compiled and pushed to GitHub main.

### Session 0 (chat, before coding)
- Read assignment PDF and email instructions; profiled both xlsx files; chose stack; wrote these docs.

### Session Sprint (Antigravity, 2026-09-19)
- Built all remaining phases in one sprint run (phases 2-8).
- Done: normalize, analytics, llm, agent loop, FastAPI main, deploy files, React frontend, tests.
- All 43 tests passing. Backend verified with live monday.com data.
- Commit: "feat: complete prototype - backend + React frontend + Vercel deploy"
