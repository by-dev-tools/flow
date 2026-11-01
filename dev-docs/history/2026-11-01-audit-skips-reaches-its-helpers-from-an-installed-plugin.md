# `/flow:audit-skips` can reach its own helpers when flow is installed rather than checked out

**Date:** 2026-11-01
**Branch:** `conductor/fix-audit-skips-cant-find-its-checker-from-installed-plugin`
**Commit / PR:** [this commit] — PR link pending push
**Version:** v1.66.0
**Feedback:** FB-0141
**SAFETY** — gate machinery. The failure mode was a gate that could never look, reporting
"I could not verify" on every invocation in every consumer project.

## What

`plugins/flow/skills/audit-skips/SKILL.md`'s first `!`-block resolved two helpers — the stamp checker
(`scripts/flow_scratch.py`) and the engine (`skills/audit-skips/lib/skip-audit-checks.py`) — with two
independent copies of the same two-arm shape: `$CLAUDE_PLUGIN_ROOT`, else `plugins/flow/<path>`.
Replaced both with one three-arm resolver (`$FPR`):

1. `$CLAUDE_PLUGIN_ROOT`, accepted only if it carries `.claude-plugin/plugin.json`.
2. `installPath` from `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/installed_plugins.json`, taking the
   first `flow@*` candidate whose own `plugin.json` says `"name": "flow"`.
3. The guarded `plugins/flow` checkout arm, unchanged — dogfooding only.

Plus: an unresolved root now *says so* in both failure paths instead of composing a leading-slash path
that was never a location.

## Why

Arm 2 above did not exist, and old arm 2 (`plugins/flow/...`) is **flow-repo-relative** — in a consumer
project it cannot exist by construction. So on any run where the host variable was absent, **both**
helpers were unreachable and `/flow:audit-skips` reported `stamp_unverifiable` on every single
invocation. Reported by an external agent against an installed **1.29.0** (every run unverifiable, while
running `lib/skip-audit-checks.py` directly worked), and reproduced here on **1.64.0**.

The premise that made this look impossible was wrong. CLAUDE.md § How to Work 3,
`flow_scratch.py`'s docstring, and `2026-07-29-safety-flow-s-ephemeral-scratch-*` all state that
`CLAUDE_PLUGIN_ROOT` is set inside a `!`-block. Measured in one session on 1.64.0: it was **unset** for
`audit-skips`' fork and **set** for `audit-plan`'s — both `context: fork`. See FB-0141 for what was and
was not established.

## How it was measured

Reproduced first, fixed second. With a correctly-stamped handoff in place, the working-tree
`flow_scratch.py` was moved aside so only the CPR arm could win; the real forked skill then printed
`stamp checker not reachable at plugins/flow/scripts/flow_scratch.py` — the **fallback** path, while
`.../cache/flow/flow/1.64.0/scripts/flow_scratch.py` existed and worked when run directly.

The shipped `!`-block was then extracted and executed three ways: CPR set → full audit; CPR **unset** →
**byte-identical** to what the real fork printed; CPR unset with the fallback present → full audit. The
third run is the reason this survived 35 releases: in the flow checkout, and only there, the broken arm
is the working one. The byte-identical match is also what licenses verifying the fix by executing the
extracted block — a real forked invocation cannot exercise a working-tree change (FB-0107).

## Tradeoffs

- **Arm 2 reads host-private state.** `installed_plugins.json` is Claude Code's own record
  (`"version": 2` today) and its shape could change. Accepted because it is the only **live**,
  version-bearing source of the root. It is *not* accepted on the grounds that it "names the exact
  version in use" — an earlier draft of this entry and of the in-block comment both said that, and
  **this plugin had already measured the opposite**: `ship/lib/plugin-provenance.py::read_running`
  records that an update rewrites the record immediately but needs a restart, so a session can run
  1.29.0 while the record advertises 1.41.0. Arm 2 fires precisely when `CLAUDE_PLUGIN_ROOT` is unset,
  so a cached old skill body *can* resolve to a newer tree. Both texts now state the skew. Caught by
  this PR's own `/simplify` altitude pass — an unmeasured premise in a comment, in the PR whose thesis
  is that an unmeasured premise in a comment cost 35 releases.
