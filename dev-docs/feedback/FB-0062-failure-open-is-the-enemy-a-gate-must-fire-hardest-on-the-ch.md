### FB-0062: Failure-open is the enemy — a gate must fire HARDEST on the change that most needs it; a stage's verdict is trusted only if its canonical artifact EXISTS and matches HEAD
**Date:** 2026-06-28
**Source:** user direction

**What was said:** A visually-significant PR could reach "ready" with no visual walkthrough because (a) verify-build was short-circuited and self-certified its verdict, and (b) the visual deliverables were best-effort — §5c skipped exactly when the buffer lacked grounding or verify-build was short-circuited, i.e. it skipped most on the changes that most needed it. Close both: make the visual deliverables REQUIRED on a visually-significant change (absence → draft, never silent pass), and audit every stage skip so "the agent did it manually" never substitutes for a stage's real pipeline output.

**Synthesized rule:** Two load-bearing disciplines for any gate:
1. **No failure-open on the high-risk case.** A gate that skips when its inputs are missing/short-circuited is inverted — it goes quiet precisely when the risk is highest. The fix is to make the gate REQUIRE its output on the high-risk path (a hand-authored fallback becomes the *required* path, not an optional workaround), routing absence to the draft manifest the human already sees at the merge gate. Never a silent pass; never a hard mid-loop halt.
2. **Verdict-without-artifact == skip.** A stage's claimed verdict ("PASS", "ran") is trusted only if its canonical OUTPUT ARTIFACT exists AND matches HEAD (branch + head_sha). A PASS with no fresh artifact is a self-certified short-circuit — the missing artifact is the tell. Audit it mechanically (deterministic ground-truth helper) and route a contradicted/artifact-less claim to a re-run or a draft. Keep skips HONEST, not impossible: a docs-only / backend-only skip whose reason the diff/config backs is LEGITIMATE and must rule clean without noise.
Apply the predicate that decides "is the high-risk case in play?" from ONE shared helper stamped into the buffer, never re-derived per consumer (FB-0010 fan-out).

**Applies to:** workflow, ship pipeline, verify-build, gate design, agent self-feedback discipline

**Validation:** v1.13.0 — Feature 1 (visual-deliverable gate: verify-build mandatory capture + ship §5c required-entry + Step 7a dual-deliverable assertion) + Feature 2 (`/flow:audit-skips` + `lib/skip-audit-checks.py`). Five acceptance cases pinned by `run_visual_significance_evals.py` (11 checks) + `run_skip_audit_evals.py` (17 checks), both wired into CI.
