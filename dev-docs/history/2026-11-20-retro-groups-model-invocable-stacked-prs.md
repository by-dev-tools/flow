# `/flow:retro` takes a group, is model-invocable; stacked-PR guidance

**Date:** 2026-11-20
**Branch:** `claude/retro-groups-auto-stacks`
**Version:** v1.69.0
**Feedback:** FB-0144
**Scope:** `plugins/flow/skills/retro/` (SKILL.md + `lib/merge-status.py`), `plugins/flow/skills/land/SKILL.md`, three eval harnesses, `docs/workflow.md`, `workflow-help`, `README.md`, one line in `ship/SKILL.md`.

## What was done

1. **`/flow:retro` accepts a group.** `/flow:retro 151 153 154`, or no argument for "every PR merged into the default branch since the last retro" with no confirmation prompt. Shared steps run once (one `/flow:land` call → one docs PR, one feedback synthesis, one verdict listing every PR); per-PR steps (three-state merge detect, branch cleanup) run per PR. Merge-detect polls the whole group against one `postMergeWaitSeconds` budget; a closed or still-queued PR is named and left out rather than aborting the group (a group of one behaves as before).
2. **`/flow:land` accepts a list** and opens one `docs: land #A #B #C` PR. §1a refuses the whole call if any number is unmerged. The title names every number because retro's already-landed search keys on it.
3. **Helper subcommands** in `merge-status.py`: `parse-prs`, `select` (default group from a per-repo watermark), `advance` (monotonic watermark write), `branch-plan` (per-PR cleanup decision against real git state). All decide-only; the SKILL executes.
4. **Branch cleanup rewritten** from the field: remote head deleted only if its tip equals `headRefOid`; fork PRs never; branches checked out in other worktrees skipped and named; a merged branch that is the base of an open PR left alone; squash-merged locals that `-d` refuses reported as left behind (never `-D`).
5. **`/flow:retro` is model-invocable**, with an AUTO-INVOCATION clause. `disable-model-invocation: false`, declared. Updated every site that asserted the old flag: `run_merge_status_evals.py`, `run_skill_composition_evals.py` (the "retro stays human-gated" assertion is inverted and now pins the flag, the clause, the §2 gate, and that no flow skill is model-disabled), `workflow.md` (the "human-only skills" section and four other sites), `workflow-help`, the retro SKILL's own FB-0074/FB-0077 history paragraph and Gotchas. `doctor/lib/skill-composition-lint.py` needed no change: it is generic over the flag, and its live scan stays green.
6. **Stacked PRs** documented once, in `docs/workflow.md` § "Stacked PRs"; `/flow:ship` carries a one-line pointer at PR creation. This also implements the plan-noting convention that `dev-docs/plan.md` has carried as a follow-up since PR C ("layer K of N, based on X", Files-touched = the layer's own diff).

7. **One small item folded in from a transcript review of five delegated `flow:ship` runs** (the same designer session): a two-line `gh` projectCards pitfall pointer at the top of `/flow:ship`, since every one of the five agents hit that error and rediscovered the Step 7 fallback they never reached. The review's larger asks (review-only mode, shrinking the ~210 KB skill, a `skipped:` one-liner) are recorded on the roadmap item with the review-skill targets, not built.

## Why

Ben ran `/flow:retro` after nine PRs merged in one batch and hit three gaps (FB-0144): one run per PR, the agent refused `Skill("flow:retro")` even when told to run it, and no guidance on stacked PRs. Each is a place where a guard was in the wrong layer or the wrong grain.

## Design decisions and tradeoffs

- **Watermark in a sibling file, not the harvest marker.** The task named `last_harvested.json` as a candidate. It maps *session id → transcript record count*; a PR watermark is a different quantity with a different key space, and sharing the file would give two writers one schema. `last_retro.json` sits beside it, in the same directory the same config slots already resolve, so no new slot (and no slot-count fan-out). Keyed by repo because the directory is user-scope and cross-project.
- **Only a default-group run moves the watermark, and only when everything reconciled.** A single timestamp cannot say "PR A failed, PR B succeeded"; advancing to B would drop A from the next default group. Not advancing costs a harmless idempotent re-pick. An explicit list never moves it: a hand-picked subset says nothing about the PRs it skipped. Cost: after an explicit run, a later bare run re-picks those PRs (and finds them already landed).
- **No watermark ⇒ 7 days, capped at 20, and the truncation is announced.** "Everything ever merged" would turn a first bare `/flow:retro` into a sweep of the repo's history; no prompt was a stated requirement, so the bound is the safety.
- **`docs: land` PRs excluded from the default group.** Without it, merging a retro's own docs PR makes it the next retro's input, forever.
- **`land` takes the list rather than retro opening its own PR.** Duplicating reconciliation in retro is exactly what FB-0077 spent a release undoing. Cost: `land`'s shell blocks gained a loop, and its branch is `land-<lowest>-<highest>` for a group (a label, stable across a re-run of the same group).
- **`while read`, never `for x in $LIST`.** zsh does not word-split an unquoted variable and flow's users run zsh; the repo already burned on this in `doctor` and `audit-coverage`. Pinned by an eval over the fenced blocks only (the prose names the forbidden form).
- **`branch-plan` decides, the SKILL executes.** The decision (remote tip == `headRefOid`, fork, other-worktree, unsafe ref name) is deterministic and was testable against a real temp repo + bare origin + linked worktree; the `-d` attempt and the pushes stay in the SKILL.
- **Open-PR-base check lives in shell, not the helper.** It needs a `gh` call; the helper stays `gh`-free so its evals need no network.
- **Stacked PRs: let `/flow:ship` open each layer, use `gh stack link` to join them.** `gh stack submit` creates PRs itself — the `gh pr create` bypass `workflow.md` forbids. This is a design call from the README, not a measured run: `gh stack` is not installed here, so the commands were verified against the README, not executed.
- **Review skills accepting a target: not done.** Measured: every one hard-codes `origin/$BASE..HEAD` at many sites (security-review, accessibility-review, staff-review, ship, plus verify-build/audit-coverage downstream), and an argument must go through the Write-then-path channel (`workflow.md` § "Skill arguments"). That is not small; filed in the roadmap.

## Review findings acted on (staff-review, security-review, simplify)

- **Staff engineer BLOCKER**: `git ls-remote --heads origin <name>` matches by ref *suffix*, so a nested sibling `a/x` at the merged tip was approved for deletion in place of `x`. Fixed by querying the full ref and keeping only the exact line; the fixture the first 92 evals used (flat names) could not have caught it, so a nested-sibling case was added and mutation-checked.
- **Security BLOCKERs**: (1) "already landed" matched on a title alone, so anyone who could open a PR titled `docs: land #151` could make #151 look reconciled, skip the real land, and advance the watermark past it — now one shared predicate (`is_landing_pr`, exposed as `landing-prs`) requires same-repo, default base, a `land-<N>` head, a `docs: land #…` title, not closed, and titles are projected to numbers, never printed; (2) a same-repo `develop`/`release/*` head merged into the default branch would get a `delete` verdict — long-lived names are refused, GitHub's `protected` answer must be `false` (fail closed), and the delete is fully qualified with `--force-with-lease` on the merged tip. Nits taken: fail-closed dependent-PR check, PR URLs refused (they name a repo), fork/base head refs never used as a grep pattern, origin must match the repo `gh` resolved.
- **Simplify (altitude)**: the landing-PR predicate had been hand-copied into three places with different strictness — consolidated into the helper (net fewer lines in the SKILL, one parity eval).
- **Deferred to the roadmap, not hidden**: verdict tiering for squash-merge repos (push-further), `closeout-verdict`/protected-fold helpers, `default-branch` helper, ~2N avoidable `gh` calls, cosmetic eval tidying.
- **audit-coverage** first read the wrong Spec-walk (plan.md's first block belonged to an older PR): this PR's criteria are now declared first; a re-audit then found four more undeclared behaviours, which were smoke-tested (bash and zsh) or pinned. The re-audit's evidence was truncated for retro/SKILL.md (19 of 56 KB mechanically read) — stated, not papered over.

## Verification

See the PR body. New helper evals (`run_merge_status_evals.py`: 92 checks) run against real temp git repos; the SKILL's shell blocks were smoke-tested under both bash and zsh against a stub `gh` (group poll, already-landed scan including `#15` vs `#151` prefix collisions, and the full cleanup matrix). Mutation-tested: reverting the tip-equality check, the fork guard, the `docs: land` exclusion, the monotonic watermark, and the other-worktree detection each turns a named eval red.
