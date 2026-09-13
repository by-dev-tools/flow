# SAFETY: a manifest entry can no longer close the manifest fence (FB-0109, v1.44.0)

**Date:** 2026-09-13 · **Branch:** `fix-manifest-fence-injection` · **Scope:** bugfix (shipped plugin surface)

## What changed

`extract_manifest_region` in `plugins/flow/skills/ship/lib/manifest_contract.py` now matches both
manifest fences **line-anchored** instead of as bare substrings. One function, plus a
`[fence-injection]` section in `run_manifest_triage_evals.py`.

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

**Only the parse half, deliberately.** The write-time half — rejecting a finding that contains a
marker — belongs in `_read_text_arg`, the validation function the FB-0108 branch is rewriting in
parallel. Doing it here would have guaranteed a conflict in one function across two PRs. It is
flagged to that branch to add at rebase, where it is three lines in code that branch owns.

**Named residual, not an implied seal.** This does not close a finding that embeds a newline
followed by a bare marker; FB-0108's newline collapse does. The docstring says so. "The class is
closed" is the sentence that stops the next person looking.

**Fallback direction chosen for the gate.** If the fences are not found line-anchored, the whole
text is returned — the "fences absent" path — so the parser sees *more* candidate entries, never
fewer. A merge gate degrading toward not-ready is the safe direction.

## Verification

- New `[fence-injection]` eval: the attack, a `roadmap.md`-style prose quote of both markers, a
  control, and the no-fence fail-safe.
- **Mutation-tested both ways.** Run against the pre-fix module the section goes **red with three
  failures**; green after. A regression test never observed failing is a claim (FB-0104).
- **Paired positive** per `.claude/rules/general.md` § Consistency rule 3: every attack assertion
  above is satisfiable by deleting fence scoping entirely, so the section also asserts scoping still
  *works* — an entry-shaped line outside the fence stays ignored. Without that half, "delete the
  fence" is a passing fix.
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
