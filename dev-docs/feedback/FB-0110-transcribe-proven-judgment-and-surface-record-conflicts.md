# FB-0110 — Encode judgment that has already proven out; where two records of it disagree, surface the disagreement instead of picking

- **Date:** 2026-09-16
- **Source type:** user direction (dispatch brief, Track A / §4.10 orchestrator skill suite)
- **What was said:** *"the spec has been field-tested by hand all week and the transcript is the
  evidence… Your job is to encode judgment that has already proven out, NOT to invent it. Where the
  spec and the field manual disagree, say so and ask — do not silently pick one."*

- **Synthesized rule:** **When a skill's purpose is to automate a practice a human or an agent has
  already been running by hand, the authoring task is transcription with citations, not design.**
  Every checklist step should be traceable to the written record; anything you cannot trace is a
  place to ask the agent at runtime, not a place to invent policy. And when the record exists in
  more than one document — a design spec plus an operational field manual — **a conflict between
  them is a finding to surface, not an ambiguity to resolve quietly.**

  The asymmetry is what makes this worth a rule. Inventing a step that *looks* reasonable costs
  nothing at review time (it reads as competent) and everything later: it ships as though it were
  proven, and the next seat inherits it as evidence. Silently picking one side of a documented
  conflict is the same failure with a witness — the other document still says the opposite, so the
  contradiction survives in the corpus and re-fires on whoever reads the loser next.

  **The conflict is usually chronological, and that is exactly why it must be surfaced rather than
  auto-resolved.** The later document is *usually* right, but "usually" is a heuristic, not an
  authority: in this suite's case the two records disagreed about the dispatch brief's own message
  line (canonical §10.2's quoted `--message "…"` vs the field manual's measured "compose via file"
  standing rule), and also about a model-routing row that may have been dropped deliberately or
  merely trimmed. Same shape, different correct answers — which no single tie-break rule would have
  gotten right twice.

  **Corollary — "read the record first" requires sweeping branches, not just the worktree.** The
  field manual this task named as required reading does not exist on `main`; it lives on the
  unmerged `orchestrator-field-manual` branch and is already cited by a merged history entry as
  though it were durable. A doc can be load-bearing and unreachable from `origin/main` at the same
  time. This is the doc-shaped instance of the same sweep failure the field manual records as T5
  for FB/version numbers, and the resolution is identical: `git ls-remote` + open branches, never
  `main` alone, before concluding that something referenced is absent.

- **Applies to:** `/flow:orchestrate`, `/flow:spawn`, `/flow:handoff`, `/flow:gate` (canonical §4.10)
  — each ships as a transcription of §4.3/§4.6/§4.8/§4.9/§10.2 plus the field manual, with the
  judgment left to the agent per §4.10's anti-bloat guardrail. Related: [[FB-0088]] (procedures
  decay — which is why the *table* ships as prose the agent applies, and only the silently-failing
  rule is mechanized), [[FB-0106]] (classify ships-or-paperwork before escalating — the conflicts
  above are "ships", which is why they are open calls rather than quiet decisions), and
  [[FB-0090]] (recommendation + confidence + justification — the format each open call uses).
