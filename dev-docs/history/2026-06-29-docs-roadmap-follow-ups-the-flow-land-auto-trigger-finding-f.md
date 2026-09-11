### docs: roadmap follow-ups + the /flow:land auto-trigger finding (FB-0063)
**Date:** 2026-06-29
**Branch:** claude/land-60
**Commit:** `f1a21fc` (on branch; final SHA in the PR)

**What was done:**
A roadmap-currency PR, re-scoped after #62 (v1.13.0) landed. The post-merge flip for #60 this PR originally carried was **superseded** — #62's own `/flow:ship` Step 5a reconciliation already moved v1.12.0/#60 into roadmap "Recently shipped". What remained genuinely missing on `main`: (1) three follow-ups dropped when #59 was re-scoped off main — the per-write freshness-token read-back, the manifest-`description` copy-hygiene cap, the `/flow:land` positioning question; (2) the stale `gh` Projects-classic roadmap item, narrowed to reflect the body-write half shipped (#56 + #59) with only the draft-toggle half open; (3) the **`/flow:land` merge-event auto-trigger** item + **FB-0063**, the dogfound finding.

**Why:**
`/flow:land` merged (#60) but, being human-invoked, wasn't run on its own merge — `main` only stayed current because #62 happened to reconcile forward. That is the FLOW-1 forget-rate, intact. FB-0063 records the structural lesson: a human-invoked skill closes cost + error, not the forget-rate; the merge-event auto-trigger is the rung that does.

**Design decisions:**
- **Dropped the superseded headline/plan flip.** #62 already flipped #60 to shipped; re-applying would conflict for no gain (FB-0051 re-scope-to-delta — the third such re-scope this session: #56→#59, #61→#60, #62→this).
- **FB renumbered 0062→0063** — #62 took FB-0062 (failure-open / trust-only-if-artifact-exists), a sibling lesson this entry cross-references.
- No version bump (a roadmap-currency reconcile, not a feature).

**Tradeoffs discussed:**
- Kept the auto-trigger finding as a first-class roadmap item + FB rather than a footnote — it's the load-bearing signal from shipping `/flow:land`.

**Lessons learned:**
- Build the mechanism and its trigger together when the failure mode is "forgotten" (FB-0063). Also: main moved under an open PR three times this session — the re-scope-to-delta discipline (FB-0051) is the routine response, not the exception.
