# `/flow:audit-coverage` gains a source-tree input mode

**Date:** 2026-09-20 · **Version:** v1.47.0 · **Branch:** `conductor/d1-a-audit-coverage-source-input-mode`
**Gates:** plan approved at the plan gate; all three plan-gate open calls resolved by the orchestrator under
§4.8 (low-stakes, reversible, high-confidence, low-taste — rule 7), none escalated.

## What

`/flow:audit-coverage` can now be handed a **source tree** instead of a diff:

    /flow:audit-coverage                      # unchanged — the workspace diff (the /flow:ship Step 2 path)
    /flow:audit-coverage <path>               # new — an approved prototype's source (file or directory)

One skill, two evidence blocks, argument-gated on `$ARGUMENTS` (the same mechanism `/flow:audit-plan` already
uses for its optional plan-file path). Exactly one block speaks per run.

## Why

`dev-docs/research/2026-09-16-d1-auto-plan-quality-spike.md` — D1's §9.3 spike. An auto-written Spec-walk plan
scored **0/13 vacuous** (clean on criterion *quality*, confirmed testable by a live headless-Chrome dry-read)
while **under-declaring 10 real behaviors against 13–14 declared**, including an entire keyboard-only
interaction path on a prototype whose own code cites WCAG 2.1.1.

The mechanism is the part worth keeping: the pre-execution reviewers read the **plan** and the **brief**, and
*nothing reads the approved prototype's code*. `plan-critic` caught the keyboard gap only because that
particular brief happened to mention keyboard — luck, not design. What caught 10 of 12 gaps was a
coverage-style pass over the prototype's **source**.

## The design decision: an input mode, not a fourth reviewer

`audit-coverage`'s **input** is diff-shaped (`SKILL.md:90` builds its file list from `git diff`). Its
**judgment** is not: *"for each user-perceptible behavior change, check whether any declared criterion would
cause someone to test it"* (`:130`), scoped at `:129` to *"declared-vs-built completeness only, not criterion
quality."* That axis is what found the gaps, and it is already written, already tuned, already eval-backed.

So the judgment is reused **verbatim** and only the input path is new. The rejected alternative was a fourth
pre-execution reviewer with its own prompt: new judgment surface to maintain, drifting against the one that
already works, to re-derive a result the spike had already reproduced by hand using this reviewer's own framing.

**Tradeoff accepted:** one skill now carries two input modes, which is more conditional shell in a file that is
already dense. The alternative — a separate `/flow:audit-prototype` skill — would have duplicated the judgment
prose into a second file, and `.claude/rules/general.md` § Consistency item 2 is precisely about contract
values that live in N files and drift. Conditional shell in one file beats identical prose in two.

## Three things the implementation had to get right

1. **The default `sourceFilePatterns` contains no `.html`.** Measured at plan time. The shared default the diff
   block uses (`SKILL.md:87`) matches `ts|js|py|go|...` — so naively reusing it on the reference prototype
   (`annotation-layer.html`) filters the file list to empty and renders a clean `[audit-coverage] SKIPPED`.
   **The feature would have reported "no undeclared changes" over a prototype it never opened** — the exact
   failure it exists to prevent, reproduced inside itself. Resolution: a **single named file is read verbatim,
   never pattern-filtered** (a human who names one file has already made the selection; re-deciding it by
   extension list re-opens the hole); a **directory** is walked with a prototype-oriented pattern set
   (html/css first — a prototype is a rendered artifact, not a service), deliberately *not* `sourceFilePatterns`.
