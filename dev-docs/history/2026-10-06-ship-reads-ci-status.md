# 2026-10-06 — `/flow:ship` never calls a PR "ready" that GitHub would block (v1.64.0)

**Branch:** `conductor/ready-check-ship-reads-ci-step-8-predicate` · **Version:** v1.64.0 ·
**Feedback:** FB-0137 · **Spec:** `dev-docs/research/2026-10-agentic-graphs.md` R1 + FB-0131 corollary 3

## What

The Step 8 ship-readiness verdict is now **computed, not remembered**.
`skills/ship/lib/ship-readiness.py` evaluates all five existing conditions from committed artifacts
plus **CI status as a live sixth**, and names which condition did not pass. A non-green CI verdict
routes to a draft PR through three new `CHECK_ONLY` manifest kinds.

- **`ship-readiness.py`** — `ci` (pure, stdin-fed), `check` (the six-condition predicate), `render`.
- **Three manifest kinds** — `ci-failing` / `ci-pending` / `ci-unknown`, all `CHECK_ONLY`.
- **`/flow:ship` §7a.7** — the CI gate, after PR create (see *Tradeoffs*).
- **`/flow:ship-spike`** — reports all three states; drafts only on `ci-failing`.
- **`ciWaitSeconds` slot** (38 → 39), swept across every surface that states a total.
- **`run_ship_readiness_evals.py`** — 69 checks, wired into CI.

## Why

#176 shipped with the pipeline calling it ready while GitHub reported `BLOCKED`. Measured here from
the run history: **six** consecutive red CI runs on that branch (2026-10-03 14:43→15:18 UTC), each
with exactly one failing job (`evals`) and five green. Every flow gate was green, the manifest said
`READY`, the body said "ready". Nothing in the pipeline looked at CI, so nothing contradicted it.
(FB-0131 records "four pushes"; runs are not pushes — `cancel-in-progress` collapses some.)

## Tradeoffs

