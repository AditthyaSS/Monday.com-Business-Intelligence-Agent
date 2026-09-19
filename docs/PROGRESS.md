# PROGRESS / HANDOFF LOG

Newest entry at the top of "Session log". Keep "Current state" always up to date.

## Current state
- **Active tool:** Antigravity (sprint build session)
- **Deadline:** 19 Sep 2026, 7:00 PM.
- **Phase:** COMPLETE — all phases built and working.
- **Real Gemini calls made today:** 0 (LLM_DISABLED=1 used for all testing)
- **Backend:** FastAPI with all endpoints (/api/health, /api/data-status, /api/chat), working with live monday data.
- **Frontend:** React + Vite built to frontend/dist, served by FastAPI.
- **Tests:** 43/43 passing.
- **Deploy:** vercel.json + api/index.py + root requirements.txt ready.

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
### Session 0 (chat, before coding)
- Read assignment PDF and email instructions; profiled both xlsx files; chose stack; wrote these docs.

### Session Sprint (Antigravity, 2026-09-19)
- Built all remaining phases in one sprint run (phases 2-8).
- Done: normalize, analytics, llm, agent loop, FastAPI main, deploy files, React frontend, tests.
- All 43 tests passing. Backend verified with live monday.com data.
- Commit: "feat: complete prototype - backend + React frontend + Vercel deploy"
