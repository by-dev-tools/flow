# The §4.10 orchestrator skill suite — `/flow:orchestrate`, `/flow:spawn`, `/flow:handoff`, `/flow:gate`

**Date:** 2026-09-17 · **Version:** v1.45.0 · **Feedback:** FB-0110 · **PR:** _(set at ship)_

## What shipped (user-facing)

Four new agent-invocable skills for running several worker workspaces from one orchestrator seat, plus the two config slots that keep them host-agnostic.

- **`/flow:orchestrate`** — boot or re-boot a seat: read the durable layer by slot, re-derive live worker state from the backend, sweep **open branches and open PRs** (not just the default branch), sweep for **silent** workers by last-activity rather than status, re-address the ping channel to this seat's id (one message per worker), load the gate policy, report ready as one decision.
- **`/flow:spawn`** — dispatch one worker: admission control, `model · effort · why` routing with the gate-machinery floor **enforced** via the shared predicate, a ≤30-line brief, workspace creation with the brief as its first message, and B's first action named as a flow skill.
- **`/flow:handoff`** — seat succession: flush durable currency through `/flow:ship`, **inventory and externalize sandbox-local artifacts**, generate a pointing-not-duplicating brief, verify it mechanically, deliver it, and run archive-safety on the outgoing seat.
- **`/flow:gate`** — four-axis plan-gate classification, merge-gate classification, the ships-or-paperwork pre-check, and escalation formatting. **Never merges.**
- **`dispatchBackend`** (five command templates, closed placeholder vocabulary) and **`sensitivePaths`** (shape-based project-agnostic defaults). Schema 34 → 36 slots.

## Why, and the tradeoffs

**This was transcription, not design.** §4.8/§4.9/§4.10 and the orchestrator field manual are a record of what a seat has been doing by hand for a week. Every checklist step is lifted from one of them; where the judgment was not already written down, the skill asks the agent. That is §4.10's anti-bloat guardrail, and it is why the PR ships ~0 new policy.

**Host-agnosticism by adapter, not exclusion.** `dispatchBackend` holds *command templates the consumer writes* — the `typecheckCmd`/`preflightCmd` shape one level up. The rejected alternative (a backend *name* the plugin maps to a built-in table) would put host literals back into shipped artifacts, which is the thing the adapter exists to prevent. Cost: a consumer hand-writes five lines of config. Mitigation: `/flow:doctor` Check 2.12 catches a malformed adapter at setup rather than mid-dispatch.

**No `{message}` placeholder, and unknown placeholders are a hard error.** T6 fired four times in a single session among authors who had each just reasoned about it — refuted design, then silent data loss, then unintended execution, then the report of the third mangled by the third. FB-0108's conclusion was that the fix belongs in the interface. So message bodies travel as a path and only as a path, and substituted values are **refused, never escaped** — an escape is something an author has to remember.

**Two slots, not one nested object.** `sensitivePaths` is gate policy, not backend mechanics, and it has two readers. The cost is a wider `N slots` fan-out, swept mechanically.

**The defaults are deliberately shape-based.** Secrets, auth, migrations, published schemas, CI. Flow's *own* gate machinery lives in flow's `flow.config.json`, not in the plugin — hardcoding `ship`/`manifest-triage`/`skip-audit` in the schema would make the plugin's gate policy assume it was running on flow. The evals make the boundary visible: with defaults `plugins/flow/skills/ship/**` is not sensitive; with flow's config it is.

**Merge delegation is hard-wired off.** `/flow:gate` classifies which branch a merge falls into and whether it would delegate at the next rung, but the verdict is one literal in the source and no input changes it. A slot that could enable delegated merges before a distinct merge identity exists would let an agent merge under the human's credential and erase the only provenance the policy asks for.

## What the reviews caught

**`/flow:critique-plan`, three rounds, 13 findings, all 13 accepted.** Rounds 1–2 found the unbuilt rule-5 return leg (an escalation with no way to relay the answer back), missing deletion criteria on ten new artifacts, a pre-declared `/flow:security-review` skip that named the *wrong predicate* on the one security-sensitive file in the PR, a shared predicate argued for and then placed where its second reader could not reach it, an unimplemented `/flow:handoff` refusal, an unwired `selfSession` consumer, and a wrong harness count.

**Round 3 changed the design in five places**, and is the reason this entry exists in the shape it does — see FB-0110's second corollary for the measurement. In particular it caught that **a model roster in a shipped skill is itself a host-hardcoded token**, which dissolved an open call rather than deciding it: neither source table ships verbatim, and `/flow:spawn` carries job-shape → **tier · effort** with ids resolved at dispatch time. It also caught that the routing record had nowhere to go (§4.4 deletes ledger *state-tracking*; §4.3 retains model/effort/why, and FB-0091 makes recording it mandatory), and that the shared predicate's two readers were being handed different input shapes — FB-0079's exact "one slot, two questions" failure, resolved by normalising spawn's input rather than overloading the predicate.

