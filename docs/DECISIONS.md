# DECISIONS (raw log; condense to the 2-page Decision Log at the end)

Format: ID | decision | why | rejected alternatives | status

## Decided
**D1. Import both spreadsheets into monday.com raw.** Only the blank first row of Work Orders is removed.
Why: the assignment tests handling of messy data; the agent must clean, not us. Rejected: cleaning in Excel first.

**D2. monday GraphQL API, read queries only, token server-side.** MCP kept as a possible adapter behind `BoardSource`.
Why: (a) assignment says read-only and MCP also exposes write tools, so we would need an allowlist;
(b) MCP auth is OAuth per user, awkward for a public demo needing one server credential (unverified whether a static token works);
(c) LLM calling MCP directly would bypass our cleaning layer. Trade-off: more code than MCP, less tool discovery.
Both are explicitly allowed by the PDF.

**D3. Code cleans and calculates; the LLM plans (chooses tools) and explains.**
Why: exact numbers, low token use, explainable. Rejected: dumping rows into the prompt (bad arithmetic, cost);
LLM-generated code/SQL (flexible but needs sandboxing, riskier on a public link).

**D4. Python + FastAPI + pandas + Pydantic; plain SDK tool-calling loop (no LangChain/LangGraph).**
Why: best tooling for messy data, ~100 explainable lines of loop. Rejected: Node/TS (weaker data tooling).

**D5. Gemini free tier via `google-genai`, behind `LLMProvider`.**
Why: only free option available. Observed limits (AI Studio, Sep 2026): gemini-3.8-flash = 5 RPM, ~250K TPM, 20 RPD, so about 10 questions/day.
Primary model is therefore chosen by requests/day, not by intelligence alone (candidates: gemini-3.5-flash-lite, gemini-3.6-flash, gemini-3.1-flash-lite; verify each in AI Studio and test tool calling).
Consequences: max 2 LLM calls per question, coarse tools with enum params, retry/backoff on 429, model fallback, answer cache keyed on data fingerprint,
per-IP and global daily budgets, deterministic degraded mode (see D9). Do not set temperature/top_p/top_k (deprecated). Model name to confirm.

**D9. Degraded mode (no-LLM answers).** When the free quota is exhausted the app still answers known intents (sample chips, leadership brief, keyword-routed questions)
by running the tools and rendering a deterministic template, clearly labelled. Why: a public demo must not fail just because the free quota ran out; also shows the design separates computation from narration.
Rejected: creating extra projects/keys to multiply quota (against the spirit of the free-tier limits); enabling billing (user wants zero cost).

**D6. React + Vite frontend served by the same FastAPI container.** One public link, no CORS setup.
Rejected: Streamlit/Gradio (faster but reads as a demo), separate Next.js deploy (extra deploy time).

**D7. Coding tools: Codex first, then Antigravity when quota ends.** Shared `AGENTS.md` (both read it),
handoff protocol in PROGRESS.md, every AI use logged in AI_USAGE.md.

**D8. "Leadership updates" interpretation:** a `leadership_brief` capability that returns headline numbers,
top risks, sector highlights and data caveats in a paste-ready format, on request ("prepare the leadership update").

**D10. Structured user-facing error handling and graceful fallbacks.** Never expose raw stack traces, exceptions, GraphQL errors, or API credentials to the client. External API failures are classified into user-friendly responses:
- Monday.com unavailable / network / 5xx / 429: Fall back to stale cached board data if present, prominently displaying `Data last refreshed: <timestamp>`. If no cache exists, return clear HTTP status (502, 503, 429) with structured error payload `{error: {code, message, user_message, retry_after_seconds}}`.
- Gemini API errors (429 quota, auth/config, timeout): Immediately degrade to deterministic tool computation on live Monday data with prominent explanatory banner (e.g. `⚠️ AI narration is temporarily unavailable because the AI service has reached its current usage limit. I'm showing the computed result directly from the Monday.com data.`).
- HTTP status codes: 400 for bad user requests, 429 for rate limits, 502/503 for upstream outages, 500 for unexpected internal errors (logged server-side only).
- Frontend preserves chat state, renders inline error cards, displays retry countdowns for 429, and provides retry actions.

## Data-handling assumptions (proposed defaults)
- A1. Currency INR; amounts excluding GST by default; state this in answers. Including-GST available on request.
- A2. Deal Status is more reliable than Deal Stage; on conflict, status wins and the conflict count is reported.
- A3. Missing deal values are excluded from totals and reported as coverage, never as zero.
- A4. "Quarter": Indian fiscal year (Apr-Mar) by default; always state the dates used. If the period has no data, say so.
- A5. Data recency: latest dates in data are around Jan 2026 while today is Sep 2026. Always show "data as of" and warn when a requested period has no records.
- A6. Sector synonyms handled in code, stated in the answer (e.g. "energy" -> Renewables + Powerline). "Tender"/"DSP" in Deals are not real sectors: reported as-is with a flag.
- A7. Junk rows (2 pasted-header rows, 1 null-status row) excluded from metrics and counted in caveats.
- A8. Exact duplicate rows (12 in Deals): PROPOSED to exclude from totals with disclosure; revisit after viewing them in monday.
- A9. Cross-board joins at sector / client / owner level, not deal level (no clean shared key). Client code matched via numeric part after stripping the prefix (assumption).
- A10. Outlier awareness: report concentration (e.g. top-2 deals = 62% of open pipeline) alongside totals.
- A11. Work-order money uses a `gst_basis` parameter, default "excl". Collected and receivable exist only incl GST, so for "excl" they are derived as value / 1.18
  (flat 18% verified on every row for order amounts; assumption for collected). This is disclosed in answers. "incl" uses reported values.
- A12. Work orders: blank billed value means "not billed yet" and counts as 0 for billing metrics (deliberate exception to A3; 63 rows, disclosed).
- A13. Negative/over-billing flags use a Rs 1 tolerance to ignore floating-point noise. Real anomalies (billed > order value, negative to-be-billed) are listed, not hidden.

## Open questions
- Which Gemini model + limits are shown in AI Studio for the key?
- Hosting: Render vs Railway vs Cloud Run (decide in Phase 6; consider cold-start behaviour).
- Do we add the MCP adapter (only if time remains in the last hour)?

## Parking lot: scaling / "what I'd do with more time" (discuss at the end)
Scheduled sync to a warehouse (Postgres/DuckDB) instead of live reads per question; Redis cache; webhooks for freshness;
auth + per-user rate limits; MCP adapter; eval harness with golden questions; observability (tracing, cost per question);
streaming responses; paid LLM tier / model routing; data-quality dashboard for the boards themselves.
