# SAFETY: a manifest entry can no longer close the manifest fence (FB-0109, v1.44.0)

**Date:** 2026-09-13 (revised 2026-09-16 at ship) · **Branch:** `conductor/ship-fb-0109-manifest-fence-injection` · **Commit/PR:** [this range — PR pending push] · **Scope:** bugfix, SAFETY (shipped plugin surface: merge-gate parser)

## What changed

Two functions, one layer apart, plus a `[fence-injection]` section in
`run_manifest_triage_evals.py`:

- `extract_manifest_region` (`plugins/flow/skills/ship/lib/manifest_contract.py`) matches both
  manifest fences **line-anchored** instead of as bare substrings, and ends the region at the
  **last** close rather than the first.
- `parse_entries` (`plugins/flow/skills/ship/lib/manifest-triage.py`) consumes that region and
  re-splits it. It now takes the **union** of `str.splitlines()` and `split("\n")`, deduped on
  every field the classifier reads — `(fingerprint, needs, already_attempted)`. The key grew
  twice under review: `/flow:security-review` added `needs`, and `/flow:staff-review` then
  measured that omitting `already_attempted` let a colliding entry be discarded *with its
  flag*, landing at class `auto` — the one class that triggers a silent re-run → commit →
  push. Widening the key can only ever add an entry, never drop one.

- `_defang_fences` (same file) matches the manifest line's **field separators** with the parser's
  own grammar (`_FIELD_SEP_RE`) instead of three literal strings. **Scope added at ship** — see the
  tradeoff below.

Also: an entry whose kind flow does not recognize — only reachable via the widened region — no
longer renders copy claiming a ship gate failed, and the unknown-kind copy is consulted inside
`_copy` rather than by a branch at two of its seven call sites.

## Why — the defect, measured not reasoned

The NOT-READY manifest is delimited by an HTML-comment fence. The extractor did:

```python
text.split(MANIFEST_OPEN, 1)[1].split(MANIFEST_CLOSE, 1)[0]
```

— everything up to the **first** closing marker anywhere in the body. So an entry whose *finding
text* contained that marker ended the region at itself, and every entry after it was invisible to
the parse.

Reproduced on `origin/main`, not inferred: a body with one marker-bearing `[status-surface]` entry
followed by a real `[verify-build]` blocker parsed with the **verify-build blocker absent**, and the
coherence verdict moved `DECIDE` → `READY`. A PR whose behavioural gate had failed reads merge-ready
— precisely the outcome the manifest mechanism exists to prevent.

Found by P5 of the FB-0108 adversarial payload suite, which attacked *the parser's own vocabulary*
— its fence marker and its field separator — rather than testing that well-formed input round-trips.
A round-trip test generates neither payload. That distinction is worth more than the two bugs it
found.

## Tradeoffs