**The new harnesses caught three real bugs in their own subjects**, which is the argument for writing them: `validate()` never stored its per-verb entries (so `/flow:doctor`'s report would have been empty); the gate classifier crashed on a non-string axis value (a gate that raises is a gate that did not run); and the host-literal sweep found a real `Conductor API` literal in `brief-check.py`'s docstring. A fourth finding was a *dead* fail-safe — "pattern failed to compile" could never fire, because translation escapes every literal — which was removed rather than kept. An unreachable fail-safe is dead code that reads like protection.

## What `/simplify` caught — including the one defect that mattered

Four parallel agents; 14 findings taken, 6 routed to the roadmap as cross-cutting refactors of files this PR does not own.

**The fail-open.** `sensitive_paths.py` returned `sensitive: false` for an owned glob matching no tracked file — the *greenfield* case, and the likeliest way the predicate is asked about exactly the work the floor protects: a worker dispatched to **create** `db/migrations/**` or `src/auth/**` owns a glob with no matches today. `/flow:spawn` reads the machine-readable field, so the stderr warning that stood in its place left the guarantee resting on author memory. The deeper framing came from the reviewer and is the part worth keeping: `expand_globs` silently converts spawn's *intensional* question ("could this worker touch gate machinery?") into an *extensional* one ("what does it own today?") and returned the weaker answer under the stronger question's field name. Now classified sensitive with a stated reason, and the module's "every degraded path escalates" invariant is literally true instead of true-with-one-exception.

**The placement contradiction.** `dispatch_backend.py` had five readers while filed under `skills/spawn/lib/` — contradicting, in the same commit, the argument `sensitive_paths.py` makes for its own placement in `plugins/flow/lib/`. The cost was already real rather than theoretical: flow's own `sensitivePaths` covered `skills/gate/**` and `lib/sensitive_paths.py` but **not** the module that decides which commands get executed. Moved and added to the list.

**The check that passed and then failed.** `{branch}` sat in the closed placeholder vocabulary with no verb requiring it and no skill supplying it. A consumer template using it passed `/flow:doctor` Check 2.12 — printing "all 5 verbs valid" — and then refused at render with "no value supplied." That is exactly the check-passes/dispatch-fails class Check 2.12's own rationale says it exists to prevent. Removed; an eval now asserts every advertised placeholder is required by some verb, and doctor reads the vocabulary out of the report instead of restating it (it had been written out in three places).

**Dead code deleted rather than kept:** `_tri`'s unused polarity flag, `classify_merge`'s entire stakes path (no SKILL.md passed a file list, `main()` passed `[]`, no eval asserted it), a `reason` fallback that could never carry anything, an unreachable `return 2`. Also `render()`'s `str.split()` → `shlex.split` (a quoted placeholder in a consumer's template produced an argument with the quotes still in it — an ad-hoc quoting decision inside the module whose argument is "refuse, don't escape").

**Two silent-degradation sites.** Two skills resolved doc slots in prose rather than through `lib/resolve-doc-slot.sh` — and flow's own `feedbackPath` is a *directory*, so `[ -f ]` is false on it and an orchestrator booting in this repo would have read the feedback corpus as empty, quietly. And `/flow:orchestrate`'s `sensitivePaths` check was vacuous in both directions: `--print-defaults` returns before the config is read (so a malformed slot still printed "available"), and `&& echo` printed nothing on failure.

**The fan-out that happened inside this PR.** `/flow:gate` got a `mkdir -p .flow` while `/flow:spawn`'s byte-identical redirect did not — one of two identical sites fixed, which is the class `.claude/rules/general.md` names. Both fixed, plus the CWE-59 symlink refusal every other scratch writer carries.

**A diff-hygiene catch worth recording:** the schema change was 247 lines for two slots, because a JSON formatter expanded every inline array in the file — burying the real addition inside a path this PR itself declares sensitive. Rebuilt as additive-only: 61 inserted, 0 deleted.

## Open, and not silently absorbed

**The field manual's satisfied deletion criteria — owed here, sequenced behind a rebase.** This PR satisfies three of them:

| Field-manual section | Satisfied by |
|---|---|
| **§ 1 — measurement traps** | `/flow:orchestrate` performs the sweep itself: T2's silent-worker sweep reads last-activity rather than status, T5's ground-truth sweep covers open branches and open PRs |
| **§ 2 — standing calls (resolve vs escalate)** | `/flow:gate` implements the four-axis classification, the ships-or-paperwork pre-check, and the escalation format |
| **§ 6 — model routing at dispatch** | `/flow:spawn` applies the table and emits the `model · effort · why` line, which § 6 names as its own deletion condition |

The rule is that whoever satisfies a criterion deletes it in the same PR — otherwise the manual advertises as an open gap something that is closed, which is the same confidence-inverting shape one layer up. **That could not be done in the first pass: the file existed only on an unmerged branch**, and cherry-picking a 296-line doc this PR did not author would have broken the merge order and put two branches on two shared research docs. The correct fix was ordering, not scope: the field-manual branch ships first, this branch rebases onto it, and the three deletions land **here**, citing this PR — because this is the PR that satisfies the criteria. They deliberately do **not** ride the field-manual branch, which lands the doc as written; deleting there would remove descriptions of capabilities that have not merged yet. **The criteria fire when the suite lands, not when it is written.**

This table is the backstop. If the ordering slips, it names the exact three sections so they cannot become an unclaimed cleanup pass.

**The one criterion whose file was already on `main` is discharged here:** §10.2's dispatch-brief template in `research/2026-08-22-conductor-orchestration.md` now carries the `--message-file` form with a dated note recording that the quoted `--message "…"` form was **removed rather than discouraged**. Shipping the file form in `/flow:spawn` while the source doc still prescribed the quoted one would have left the next reader to re-derive the conflict and possibly resolve it the other way — a documented conflict fixed in code but not at the source is a landmine with a longer fuse.

**The suite is over its stated size budget** — 37,597 chars against ≤35 KB, with `spawn` at 12,010 against ≤10 KB. One trim pass ran first (descriptions −25%, `spawn` −7%). Reported rather than quietly accepted, with the honest lever named: dropping `/flow:handoff` to a later PR, not thinning the other three.

**A live FB-0107 instance, reported and not widened into.** This workspace's installed plugin is 1.29.0 while `main` is 1.43.0, so `/flow:critique-plan` has loaded zero reference documents in this repo since #146. It is the second independent confirmation that installs are stale **per workspace** rather than globally, and that #150's provenance work *reports* the skew without remediating it.
