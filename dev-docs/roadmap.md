# Roadmap

Where the flow plugin is going over the next few horizons. Active work lives in `plan.md`; this is what's queued + what's being explored.

The plugin extraction umbrella (PRs 1-3 in flow + PRs 4-6 in md-manager) is the load-bearing scope through v1.2.0. Post-extraction v1.x+ work (autonomous routines, JTBD substrate, visual artifacts, design lenses, HTML reports, deploy previews) is documented in md-manager's `core-docs/handoffs/*-design-2026-05-23.md` series — that's the canonical roadmap for post-extraction; mirror entries here only when they become Now/Next.

---

## Now

Five consumer-feedback follow-up PRs sequenced from md-manager's PR 4 dogfood report (FB-0005 through FB-0009 in `dev-docs/feedback.md`; see § "Active Work Items" in `dev-docs/plan.md` for per-PR plans):

- **PR A** (this PR — in flight) — consumer feedback intake (docs-only): 5 FB entries + 1 EXPLORATION + create this `roadmap.md`. Closes the loop on capturing md-manager's PR 4 + PR 24 findings as canonical.
- **PR B** (next) — stale-base preflight in `/flow:ship` Step 1. Highest leverage; mechanical.
- **PR C** (next + 1) — marketplace-key-mismatch install verification step in `bootstrap.md` + `migration.md`; `/flow:ship` prints workflow-step assumptions at start.
- **PR D** (next + 2) — per-diff non-UI early-exit paired in `/flow:security-review` + `/flow:accessibility-review`.
- **PR E** (next + 3) — `gh` CLI fail-fast check in `/flow:ship` + `/flow:staff-review`; document `gh` as a dependency.

## Next

After the consumer-feedback PRs land:

- **Resume umbrella retirement.** md-manager PRs 5 (dogfood) + 6 (delete duplicates + retire umbrella) per `dev-docs/handoffs/md-manager-pr4-6-spec.md`. Flow-side: standing by for PR 5's feedback intake; may surface additional rough edges worth a second follow-up bundle.
- **Carryover PR-2 FOLLOW-UPs not yet absorbed** (items 3-8 in `dev-docs/plan.md` § "PR 3+ follow-ups from PR 2 review"). Most are MEDIUM-priority polish or v1.2 hygiene; pick up opportunistically rather than as a focused PR.

## Later

- **Schema slot bi-directional consumer-pairing check** as a pre-commit recipe (FB-0003 pre-commit grep + FB-0009 follow-up). One-shot script under `tools/` would catch the next schema-without-implementation / implementation-without-schema bug before it ships.
- **End-to-end `/flow:ship` regression coverage.** Currently zero fixtures for the workflow skills; verification is dogfood-only. A small fixture project under `evals/` that exercises one ship pipeline in CI would catch the runtime-permission class (FB-0002) before it ships.

---

## § Exploration

Items surfaced by `/flow:staff-review`'s push-further lens or consumer dogfood. These don't have a concrete shape yet — they describe a direction worth investigating when relevant code is touched. Each entry includes a **`Surfaces when:`** trigger naming the file paths or area that should re-surface the item, so the auto-loading `exploration` rule can grep this section for trigger matches.

### Rule-of-three: `flow:close-out` skill abstraction for umbrella tracker hygiene

**Surfaces when:** a fourth umbrella close-out PR lands in any consumer (e.g., the eventual designer migration creates the same shape) — currently three instances: md-manager#21 (close-out for flow PR 1+2), md-manager#22 (close-out for flow PR 3), and md-manager#24 (close-out for flow PR 4).

**Direction:** The mechanical 70% of these close-out PRs is now stable across three instances — SHIPPED header format, checkbox-flip diff in `core-docs/plan.md`, sweep-to-Recently-Completed at `/flow:ship` time. The per-PR 30% (which FB-derived confidence verdicts to name, which post-merge action items to surface) is genuinely PR-specific. If a fourth instance lands, that's the rule-of-three trigger to consider whether the variance is principled (worth keeping bespoke) or accidental (worth a `flow:close-out` skill that templates the mechanical parts and prompts for the FB-derived parts). Do not extract yet — three is the cue to flag, not the cue to commit.

**Origin:** md-manager PR #24 push-further lens; consumer feedback report 2026-05-25.

**Out of scope (don't conflate):** This is distinct from `/flow:ship` itself (which closes out a PR's OWN session) and from `/flow:ship-spike` (which closes out a spike). The proposed `flow:close-out` would close out a CROSS-REPO umbrella tracker entry — orthogonal scope.
