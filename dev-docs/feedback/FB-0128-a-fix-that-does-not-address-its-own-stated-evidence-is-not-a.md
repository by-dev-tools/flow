# FB-0128 — A fix that does not address its own stated evidence is not a fix

**Date:** 2026-10-01
**Source:** orchestrator decision OD2 on the CV1 follow-up plan gate
**Status:** applied in v1.56.0 (CV1 follow-up, item 3)

## What happened

My plan for item 3 cited #171's red pin gate as the motivating evidence and then proposed
fixing **one** of its two causes. #171 went red because a criterion's pin was invisible, and
that had two independent causes: the reader kept only each bullet's first physical line, so a
pin on a wrapped line never reached the consumer; and `ARTIFACT_RE` used `\b`, which treats `_`
as a word character, so `eval` inside `run_coverage_docblind_evals.py` — this repo's own naming
convention for the artifacts it asks authors to cite — never matched. I named the first and
scoped the second out.

The orchestrator chose option (b2) and said why: **"A fix that doesn't address its own stated
evidence isn't a fix."** Also required: the second scan site, because
`critique-plan/lib/walk-pin-lint.py` had its own copy of the block scan, so a fix in
`extract_block` alone would have left `/flow:critique-plan`'s pin lint reading a fraction of
every plan and reporting it clean.

## Why this is the right call

A plan that cites evidence E and fixes half of E ships a PR whose own motivation still
reproduces. The remaining half is *harder* to fix afterwards, not easier: the citation has been
spent, the symptom is gone from the one case anyone remembers, and the next person to hit it
reads a closed roadmap bullet and a history entry that both say "fixed".

It also interacts with [[FB-0010]] item 2, the fan-out class. "Fix the cause I named" and "fix
the causes my evidence contains" differ exactly when the evidence has more causes than the
author noticed — which is the normal case for anything found by a failing gate rather than by
reading.

## How to apply

- When a plan cites a specific failure as motivation, **enumerate that failure's causes before
  scoping**. If the plan fixes a strict subset, say which cause is being left and why, at the
  plan gate — not in the history entry afterwards.
- Treat "the gate went red" as plural evidence until proven singular. #171's gate reported one
  symptom with two causes, and the symptom could not distinguish them.
- Before fixing a shared primitive, `git grep` for a **second implementation** of the same
  contract. Two copies of a scan is the normal state of a primitive that was once private; the
  copy keeps the defect after the original is fixed, and nothing fails.

Related: [[FB-0010]] (consistency discipline, fan-out), [[FB-0121]] (a gate must distinguish
"nothing there" from "I could not see").
