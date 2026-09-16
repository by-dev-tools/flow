# FB-0111 — A reviewer's VERDICT must be conditional on its own context having resolved

- **Date:** 2026-09-16
- **Source type:** two observers, two branches — a worker's degraded `/flow:critique-plan` run during
  the FB-0107 provenance PR, plus the orchestrator hitting the same symptom in a `/flow:staff-review`
  run on a different branch.

- **What was said:** a `/flow:critique-plan` run reported resolving **zero** reference documents and
  was therefore structurally unable to raise a Spec-violation finding. It said so, loaded the docs by
  hand, and returned seven real findings anyway. The observation that matters is the counterfactual:
  **had it instead returned `APPROVED`, nothing would have been wrong with that output.** The plan
  would have carried a confident pass from a reviewer that never read the rules.

- **Synthesized rule:** **a reviewer that could not load its sources of truth must not emit a clean
  verdict.** The warning and the verdict are currently independent: a critic can print `⚠️ MISSING`
  in its injected context block and return `APPROVED` in the same output, and no rule forbids it.
  Loud degradation protects the *human reading the transcript*; it does nothing about the *artifact
  the pipeline consumes*. A verdict is a claim about evidence, so it has to be gated on the evidence
  having arrived.

  **The gap is narrower and more specific than "reviewers should warn", which is why it survived.**
  Three things are already true and none of them closes it:

  1. `plugins/flow/lib/resolve-doc-slot.sh` (#146) resolves fragmented doc directories correctly and
     warns loudly. Verified on `main`: `sh plugins/flow/lib/resolve-doc-slot.sh feedbackPath
     dev-docs/feedback.md` → `DIR dev-docs/feedback (93 entries…)`. **The silent-fallback bug it was
     written to kill is dead** — its own header documents it — and any sighting of
     `(no feedback doc at …)` today is an old *installed* plugin, i.e. an FB-0107 artifact, **not** a
     live defect. Do not re-file it as one.
  2. `skills/critique-plan/SKILL.md` already carries the right sentence — *"This is not an APPROVED"* —
     but for exactly **two** shell-level preconditions: `ROOT-UNRESOLVED` and `JQ-MISSING`. Both are
     failures to *start*. The case actually hit was a failure to *find*: the root resolved, jq was
     present, the globs ran, and they matched nothing. No rule covers that.
  3. The rule lives in the **wrapper skill**, not in the agent that writes the verdict. Measured:
     `agents/plan-critic.md` names `APPROVED` three times and contains **zero** instructions making it
     conditional on context; `agents/auditor.md` likewise. So an agent handed a context block with a
     `⚠️` in it has been told nothing about what to do with it.

  **Shape of the fix, when someone takes it:** put the conditional in the **agent prompts**, where the
  verdict is authored — "if the injected context reports that a source of truth failed to resolve, you
  may still report findings, but you may not return `APPROVED` / `No issues flagged.`; return the
  degraded-context verdict instead" — and give it a distinct verdict token so a consumer can tell
  "reviewed and clean" from "could not review". The existing two-precondition wording in
  `critique-plan/SKILL.md` is the model for the sentence; the work is generalising it from *failed to
  start* to *failed to resolve*, and moving it to where the verdict is written.

  **Family:** FB-0082 (`absent` / `invalid` / `stale` / `ok` must stay distinct — here applied to a
  verdict rather than to a handoff), FB-0062 (a stage's verdict is trusted only when its canonical
  artifact exists — here the artifact is the reviewer's own input), and FB-0107 (a gate that reports on
  the wrong artifact is worse than a missing gate, because it manufactures the belief that the check
  happened — this is that, one layer up).

- **Applies to:** `plugins/flow/agents/plan-critic.md`, `plugins/flow/agents/auditor.md`,
  `plugins/flow/agents/lens-*.md`, `plugins/flow/skills/critique-plan/SKILL.md` (generalise its
  existing two-precondition rule), `plugins/flow/scripts/extract_session.py` (the zero-resolution path
  is what must be signalled to the agent).
