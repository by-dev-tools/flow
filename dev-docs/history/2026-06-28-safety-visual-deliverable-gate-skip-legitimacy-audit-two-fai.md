### SAFETY: Visual-deliverable gate + skip-legitimacy audit — two failure-open ship-pipeline gaps closed (v1.13.0, FB-0062)
**Date:** 2026-06-28
**Branch:** claude/pensive-visvesvaraya-9ee710
**Commit:** [pending ship]

**What was done:**
Closed two related failure-open defects that let a visually-significant PR reach "ready" with no visual walkthrough — because a short-circuited verify-build self-certified its verdict and the visual deliverables were best-effort.

- **Feature 1 — visual-significance gate + mandatory dual deliverable.** New shared predicate `skills/verify-build/lib/visual-significance.py` (reused by verify-build + ship, ONE source of truth): a change is visually significant when `uiSurface != false`, the diff touches `uiFilePatterns`/asset files, and it isn't a pure no-render-delta refactor; a plan `Visual-walk` block or an explicit agent flag forces it (but `uiSurface:false` always wins, recording a suppressed override). verify-build §2c computes it and stamps `metadata.visual_significant` + `visual_signals` into the buffer; §5a makes capture mandatory when true (zero frames ⇒ §7 aggregates to `Unknown`, never PASS, with a `not_tested[]` rationale); §10 render is mandatory whenever a buffer exists + returns the report path. ship §5c removes the failure-open (a visually-significant change with no qualifying buffer entry REQUIRES a hand-authored visual-history entry — the FB-0025 workaround becomes the required path); ship §7a asserts BOTH deliverables (fresh walkthrough w/ ≥1 frame + a new visual-history entry referencing the branch) before ready, else a `[visual-deliverable]` draft entry naming the gap + the walkthrough's local path in the body handoff.
- **Feature 2 — skip-legitimacy audit.** New `/flow:audit-skips` skill (fork, read-only) + deterministic `skills/audit-skips/lib/skip-audit-checks.py`, run at ship Step 2a after the four reviewers. Per stage: LEGITIMATE (skip reason verified vs config/diff) or SHOULD-RE-RUN (reason contradicted, OR a "ran" claim whose canonical artifact is absent/stale for HEAD). Routing mirrors audit-coverage: auto-resolvable → re-run + re-audit once; else `[decision-required]` draft.
- Schema: additive `metadata.visual_significant` + `visual_signals` (no schema_version bump). Evals: `run_visual_significance_evals.py` (11) + `run_skip_audit_evals.py` (17, the five acceptance cases), both wired into `.github/workflows/ci.yml`. Docs: workflow.md (skip-audit in the loop + visual-deliverable gate), README skill list, CHANGELOG v1.13.0, plugin.json + marketplace.json (version + description), FB-0062.

**Why:**
Failure-open is inverted gate behavior — §5c skipped exactly the changes that most needed a durable visual record (short-circuited / grounding-less buffers), and nothing stopped a self-certified verify-build PASS (no findings buffer for HEAD) from producing a merge-ready-looking PR with no captured frames. The most expensive errors compound when a gate goes quiet on the high-risk case.

**Design decisions:**
- **One shared predicate, stamped once.** The visual-significance verdict is computed by a single helper and stamped into the buffer; ship reads `metadata.visual_significant` and only falls back to re-running the helper when there is no buffer (verify-build skipped). Avoids the FB-0010 fan-out of two drifting definitions.
- **Determinism where it belongs.** Both new helpers are stdlib-only and eval-pinned; the LLM (`/flow:audit-skips` fork) only adjudicates the `NEEDS-JUDGMENT` residue (mode-declared spike/tiny skips). The mechanical "verdict-without-artifact == skip" rule is the load-bearing half.
- **Skips honest, not impossible.** A docs-only / backend-only / library skip whose reason the diff/config backs rules LEGITIMATE without noise — the audit validates skips, it doesn't ban them (no false positives, per the anti-goals).

**Technical decisions:**
- Pure-refactor exclusion parses the unified diff for UI/asset hunks: a new/untracked file is a real delta by construction; rename-only / comment-only / whitespace-only / punctuation-only changes are excluded. The conservative bias is documented (an agent `--flag-significant` override exists for render paths the heuristic can't see, e.g. canvas/WebGL).
- Stage report handoff is a temp file (`/tmp/flow-skip-audit-stages.json`, override `FLOW_SKIP_AUDIT_STAGES`) like the findings buffer — no new config slot.
- No new config slots: the predicate + audit reuse `platform`, `uiSurface`, `uiFilePatterns`, `verifyEnabled`, `verifyFindingsPath`, `verifyReportPath`, `visualHistoryPath`, `sourceFilePatterns`.

**Tradeoffs discussed:**
- **Comment-only detection is heuristic** (a fixed comment-prefix set across languages) vs a full per-language parser — chose the heuristic + an explicit agent override, since over-triggering to "significant" only *adds* a walkthrough requirement (the safe direction) and the common cases (rename / blank / brace-move) are caught precisely.
- **audit-skips as a fork skill (own tools: Read/Grep/Bash) vs reusing the `auditor` agent** (Read/Grep only) — chose a standalone fork: skip-legitimacy is not one of the auditor's five categories and it needs Bash to run the ground-truth helper.
- **Re-audit once, not loop** — same single-pass discipline as Step 2's reviewers (iterating LLM judgment is reward-hackable); only the mechanical re-run + one re-audit is permitted.

**Lessons learned:**
- The failure-open pattern is subtle precisely because it reads as "graceful degradation." The tell is asking: *does this gate go quiet on the case it exists to catch?* If yes, it's inverted (FB-0062).
- flow's own repo is `platform: library` + `uiSurface: false`, so verify-build self-skips and the visual gate N/A's out here — these surfaces are pinned by the synthetic-input evals, not a live dogfood, until a UI consumer exercises them (same provisional status as V3b §5c).
