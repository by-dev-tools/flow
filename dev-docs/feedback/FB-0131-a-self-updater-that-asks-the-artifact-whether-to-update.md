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
