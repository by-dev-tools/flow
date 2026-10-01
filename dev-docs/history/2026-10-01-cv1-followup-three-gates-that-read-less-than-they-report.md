# CV1's unfinished half — three gates that read less than they report

**Date:** 2026-10-01
**Branch:** `conductor/cv1-followup-reviewer-rigor-walkextract`
**Version:** v1.56.0
**Feedback:** FB-0128, FB-0129
**Scope:** exactly the three fixes the dispatch named
(`dev-docs/handoffs/2026-10-01-cv1-followup-dispatch.md`), and nothing else.

## What this is

CV1 (#172, v1.55.0) taught `/flow:audit-coverage` to *select* behaviour-bearing prose. Three
things it left behind each had the same shape — a gate that reads less than it reports, with
nothing said:

1. **The reviewer was told to ignore the prose it had just been handed.** Stage 1 said
   "test/doc changes are **not** behaviors"; the shared agent's coverage-only category said
   "do not flag ... doc-only changes". So the evidence arrived and the instructions suppressed
   it. Selection without instruction is not a fix.
2. **The rigor fingerprint was computed through `sourceFilePatterns`**, which matches no `.md`
   path at all. On #172, **0 of 13** changed `.md` files were in it — including the two shipped
   `SKILL.md` files that PR existed to change. Either could have been rewritten after
   `/flow:staff-review` with the gate still reading "ok".
3. **`walk_extract` lost criteria two ways at once**: it kept only each bullet's first physical
   line, and it ended the block on an indented continuation line opening with a bold span.

## What shipped

**Item 3 — one collector, shared.** `walk_extract.collect_items` is now the single definition of
"what a block contains". An indented non-checkbox line under an item folds into that item (which
markdown already says it is), and a block that ends at a terminator reports the line and the item
count in `warnings`, so a truncated read and a complete one stop looking alike (FB-0121). Running
to EOF stays silent; a warning on every clean block is noise, and the fixture pins the silence as
well as the announcement. `is_pinned`'s `ARTIFACT_RE` moved from `\b` to alphanumeric-only
boundaries, because `\b` treats `_` as a word character and so `eval` inside
`run_coverage_docblind_evals.py` — this repo's own naming convention for the artifacts it asks
authors to cite — never matched.

**The second scan site was the load-bearing half.** `critique-plan/lib/walk-pin-lint.py`
imported the primitives and re-scanned, because it needs every block rather than the first. Both
copies carried both defects, so fixing `extract_block` alone would have left
`/flow:critique-plan`'s pin lint reading a fraction of every plan and reporting it clean.

**Item 2 — `plugins/flow/lib/doc_patterns.py`**, one definition with two readers: the coverage
block's shell literal (a `!`-span cannot import Python, so an eval asserts byte-equality and that
the shell declares it exactly once) and the rigor fingerprint. OD1's (a′): the fingerprint is
`sourceFilePatterns ∪ DOC_BUILTIN ∪ behaviorBearingDocPatterns`. Union into the FINGERPRINT only —
folding docs into the shared source ruler would have broken the docs-only early-exit.

**Item 1 — `[audit-coverage] DOC-SURFACE`**, the positive counterpart to `DOC-BLIND`, naming
every doc-shaped file the slot selected, above the delimiter, with no `WEAKENED` token: every
weakening says less was read than normal, and this says more was. Both instruction sites carry an
exemption keyed on that line, and **both keep their suppression** — absent the line, an ordinary
README or comment edit is still not a behaviour.

## Measured

**Item 3, on the real case.** #159's plan declares 12 criteria in a 67-line block carrying 52
continuation lines: **1,143 → 5,831 characters** reaching the reviewer, with the criterion count
unchanged at 12. The count never moving is why nothing caught this for as long as it ran. On
*this* PR's own plan the same fix recovers **3,084 → 5,104 characters** across 13 criteria — and
the early-block-end did *not* fire here, because these notes carry trailing prose after the bold
span. Two distinct defects; one case exercises one of them.

**Item 2, on real files.** Editing a `SKILL.md` moves the fingerprint; editing an agent prompt
moves it; editing `dev-docs/plan.md` does not — which is the point, since ship Step 5 rewrites the
plan doc in the code commit and a gate that always fires is one people learn to click past.

