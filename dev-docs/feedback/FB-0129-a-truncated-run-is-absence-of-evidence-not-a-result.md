# FB-0129 — A truncated run is absence of evidence, not a result

**Date:** 2026-10-01
**Source:** orchestrator, resuming the CV1 follow-up after an account session limit
**Status:** applied in v1.56.0 (CV1 follow-up, measurement)

## What happened

Eight reviewer runs for the CV1 follow-up's measurement were launched in parallel and all eight
died mid-flight on an account session limit. Two of them had already written an output file —
one had reported "both files are read, writing the audit now" before it was killed.

On resuming, the orchestrator said: **"If a recall or precision run was in flight when you were
cut off, discard it and re-run — a truncated run is absence of evidence, not a result."**

Both partial files were moved out of the scored directory and re-run from scratch.

## Why this is the right call

A reviewer output is only interpretable if the reviewer saw its whole input. A file that exists
proves the agent reached the Write call; it proves nothing about whether the 29 KB prompt was
fully read before the audit was composed, and a partial read produces a *confident, well-formed*
audit — exactly the shape that reads as a result. `tools/coverage-recall/runs/README.md` already
records one such case (a run that returned only "I need to read the rest of the file"), and
`recall.py`'s `no_verdict` state exists because averaging a truncated read in as a real 0 was a
measured defect.

This is [[FB-0010]] item 4 applied to the instrument's *inputs* rather than its logic: a
measurement whose input may be partial cannot distinguish "the reviewer found nothing" from "the
reviewer was not shown the thing". Keeping the file because it is *there* is the same error as
keeping a grep result because it exited 0.

It is also a contamination hazard, not just a dilution one. Earlier in this same PR a leftover
stamped argument file flipped a gate into source mode and produced an audit of the wrong
artifact. A stale output in a scored directory is the same shape: the next scoring pass cannot
tell it apart from a fresh one.

## How to apply

- **Discard every in-flight run after an interruption.** Do not inspect it first and decide: an
  output that looks complete is the case this rule exists for.
- Move discards OUT of the directory a scorer reads, rather than deleting them silently — then
  say in the report how many were discarded and why, so the run count is auditable.
- When a run is excluded, exclude it as a **named state**, never as a zero. `recall.py` already
  does this with `no_verdict`; hand-scored arms need the same discipline.
- Launch measurement runs in small batches. Eight concurrent runs meant one limit took the
  entire measurement, including the five that had barely started.

Related: [[FB-0010]] (item 4, instrument validation), [[FB-0127]] (a disclosed confound is still
a confound).
