### FB-0144 — `/flow:retro` should close out a group of merged PRs, be runnable by the agent, and dependent PRs should be stacked

**Date:** 2026-11-20

**Source type:** user direction (three requests, relayed from a `byamron/designer` session that merged nine PRs in one batch and then ran `/flow:retro`)

**What was said:** Ben, after the batch: "it should be able to handle groups - i want the retro on everything that merged. i shouldn't have to run it every single PR"; "if i tell you to run the retro, you should be able to do it"; and, in the same breath, that it "can be triggered without me directly calling it". Separately that PRs which depend on each other should be GitHub Stacked PRs rather than N independent PRs that later need conflict-resolving merges, and that flow should say so in one place rather than scatter it.

**Synthesized rule:**
1. **A post-merge close-out is a per-batch event.** Shared work (the doc-currency PR, feedback synthesis, the verdict) runs once per group; only genuinely per-PR work (merge check, branch cleanup) runs per PR. Default the group to "everything merged since the last retro" and do not prompt for it.
2. **A `disable-model-invocation: true` flag is the wrong guard when the thing it protects already has a mechanical gate.** `/flow:retro`'s flag was justified as "the human gate above `/flow:land`", but §2 (refuses unmerged) and `/flow:land` §1a already refuse the dangerous case, and nothing in the skill can merge. The flag only blocked the user it was meant to serve. Replace it with the gate plus an AUTO-INVOCATION clause that says *when* (after a merge, never mid-loop) — the part a flag could never express. FB-0077 reached the same conclusion for `/flow:land` and stopped one skill short.
3. **Dependent PRs are a stack, not siblings.** Documented once, in `workflow.md`, with `/flow:ship` carrying a one-line pointer.
4. **A squash-merge makes `git branch -d` refuse every local branch, and a batch makes that the common case.** Report them as left behind; never reach for `-D`. Delete a remote head only if its tip still equals the PR's `headRefOid`; skip and name anything checked out in another worktree.

**Applies to:** `/flow:retro`, `/flow:land`, any skill whose frontmatter flag is carrying a safety claim that a gate elsewhere already carries; stacked-PR guidance in `docs/workflow.md`.