**Precision first, because the reassurance it replaces was false.** CV1 recorded that a
wording-only change returns `No issues flagged.` and read it as precision holding; the suppression
fired before any judgment, so the silence was the carve-out answering. Measured now over a pair
differing in exactly one thing, under the tier most biased toward flagging: **zero findings in 3
of 3** wording-only runs, **flagged in 2 of 2** with one added rule. Two of the three clean runs
returned the verdict verbatim; the third returned zero findings via the roadmapped
empty-enumeration shape. All three *name* the `DOC-SURFACE` line and classify the specific
rewordings — the reviewer had no way to say that before.

**Recall on pr159:** 2/5 (40%), 3/5 (60%), 3/5 (60%) — mean 53%, **union 3/5 (60%)**. The
single-run mean moved (CV1's arms were 40% and 20%); the union did not, and all three runs miss
the same two gaps, so that ceiling is not variance. **Confound disclosed:** item 3 changed what
this case feeds, so these are not a clean prompt A/B against CV1's headline; the comparable
pre-existing arm is CV1's untruncated 1/5.

**False positives:** r1 zero; r2 and r3 each carried one unmatched finding, the *same* behaviour
both times. Adjudicated borderline-TRUE-positive: the nearest declared criterion names the right
input class and asserts a refusal, while the diff's own comment says the hazard fires first and
the refusal then prints a correct-looking `SOURCE-UNRESOLVED`, so a test written to that criterion
passes without exercising it.

## Tradeoffs

- **A module for `DOC_BUILTIN`, not a second literal.** The shell cannot import it, so one copy
  is unavoidable; what is avoidable is an unpinned copy. The eval asserts byte-equality *and* that
  the shell declares it exactly once — the second half is what makes a third copy fail.
- **`DOC_BUILTIN` built exactly as specified, not quietly widened.** It is three directory names
  matched anywhere in a path, not "every shipped prose surface": it MISSES
  `plugins/flow/docs/workflow.md` and `README.md`, and it MATCHES `.claude/rules/general.md`,
  which ships to nobody. Over-inclusion costs one human decision; under-inclusion is the unsafe
  direction and `workflow.md` sits on it. Widening to `docs/` would guess for every consumer, and
  the slot already exists for consumers who need it. Raised rather than absorbed.
- **The shared-agent edit is measured inert, and measured unnecessary.** `/flow:audit-completion`
  matches its expected category under the new prompt; `/flow:audit-plan` returns an identical
  summary under new and old. But the positive arm run under the OLD category flagged the added
  rule just as precisely, so this edit's necessity is not demonstrated. It ships because dropping
  it leaves Stage 1 carving out what Stage 2's text still forbids, and n=1 cannot show the old
  category never suppresses — flagged for the orchestrator with both arms committed.
- **An always-on end-of-read warning, not a new result field.** `warnings` is the channel
  consumers already read, and checking first showed none treats a non-empty list as a verdict.
- **Continuations must be INDENTED.** Markdown permits a lazy flush-left continuation, but a
  flush-left line is ambiguous with a new paragraph or heading, and resolving it the other way
  would merge real blocks.

## Instrument errors caught (all mine)

- A fixture that **guessed** its output key read a missing key as "0 extracted" when the figure
  was 2 of 3, misstating what it had caught; the key is now derived from the output.
- The first control for that fixture stripped every `**`-leading line, removing the block header
  too, and returned 0 of 3. A control that changes two things measures neither.
- The two shared-agent cross-checks first rendered with the bang-span **unexpanded** — `recall.py`'s
  `BLOCK_RE` matches only the multi-line form. Both reviewers refused, which is the only reason it
  was obvious; the re-render asserts the span is gone *and* the fixture's content is present.
- I moved a **fresh** output into the discard pile, having listed the directory before the agent
  wrote and moved it after. Content identified it; it was restored.
- Two outputs from the session-limit interruption were discarded rather than scored (FB-0129).
- The claim "this plan would have been cut" was **wrong**, and measuring it is what showed the
  terminator does not fire on a bold span with trailing prose.

## Open

- CV1's `pr159` numbers were never committed as raw outputs; that baseline exists in prose only.
  This PR's three runs are committed as `runs/pr159.followup.r*.txt`.
- The empty-enumeration verdict gap is now reached more often on prose-only diffs, because the
  reviewer considers the prose instead of dismissing it by rule. Already roadmapped; this
  strengthens it.
