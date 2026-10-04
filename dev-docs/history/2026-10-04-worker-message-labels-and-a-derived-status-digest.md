# 2026-10-04 — Worker-message labels, and a status digest that is derived rather than stored

**Version:** v1.61.0 · **Feedback:** FB-0132 · **Branch:** `conductor/mobile-option-5-label`
**Mode:** feature · **Surface:** non-visual (prose contracts + one skill section; no UI)

## What

Mobile-workflow research option 5 plus the message-label convention. Two surfaces, one theme:
make the orchestrator seat's chat readable on a phone.

1. **The `[w:<short-name>] <STATUS>` opener**, stated at all four sites that state the ping
   contract — `/flow:spawn`'s brief Contract block, canonical §4.8 rule 6, the orchestrator field
   manual §3, and the shipped consumer doc `plugins/flow/docs/workflow.md`. Statuses are exactly
   `GATE` · `DONE` · `BLOCKED` · `FYI`, under a published mapping from §4.8 rule 6's three ping
   triggers.
2. **`/flow:orchestrate` §8 — a status-only digest path.** Re-runs steps 2–4 (the derivation that
   already exists), prints one phone-sized table, stores nothing, and skips steps 5 and 6.
3. **`plugins/flow/evals/run_ping_label_evals.py`** (new, CI-wired), deriving its site list from a
   grep.
4. Two rules added mid-execution by Ben: short-name uniqueness, and the loopback-in-a-code-span
   delivery failure.

## Why, and the decisions behind it

**A stall reports as `BLOCKED` rather than getting a fifth status.** The seat's next action is
identical either way — unblock or re-dispatch — and the body carries the distinction. Four tokens
scan; five start costing the thing the label exists to buy. This was flagged at MEDIUM confidence
in the plan specifically because it is a taste call on Ben's own reading, and it was approved as
recommended rather than assumed.

**The digest is derived, not durable — which inverts what research option 5 proposed.** The
research note asked for a *durable, glanceable* surface. A stored status table was measured stale
**within minutes** in this very program: it read "dispatched" for three workspaces the API already
reported deleted. So the digest's correctness comes entirely from being recomputed; persisting it
would rebuild the thing `/flow:orchestrate` step 2 already forbids ("never from a snapshot"). The
research doc now records the inversion and why, so the next reader finds the reasoning rather than
an apparent mismatch between the option and the code.

**Steps 5 and 6 are skipped, and the reason is not symmetry.** Step 6 (load the gate policy) is
merely unused by a path that classifies nothing. Step 5 is *actively harmful*: it tells every live
worker where to ping, so running it from a session that is not the orchestrator points the whole
fleet at that session, and every subsequent ping is lost to a seat nobody reads. The skip is
therefore documented as a correctness requirement rather than an optimization.

**Option 5's second limb — "lean on Conductor's own per-workspace status rows" — was declined as
the basis.** Research §7 records that claim as *secondary*, from search results rather than a
fetched page, and explicitly worth confirming. Building the answer on an unverified vendor claim
would make the work's value unmeasurable. The digest is Conductor-independent and carries a
deletion criterion naming exactly that surface, so if the rows do turn out to be sufficient this
costs one section to delete.

## Tradeoffs

- **The convention is unenforceable at the point that matters, and that is stated rather than
  designed around.** Nothing wraps a worker's outgoing message, so the eval pins the *brief* and
  the four contract docs — not a worker's actual output. A mechanical enforcement point would need
  the backend to intercept messages, which flow does not control. Recorded as a known gap in all
  four sites and in the changelog, not papered over.
- **Four files stating one contract is a fan-out** (`general.md` § Consistency item 2). The defense
  is that the eval's site list is **grep-derived**, not hardcoded: `contract_sites()` greps
  `plugins/flow/skills`, `plugins/flow/docs` and `research/` for the contract's own trigger phrase,
  and every file it finds must carry the convention verbatim. A hardcoded list of four paths would
  have been the bug. `dev-docs/` is excluded deliberately — plan/history/feedback entries *quote*
  the contract as a record of a decision, and a record of what was decided is not a statement of
  the live rule.
- **C1 grew from one sentence to three, and that was authorized twice over.** The grant was one
  sentence in `workflow.md` stating the label; two later instructions each added a line to the
  convention (uniqueness, then the loopback rule), and the convention is asserted *identically* at
  every site, so the consumer doc carries all three. Flagged here because the grant as literally
  worded was for one sentence.
- **C3 deferred, with the reasoning recorded rather than the conclusion.** `/flow:handoff` and
  `brief-check.py` still do not carry the convention, so a successor seat inherits the ping channel
  without the message contract on it. Widening `brief-check.py` is a `sensitivePaths` edit (gate
  machinery) for a currently-cosmetic gain. The roadmap row states what would change the calculus:
  if anything automated ever *parses* the label rather than a human reading it, an omitting brief
  becomes a real break. Nothing needs rewiring to do it later — the grep would pick `handoff/` up
  automatically.

