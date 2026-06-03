# Fixture: resolution-confidence-routing

**Purpose:** Pin the PR U contract — every ship-time reviewer BLOCKER carries a
resolution-confidence tag (`[auto-fixable]` | `[decision-required]`), and that tag
deterministically decides `/flow:ship`'s handling: auto-fixable → fix in-tree;
decision-required → draft PR + `🚫 NOT READY TO MERGE` manifest (never a silent
proceed, never a hard mid-loop halt). Demonstrates FB-0011 (ESCALATE-by-default →
default-to-`decision-required` when unsure) applied to the reviewer output contract.

**Phase:** PR U Phase 1/2 deliverable. Harness wiring deferred — like the `verify-*`
fixtures, the security/a11y reviewers are prompt-driven `Agent` calls, not wired into
the auditor-specific `run_evals.py`. This fixture documents the contract a future
reviewer-output harness must enforce.

## What this fixture contains

- `input/diff.patch` — a small synthetic diff with two BLOCKER-class findings of
  *different resolution-confidence*:
  1. a hardcoded API key committed to source → **decision-required** (the in-tree
     removal is easy, but the live key must be **rotated** — a human/out-of-repo action);
  2. an `<a href={userUrl}>` with no `javascript:`-scheme guard → **auto-fixable**
     (one clear, mechanically-verifiable fix: add the protocol allowlist).
- `expected/security-review-output.md` — the expected `/flow:security-review` output,
  showing each BLOCKER tagged with its resolution-confidence.
- `expected/ship-routing.md` — the expected `/flow:ship` Step 2/7 behavior given those
  tags.

## Expected behavior (the contract this fixture pins)

1. The reviewer tags finding (1) `[decision-required]` (out-of-repo rotation needed) and
   finding (2) `[auto-fixable]` (single clear, verifiable fix).
2. At `/flow:ship` Step 2: finding (2) is fixed in-tree (add the scheme allowlist),
   typecheck re-run; finding (1) is **added to the draft manifest** — NOT best-effort-fixed
   (removing the key from source does not un-leak it; rotation is the human action).
3. At Step 7: because the draft manifest is non-empty, the PR opens as a **draft**
   (`gh pr create --draft`) with a `🚫 NOT READY TO MERGE` block pinned at the top naming
   finding (1), what it needs (rotate + invalidate the leaked key), and the candidate
   resolution.
4. The auto-fixable fix never appears in the manifest (it was resolved in-tree).
5. **Invariant:** no merge-ready PR is produced while any decision-required finding is
   unresolved — draft status is the mechanical NOT-READY signal the merge gate trusts.

## The verify-build regression case (same contract, different source)

The same routing applies when ship's verify-build *confirmation* re-run returns a
non-converging FAIL/Unknown (a regression since the Step 8/9 readiness PASS): after the
FB-0012 bounded mechanical fix fails to converge, the regression is added to the draft
manifest exactly like a decision-required reviewer BLOCKER. (No separate fixture dir — the
routing is identical; `verify-unknown-blocks` already pins verify-build's verdict shape.)

## Why this fixture exists now (not deferred)

The resolution-confidence classification is a new heuristic, and the project quality bar
requires a fixture demonstrating any new heuristic before it ships. Pinning the
input→tag→routing contract now keeps a future reviewer-output harness honest: it must
implement what this fixture documents.
