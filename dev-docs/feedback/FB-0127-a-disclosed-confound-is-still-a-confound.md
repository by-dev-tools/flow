# FB-0127 — A disclosed confound is still a confound: the harness's own setup became the only finding

- **Date:** 2026-09-30
- **Source type:** measurement during execution (CV1), correcting a decision this repo had written down
  and justified.

- **What was said:** nothing — this one was self-inflicted, and the previous session had already
  reasoned about it *and reached the wrong conclusion in a comment that read as careful*.
  `tools/coverage-recall/recall.py` injected the doc slot as an uncommitted `flow.config.json` edit and
  disclosed it on stderr, with this justification: *"the contamination is ACCEPTED AND DISCLOSED rather
  than hidden: exactly one extra hunk ... It cannot affect the question being measured."*

- **What was measured.** It affected the question being measured. The first slot-set run of the #159 case
  flagged **exactly one** issue, and it was the injected hunk — `flow.config.json:30`, tier
  `UNCOMMITTED` — scored as a false-positive candidate while all five of the case's real gaps went
  unflagged: **0-of-5, fp=1**. Hiding the same edit behind `git update-index --skip-worktree` (the block
  reads the config from the *working tree* but builds its file list from `git diff`, so the setting stays
  live while its hunk disappears) moved the identical case to **2-of-5, fp=0**. Same evidence, same
  reviewer, same slot; the only difference was whether the instrument's own setup was in the input.

- **Synthesized rule:** **a disclosure is a note to the human reading the harness; it is not a note to
  the subject being measured.** When an instrument must modify the thing it measures, the fix is to make
  the modification *invisible to the subject* — and if that is impossible, to say the measurement is
  confounded rather than to argue the confound is harmless. "I disclosed it" answers a different question
  than "does it change the result".

  The tell is specific and worth recognizing: the old comment's premise was **true** (there was exactly
  one extra hunk, and it was disclosed) and its conclusion was **false** ("it cannot affect the
  question"). A true premise carrying an unmeasured conclusion is the most convincing kind of wrong,
  because the part you can check is correct. Treat *"it cannot affect X"* as a claim requiring a
  measurement, never as a rationale — this is `.claude/rules/general.md` § Consistency item 4 applied to
  a harness's own setup rather than to its detector.

- **Applies to:** code, workflow — any measurement harness that must mutate its subject to run.
