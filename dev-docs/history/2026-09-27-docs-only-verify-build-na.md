# A docs-only PR is N/A, not unverified — and was unmergeable

**Date:** 2026-09-27 · **Version:** v1.52.0 · **Branch:** `conductor/docs-only-verify-build-na` · **Feedback:** FB-0122

## What

On a docs-only PR from a host without the platform's toolchain, flow produced a pull request **that could not be merged through any sanctioned path**. `verify-build` could not build, so it emitted a toolchain skip; `/flow:audit-skips` filed a `toolchain` manifest entry; `manifest-triage.CHECK_ONLY` makes that kind never waivable-to-ready and never subtracted from the residual — and the entry's own re-check could never pass, because a docs-only diff contains no behaviour for any build to exercise. The verdict stayed `BLOCKED` permanently, and the skill's own remediation text told the human to *"mark the PR ready and merge it yourself"*: **flow instructing the user to bypass flow.**

- **`verify-build` § 1.2 gains a docs-only N/A exit, positioned *before* the toolchain check.** Ordering is the fix, not an optimisation: on a toolchain-less host the toolchain check would otherwise claim the diff first.
- **`audit-skips` gains the diff condition** it previously declared it deliberately lacked, as an explicit N/A arm ahead of the toolchain arm — kept on the consumer side even though the producer now exits first, because an installed plugin lags the repo (FB-0107 measured twelve releases), so an older `verify-build` will still hand it a toolchain reason on a docs-only diff.
- **One verdict for one input shape.** A docs-only diff previously behaved two ways: with no plan it took the spike-rubric smoke path and could PASS; with a plan it took the full path into the blocker. The plan's presence does not create behaviour to verify, so the smoke path's docs-only arm is retired and § 1.2 answers both.
- **`run_docs_only_evals.py`** (new, CI-wired) + a fifth corner in `run_skip_audit_evals.py`.

## Why

**The fix belongs upstream of the entry, not in how the entry is handled.** `CHECK_ONLY` is correct and is deliberately untouched — *"no merge-ready PR on a non-PASS build"* is unqualified and should stay that way. Weakening it, or adding `toolchain` to a waivable set, would let a genuinely failed build reach READY: the opposite and worse bug. The defect was never that `CHECK_ONLY` is too strict; it was that a docs-only diff was being routed into it at all.

**"There is nothing to verify" is not "I could not verify."** That is FB-0121's distinction one layer down. Both collapsed into the second, so a change with no behaviour got a blocker describing a gap that did not exist. Implementing this as a fourth self-skip emitting the same unverified-shaped entry would have reproduced the bug with more code.

**The predicate is the union of three rulers, not `sourceFilePatterns` alone.** `/flow:audit-skips` validates a docs-only claim against source **and** visual **and** a11y patterns. A producer checking only source would call an html-only diff docs-only (html is in `uiFilePatterns`, not `sourceFilePatterns`), get refused as `SHOULD-RE-RUN`, and re-run into the same skip. The two predicates now agree by construction, and the eval pins that exact divergent case.

## Tradeoffs

- **A docs-only diff with a plan no longer gets its Spec-walk criteria judged.** Correct, and it is what flow already does on `platform: library`: the rendered Test plan takes the documented manual fallback (`⚠️ No behavioral gate ran … manual verification required`, checkbox unchecked). Honest, and consistent with the existing no-behavioural-gate shape — a criterion about doc content is verified by reading, not by driving a build.
- **The producer predicate is shell, duplicating the consumer's Python.** A shared helper would be one definition, but it would mean a new shipped lib and a wider diff across four in-flight PRs. Instead the two are pinned against each other on a matrix including the html-only case — the FB-0109 two-readers discipline.
- **Kept the consumer-side arm despite the producer fix.** Strictly redundant on a current install and deliberately so: FB-0107 means the installed producer is usually old.

## What the measurement cost, and who measured it

