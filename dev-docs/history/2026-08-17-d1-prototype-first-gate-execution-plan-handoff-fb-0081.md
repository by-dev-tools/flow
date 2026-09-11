## 2026-08-17 — D1 prototype-first-gate execution plan (handoff, FB-0081)

**Branch:** `d1-prototype-first-gate-handoff` · **SHA:** _(set at ship)_

**What was done (docs-only).** Wrote `dev-docs/handoffs/d1-prototype-first-gate.md` — a self-contained, cold-start-executable execution plan for **D1**, the Designer-signal track's load-bearing item (move the human's first gate from the plan to a prototype). Indexed it in `dev-docs/README.md` and pointed the roadmap D1 entry at it.

**Why.** The user reviewed the five held/queued design-forks (from the #119 drain triage) and directed D1 forward, to be **handed off to a fresh workspace**. D1 is the biggest of the forks — it restructures the front half of the loop — so it earns a handoff doc rather than an inline build. The plan implements FB-0081 (the definitive, user-directed spec) verbatim: the seven-step loop, the two-gates-only constraint, prototype-before-plan ordering, the auto-written machine-gated technical plan, the orchestrate-agents-don't-merge-skills substrate (§5), and the proportionality guard.

**Design decisions captured for the fresh agent (so they aren't relitigated).** §4 lists the seven settled, user-directed decisions. Two assumptions are flagged as gating the build: §9.3 (the auto-written technical plan's quality — LOW, needs a spike before Phase 3, because the whole design rests on the machine gate having a real plan to check) and §9.4 (the prototype medium for non-web/native surfaces — a human decision, since FB-0081 assumes HTML-ish prototypes but flow's consumers include native apps). The #119 held item [10] (HTML-prototype geometry + taste self-check) is folded in as the prototype-phase self-check rather than a separate fork — its timing moves pre-execution.

**Relationship to verify-build (the user's explicit constraint).** D1 restructures Clarify→Plan only; Execute→Ship and `/flow:verify-build` are untouched. The visual human-gate (prototype approval) sits *before* execution and does **not** replace the post-execution behavioral gate — stated as an out-of-scope boundary in §2.

**No plugin artifacts changed** — this is a dev-docs handoff; the four ship reviewers self-skip.
