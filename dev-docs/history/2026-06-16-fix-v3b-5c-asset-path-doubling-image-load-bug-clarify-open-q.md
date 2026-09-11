### Fix V3b §5c asset-path doubling (image-load bug) + clarify open-question routing (v1.8.1) — SAFETY
**Date:** 2026-06-16
**Branch:** claude/v3b-asset-path-fix
**Commit:** [this PR]

**What was done:**
The first real FB-0016 cold-run — a fresh agent running `/flow:ship` Step 5c on the health-tracker iOS app — confirmed V3b works (5c fires, the curated entry is editorially sound, screenshots load) and caught a real bug it had to route around: the §5c asset-copy doubled the `assets/` path so the durable record's screenshots resolved to missing files (the "recent images may not resolve" symptom the V3b author flagged). Fixed §5c to resolve frame sources against the report dir + copy by basename; clarified the resolved-this-iteration open-question routing; added an eval guard; bumped to v1.8.1; routed the two remaining cold-run findings to the roadmap.

**Why:**
§5a writes `observations[].content` as `assets/<slug>.jpg` **relative to the report dir** (the convention `render-report.py` reads). §5c set `ASSETS_SRC="$(dirname REPORT)/assets"` and copied `"$ASSETS_SRC/<content>"` — prefixing a second `assets/` → `.../assets/assets/<frame>`, a missing file. An agent following the pseudocode literally produces broken `<img>` refs. The two sections contradicted on "relative to what" — the FB-0010 fan-out class applied to a path convention spanning two skill sections.

**Design decisions:**
- **Fixed §5c, not §5a.** §5a was correct ("relative to the report dir"); §5c misread it. Aligning §5c to §5a (resolve against `$REPORT_DIR`, copy by basename) is the minimal correct fix and removes the contradicting `ASSETS_SRC` construction entirely.
- **Pinned with an eval guard, not just prose.** `run_visual_history_evals.py` now asserts §5c contains `$REPORT_DIR` + `basename`, contains **no** `ASSETS_SRC`, and keeps the explicit `assets/assets` trap note — so a future edit can't silently reintroduce the doubling. (The copy itself is agent-driven shell, not the helper, so this contract-assertion is the closest mechanical pin available.)
- **Clarified open-question routing rather than changing the schema now.** The cold-run agent had to relabel a gate-approved `this-iteration` decision as `future-planning` to clear the Step 8 gate (which blocks on any `this-iteration` question, with no `resolved` state). §5c now distinguishes "answered with a decision → distill it" from "genuinely forward → `future-planning`" and warns against the relabel-to-dodge. The proper `resolved` schema flag is roadmapped (§ Next) — a schema change deserves its own PR.

**Technical decisions:**
- **SAFETY — asset-persistence path correctness.** This corrects where committed screenshot assets are sourced from; the prior behavior silently committed a `visual-history.html` with broken image refs (no crash, no warning — exactly the silent-skip class). No error-handling was downgraded; the fix makes the documented copy resolve to real files.

**Tradeoffs discussed:**
- **Patch vs. deeper refactor.** Considered moving the asset-copy out of §5c prose into `insert-visual-history.py` (deterministic + directly eval-able, kills the bug class). Chose the minimal §5c fix + contract-assertion guard for v1.8.1 (fast fix for a live bug in the exact symptom the user reported); the helper-owns-copy refactor is a roadmap follow-up.

**Lessons learned:**
- The cold-run paid for itself immediately: a fresh agent following the prose literally surfaced a bug the author (who knew the intended convention) didn't. A path-relative-to convention referenced in two skill sections must state the SAME base in both — reinforces FB-0010 (fan-out contradiction) for prose conventions, not just counts/names.
