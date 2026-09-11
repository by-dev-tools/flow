### SV2-spike handoff clarity — wire the resolved capture mechanism into the V2 acceptance checklist
**Date:** 2026-06-08
**Branch:** `claude/v2-handoff-clarity`
**Commit:** (this PR; squash SHA at merge) — base `f5d01cf`

**What was done:**
Tightened two `dev-docs` surfaces so a cold agent picking up V2 in a fresh session inherits the SV2-spike's conclusion without re-deriving it. (1) `roadmap.md`'s "PR-1 — track V2 (capture) + V3a" acceptance checklist: the capture checkbox previously read *"verify-build (via bundled `/verify`/`/run`) … writes an `observations[]` entry per state,"* wording that predates the spike and implies `/verify` captures structurally on its own. Rewrote it to name the **capture-and-persist** step explicitly (orchestrator drives the browser-MCP screenshot → persists each frame to a flow-controlled path → path-referenced `observations[]` entry; bundled `/verify` narrates to the orchestrator but does not hand frames to the fresh-context judges; read text from the a11y tree). (2) `plan.md` Handoff Notes: added a precise "▶ V2 handoff" pointer naming the read-order (roadmap ▶ Next-up → V2 § → PR-1 block → `history.md` SV2-spike) so the next session's first doc routes it to the spec. Docs-only; no `plugins/flow/*` change, no version bump.

**Why:**
The SV2 spike resolved the screenshot-structure question and recorded it in the roadmap ▶ Next-up + V2 § + the history entry — but the *acceptance checklist* a V2 agent turns into a spec-walk still carried the pre-spike wording. That's the FB-0010 fan-out class (a contract resolved in the narrative but not in every downstream reference) applied to a spike→feature handoff: an agent following the checklist rather than the prose would have been misled into assuming `/verify` produces structured frames. Closing it before archiving this workspace, per the user's "make sure docs are updated — we'll give this to another agent in a new session" direction (an application of FB-0043 doc-currency).

**Design decisions:**
- **Tighten the checklist, not just the prose.** The V2 § already carried the resolved mechanism; the gap was specifically the PR-1 checkbox. Fixed the exact line a cold agent acts on rather than adding more narrative.
- **No new FB-XXXX.** The session's direction is an instance of existing FB-0043 (doc-currency) + FB-0010 (fan-out), not a new rule — the quality bar favors a lean feedback corpus over a near-duplicate entry.

**Tradeoffs discussed:**
- **Ship a follow-up PR vs leave the checklist imperfect and archive.** The imperfection was non-blocking (the V2 § corrects it), but the user explicitly chose to fix it from this workspace and accept a short archive delay — a clean handoff is cheap insurance against a cold agent mis-reading the one line it acts on.

**Lessons learned:**
- A spike that resolves a question some downstream **acceptance checklist** depends on should sweep that checklist in the same handoff — not only the narrative that frames it. Same grep-first-edit-second discipline as FB-0010, applied across the spike→feature seam.
