# AGENTS.md — Skylark Monday.com BI Agent

Read this file first, then `docs/PROGRESS.md`, `docs/DECISIONS.md`, `docs/DATA_NOTES.md`, `docs/MASTER_PROMPT.md` (the phased build spec).
This file is shared by Codex and Antigravity. Do NOT create a `GEMINI.md` that contradicts it.

## What this project is
A conversational business-intelligence agent for founders. It answers questions like
"How's our pipeline looking for the energy sector this quarter?" by reading two monday.com
boards (Work Orders, Deals) live, cleaning the messy data in code, and replying with
insights AND data-quality caveats. This is a hiring assignment (Skylark Drones, Full-Stack
Engineer, AI & Agents). Evaluators judge reasoning, prioritisation and explainability more
than feature count. Deadline: 19 Sep 2026, 7:00 PM.

## Hard constraints (never violate)
1. monday.com access is READ-ONLY. Only GraphQL queries, never mutations.
2. NO hardcoded CSV/XLSX data anywhere in the app. Every answer comes from a live monday call.
3. monday token and Gemini key live in server env vars only. Never in frontend code, never committed.
4. Must handle missing/null values, mixed formats, inconsistent names, and TELL the user about data quality.
5. Ask a clarifying question when ambiguity would materially change the answer.
6. Public hosted link, working with no local setup.

## Architecture principles
- **Code cleans and calculates. The LLM only chooses tools and explains results.** Never ask the LLM to do arithmetic over raw rows.
- Every analytics tool returns `{data, coverage, caveats, assumptions_used, data_as_of}`. The answer must surface caveats.
- Missing values are excluded from totals and reported as coverage ("value present for 47 of 49 deals"). Never treat missing as zero.
- Do not silently drop rows. Anything excluded is counted and disclosed.
- At most 2 LLM calls per user question (free-tier rate limits). Prefer few, coarse tools with simple schemas and enum parameters.
- Two seams, keep them clean: `BoardSource` (monday API now, MCP adapter possible later) and `LLMProvider` (Gemini now, swappable).
- Stateless backend. Small in-memory TTL cache for monday data; always show a "data as of" timestamp.

## Stack
Python 3.11+, FastAPI, pandas, Pydantic, `google-genai` SDK, pytest, venv + pip (`backend/requirements.txt`).
Frontend: React + Vite + TypeScript + Tailwind, built and served by the same FastAPI container.
Deploy: Docker on a free host (TBD, see DECISIONS.md). No LangChain/LangGraph: plain tool-calling loop.

## Gemini rules (free tier, tiny quota)
- Use stable model IDs only (no preview, no `-latest`). Model names come from env (`GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`).
- Do NOT set `temperature`, `top_p`, `top_k` (deprecated by Google).
- Free quota is small (gemini-3.8-flash = 5 RPM, 20 requests/day). Never loop real model calls. Tests use `FakeProvider`.
- Design must survive quota exhaustion: caching, budgets, and a deterministic no-LLM "degraded mode" (docs/MASTER_PROMPT.md section 1b).

## Target layout
```
backend/app/
  main.py, config.py
  sources/   base.py (BoardSource), monday_api.py
  normalize/ common.py, deals.py, workorders.py
  analytics/ pipeline.py, revenue.py, sector.py, cross_board.py, leadership_brief.py
  llm/       base.py (LLMProvider), gemini.py
  agent/     loop.py, tools.py, prompts.py
  api/       chat.py, health.py
backend/tests/
frontend/
docs/
```

## Working rules for any coding agent
- Before starting: read the four docs above. After finishing a task: update `docs/PROGRESS.md`
  (done / next / gotchas), append to `docs/DECISIONS.md` if you made a decision, add a line to `docs/AI_USAGE.md`.
- Small commits, conventional messages (`feat:`, `fix:`, `docs:`, `test:`). Commit before ending a session.
- Never commit `.env`. Keep `.env.example` current.
- Run `pytest` before declaring a task done. Numbers must be verified against pandas on the raw files.
- Do not edit or "fix" the source spreadsheets. The mess is the test.
- If a requirement is ambiguous, document the assumption in `docs/DECISIONS.md` and proceed.
- Be able to explain every line: prefer simple, readable code over clever code.

## Definition of done (whole project)
Hosted link works; repo public; README (approach, architecture, assumptions, trade-offs, AI tools used,
challenges, improvements); Decision Log (max 2 pages); test question set with verified numbers.
