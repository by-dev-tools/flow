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

## Open, and not silently absorbed

**The field manual's satisfied deletion criteria.** This PR satisfies three of them — §1's traps (`/flow:orchestrate` now performs the sweep), §2 (`/flow:gate` implements the four-axis classification), §6 (`/flow:spawn` applies the table and emits `model·effort·why`). The rule is that whoever satisfies a criterion deletes it in the same PR, otherwise the manual advertises as open a gap that is closed. **The file is on the unmerged `orchestrator-field-manual` branch**, so this PR cannot delete from it. The one satisfied criterion whose file *is* on `main` — §10.2's quoted `--message` template — is corrected here, with a dated note recording why the quoted form was removed rather than discouraged. The other three deletions are owed on that branch and were escalated rather than left to a cleanup pass.

**The suite is over its stated size budget** — 37,597 chars against ≤35 KB, with `spawn` at 12,010 against ≤10 KB. One trim pass ran first (descriptions −25%, `spawn` −7%). Reported rather than quietly accepted, with the honest lever named: dropping `/flow:handoff` to a later PR, not thinning the other three.

**A live FB-0107 instance, reported and not widened into.** This workspace's installed plugin is 1.29.0 while `main` is 1.43.0, so `/flow:critique-plan` has loaded zero reference documents in this repo since #146. It is the second independent confirmation that installs are stale **per workspace** rather than globally, and that #150's provenance work *reports* the skew without remediating it.