2. **`SOURCE-UNRESOLVED` is its own outcome, never `SKIPPED`** (FB-0074's distinction, applied to a new sibling).
   Missing path, path outside the repo, newline-bearing path, empty walk, zero readable bytes — all route as
   "I never looked", never as "I found nothing to audit". If you named a path, an empty result is evidence the
   *input* is wrong, not that the work is covered. Asserted non-confusable with the skip line directly, the way
   `run_root_anchor_evals.py` pins it for `ROOT-UNRESOLVED`, and **paired** with §4b's positive: the real
   `SKIPPED` path still works, so deleting the skip branch cannot satisfy the suite.
3. **The cap is derived, not hardcoded.** The reference prototype is **60,805 bytes** against a **60,000-byte**
   diff cap. `SOURCE_CAP=$(( DIFF_CAP * 2 ))`, with the measurement in a comment and a cross-check in §6 against
   the diff block's own literal — a bare `120000` is the FB-0010 fan-out shape, silently stopping to mean
   "twice the diff cap" the day that value moves. The two live in separate shells, so a comment cannot hold them
   together; an assertion can.

## Evidence

**Diff mode is unchanged — measured two ways.** One-time comparison against `origin/main`: the diff block and
the criteria block each produce **byte-identical** output (355 bytes) in a temp repo rendering a real non-empty
diff, so the equality is not the vacuous "both empty" kind. The durable CI form needs no git ref (an
`origin/main` comparison stops meaning anything once this merges): §1 strips the mode-gate lines back out of the
shipped block and requires byte-identical stdout from both copies — the stripped copy literally *is* the
pre-change code path. `ship/SKILL.md` and `ship-spike/SKILL.md` are untouched.

**The instrument test (`.claude/rules/general.md` § Consistency item 4).** A measurement that can only return
"clean" is not a measurement, so §5 runs the real source block against the real `annotation-layer.html` and
asserts all **ten** spike-documented behavior anchors survive assembly — then validates that probe against a
context clipped at a measured 57,000 bytes, where finding 9 provably drops out and the probe **must** fail.

**Item 4 earned its place within days of landing (#157).** Writing the harness first surfaced three real defects
that a "does it run and return clean?" test would have passed:
- a **zero-byte named file** rendered the full source-mode header over nothing and read as a clean pass;
- the probe's **own negative control passed**, because every anchor token appears early in the file — a probe
  that could not return not-clean;
- the metacharacter assertion **failed on a correct refusal**, because it searched for a literal that the
  refusal message echoes back — an assertion that could not distinguish refusal from execution. Replaced with a
  filesystem side-effect canary.

**On the 2x cap, at the precision it was actually measured.** The coarse token probe *survives* a 60,000-byte
clip, so "the diff cap would have truncated the reference case" needed a sharper instrument than the probe: the
prototype's **third** `focusin` registration — the focus-restoration half of the WCAG 2.1.1 path the spike cites
at lines ~1146–1154 — sits at file byte 59,915 with its body running past 60,000, and is provably absent from a
60,000-byte clip. Asserted in **bytes**, not characters: the first version compared Python `str` slices against
a shell `head -c` cap on a file carrying non-ASCII punctuation, and passed by accident. The unit was wrong, not
the claim.

**Live joint test (one authorized `flow:auditor` spawn) — the path works, and the number is not 10.** The joint
(new input feeding the existing judgment, end to end) was the one thing neither the instrument test nor the
spike had exercised: the instrument test proves the *context*, the spike proved the *judgment*. Fed the real
source block's output plus the spike's 13-criterion auto-plan, a fresh auditor returned **4 findings, all 4
real** — precision 4/4, zero false positives — covering **5 of the spike's 10 behaviors**: finding 1 (the
flagship keyboard/WCAG gap) reproduced independently, plus `snapPreview`, show/hide-pins, and bulk + single
delete consolidated into one finding. **Not reproduced this run:** panel open/close, per-row copy, the
storage-quota warning, the Escape state machine, discard-on-empty-close.

So the mechanism is confirmed end-to-end and re-found the gap that motivated the work — but **recall varied
substantially between two runs of the same judgment on the same artifact** (10 behaviors hand-run, 5 here). That
is a property of best-effort LLM judgment, which this reviewer has always been documented as. Recorded rather
than rounded up, because "audit-coverage finds ~10 gaps on a prototype" is exactly the kind of claim that
hardens into folklore. **n=1 on each side, one prototype.** Shipping is how this reaches n=2.

## Provenance (FB-0107)

Measured in this workspace before any verification was believed: **installed plugin 1.29.0** (`gitCommitSha
cf783ac`) against a working tree at **1.45.0** — sixteen releases stale. So `Skill("flow:audit-coverage")` in
this session resolves 1.29.0's `SKILL.md` and **structurally cannot exercise the mode this PR adds**. Every
verification above ran the extracted shell block under the **Bash tool** (working tree), never via the skill.
If a later reviewer proposes "just dogfood it through `/flow:ship`" as evidence for this change, that is not
evidence — it is the previous release reviewing itself. Substitute evidence, labelled, per #150.

## Scope held

No D1 Phase 3. No auto-plan writing. No wiring into a Step 6 that does not exist. No change to `/flow:ship`
Step 2 or `/flow:ship-spike`. No fourth reviewer and no new judgment prose — the `What to check` section gained
only mode-scoping for the new not-clean outcomes; `:129`/`:130` are untouched. No edit to
`dev-docs/handoffs/d1-prototype-first-gate.md`, including its known §0/§8-vs-§9.3 self-contradiction about
whether the spike gates Phase 2 or Phase 3. §9.3 itself is **not** resolved — this closes the *mechanism* gap
the spike identified; the Phase-3 design decision (spike option (a) vs (b)) remains the orchestrator's.

## Files

- `plugins/flow/skills/audit-coverage/SKILL.md` — the source block, the one-line diff-mode gate, mode-scoped prose
- `plugins/flow/evals/run_coverage_source_mode_evals.py` — new, 48 checks, CI-wired
- `plugins/flow/evals/fixtures/coverage_source_mode_undeclared_context{,.expected}.{md,txt}` + `ground_truth.yaml`
  — offline-validated fixture pair, the same tier as the three diff-mode coverage fixtures (it pins the
  assembled-context shape and the output schema; it does **not** demonstrate live LLM behavior)
- `plugins/flow/evals/run_root_anchor_evals.py` — `EXPECTED_GUARDS["audit-coverage"]` 2 → 3 (exact count, not a floor)
- `plugins/flow/docs/workflow.md`, `README.md`, `skills/workflow-help/SKILL.md` — two-input-mode wording
- `plugin.json` / `marketplace.json` → 1.47.0; `changelog/v1.47.0.md`
