# Design-language doc migration brief

**What this is:** a portable prompt. Paste the section below (from "What this is" through the
end) into an agent session working inside a repo that already has — or should have — a
design-language doc, and ask it to run the audit. It works in any repo, flow-consumer or not;
nothing in it depends on flow being installed.

**Provenance:** the five rules quoted below are character-for-character identical to the
definitions in `template/base/core-docs/design-language.md` (the sibling scaffold this repo
ships to brand-new projects, merged in #141) — both derive from
`dev-docs/research/2026-09-design-md-investigation.md` §5a/S3. Confirmed by a mechanical diff
against #141's merged content at this branch's rebase (v1.36.0 → v1.37.0), 2026-09-03. One
deliberate, non-drift exception: the Tokens rule's template source ends with a template-authoring
instruction — "see the token names below only if you chose the code-pointer form" — that points
at the template's own fill-in-the-blank placeholder section. This brief has no equivalent
placeholder (its "Check for token drift" step covers that ground instead), so that trailing
clause is intentionally not copied; everything through "...is a doc that will drift." is exact.
Keep the two in sync: if either file's rule wording changes, update the other in the same PR, or
note here why this occurrence is deliberately different.

**Why this exists, not something more automated:** `dev-docs/research/2026-09-design-md-investigation.md`
found that a fleet of existing design-language docs already work — three of four repos surveyed
had zero token drift against shipped code — and that nothing enforces them. The gap isn't
missing tooling; it's that each repo independently reinvented one or two of five recurring shape
rules and never had a reason to check for the rest. This brief closes that gap with a prompt, not
a gate: it audits and proposes, a human decides, and it deliberately builds no new checker,
eval, or skill (see "Explicitly out of scope" below).

---

## What this is

This repo's design-language doc is being checked against five structural rules that a survey of
Vercel's `design.md`/`product-design` system and a small fleet of sibling repos converged on
independently. These are rules about the *shape* of a usable design-language doc, not about
taste — no design opinion is imposed here. The five rules:

1. **Axioms** — Numbered, falsifiable rules — phrased so a violation is pointable, not a matter
   of opinion. "Violate = design bug." One sentence each.
2. **Anti-patterns** — Named patterns to recognize and reject on sight — giving a pattern a name
   makes it far easier for an agent to catch than a vague "avoid X-ish things." Group by surface
   if useful.
3. **Priority order** — The single most commonly missing piece in design docs we've seen. When
   two rules in this file conflict, which wins? A numbered list, most important first.
4. **Tokens** — Pick ONE home for token values and say so explicitly — never both, or they will
   drift: "Values live inline in this doc — this file is the source of truth." (then list them
   below), OR "Values live in code at <path> — this doc names identifiers only, never raw
   values." (then list identifier names, not values) A doc that duplicates values in two places
   is a doc that will drift.
5. **Coverage gaps** — What has no standard yet? Naming the gap is cheaper than pretending it's
   covered, and tells an agent "improvise carefully here" instead of "follow a rule that doesn't
   exist."

Plus one authoring rule for anything you propose: write corrections as observable decisions, not
impressions. An agent can check "let evidence tables use the full available width" against a
render; it cannot check "make the table feel less cramped." When you correct a generated result,
encode *what changed* here, in checkable language, rather than leaving the correction only in a
PR comment or your own memory.

## What you do

1. **Locate the doc.** Search for this repo's design-language doc. Common locations:
   `core-docs/design-language.md`, `decisions/design-language.md`, a root-level
   `design-language.md`, or companion token/style docs (e.g. `tokens.md`, a theme/CSS file) next
   to it. If a `flow.config.json` exists, check its `designLanguagePath` slot first. If nothing
   exists, say so plainly — don't invent one to fill it.

2. **Audit against the five rules.** For each rule, report one of: **Present** (cite the
   section), **Partial** (something adjacent exists but doesn't meet the rule — say what's
   missing), or **Missing**. Judge "present" using the repo's own existing headings and
   vocabulary — a section titled differently that does the same job counts.

3. **Check for token drift.** If the doc states or implies token values (colors, spacing, motion
   curves, type scale), compare them against what the code actually ships (the theme/token file,
   CSS custom properties, a `Tokens.swift`/`Palette.ts`/equivalent). Report every mismatch you
   find, with both values and their sources. A doc that says one thing and code that ships
   another is a defect regardless of how "Tokens: one home" scores.

4. **Propose, don't impose.** For every rule scored Partial or Missing, draft a proposed
   addition — but write it **in this repo's own vocabulary and existing design language**, using
   terms, tone, and structure this repo's doc already uses elsewhere. Never import outside
   wording verbatim — not this brief's example phrasing, not another repo's, not a vendor's.
   Ground every proposed axiom or anti-pattern in something you can point to: an existing
   convention in the code, a past correction in commit history/CHANGELOG, or an explicit open
   question if you can't ground it. Phrase every proposal per the authoring rule above —
   observable, not evaluative.

5. **Stop and present.** Output a report: per-rule verdict, token-drift findings (if any), and
   proposed additions. **Do not edit the design-language doc.** Design language is the human's
   taste; you propose, they decide. Do not build tooling to automate this check, and do not
   scope-creep into fixing the drift you found — surface it and stop.

## Explicitly out of scope for this exercise

Do not build any of the following while running this brief, even if the audit surfaces a
plausible case for one:
- An automated eval/test suite for the design doc's content.
- A drift-checker tool (script, CI check, or lint rule) that re-runs this comparison
  mechanically.
- A new review gate/skill dedicated to design-language compliance.
- A schema change to support multiple design-doc paths.
- Any linter enforcing a specific rule from the doc.

If the audit turns up a strong case for one of these, say so as a recommendation with the
evidence that would justify it — don't build it here.
