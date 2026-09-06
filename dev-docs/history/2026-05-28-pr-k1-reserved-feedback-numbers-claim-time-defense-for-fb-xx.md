### PR K1 — Reserved feedback numbers (claim-time defense for FB-XXXX collisions across parallel branches; no version bump)
**Date:** 2026-05-28
**Branch:** `pr-k1/reserved-feedback-numbers`
**Commit:** [SHA at ship time]

**What was done:**
Added `dev-docs/reserved-feedback-numbers.md` — a small protocol file where in-flight branches claim their `FB-XXXX` number before drafting the entry in `feedback.md`. Parallel branches editing this file at the same line produce a clean textual merge conflict (mechanical enforcement). When a PR ships, `/flow:ship`'s synthesis step removes the line. Also added a Handoff Notes entry in `dev-docs/plan.md` documenting the FB-collision audit + resolution.

**No version bump.** `dev-docs/` is project-dev only; doesn't ship in the plugin install.

**Why:**
Post-PR-J cross-worktree audit (triggered by user prompt 2026-05-28: "make sure there hasn't been any lost work… as the PR letters advance on this branch and others") discovered three in-flight FB conflicts before any branch had rebased:

1. `sweet-hellman-6c0745` drafted FB-0011 = "bounded-retry agent loops" while PR J had already shipped FB-0011 = "autonomy bar" to main.
2. `sweet-hellman` drafted FB-0012 = "same-model critic collusion."
3. `pr-m/verify-build-skill` (lucid-matsumoto-730ba0) independently drafted FB-0012 = "check bundled Claude Code skills first."

Counts at audit time: sweet-hellman had **20 FB-0011 references across 5 files** (feedback.md, history.md, plan.md, research doc, schema.json) and **12 FB-0012 references across 2 files** (plan.md, research doc). PR M (verify-build) had 1 FB-0012 textual entry + by-name handoff-doc references.

The textual merge conflict on `feedback.md`'s insertion point only catches the entry itself. The 19 + 11 cross-file references would survive a feedback.md-only rebase resolution and silently point at the wrong concept (the FB-0010 "fan-out contradiction" sub-class applied to FB numbers).

**Resolution recorded mid-PR-K1:** Between this PR's initial draft and the rebase onto main, sweet-hellman rebased + shipped at `0cf642e` (#22) as v1.2.6. Sweet-hellman **renumbered their drafted FB-0011 → FB-0012 and swept all 20 cross-file references cleanly before pushing** — no silent overwrite occurred. PR J's FB-0011 ("autonomy bar") survives untouched on main. The verify-build PR (lucid-matsumoto) still has the open arbitration item: its drafted FB-0012 must renumber to **FB-0013**, and its drafted "PR M" letter is now taken (suggest PR N at its ship time). PR K1's protocol file is updated to reflect the resolution; the audit-trail section preserves both the original contention and the outcome for institutional memory.

**Design decisions:**
- **Why a separate file rather than a section in `dev-docs/plan.md`** — the protocol's mechanical benefit is the textual merge conflict on a small, dedicated file. Sections in plan.md edit other lines too, weakening the conflict-detection guarantee. Single-purpose file is sharper.
- **Why a docs-only PR rather than folding into PR K** — sweet-hellman + PR M (verify-build) were both actively in flight at PR K1's commit time; landing the protocol file ahead of either rebase gives both branches a fetch-and-pull-in coordination surface. PR K (which adds the mechanical Doctor Check 6 + lens-staff-engineer FB-cross-file hunt) is the *permanent enforcement*; PR K1 is the *immediate-coordination signal* layer. Option C from the layered-defense recommendation.
- **Why include current state details in the file itself** — concrete inline references (which branches claim which numbers, what the resolution was) are higher-signal than abstract protocol description. Branches reading the file see the live state plus the rule.
- **Suggested arbitration of the residual FB-0012 contention** — lucid-matsumoto's verify-build PR moves to FB-0013 (single cross-reference; cheaper than re-renumbering sweet-hellman's now-merged FB-0012). Not enforced; surfaced for human decision at PR M-verify-build ship time.

**Technical decisions:**
- File lives at `dev-docs/reserved-feedback-numbers.md` alongside other dev-docs metadata. Not `plugins/flow/` — doesn't ship in the install.
- Format: protocol description + Currently reserved list + Audit trail. The Audit trail section is intentional; FB-0010-style institutional memory for past collisions.
- Protocol step 3 ("push your reservation immediately, don't batch") is the load-bearing race-detection move. Without immediate push, two branches can both reserve the same number locally before either pushes; the push order then determines who wins, but the local edits diverge silently.

**Tradeoffs discussed:**
- **Protocol file vs Doctor Check 6 first.** Doctor Check 6 (FB-collision check vs `origin/main`) is the *rebase-time* enforcement; this file is the *claim-time* enforcement. Both are needed: Doctor catches collisions even if the protocol file isn't updated; the protocol file prevents collisions from being introduced in the first place. PR K ships Doctor Check 6 + lens-staff-engineer hunt extension as the second + third defensive layer. The user explicitly chose Option C (both): land this small PR now, fold Doctor + lens changes into PR K.
- **Audit-trail section in the file vs in history.md.** Kept in the file because the audit trail IS the institutional memory of why this protocol exists. history.md tracks "what we built"; reserved-feedback-numbers.md tracks "what conflicts the protocol caught." Different surfaces; cheap to maintain both.
- **Auto-update on `/flow:ship` vs manual entry removal.** Decided: `/flow:ship` synthesis step (step 4) handles the entry removal — same place that updates feedback.md with the new FB entry. Single source of doc-write timing.

**Lessons learned:**
- **Cross-worktree audits are cheap and catch class issues mechanical merge can't.** The 20-FB-0011-references finding was invisible to git merge-conflict detection but obvious to a one-shot grep across uncommitted state. Periodic "what's in-flight elsewhere?" sweeps are a good discipline; consider folding into the `/flow:doctor` Check 6 design when PR K builds it.
- **Sweet-hellman's clean renumber-then-rebase validated the protocol shape even before the protocol file existed.** Their sweep covered all 20 FB-0011 references + 12 FB-0012 references; nothing silently survived. This is the existence proof that the discipline (grep first, edit second per FB-0010) works when applied. The protocol file makes it harder to forget the sweep, but doesn't change the mechanics.
- **Naming registries work mechanically when the registry file is small and dedicated.** Same pattern works for skill names, schema slots, agent names. If a fourth class hits the same "merge-conflict-but-cross-file" pattern, consider generalizing this file to "reserved-identifiers.md" with sections per identifier type.