- **SAFETY — arm 3 is content-gated, not authenticated, and the earlier claim here was false.** The
  sentence this bullet replaces said a miss "degrades to today's loud refusal — never to a false pass."
  That is wrong: an arm-2 miss falls through to **arm 3**, which is cwd-relative, and this block runs
  after a `cd` into the repo under review. An untrusted repo shipping `plugins/flow/.claude-plugin/plugin.json`
  with `"name": "flow"` plus its own two scripts gets its Python executed. The exposure is
  **inherited, not introduced** — the arm it replaces was a bare `plugins/flow/...` with *no* gate at
  all, reached whenever `CLAUDE_PLUGIN_ROOT` missed — and this change strictly narrows it: arm 2 now
  shadows arm 3 on any normal install, and a name check exists where there was none. It does **not**
  close it, because no file inside a tree can authenticate that tree against whoever wrote it. Routed
  to the PR as a `[decision-required]` security blocker rather than best-effort patched; the candidate
  fixes all cost in-repo dogfooding, which is a call for the human. Found by `/flow:security-review`.
- **Why the identity greps are not an attacker boundary, stated at both arms.** Forging arm 2 means
  writing into the user's own config dir — where `settings.json` hooks already live — so anyone able
  to do it has easier options; that, not the grep, is what makes arm 2 safer than a cwd guess. The
  comment now says "install-sanity check" rather than implying either grep authenticates anything.
- **Rejected: globbing `~/.claude/plugins/cache/*/flow/*/`.** The obvious shortcut, and wrong — this
  host carries both 1.29.0 and 1.64.0, so a glob can run one version's engine against another version's
  handoff.
- **Rejected: inlining the stamp check as jq+git.** Tempting and symmetric (ship Step 2a.1 *builds* the
  stamp in shell for exactly this reason, per the FB-0082 entry). But it fixes only the stamp arm; the
  engine cannot be inlined, so the skill would stay dead against an install. Recorded because it is the
  plausible half-fix.
- **Arm 1's identity gate is the manifest, not the individual helper it used to test.** A root with a
  manifest but a missing helper is a broken install, and the honest outcome is a loud error naming that
  root — not silently reaching past it into a different tree, which is how a working-tree engine ends up
  grading an installed release's handoff.
- **One root for both helpers, not two resolvers.** Two independent copies is what made the stamp
  checker and the engine fail together while presenting as one bug, and it admits a state where the
  install checks the stamp and the checkout computes the verdicts.

