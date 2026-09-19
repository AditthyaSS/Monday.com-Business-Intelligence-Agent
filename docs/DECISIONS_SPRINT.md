## Sprint Build Decisions (2026-09-19, Antigravity)

**D_SPRINT_1. Per-instance in-memory state on Vercel.**
Rate-limit windows, LLM call counter, answer cache, and data cache are all Python
module-level variables. On Vercel serverless, each function instance is isolated;
multiple concurrent instances do not share state. Consequence: the global daily LLM
budget is per-instance, not global; the real-world budget is effectively
`GLOBAL_LLM_CALLS_PER_DAY * num_instances`. For a low-traffic demo this is acceptable.
A Redis cache would solve this but requires a paid tier.
Documented in `.vercelignore` comments and here.

**D_SPRINT_2. Sector/column name tolerance.**
The actual monday.com column names differ from the xlsx header names used in DATA_NOTES.md.
The normalizer uses a priority-ordered list of candidate names (casefold, whitespace collapse)
so it finds the correct column regardless of minor name variation. The first match wins.

**D_SPRINT_3. Duplicate detection key columns.**
Deduplication uses: deal_name, owner, client_code, status, stage_name, value_inr.
DATA_NOTES says 12 exact duplicates; the app finds 16, because the match criteria
may differ from what was used during manual profiling. The count is disclosed in quality lines.

**D_SPRINT_4. Work orders: "Name" column is the item name.**
Monday stores the item name separately. The first column in the DataFrame is always the
item name. For work orders this is the deal name masked. The normalizer's candidate list
now includes "name" as the first candidate for both deal_name and client_code equivalent.

**D_SPRINT_5. No LangChain, no auto-function-calling.**
The agent loop is a plain while loop (max 3 iterations). Tool calls are parsed from
the Gemini response, executed in Python, and results are injected as user messages for
the next model call. This gives us full control over call counting and error handling.

**D_SPRINT_6. Frontend: no TypeScript, no Tailwind, plain JSX + CSS.**
Chosen per the spec to minimise build complexity for Vercel. The build output is
155KB JS + 8KB CSS (gzipped: 50KB + 2KB), which is fast to load.

**D_SPRINT_7. Vercel configuration.**
Uses `framework: null` (not a framework project) with a custom buildCommand.
The Python function at `api/index.py` receives all `/api/*` requests via rewrites.
The static React build is served from `frontend/dist` as the output directory.
MaxDuration 60s to allow monday.com fetches on cold start.