**1. The instrument is the structured output, not the exit code — a measured exception to our own
rule.** `.claude/rules/general.md` item 4 prefers a tool's exit code over a grep of its output. It
does not apply here: measured on gh 2.100.0, `gh pr checks` returns **exit 1** for a failing check
(#176), for "no checks reported" (#183, which emits no JSON at all even with `--json`), *and* for a
nonexistent PR (#99999). Collapsing three unlike worlds into one value is precisely how "pending"
becomes "passing". So the engine reads the structured rollup and uses process failure only to
separate "I read it" from "I could not look". Recorded as an exception rather than a silent
departure, because the rule is right in general.

**2. One `gh pr view` call, not `gh pr checks`.** `gh pr checks --json` *fails* when a PR has no
checks, so that case would arrive as a parse error indistinguishable from a network failure.
`gh pr view --json statusCheckRollup,mergeStateStatus,isDraft` always yields valid JSON for an
existing PR — an empty rollup is `[]`, a readable fact — and carries `mergeStateStatus` in the same
call, which is GitHub's own answer to "would this be blocked".

**3. "No checks reported" is disambiguated by asking GitHub, not by parsing workflow YAML.** Empty
rollup + `CLEAN` → nothing is configured or required, condition satisfied *with its reason stated*.
Empty rollup + anything else → `ci-unknown`. Measured: #183 was an open PR with an empty rollup and
`DIRTY`, where `pull_request` checks can never arrive. Scanning `.github/workflows/` was rejected for
three independent reasons — it needs a YAML parser we do not have (stdlib-only), it is blind to
non-Actions CI (which arrives as `StatusContext` commit statuses, mapped here), and it cannot see
branch protection, which is what actually decides blocking.

**4. `mergeStateStatus` is a cross-check and can never be the sole source.** A **draft** PR reports
`DRAFT` for that field, and flow drafts PRs — so it says nothing about checks for exactly the PRs
this engine is asked about. A merged PR reports `UNKNOWN` (measured on #176). Checks come from the
rollup; the merge state only ever *adds* a reason not to be ready.

**5. The gate runs AFTER `gh pr create`, and the window is named rather than argued away.** flow's CI
— and most projects' — triggers on `pull_request`, so before the PR exists there are **zero** checks.
There is no earlier point where the condition is answerable. The alternative, always creating a draft
and promoting it, was rejected: it would route the green majority of ships through a draft, and
FB-0075 is explicit that a draft PR is a last resort rather than a deliverable. The residual: the PR
exists as ready until §7a.7 converts it. Bounded inside one step, closed before the Step 8 hand-off,
so no human is handed a ready-looking PR — but a watcher polling GitHub inside the window would see
one. Disclosed in §7a.7, in the PR body, and in the roadmap entry.

**6. Three kinds, not one `ci`.** `KIND_COPY`'s own design is one record per kind; a single kind would
need generic `means` copy, and "a check is failing: `evals`" / "checks have not finished" / "I could
not see CI at all" are three different things to tell a human — a bug to fix, a wait, and a blind
spot. All three are `CHECK_ONLY`, so no "waive and ship as-is" is offered: that is the brief's
requirement stated mechanically. The dead-end this could create for a slow-CI consumer is handled as
`toolchain` already handles it — the copy says plainly that the human may mark the PR ready
themselves, because they can and flow cannot. **Notably this was prescribed, not invented:**
`CHECK_ONLY`'s comment already predicted "a `CI red` kind … identical semantics", so the integration
cost one edit instead of the four scattered string compares it warned about. That comment has been
updated to record that the prediction landed.

**7. Two decisions, one engine — and conflating them would have broken the pipeline.** `check`'s
`UNDECLARED` blocks Step 8 **auto-advance** (cost: an explicit "ship it"). `ci` gates the **ready/draft**
decision. If `UNDECLARED` artifact conditions also drafted PRs, *every* ship would draft, because two
of the six conditions have no artifact to read. Keeping the two gates distinct is what makes an honest
`UNDECLARED` usable instead of fatal.

**8. `ciWaitSeconds` as a slot rather than a constant.** Approved at the gate on the reason that CI
duration is genuinely project-shaped (flow's own suite settles in ~75s; a large consumer suite can
take 20 minutes), and it follows `postMergeWaitSeconds`' precedent rather than inventing a pattern.
The cost is real and was paid in this PR, not deferred: the sweep caught two stale counts nobody had
noticed — `skills/doctor/SKILL.md` ("38 schema slots") and `README.md` ("38-slot"). Left **unset** in
flow's own config, matching `postMergeWaitSeconds`: unlike `previewBackend`, an integer with a
documented default is not "off" when unset, so FB-0085's argument does not apply.

**9. Blocking wait, never a polling loop.** `timeout <N> gh pr checks --watch` yields the same verdict
for zero model turns; measured, it returns in 1s on a settled PR. This is FB-0137: under *tokens
matter, lost time doesn't*, the polling loop is strictly dominated. On timeout the verdict is
`ci-pending` — a separate entry point, so the timeout path cannot fall through to the all-passing
branch.

## Two bugs this change caught in itself

Worth recording, because both are the classes `general.md` tracks and both were caught by the
discipline rather than by luck.

1. **`|| true` before `$?`.** The first draft of §7a.7 read `timeout … || true` then `RC_WATCH=$?`,
   which captures `true` — so a timeout would have read as success. Now `|| RC_WATCH=$?`, and
   `test_rc_capture_is_not_clobbered` pins it in both skills.
2. **CLI key names read off a library return value.** `spec_walk_condition` asked for
   `source_heading_line`/`criteria`, which are `extract-criteria.py`'s *CLI* names;
   `walk_extract.extract_block` returns `first_heading_line`/`items`. The result was a silent `None`
   reported as "the plan declares no Spec-walk block" — a plausible-looking `UNDECLARED` over a fully
   declared plan. Caught by `test_unchecked_criterion_fails_not_undeclared`, which is why that test
   asserts FAIL-vs-UNDECLARED rather than merely "not ready".

## Verification

- `run_ship_readiness_evals.py` — 69 checks. **Every CI state is pinned as a pair**, because a
  one-armed pending assertion cannot distinguish a working checker from the bug (both predict "not
  FAIL"). `ci-passing` and `ci-pending` differ in exactly one field, and that one-field-apart property
  is itself asserted so a later edit cannot quietly weaken the pair.
- **The known-positive** (`general.md` item 4): `test_pr176_regression` replays the measured shipped
  state — six checks, five green, `evals` red, `BLOCKED`, every artifact condition green — and must
  return NOT-READY naming `evals`. Paired with `test_pr176_pair_green_ci_is_ready` on the same
  artifacts with a green blob, so a checker hardwired to NOT-READY fails.
- Validated live against #179 (6 passing, `CLEAN` → PASS) and #183 (empty rollup, `DIRTY` → `ci-unknown`).
  **#183 was rebased mid-session** and now reports 6 passing checks; the earlier measurement was
  accurate for head `81a2a4c` and is preserved as `ci-no-checks-dirty.json`. The surprise was resolved
  by doubting the instrument first (FB-0131's general shape) and confirming against the live API.
- `tools/eval-sweep.sh`: 46/46 green by exit code. CI's harness↔runner join replayed locally.

## Honest limitation

`StatusContext` field names are transcribed from GitHub's documented GraphQL schema and are **not
measured** — this repo has no non-Actions CI to produce one. The fixtures exercise the mapper's
handling of that shape; they do not prove GitHub emits it. Flagged in the code at the mapping site.