**Line anchoring, not a longer or randomized delimiter.** The emitter already writes each fence
alone on its own line, so the producer needed no change at all — the property existed and nothing
was reading it. A longer delimiter would have been the same bug with a lower probability, which is
[#148](https://github.com/by-dev-tools/flow/pull/148)'s refuted heredoc all over again.

**Only the parse half, deliberately.** The write-time half — defanging a finding that contains a
marker — belongs in `_read_text_arg`, which FB-0108 was rewriting in parallel; doing it here would
have guaranteed a conflict in one function across two PRs. That branch has since merged as
**#152**, so the write-time half is now present in this tree rather than pending, and the two
layers can be described together (see the residual note below).

**Named residual, not an implied seal — and the first version got the residual WRONG.** The fix
originally used `str.splitlines()` and claimed a newline was the only remaining vector, in four
places. `/flow:staff-review`'s staff-engineer lens refuted it by measurement: `splitlines()` breaks
on eight further code points (`\x0b \x0c \x1c \x1d \x1e \x85 \u2028 \u2029`), each of which still
erased the `[verify-build]` blocker, and no write-time newline collapse strips `\u2028` or `\x0c`.
Fixed to `text.replace("\r\n", "\n").split("\n")`.

That correction shipped alongside a second claim which was itself a reading: that
`pr-coherence.py` "already split on `\n`", so the fix had diverged from a correct in-repo
precedent. Measured, that module is **mixed** — one `split("\n")` site and two `splitlines()`
sites. The generalization was drawn from one of three call sites, in the same document that names
"only X remains is a measurement, never a reading" as its headline lesson. Corrected here and in
the docstring.

The same review caught that **first**-close was the unsafe direction: a doc-style example quoting
both markers above the real manifest captured the region and the real entries vanished. Now
**last**-close, which can only widen.

**The residual, restated after the rebase — and this is the third time on this one change that a
claim was made by reading rather than running.** The entry above was written while FB-0108 was an
unmerged sibling, so it said the `\n`-before-bare-marker residual had no write-time layer and the
docs must say "will be closed". FB-0108 then merged as **#152**, this branch rebased onto it, and
the claim became false without anyone editing it. Measured end to end on the rebased tree: a
finding of `"drifted\n<close-marker>\ntail"` written through `add-entry` emits one physical line
with the marker rewritten to an inert token, and a following `[verify-build]` blocker still parses.

The honest statement is narrower than either version: for text written through `add-entry` the
residual is closed by v1.42.0's collapse + defang; for a body that did NOT come through
`add-entry` — hand-edited on GitHub, or assembled from sections the write guard never touched —
line anchoring is the only layer and the residual stands. A cross-branch fan-out is the one
direction `git grep` cannot see, which is exactly why it survived four documents.

**Scope added at ship, on a security finding — stated as a tradeoff, not smuggled.** The
field-separator defang fix is not what this branch set out to do. `/flow:ship` Step 2's own
`/flow:security-review` found it, measured it, and tagged it `[auto-fixable]`; the pipeline's
prescribed routing for that tag is *fix in-tree and continue*, and the alternative — shipping a PR
whose entire thesis is "close the merge-gate bypass" while leaving a measured, reachable bypass in
the same file — is incoherent. It sits in its own commit so the merge gate can drop it without
touching the rest.

The defect: `_LINE_RE` matches a separator as `\s+—\s*needs:`, a whitespace **class**; the defang
matched the literal `" — needs:"`, **one space**. A TAB or NBSP therefore matched the parser and
missed the defang. Measured: `--kind security --needs "secret rotation"` (out-of-session verb ⇒
class `blocked`, not waivable) parsed as `needs='design decision'` ⇒ `ask`, `waivable: True`,
verdict BLOCKED → DECIDE.

Two things make it more than a one-line fix, and both are recorded in FB-0109 rule 8. The existing
`P22` separator test **passed while the hole was open** because it used a single space — the one
shape the literal caught; two spaces were safe only because the literal is a substring of them. And
the queued `FIELD_SEPS` roadmap item would **not** have closed it: that item derives the token
*set*, and this was two matchers of different *shapes* over the same grammar. The roadmap entry has
been amended to say so rather than left to imply coverage it never had.

**Fallback direction chosen for the gate.** If the fences are not found line-anchored, the whole
text is returned — the "fences absent" path — so the parser sees *more* candidate entries, never
fewer. A merge gate degrading toward not-ready is the safe direction.

## Verification

- New `[fence-injection]` eval: the attack, a `roadmap.md`-style prose quote of both markers, a
  control, the no-fence fail-safe, all eight separators around the marker, all eight *inside* a
  single entry, all eight *joining* two entries, the preceding and trailing fence-pair cases, an
  unclosed fence, a CRLF body driven against the engine directly (routed through a file it was
  vacuous — `_read` translates newlines before the parser sees them), and an emitter↔reader round
  trip asserting that what `render_manifest` writes, `parse_entries` reads back.
- **Mutation-tested against seven builds**, re-measured against the final eval: **21** failures on
  the pre-fix extractor, **8** with the wide split alone, **8** with the narrow split alone, **9**
  with the literal field-separator defang restored, **1** with first-close, **1** with the CRLF
  normalization removed, **0** on the fix. A regression test never observed failing is a claim
  (FB-0104).

  **The numbers in the first version of this entry were wrong** — it said 12 / 8 / 5. Those were
  measured against an earlier, smaller revision of the eval and never re-measured after the
  section grew, so the doc asserted a specific count that no build produced. The same fan-out
  discipline that applies to a slot count applies to a measurement: re-run it, or do not quote it.
  (The first re-measurement attempt was itself wrong in a way worth recording — the mutations were
  applied to a `.git`-less copy and one of them introduced a `SyntaxError`, which the harness
  reports as *zero failures*. A mutation that does not compile is a silent pass. The rerun compiles
  every mutant before trusting its count.)
- **The first revision of the eval did not catch its own bug.** Its separator cases used a body with
  a real close fence — under which the last-close rule rescues the entry independently — so they
  went green against a `splitlines()` build while *naming* the split choice. Rebuilt to use an
  **unclosed** fence, which isolates the property. This is the "mutation survived vs mutation never
  applied" trap, hit and corrected in the same pass — and then hit a second time, one layer down,
  when the same section's entry-level cases passed under either split until the joined-pair case
  was added.
- **Paired positive** per `.claude/rules/general.md` § Consistency rule 3: every attack assertion
  above is satisfiable by deleting fence scoping entirely, so the section also asserts scoping still
  *works* — an entry-shaped line outside the fence stays ignored. Without that half, "delete the
  fence" is a passing fix. The same pairing was added for the unknown-kind copy (a recognized kind
  must still render its own specific sentence) and for the emitter (each fence alone on its own
  line), so neither is satisfiable by deletion either.
- Fence literals are read from the engine's own module rather than retyped, so a marker rename
  cannot leave the test green against a stale copy.
- `run_manifest_triage_evals.py` and `run_pr_coherence_evals.py` both green.

## Correction recorded

The first framing of this — including the orchestrator's escalation to the human — claimed the
payload was "already committed to main, no attacker required", citing `dev-docs/roadmap.md:720`.
Measured, that is wrong: `[status-surface]` findings quote from *scanned candidates*, and none of
the six defaults carries the marker; `roadmap.md` is the reference the scan compares against, not a
candidate. The accurate framing is **a latent self-trigger, one docs commit from live** — `README.md`
already discusses the manifest. Caught by re-running the check rather than repeating the sentence,
and corrected in the code docstring before it shipped as a false claim.
