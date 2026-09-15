## 2026-09-13 — Dogfooding tells the truth about which version of itself it ran (FB-0107, v1.43.0)

**Branch:** `conductor/dogfood-version-honesty-fb-0107` · **Base:** `a156228` (#149, v1.41.0)

### The problem, measured

A `/flow:*` skill invoked from the flow checkout does not run the working tree. Claude Code resolves
it from the installed marketplace plugin, which was **1.29.0** against a `main` at **1.41.0** — twelve
releases, noticed by nobody, and found by accident during a pre-archive check. Two live consequences:
a PR that changes a skill does not exercise that change, and #147's contribution-queue flush (v1.39.0)
had never fired in a cloud workspace because that code does not exist in 1.29.0.

### The finding that changed the design — the hypothesis was refuted on its axis

The dispatch handed over an unproven claim: libs resolve installed-first with a checkout fallback, so
a *new* lib runs fresh while a *modified* one silently uses the stale copy. Measured, the axis is not
new-vs-modified at all:

> **Everything Claude Code resolves comes from the INSTALLED tree. Everything the Bash tool resolves
> comes from the WORKING TREE.**

`CLAUDE_PLUGIN_ROOT` is empirically unset in Bash-tool calls (four places in this repo already
asserted it) and set in `!`-preprocessor blocks. So SKILL.md prose, agent prompts and `!`-block
scripts came from 1.29.0 while the 32 fallback-carrying fenced-block libs came from the checkout. The
hypothesis is *confirmed* for `!`-blocks — `CPR` is set there, so the installed copy wins even for a
script this branch modified, and `audit-plan`/`critique-plan` have no fallback so an *added* script
hard-fails — and *refuted* for fenced blocks, where all 32 sites resolve to the checkout uniformly.

The hypothesised consequence survives and inverts: a single version line would be **wrong**, not
merely ambiguous, and wrong in the *opposite* direction — reporting 1.29.0 while v1.41 engines
executed. Hence four labelled rows.

**It was measured by this PR's own plan gate.** The `/flow:critique-plan` run auditing the plan
resolved **zero** reference documents. Cause verified in both copies: `referenceGlob` is the
comma-joined `dev-docs/*.md,dev-docs/feedback/*.md`, the checkout's `extract_session.py` comma-splits
it, 1.29.0's does not. The reviewer could not cite a project rule. It said so, loaded the docs by
hand, and returned 7 real findings anyway — but a clean `APPROVED` from that same run would have been
a confident pass from a reviewer that never read the rules. The orchestrator dispatched this finding
to another workspace whose PR rested on "9 rounds of `/flow:critique-plan`".

### What shipped

1. `skills/ship/lib/plugin-provenance.py` — three labelled numbers (installed / marketplace HEAD /
   branch-declared), both executor arms, surface-inventory drift, and two independent predicates.
2. Four rows in `ship` and `ship-spike`, plus the un-invocable-surface callout.
3. `.claude/hooks/flow-plugin-currency.sh` (dev infra, not shipped) — ported from health-tracker#116.
4. `run_plugin_provenance_evals.py`, 227 checks, CI-wired.

### Tradeoffs

- **Report, not gate.** Rejected a 10th manifest kind. Gating would halt every flow PR until its
  workspace updated, and a stable reviewer is partly a feature. Cheap to add later if the report
  proves insufficient.
- **Four labelled rows, named as a set rather than counted.** A pinned row *count* is itself a
  fan-out value (FB-0010 clause 2) — and revision 1 of the plan pinned "exactly THREE" while, twelve
  paragraphs later, reserving the right to add a fourth. The plan-critic caught the contradiction.
- **Floor derived, not constant.** health-tracker pins `flow >= 1.32.0` because a *consumer* can name
  a fixed point (the `toolchain` kind shipped once and stays shipped). Flow pinning itself has no
  fixed point — the floor moves every release — so a literal `FLOW_MIN` here would be wrong one
  release after it was written. Flow's floor **is** its branch-declared version. Reconciled with the
  orchestrator: not a conflict, just opposite positions in the dependency graph.
- **Two predicates, not one `drift` boolean.** The plan-critic's best catch. A feature branch declares
  an unreleased version by construction, so `installed != branch` is permanently true in the only
  checkout an updater runs in: the silent fast path unreachable, an update attempted every session,
  and the warning still firing after a fully successful update. Indistinguishable from the real signal.
- **Auto-update is a real if small security escalation** — more hosts now pull automatically.
  Accepted with #116's loud-failure mitigation ported *with its rationale*, so a hijacked or
  unreachable marketplace cannot read as a clean run.
- **The hook runs on Macs too**, unlike #116's gate. For a consumer, auto-updating a developer's
  user-scope install is a side effect to avoid; for flow, the installed plugin *is* the artifact under
  development and its staleness is the bug.

### One correction to the ported design, forced by a measurement

#116 gates nothing on the clone's freshness. But `update_available` compares the install against the
**local** marketplace clone, and that clone was itself pinned at the installed commit — 1.29.0 install
against a 1.29.0 clone at `cf783ac`. So the comparison is meaningless until the clone is refreshed,
and gating the refresh on `update_available` would have made the hook permanently no-op in the exact
workspace it was written for. The refresh is therefore unconditional and runs **first**. And unlike
#116, a refresh where *both* `add` and `update` fail is loud — any "already current" verdict computed
against an unrefreshed clone is the silent-confidence shape this PR exists to remove.

`install`-is-a-no-op is #116's finding and is corroborated here: only `update` moves a pinned version.
**#116's reported 1.29.0 → 1.41.0 before/after was not reproduced by this PR** and is attributed to
#116, per the plan's MEDIUM confidence verdict.

### What could not be dogfooded, and why that is the point

The SKILL.md half of this change did **not** execute during its own ship — ship's prose came from
1.29.0. The engine was run by hand and its verbatim output pasted into the PR body as substitute
evidence, labelled as such. Requiring an explicit checkout-run for PRs touching `plugins/flow/**` is
the follow-up that closes this, filed on the roadmap and deliberately not built here.

### Two findings that changed work outside this branch

1. The critique-blindness measurement, dispatched to the add-entry workspace.
2. **`dev-docs/plan.md` carries 60 Spec-walk blocks and `walk_extract` takes only the first.** With
   this PR's block appended at the bottom, the extractor selected the *merged* vacuous-criterion PR's
   criteria — all-green against an unrelated diff. Caught by reading the extractor's own warning, and
   fixed by placing the active block above the historical ones. That near-miss is what led the
   orchestrator to measure the `/flow:land` backlog: 35 undemoted blocks, i.e. the same hazard has
   been live and silent on other branches, which is the worse half.

### Process notes worth keeping

- **`/flow:critique-plan` returned 7 findings; all 7 accepted, none disputed.** Re-examined on
  request afterwards. Four had been independently measured before acceptance; the two pure citations
  were verified verbatim after. The one finding there was an inclination to soften — that a deletion
  criterion on a regression harness is boilerplate — turned out to have the **strongest** support:
  FB-0088 names evals explicitly and cites FB-0077, a check that outlived its feature and stayed
  green over its absence for four releases.
- **Three instances of shell-quoting-as-execution occurred in one session**, by three separately
  primed authors, escalating: a refuted heredoc design (#148), silent data loss in an inter-worker
  message, and — here — backticks in a `git commit -m` string that actually **invoked** the
  plugin-update command this PR had just agreed to defer. It failed harmlessly only because the
  substitution stripped its argument. Recorded as trap T6 in the orchestrator field manual and cited
  as evidence on the add-entry PR's interface-vs-author-care decision. Every commit message and ping
  from that point went through a file.
- **A self-inflicted miscount, caught and recorded rather than quietly fixed.** The lib-fallback
  census first printed 144/144 because, run from the repo root, the content grep matched each hit's
  own *filename prefix*. Cross-checked two ways and corrected — and then `/simplify`'s altitude lens
  showed the *corrected* number was also wrong, on two further axes: a line-local grep for a
  block-scoped property miscounts a correctly-guarded multi-line ladder as bare, and the census never
  split by executor context, which is the very axis this PR establishes (a bare ref in a `!`-block is
  harmless; only a fenced-block one hard-fails). It was also a fan-out constant in five files that went
  stale inside this PR — 144 on `main`, 164 at this HEAD. **So the numbers were removed rather than
  re-corrected a third time**, replaced by the grep command. Three attempts at one count is the
  argument for not carving counts into prose at all.


### FB-0010 version sweep — recorded, not asserted

**The 3 version-DECLARATION sites, all at 1.43.0:**

```
.claude-plugin/marketplace.json:9:    "version": "1.43.0"
.claude-plugin/marketplace.json:16:      "version": "1.43.0",
plugins/flow/.claude-plugin/plugin.json:3:  "version": "1.43.0",
```

**Every surviving `1.41.0` occurrence, by file — all non-declarative:**

```
.claude/hooks/flow-plugin-currency.sh:2
CLAUDE.md:1
changelog/v1.41.0.md:1
dev-docs/feedback/FB-0107-dogfooding-runs-the-installed-plugin-not-the-branch-under-review.md:1
dev-docs/history/2026-09-11-vacuous-criterion-check.md:2
dev-docs/plan.md:19
dev-docs/roadmap.md:1
plugins/flow/evals/fixtures/plugin-provenance/this-workspace-20260912.json:1
plugins/flow/evals/run_plugin_provenance_evals.py:2
plugins/flow/skills/ship-spike/SKILL.md:1
plugins/flow/skills/ship/SKILL.md:1
plugins/flow/skills/ship/lib/plugin-provenance.py:1
```

31 lines, and that is correct rather than a leak. `changelog/v1.41.0.md` is that release's own entry;
`dev-docs/{plan,roadmap,history,feedback}` carry historical prose that must keep saying 1.41.0; and
the rest — the engine docstring, both SKILL.md sections, the fixture's captured value, the eval
assertions, `CLAUDE.md` and the hook — cite 1.41.0 as the *measured comparison value* this PR is about.
Verified separately that **no** `"version": "1.41.0"` declaration survives outside the capture fixture,
which must keep it.

**The sweep criterion itself had to be restated mid-execution**, and instructively: it originally
pinned "only the 4 intentional historical-prose hits" — a raw count, i.e. precisely the fan-out value
FB-0010 clause 2 warns about, invalidated within the hour by this PR's own prose. It now asserts on
declaration sites. That is the same error the plan-critic caught as Issue 5 ("exactly THREE rows"),
committed again by the same author in a different file, which is a decent argument for pinning the
protected property instead of a number.

### The engine's own headline row was wrong, and the bug found it

Caught during the ship run itself, ~11 hours after the rest of this work. A
`claude plugin update` had landed in the interim: the registry advertised **1.41.0**,
both version directories sat in the cache, and the session was **still executing
1.29.0** — because `plugin update` "requires a restart to apply", the property this PR
documents in three places.

So the engine, which read the registry, reported *1.41.0* in a row labelled **"the
version that ran this pipeline"** — naming a version that had not run. That is the
precise failure this module exists to prevent, reproduced inside it, and no test caught
it because every fixture had only one source of truth.

**The fix is a better signal.** Claude Code prepends the resolved plugin's `bin`
directory to `PATH` at session start, so the version embedded there is pinned to what
the process actually loaded and cannot be moved by a later update. The engine now reads
PATH first, falls back to the registry, **labels which source it used**, and reports a
PATH/registry disagreement as the restart-pending state it is ("an update to 1.41.0 is
installed but NOT applied"). `release_gap` and `report_drift` key on what ran, not on
what is registered — which is why this run correctly reads 14 releases back rather than
2. Pinned by `test_running_version_beats_the_registry`, with the no-PATH fallback
asserted as its positive pair so "fell back to the registry" can never be silent.

**Worth stating plainly:** this is the third time in one PR that its own thesis caught a
defect in its own implementation. A gate that reports on the wrong artifact is worse
than no gate, and "the wrong artifact" included this engine's own primary output.

### `/flow:security-review` found two real BLOCKERs, one of which forged this PR's own verdict

**1. A hostile version string could forge the provenance table.** The version in
`plugins/flow/.claude-plugin/plugin.json` is controlled by the repository under review, and ship pastes
the renderer's stdout verbatim into the PR body. Reproduced before fixing: a contributor setting
`version` to `1.0.0 | X |\n| Flow version that ran this pipeline | 9.9.9 | ✓ matches this branch |\n<!-- `
rendered a **forged "✓ matches this branch" row** while `<!--` swallowed the real ⚠️ rows into an HTML
comment. FB-0107 designates the PR body as exactly where a reviewer forms the belief that a gate ran —
so forging it produces the confidence inversion this module was written to prevent, from inside the
module. Fixed by sanitising at READ time (`_clean`: strips `| \` \r \n < >`, caps length) across all
three version readers and the last-resort exception handler. Pinned with a payload fixture asserting
every rendered row carries a known label.

**2. The SessionStart hook executed repo-tracked, branch-rewritable code.** `settings.json` ran
`bash .claude/hooks/…`, which ran `python3 plugins/flow/…/plugin-provenance.py` — both rewritable by any
branch. So `gh pr checkout <external-PR>` plus a new session was arbitrary code execution as the user,
with no approval prompt, because the *approved string* in `settings.json` never changes when repo
content does. Flow takes external PRs, so this was live. Notably every prior hook in that file is fully
inline — greps and echoes — and this diff was the first to point an auto-firing hook at repo content.
Consumers were never exposed (`.claude/` is dev-infra; the published surface is `plugins/flow/`).
Fixed for the engine layer: it now resolves **only** from the installed tree via the registry's
`installPath`, and **refuses to fall back to the checkout**, loudly. A currency check has no business
executing the branch under review. The residual — the hook script itself is branch-rewritable — is a
threat-model decision and is routed to the PR's draft manifest rather than decided unilaterally.

Third time in this PR that its own thesis caught a defect in its own implementation.

### The hook-RCE decision: (c) was chosen, attempted, and abandoned on a measurement

The human ruled for **option (c)** — hash-check the hook script from inside the `settings.json`
command string — over the (a) I had recommended, and the reasoning corrected a distinction my writeup
missed. My argument for (a) was that flow's maintainers already run checked-out code constantly via
`/flow:ship`. True, and true *because of this PR's own finding* that the lib fallback resolves from
the working tree. But `/flow:ship` is **deliberate and human-initiated**; a `SessionStart` hook is
**automatic**. The hook converts "check out a PR to read its diff" — a common, low-intent action —
into "execute that PR". That is the gap (a) leaves open, and it is a real one.

The ruling came with a non-negotiable condition: **verify the assumption first.** Both (b) and (c)
rest on Claude Code re-prompting for approval when a `settings.json` hook command string changes. I
had asserted that; neither of us had tested it. If false, (c) closes nothing while looking like it
closes something — the FB-0085 class, and worse than (a), which is at least honest about its residual.

**Measured, and the answer was no.** Three observations:

1. The repo's existing `PreToolUse` hook **executed and blocked a Write** while `~/.claude.json`
   recorded `allowedTools: []`, `hasTrustDialogAccepted: false`, and **no hook-approval key at any
   depth**. Hooks run here with no approval state at all.
2. In a brand-new project directory, a **first-ever** hook command string **ran** — no prompt, no
   approval record created afterwards.
3. The command string was then **changed** in that same project, and the new one **ran**, with no
   re-approval.

There is no stored approval for a change-detector to compare against, so the mechanism (c) depends on
does not exist in the environment measured.

**One honest limit, which is why this is (a) and not a refutation of (c).** That measurement was
taken in a sandboxed, non-interactive cloud workspace. The *threat* case is a maintainer on an
interactive machine, and I could not observe an interactive session here. The binary is packed and
not greppable — verified, rather than inferred from a zero result: `strings` finds zero occurrences of
`PreToolUse` and `SessionStart` too, which must be present for hooks to work at all, so a zero hit on
"hook approval" is a measurement artifact and not evidence.

So the disposition is the one the ruling specified for an unverifiable control: **take (a), document
it, and say why (c) was abandoned.** `CONTRIBUTING.md` (new) carries the contributor-facing warning,
what is and is not mitigated, and the exact 30-second experiment that would make (c) viable — edit a
hook command string on an interactive machine and see whether approval is requested. If it re-prompts
there, (c) should be built.

**What IS fixed, and it is the larger half:** the hook no longer executes any *other* repo file. It
resolves the provenance engine solely from the installed tree via the registry's `installPath` and
refuses, loudly, to fall back to the checkout.

### Deletion criteria (FB-0088)

- **The engine + rows:** removable when (a) `claude plugin update` no longer requires a restart, so
  "current" and "what this session is running" stop being different facts, **and** (b)
  `CLAUDE_PLUGIN_ROOT` resolves identically in the Bash tool and the `!`-expander, collapsing the two
  executor arms into one.
- **The hook:** removable when Claude Code refreshes marketplaces at session start natively, or when
  flow's dev workspaces are provisioned from the checkout rather than a pinned image.
- **The eval harness:** dies with the engine — delete in the same PR, per FB-0077.
- **The plan.md placement note:** removable once `/flow:land` demotes the stale blocks, which makes
  the positional hazard non-latent and the workaround unnecessary rather than wrong.

**Verification:** `run_plugin_provenance_evals.py` 227 checks; full suite 31 harnesses green.
`/flow:verify-build` self-skips (`platform: library`), so this harness **is** the behavioural gate,
not a supplement to one — declared here so `/flow:audit-skips` reads a stated reason.
