### FB-0008: Stale-base preflight is the cheapest gate for the most expensive class of dogfood waste
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager PR 4 (PR #23) forked at `b8b0e0b` while `origin/main` had advanced to `eb8e7b9` by the time Phase 4.3 ran `/flow:staff-review`. Three of four lenses converged on "stale-base producing phantom-deletion diff" as the headline BLOCKER. Fix was a single rebase; **discovery cost was 4 lens spawns + minutes of triage**. md-manager's retro `/critique-plan` post-merge also flagged "base is current with main" as the missing load-bearing assumption from the per-PR plan — captured as md-manager's FB-0033.

**Synthesized rule:** Every flow skill that consumes a diff vs the default branch must include a stale-base check at the workflow entrypoint, before any expensive operation (especially lens-agent spawn). Pattern for `/flow:ship` Step 1, `/flow:staff-review` Step 1, `/flow:ship-spike` Step 1:

```sh
# Resolve default branch via PR-1's 3-tier fallback chain
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' \
  || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' \
  || echo "main")

git fetch origin --quiet
if ! git merge-base --is-ancestor "origin/${DEFAULT_BRANCH}" HEAD; then
  echo "⚠️ BLOCKER: branch is stale vs origin/${DEFAULT_BRANCH}. Rebase or merge before /flow:<skill>." >&2
  echo "       (current HEAD: $(git rev-parse --short HEAD); base needs $(git rev-list --count HEAD..origin/${DEFAULT_BRANCH}) commits)" >&2
  exit 1
fi
```

Class lesson: when a recurring expensive review-loop pattern is reducible to a mechanical check, write the mechanical check. The 4-lens-spawn-then-converge dynamic that caught PR 23's stale base is exactly what the loop's review surface is for — but a free upstream check that prevents the burn is strictly cheaper.

**Applies to:** workflow, preflight discipline, cost-of-review

**Validation:** 1 BLOCKER in md-manager PR 4. Reinforced cross-repo: md-manager's own retro `/critique-plan` reached the same conclusion independently and captured it as md-manager FB-0033 ("don't skip /critique-plan or /simplify even on docs-only diffs"). The class is real.
