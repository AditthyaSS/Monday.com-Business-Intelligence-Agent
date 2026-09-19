# PROGRESS / HANDOFF LOG

Newest entry at the top of "Session log". Keep "Current state" always up to date.

## Current state
- **Active tool:** Codex (switch to Antigravity when quota is exhausted; see protocol below)
- **Deadline:** 19 Sep 2026, 7:00 PM. **Started at:** ____ (fill in)
- **Phase:** 0 done. Next: Phase 1.

## Next 3 steps
1. Create monday boards by importing the raw xlsx files (only delete the blank first row of the Work Orders sheet).
2. Scaffold repo (layout in AGENTS.md), `.env.example`, first commit.
3. Build `BoardSource` + monday GraphQL client with cursor pagination; print row counts to verify 346 / 176 rows.

## Phase checklist (6-hour plan)
- [x] Phase 0: problem analysis, data profiling, stack decisions (docs seeded)
- [ ] Phase 1 (0:00-0:30): monday boards, tokens, repo
- [ ] Phase 2 (0:30-1:30): monday client + normalization layer
- [ ] Phase 3 (1:30-2:30): analytics tools (pipeline, revenue/billing, sector, cross-board)
- [ ] Phase 4 (2:30-3:30): agent loop, clarifying questions, caveats
- [ ] Phase 5 (3:30-4:30): chat UI
- [ ] Phase 6 (4:30-5:15): deploy + run test question set
- [ ] Phase 7 (5:15-6:00): README, Decision Log, submit (Google Form), test links in incognito

## Gotchas / things learned
- Work Orders sheet: header is on row 2 (row 1 blank).
- Deals sheet contains 2 rows with header text pasted into data cells.
- Data ends around Jan 2026; today is Sep 2026, so "this quarter" needs a stated anchor.
- Gemini free tier has low RPM/RPD: keep LLM calls per question minimal, add retry/backoff/cache.

## Tool-switch protocol (Codex <-> Antigravity)
1. Stop the current agent. Run tests. `git add -A && git commit`.
2. Update "Current state", "Next 3 steps", "Gotchas" above, plus a Session log entry.
3. Open the SAME repo folder in the other tool (File > Open Folder, repo root).
4. Paste this starter prompt:

> Read AGENTS.md, docs/PROGRESS.md, docs/DECISIONS.md and docs/DATA_NOTES.md. Summarise the
> current state in 5 lines, confirm the next 3 steps, then continue from step 1. Follow the
> working rules in AGENTS.md (update PROGRESS.md and AI_USAGE.md when done). Ask me before
> changing any decision recorded in DECISIONS.md.

5. Never run both tools editing at once.

## Session log
### Session 0 (chat, before coding)
- Read assignment PDF and email instructions; profiled both xlsx files; chose stack; wrote these docs.
- Open items: monday account/token, Gemini key + free-tier model limits (check AI Studio), GitHub repo, hosting choice.

<!-- Template for new entries:
### Session N (tool, time)
- Done:
- Decisions (link to DECISIONS.md ids):
- Broke / not working:
- Next:
-->
