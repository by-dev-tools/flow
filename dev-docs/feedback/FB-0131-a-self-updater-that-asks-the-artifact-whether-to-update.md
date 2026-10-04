# FB-0131 — A self-updater that asks the artifact whether to update it cannot bootstrap

**Date:** 2026-10-03 · **Source:** Ben, via the orchestrator seat · **Observed on:** installed flow 1.29.0 against a working tree at 1.55.0, in two independent Conductor cloud workspaces

## What happened

`.claude/hooks/flow-plugin-currency.sh` exists to keep this repo's **installed** flow plugin current,
because dogfooding resolves `/flow:*` from the install and not from the checkout (FB-0107). It had
never once updated anything.

The engine it consults — `skills/ship/lib/plugin-provenance.py` — **ships inside the plugin**, added
in v1.43.0. The hook resolves that engine from the installed tree only, which is the correct security
call (it fires with no approval prompt, so running the checkout's copy would make `gh pr checkout` of
an untrusted branch equivalent to executing it). On any install older than v1.43.0 there is no engine,
so the hook printed *"this currency check is inactive"* and exited 0.

**The updater could only update installs that were already new enough not to need it.**

Measured, and the numbers matter because they say how long this can hide: every Conductor cloud
workspace boots from a snapshot carrying **1.29.0** with an identical `installedAt`, the working tree
was at **1.55.0** (`release_gap: 26`), and `surface_drift.skills_missing_from_installed` named
`autoplan, gate, handoff, orchestrate, prototype, review-brief, spawn` plus all four rule-skills. A
roadmap entry had separately filed *"the orchestrator seat does not use `/flow:spawn`"* as a
discipline problem. The skill was not installed.

## Why it survived 26 releases

Three compounding reasons, and each is the generalizable part.

1. **The failing state and the healthy state printed the same shape.** "Exits 0, prints a note" reads
   identically whether the hook did its job or refused to. There was no before→after number anywhere,
   so nothing distinguished *converged* from *declined to try*.
2. **Nobody could read the note anyway.** Every line went to stderr, under a comment that said
   *"All output to stderr so nothing is injected into the session's context."* The mechanism was
   understood; the consequence was not. Claude Code's hook docs: stderr from a hook that exits 0
   "goes to the debug log only, never the transcript, and Claude never sees it" — and this hook
   always exits 0, by design. Confirmed by probe: a fresh session asked for its `[flow-currency]`
   line reported none. The warning existed, was correct, and had no reader.
3. **An eval asserted the bug was correct.** `test_hook_degrades_safely` carried
   `check(not any("plugin update" in c for c in calls), "with no engine the hook must not
   blind-update")`. Defensible when written — it was guarding against the hook blind-updating on an
   unreadable registry — and it pinned the deadlock as the contract. CI was green over it.

## The rule

**A mechanism that updates X must not depend on X to decide whether to run.** When the predicate ships
inside the artifact, absence of the predicate is not "cannot tell" — it is the answer, and the
strongest available one. The bootstrap arm acts on it rather than stopping.

**Corollary — a self-check's output must distinguish "I acted" from "I declined", by naming a value
that changed.** A verdict with no before/after is indistinguishable from a no-op for as long as nobody
looks, which here was 26 releases. This is `.claude/rules/general.md` § Consistency item 4 aimed at a
mechanism's *output* rather than at a detector's inputs.

**Corollary — know which channel your audience reads.** A diagnostic on a channel nobody reads is not
a diagnostic. Before relying on a warning, check that the intended reader receives it; for a Claude
Code hook that means knowing which events inject stdout into context (`SessionStart`,
`UserPromptSubmit`, `UserPromptExpansion`, `PostModelSwitch`) and that stderr on a zero exit reaches
neither Claude nor the transcript.

## How to apply

- **When adding a self-updating or self-checking mechanism, write the bootstrap case first.** Ask:
  *what does this do on the oldest state it will meet?* If the answer is "detects that it cannot tell
  and stops", that is the deadlock, not graceful degradation.
- **Pin both polarities of the acting case**: it acts when it should (named versions, before → after),
  and it stays quiet when it should not. A single-polarity pin passes on a mechanism that never fires.
- **Pin the one-that-looks-like-success too.** `plugin update` can exit 0 having moved nothing; an
  unconditional `X → Y` arrow would then manufacture exactly the confidence the mechanism exists to
  provide honestly. The `⚠️ … is STILL X` branch is asserted in the failing direction.
- **Before trusting an operational warning, measure that its reader gets it.** Cheap: one probe session
  asked to quote the line back.

## Three corollaries the review pass added, each paid for

**An eval can pin the bug as correct, so when you fix one, grep the suite for assertions that encode
the old behaviour.** This happened **twice in one PR**, and the second instance survived the first
fix: `"with no engine the hook must not blind-update"` *was* the deadlock, and
`"an undeterminable comparison must not blind-update"` was the same deadlock one arm over, still
green after the first was flipped. CI was green over the bug for 26 releases in the first case. The
tell is an assertion phrased as *"must not act"* on a path where acting is the remedy. **Both halves
of the replacement are required** (FB-0010 clause 3): it must act, *and* the thing the old assertion
legitimately protected must still hold.

