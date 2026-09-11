### SAFETY: /flow:ship discovers undeclared status surfaces that drifted (v1.14.0, FB-0064)
**Date:** 2026-07-01
**Branch:** claude/kind-blackburn-7ac67f
**Commit:** _(on branch; final SHA in the PR)_

**What was done:**
Closed the orientation-doc-staleness gap in `/flow:ship`. The existing doc-currency machinery (Step 5a reconcile + Step 5b marker-coverage gate + doctor Check 2.7 + the `statusDocs` slot + `lib/status-docs.py`) already keeps forward-looking status current at ship time — but ONLY for surfaces a project explicitly declared in `statusDocs`. With it unset (the default `[]`), an UNDECLARED orientation doc (the CLAUDE.md a fresh agent reads first) is invisible to the whole pipeline and silently rots after a merge. Added a **discovery tier** on top of the working machinery:
- **`statusSurfaceCandidates` schema slot** (default ships: `CLAUDE.md, AGENTS.md, README.md, GEMINI.md, .cursorrules, .github/copilot-instructions.md`) — the well-known auto-loading orientation files to scan.
- **`skills/ship/lib/status-surface-scan.py`** (stdlib, POSIX-friendly) — emits each candidate that EXISTS and is NOT already declared, plus a bounded, line-numbered status-bearing slice for the judge (`candidates` / `slice` / `scan` subcommands).
- **Ship Step 5a.5** — ONLY when this ship moved forward-looking status (the same `STATUS_MOVED` signal Step 5b uses, recomputed via the shared `status-docs.py section` helper), best-effort-judge each undeclared candidate for a stale "next/not-started" claim about just-shipped work; a flagged surface → a `[decision-required]` draft-manifest entry; clean → an explicit skip line.
- **doctor Check 2.9** — warn-only setup-time nudge to fence + declare an undeclared candidate carrying status content.
- **Bootstrap** — the scaffolded `CLAUDE.md` ships with a `<!-- flow:status -->` fenced region + a seeded `statusDocs` entry, so new consumers get Tier 2 auto-reconcile by default.
- **`evals/run_status_surface_evals.py`** (positive dogfood / negative declared-fenced / false-positive fixtures + helper unit coverage + SKILL/doctor/schema/example contract) wired into CI. Version → v1.14.0; slot count 28 → 29 (doctor description + CLAUDE.md.template updated).

**Why:**
The dogfood (FB-0064): a consumer merged sub-PR "3c₁"; `/flow:ship` correctly reconciled plan Current Focus + roadmap Now, but CLAUDE.md's two status paragraphs still read "▶ 3c is next (not started)" — describing just-merged work as upcoming. The next agent would have picked up against a stale map; a separate manual PR (#53) was needed. This is the FB-0010 "stale forward-looking direction" class applied to *what to work on*, and the surface flow itself mandates reading every session must not have opt-in currency.

**Design decisions:**
- **Extend, don't rebuild.** The mechanism EXISTS and works; the gap was 100% adoption/discovery. Reused Step 5a/5b, `status-docs.py`, and the `STATUS_MOVED` signal; added only the discovery helper + the 5a.5 detection step. (Considered auto-declaring every candidate into `statusDocs` — rejected: that would auto-fence + auto-edit un-fenced human docs, which many CLAUDE.mds forbid.)
- **Best-effort, route-to-draft — mirror `/flow:audit-coverage`, never a hard halt.** A false positive must not wedge a ship; draft-routing is the ceiling. The draft item IS the propose-before-editing proposal, so flow never silently rewrites an un-fenced human doc — auto-reconcile stays gated behind the opt-in fence (Tier 2).
- **False-positive discipline via required evidence.** Flag ONLY with a verbatim drift quote; mere keyword presence ("Phase 3c") is not drift. The candidate list is conservative on purpose — the drift *judgment*, not the list, carries the precision.
- **Two clean tiers.** Declared + fenced = Tier 2 (auto-reconciled by 5a, never a draft item); the scan excludes declared paths so it never double-counts. Undeclared + drifted = Tier 1 (5a.5 → draft).
- **Gate on `STATUS_MOVED`.** Only scan when a ship actually moved plan/roadmap status — a ship that moved no status can't have made an orientation doc stale, so scanning would be pure false-positive surface.

**Technical decisions:**
- **`status-moved` stays in the shell, computed via the shared `section` helper.** `status-docs.py` keeps git out of the pure-text helper (unit-testable); Step 5a.5 recomputes `STATUS_MOVED` in its own shell block (separate blocks don't share scope — the codebase's established idiom, e.g. 5b re-resolves DEFAULT_BRANCH/PLAN/ROADMAP) via the SAME tested `status-docs.py section` text path, so the section-extraction logic lives in one place. Did NOT add a git-touching `status-moved` subcommand to the helper (would break the pure-text/unit-testable convention).
- **doctor Check 2.9 uses a `while-read` heredoc, not `for c in $CANDS`** — zsh doesn't word-split unquoted vars (the exact FB-0010 silent-skip class Check 2.5 documents); verified identical output under dash/sh/zsh.
- **`DEFAULT_CANDIDATES` in the helper is pinned to the schema default by an eval** (`slot-2-default-parity`) so the two lists can't drift (FB-0010 fan-out).
- **Malformed config is loud (exit 1), never a silent fall-through** — both a bad `statusSurfaceCandidates` and a bad `statusDocs` (used to compute the exclusion set) raise, mirroring `status-docs.py`.

**Tradeoffs discussed:**
- **Discovery precision is the LLM's, not mechanical.** The eval pins the mechanical half (scan surfaces the right candidates + the verbatim slice; declared excluded); the drift *decision* is best-effort, backstopped by the human at the merge gate — the same determinism boundary as `/flow:audit-coverage`. Accepted: raising the completeness bar without a false guarantee beats a deterministic check that either over-fires on keywords or misses real drift.
- **Seeding `statusDocs` with CLAUDE.md in the scaffold** changes bootstrap behavior (new projects get a fenced CLAUDE.md + a declared entry). Accepted — that IS the point-5 deliverable (Tier 2 by default); the un-adopted state still gets Tier 1 discovery.
- **Over-fire risk on 5a.5 mirrors 5b's documented over-fire** (a non-status plan/roadmap edit that trips `STATUS_MOVED`): here the cost is a draft item the human waives, not a hard block — a strictly softer failure than 5b's.

**Lessons learned:**
- When a gate protects a surface class but only fires on opted-in members, the gap is adoption, not mechanism — add a discovery tier with a shipped default, and discover what should be enrolled rather than waiting for enrollment (FB-0064).
- Dogfood note (honest): the ship that opens this PR runs from the INSTALLED plugin (v1.13.0), which predates Step 5a.5 — so 5a.5 did not execute on this ship. It was exercised by a manual live scan against flow's own CLAUDE.md + README (both surface as undeclared candidates; neither carries a stale "next" claim about just-shipped work → no flag) and pinned by `run_status_surface_evals.py`. It runs live in the pipeline once v1.14.0 is installed.