**Every measurement in the finding came from the health-tracker workspace (`463e6017`), on PR [#118](https://github.com/byamron/health-tracker/pull/118), which was stuck in this state.** That workspace established: § 1.2's three exits and that none was docs-only; that a docs-only no-plan diff takes the spike-rubric SMOKE path and can PASS; that `audit-skips`' *"no diff condition, deliberately"* premise was false on **both** host shapes; and the `sourceFilePatterns` check that closes the one real counter-argument (a config-driven toggle in a non-code file — impossible, because json/yaml/toml are SOURCE). The orchestrator found the `CHECK_ONLY` deadlock. I re-verified each against the engine rather than the prose before relying on it, and two things only a re-read would catch: the consumer **already had** a correct docs-only branch returning no entry (it never fired because nothing emitted a docs-only reason), and adding the diff condition naively dropped the case through to `NEEDS-JUDGMENT` — a different wrong answer.

## The review round rewrote the fix, and that is the story

The first cut hand-rolled the docs-only predicate in shell — three `jq` slot reads and three
`grep`s. `/flow:staff-review` and the cleanup lenses measured **three divergences** from the
engine that validates this very claim, each one a failure:

1. **Two-dot vs three-dot.** `git diff origin/main..HEAD` attributes commits that landed on
   `main` after the branch started to *this* diff. `main` moving is the normal case during a PR,
   so a docs-only branch was reclassified source-touching and the deadlock came straight back —
   **the fix missed most real instances of the bug it was written for.**
2. **A different UI ruler.** `file_patterns.resolve()` is `visualFilePatterns → uiFilePatterns →
   DEFAULT_UI_PATTERN`; the shell read only `uiFilePatterns` and had no default. On a project
   setting neither, a css/html/vue-only change was called docs-only and skipped the behavioural
   gate — a **failure-OPEN on a source change**, strictly worse than the deadlock being fixed.
3. **An unresolvable base read as "nothing there."** `2>/dev/null` on the committed arm made "I
   could not look" indistinguishable from "no committed changes" — the exact FB-0121 conflation
   this exit exists to end, reproduced inside it.

So the predicate stopped being shell. `lib/diff_scope.py` shares `file_patterns` with the
reviewer that audits the skip, uses `{base}...HEAD`, validates its own regex, sets
`core.quotePath=false`, and **fails closed**: anything it cannot determine is `undetermined`,
never docs-only. That also retired the hand-rolled `VB_HITS` accumulation, a second source-only
`NO_PLAN_SCOPE` classifier in Step 2 (so "docs-only" no longer named two different things in one
skill), and five places of dead prose the retirement had left behind — including
`spike-rubric.md`, which is the judge's own system prompt.

**Then I mutation-tested the harness, and it had two holes.** Disabling the shell exit entirely
left every check green, because nothing *ran* § 1.2 — only greps of its text and tests of the
predicate. And rewriting the `undetermined` arm to `exit 0` escaped too, because no fixture
produced that state — the single failure-open the whole fix exists to prevent was the one state
nothing exercised. Both are closed by a composed-layer section that extracts § 1.2 and runs it
over docs-only, source-touching **and** undetermined fixtures. All five mutations are now caught.

**And that new section immediately failed for a fixture reason worth recording:** it copied the
three helper `.py` files into the repo to make them reachable, and the predicate correctly counted
them as source. The harness's own artifacts were part of the diff it measured — the same trap as
leaving `flow.config.json` uncommitted, twice in one PR. It reaches them via `CLAUDE_PLUGIN_ROOT`
now, which also exercises the resolution branch production actually uses.

## Verification

Measured before/after on a simulated toolchain-less `platform: ios` host — the #118 shape — by extracting § 1.2 from `origin/main` and from this branch and running both:

| case | before (`origin/main`) | after |
|---|---|---|
| docs-only (md only) | `toolchain skip => BLOCKER` | **`N/A` (clean skip, no entry)** |
| docs + one `.json` | `toolchain skip => BLOCKER` | `toolchain skip => BLOCKER` |
| one `.html` only | `toolchain skip => BLOCKER` | `toolchain skip => BLOCKER` |
| one `.py` only | `toolchain skip => BLOCKER` | `toolchain skip => BLOCKER` |

Both directions, and the three unchanged rows are the point — the exit must not fire on a source-touching diff. The harness makes the toolchain helper **reachable** in its fixtures so those rows assert the blocking exit is *genuinely still reached*, not merely that the N/A line is absent: without that, both exits silently ceasing to fire would pass. End to end, a docs-only run reaches `verdict: READY`, and a real toolchain gap still does not — **including after a waiver**, asserted directly so `CHECK_ONLY`'s survival is measured rather than claimed. 39/39 harnesses green.

Two of my own errors, both caught by the harness rather than by reading: the fixture left `flow.config.json` uncommitted, and `.json` is SOURCE, so every scenario was source-touching and the new exit correctly never fired — the harness was wrong, not the predicate, and the same trap catches a real repo (a PR editing `flow.config.json` is not docs-only). And my replacement comment *quoted* the retired justification verbatim, so a grep for the dead premise still hit the file; it is paraphrased now.