**Mutate the mechanism the assertion protects, not only the feature under test.** A five-mutation
sweep validated this change's hook arms and still missed that the new channel test was **vacuous** —
the shim wrote its chatter to a log file, never stdout, so *"CLI chatter must never reach stdout"*
could not fail. `/simplify`'s efficiency lens found it by deleting the `1>&2` redirect in `cc()` and
watching the suite stay green. The sweep had mutated every branch the test *described* and never the
one line it *depended on*. Before trusting a guard, ask what single edit would make it meaningless,
and make that edit.

**A hedge keyed on a permanent condition is a permanent warning, which is the same as no warning.**
The ambiguity probe first keyed on "more than one version tree in the plugin cache" — and since
`claude plugin update` never prunes the old tree, that is **permanently** true on any machine that
has ever updated. Caught by two independent review lenses; the cry-wolf eval could not catch it
because its fixture used an install path outside the cache, i.e. a state the fixture's own docstring
calls impossible. Two rules: when a predicate gates a warning, check whether its condition ever
becomes false again; and a severity decision belongs in the renderer, not in the predicate — the
predicate should say what is *true* (undeterminable), and the renderer should decide how loudly to
say it (`ℹ️`, not `⚠️`, when the state is the steady state).

**The sweep I used to say "full eval sweep clean" could not see a failing harness — and I had written
the rule it broke.** Measured: `run_autoplan_evals.py` exits **1** while its last output line reads
`241/244 checks passed`. My ad-hoc sweep was `out=$(python3 "$f" 2>&1 | tail -1); case "$out" in
*FAIL*|*Traceback*|*rror*)` — a grep of the last line. No failure token appears in that line, so the
sweep reported the suite clean on **four consecutive pushes** while CI was red on the same SHAs, and
the phrase went into four commit messages and a readiness report to the orchestrator.

`.claude/rules/general.md` § Consistency item 4 already states the corollary: *"prefer a tool's own
exit code over a grep of its output … an exit code is a signal the tool's author designed and
maintains against their own output format."* I quoted that rule into this file's corollaries and then
violated it in the instrument I used to make the claim. The CV1 worker hit the identical defect a day
earlier (its runner read the last line and reported 43 green with one red), which is what makes this a
**class rather than a slip**: a convenience grep is the default thing a shell loop reaches for, and
nothing about writing it feels like a decision.

**How to apply.** Three things, in order of how much they buy:

1. **Never key a pass/fail loop on output text when the tool exits non-zero.** `if ! cmd; then` is
   shorter than the `case` statement it replaces. `tools/eval-sweep.sh` now exists so the loop is not
   retyped per session — a one-liner retyped is a one-liner re-broken.
2. **Give the runner a `--selftest` that proves it can report RED**, and make the decoy reproduce the
   shape that fooled the last one — non-zero exit, innocuous last line. A runner validated only
   against passing harnesses cannot be distinguished from a broken one.
3. **A green local sweep is not CI.** The ship pipeline never reads CI status, so "ready" in a PR body
   is not evidence that checks pass. Run `gh pr checks <N>` and read it before saying ready. I said
   ready on a PR GitHub was reporting as `BLOCKED`.

**The general shape, which is the part worth carrying:** when an instrument and an independent
authority disagree about the same artifact, the instrument is the thing to doubt first — and if the
instrument has only ever returned one answer, it has produced no evidence at all. Two surfaces
disagreeing on one SHA is the cheapest possible signal that one of them is broken; it should trigger
an investigation of the measurement, not a re-read of the thing measured.

**A clean merge is not evidence the document is right — and for a positionally-parsed doc it can be
actively wrong.** After rebasing onto a `main` that had gained a PR, `dev-docs/plan.md` merged with no
conflicts and the result placed this PR's plan block **second**. `extract_block` takes the first
non-demoted `Spec-walk`, so it selected the other PR's 20 criteria as this change's active plan, and
`/flow:verify-build` + `/flow:audit-coverage` would have graded this diff against them and reported
green. Git chose the order; no author made a mistake; nothing warned.

**How to apply:** after any rebase or merge that touches a positionally-parsed document, run the
parser and confirm it selected *your* block — do not infer it from the absence of conflict markers.
One command: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/extract-criteria.py <planPath>`
and check `source_heading_line` against your own block. The generalizable form is wider than plan
docs: **a text merge preserves content but not ORDER, so any consumer that derives meaning from
position can be silently rewritten by a merge it never saw** (field-manual T4 is the same lesson for
keep-both conflict resolution; this is the no-conflict case, which is worse because there is no prompt
to think at).

## Also recorded here, because it cost a measurement

`.conductor/settings.toml`'s `scripts.setup` was the obvious provisioning-time fix and **does not run
at all** in a Conductor cloud organization — the org's *saved* per-repository setup script is the only
one that executes; repo-defined ones are ignored. Three agreeing sources (Conductor's worker code, its
bundled `computer-admin` skill, and a marker-first probe whose marker was absent with the file provably
on disk). Shipping it would have been a mechanism that never fires in the one environment it targets —
this file's own failure class, committed deliberately. The remedy is org config and is written up as
copy-paste commands in `dev-docs/roadmap.md` § "FOR BEN — one org-level save per repo".

Related: [[FB-0107]] (the provenance rows this hook backstops), [[FB-0085]] (shipped, believed
effective, never firing), [[FB-0118]] (pin a claim at the layer where it is claimed).