- **Arm ordering quietly retires the dogfooding path, and that deserves to be written down somewhere
  other than a test comment.** Arm 2 precedes arm 3, and the `SessionStart` currency hook keeps flow
  installed in this checkout — so here arm 2 now wins and the **installed** `skip-audit-checks.py`
  grades the handoff, where before (CPR unset in this fork) the working-tree engine ran. Measured in
  this pass: from the real checkout the block reports `plugin_root_arm: install-record`, and only with
  the record hidden does it report `checkout`. That is more coherent than the old mixed state, but
  `CLAUDE.md` § How to Work 3 still tells a reader that "everything the Bash tool resolves comes from
  the working tree", which now over-promises for this skill's helpers. Routed to the PR alongside the
  CLAUDE.md `CLAUDE_PLUGIN_ROOT` correction rather than edited here (out of this worker's lane).

## Evals

`run_scratch_isolation_evals.py` gains `test_installed_layout()` + `test_fork_skill_roster()`
— **31 checks** (counted on the wire, not estimated), all run with
`CLAUDE_PLUGIN_ROOT` **unset** from a temp git repo that has a `flow.config.json` and **no**
`plugins/flow/`, against a staged *copy* of the plugin tree named by a fake `CLAUDE_CONFIG_DIR` install
record. The existing `block-*` cases `export CLAUDE_PLUGIN_ROOT="{FLOW}"` first, so they could not
observe this; the positive here comes from outside the harness's own path vocabulary (FB-0136).

Paired per `general.md` items 3 and 4: the positive (`installed-layout-resolves`) has two mutations
(install record removed; record pointing at a non-flow tree) that must refuse, each named separately so
a failure says which assertion died, plus positive pins for all three arms so deleting the resolver
cannot turn the test green.

**Instrument validated against a known positive:** reverting only `SKILL.md` to pre-fix turns
`installed-layout-resolves` red with the exact message from the field report, while
`checkout-cpr-unset-resolves` stays **green** — demonstrating in the harness itself that no
checkout-based case can detect this class.

`tools/eval-sweep.sh`: 47/47 GREEN by exit code; `--selftest` confirms it can report RED.

## Known gap — the class is ~35 call sites, not five

**The first draft of this entry said "five `!`-block fork skills". That was a ~7x under-count**, found
by this PR's own reuse pass and then verified by grep. The flow-repo-relative arm also appears in:

- **13 `resolve-doc-slot.sh` preludes across 8 skills** (`accessibility-review`, `gate`, `land`,
  `orchestrate`, `security-review`, `ship-spike`, `staff-review`, `verify-build`). Consequence there is
  the exact silent degradation `resolve-doc-slot.sh` was built to kill: a cold-read reviewer running
  with no design-language or feedback context.
- **17 bare `${CLAUDE_PLUGIN_ROOT:-plugins/flow}` defaults across 5 skills** (`gate` 5, `spawn` 4,
  `handoff` 3, `orchestrate` 3, `doctor` 2). **This form is strictly worse than the gated one and is
  its own security item**: it is an *unconditional* cwd-relative `python3` target with no identity
  check at all — the shape `skills/doctor/SKILL.md`'s own SECURITY header records as having shipped
  once and been arbitrary code execution. Filed as a separate roadmap item, not folded into the
  reachability one, because the fix is different (remove the default, don't widen it).

Only `audit-skips` is fixed here. The orchestrator seat confirmed that scoping (2026-11-01: ship
audit-skips only, route the siblings to a separate dispatch, per FB-0139's chunking discipline). The
four fork-skill instances, ordered by severity:

| skill | helpers | fallback |
|---|---|---|
| `audit-plan` | `extract_session.py` | **none** |
| `audit-completion` | `extract_session.py` | **none** |
| `critique-plan` | `extract_session.py`, `walk-pin-lint.py` | `plugins/flow/...` |
| `audit-coverage` | `extract-criteria.py`, `change-inventory.py`, `evidence-budget.py` | `plugins/flow/...` / guarded |

**The risk ordering of this PR is inverted, and that is worth stating plainly.** `audit-skips` failed
**closed** — it said "I cannot verify" on every run, which is loud and blocking. `audit-plan` and
`audit-completion` fail **open**: with no fallback at all, `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py`
becomes `python3 /scripts/extract_session.py`, the extractor never runs, and the reviewer audits an
**empty session context** — then reports "No issues flagged." Verified in this pass:
`plugins/flow/agents/auditor.md` contains **no** empty-context or no-transcript guard, so nothing
downstream catches it. So this PR fixed the fail-closed instance and deferred the two fail-open ones.
That was the seat's explicit call on scope, not an oversight — but the follow-up should take
`audit-plan`/`audit-completion` first, and the port must carry the **arm-3 security decision**, not
just the three-arm mechanics, or the cwd-relative arm gets copied into four more deployed prompts.

**A mechanical tripwire now guards the deferral.** `test_installed_layout()` derives every
`context: fork` skill from disk and requires each to be either ported or named in an explicit
known-broken ledger. Dropping a name without porting it goes red; so does adding a *new* fork skill
with the two-arm shape (both mutation-verified). Extending `test_contracts()`'s own `idiom_sites`
roster to the arm-2 idiom is a separate follow-up the orchestrator owns and is deliberately **not**
done here.