## Two bugs in this PR's own eval, both caught by its selftest

Worth recording because they are the failure classes this repo keeps re-earning.

1. **`p_triggers` and `p_status_set_exact` read the `MAPPING` module constant instead of the file
   text.** Both therefore asserted a property of a literal sitting three lines above them and would
   have stayed green over *any* edit to the shipped prose. They are now parsed out of the file via
   a `<trigger> → \`STATUS\`` pair regex. This is `general.md` § Consistency item 4's third
   corollary — a criterion pinned one layer below the surface it describes — committed inside the
   harness written to prevent it.
2. **A naive `"STALLED" in text` negative would have fired on `INSTALLED`.** Four innocent sentences
   in this repo say "INSTALLED", and `INSTALLED` ends in `STALLED`. The check is now
   `(?<![A-Z])STALLED\b`. An always-failing detector is a different bug from an always-passing one
   and is caught faster, but it is the same root cause: a negative assertion shipped without being
   run against a case whose answer is known.

The selftest that caught (1) runs on **every** invocation, not behind `--selftest`. A validation
step you have to remember to pass a flag for is a validation step that does not run in CI. It
mutates the real shipped text (label removed, fifth status added, a trigger unmapped, a trigger
mapped twice, uniqueness dropped, firewall dropped, PR link unlinked, …) and fails if any predicate
*accepts* a mutation.

**And the grep itself was validated at the composed layer, which a mutation cannot do.** A
throwaway `research/__probe-fifth-site.md` containing only the trigger phrase was picked up as a
fifth site and failed 6 of 7 per-site checks by name; it returns to green on removal. So the
instrument is known to be able to *find* a new site, not merely to reject bad text in a site it was
already pointed at.

## The mid-execution additions

Both arrived from Ben during execution and are recorded as Spec-walk criteria rather than absorbed
silently (`general.md` § Scope discipline).

- **Short-name uniqueness (FB-0132).** This seat had been labelling its own messages `[w:mobile]`,
  the research worker's name. The plan that designed the convention was itself a counterexample to
  it. The deeper point is in the FB entry: uniqueness is the one property of an identifier that is
  invisible from inside a single message, because it is a property of the *set* of senders — so a
  seat reasoning about message design never has it in view. `/flow:spawn` §3 now instructs the seat
  to check the name against the backend's `listWorkers` verb before writing the brief, i.e. a check at the point of
  use rather than a resolution to remember.
- **The message channel drops loopback URLs inside a code span** (measured by the touch worker,
  2026-10-04; the identical text without backticks delivers). The convention line is a *mitigation*
  — it tells a worker to state such URLs bare. It does not stop a future skill from composing one
  in backticks, because nothing checks message bodies, and the send reports success so the loss is
  invisible from the sending end. That honest gap is why this also got a roadmap § Next row naming
  the cause and three candidate fixes, of which only a `sendMessage` read-back actually *detects*
  the drop rather than preventing one known cause of it. The row also flags what is **not**
  characterized: whether the trigger is loopback-specific or a broader URL-in-a-code-span rule.

## Version and number claims

`v1.59.0` was taken by `conductor/mobile-options-1-3` between plan and execution, and `v1.57.0` by
[#176](https://github.com/by-dev-tools/flow/pull/176). The sweep read **all 130 remote heads**, not
just open PRs — load-bearing here, because only one PR is open and 1.59.0 sits on a branch without
one, so an open-PR-only sweep would have collided. Took **v1.61.0**. FB-0132 re-swept across every
remote `dev-docs/feedback/` tree and confirmed free (highest claimed anywhere: 0131).

**Post-rebase extractor check** run per the plan's mandatory step: `extract-criteria.py` reports
`source_heading_line: 103` with this block's nine criteria, not another PR's.

## Files

`plugins/flow/skills/spawn/SKILL.md` · `plugins/flow/skills/orchestrate/SKILL.md` ·
`plugins/flow/docs/workflow.md` · `plugins/flow/evals/run_ping_label_evals.py` (new) ·
`.github/workflows/ci.yml` · `research/2026-08-23-flow-cloud-workflow-plan.md` ·
`research/orchestrator-field-manual.md` · `dev-docs/research/2026-10-mobile-workflow.md` ·
`dev-docs/roadmap.md` · `dev-docs/plan.md` · `dev-docs/feedback/FB-0132-*.md` · `CLAUDE.md` ·
`changelog/v1.61.0.md` · `plugins/flow/.claude-plugin/plugin.json` ·
`.claude-plugin/marketplace.json`

**`CLAUDE.md` layout fix (granted separately):** top-level `research/` was absent from the
repository-layout tables, which listed only `dev-docs/research/*.md` — while two of the four files
this PR edits live there, and two of them are grep-derived eval sites. Added as one row under
project-dev infrastructure, naming the canonical plan and the living field manual.
