### jq `// true` boolean-slot footgun — `verifyEnabled`/`uiSurface` opt-outs silently inverted (v1.10.2) — SAFETY
**Date:** 2026-06-26
**Branch:** fix/verifyenabled-jq-false-default (PR #44, brought current)
**Commit:** (this PR — squash SHA at merge)

**What was done.** Replaced `jq -r '.X // true'` with `jq -r 'if .X == false then "false" else "true" end'` at all four boolean-slot read sites: `doctor/SKILL.md` Check 5.3, `verify-build/SKILL.md` Step 1.2 skip-gate + the preprocessed "Verify enabled:" display line, and `ship/SKILL.md` §5c's `uiSurface` visual-history gate. Bumped to v1.10.2 + CHANGELOG; filed the lesson as FB-0058 (renumbered from the drafted FB-0047).

**Why.** jq's `//` (alternative) operator treats boolean `false` — not just `null` — as "empty", so `false // true` evaluates to `true`. An explicit `verifyEnabled: false` opt-out therefore resolved to *enabled*, and `/flow:verify-build`'s skip-gate never fired — the behavioral gate ran on a project that opted out. Surfaced by the valletta consumer (iOS, `verifyEnabled: false` pending a `/run` recipe) via a spurious `/flow:doctor` run-skill WARN.

**Design decisions.**
- **Brought PR #44 current rather than re-implementing.** The original (2026-06-11) fix was correct and still needed — main never fixed it (confirmed: all three `verifyEnabled` sites still buggy). Rebased onto current main; the 3 code fixes applied cleanly.
- **Extended scope to the 4th site (`ship` §5c `uiSurface`).** PR #44's body claimed "uiSurface reads correctly today" — true on 2026-06-11, but v1.8.0's §5c distill (merged later) introduced a new `.uiSurface // true`. Folding it in closes the whole bug *class*, which is exactly what the FB rule mandates ("grep for `.<slot> //` when adding a boolean slot"). `accessibility-review` already used the safe form, so 4 sites total.
- **Renumbered FB-0047 → FB-0058.** PR #44's drafted FB-0047 collided with main's shipped FB-0047 ("non-forgeable Test plan", PR TP) — the exact cross-branch FB collision the reserved-numbers protocol defends. Swept the reference; the entry now reflects the final 4-site scope.

**Tradeoffs discussed.** A one-time boolean-slot audit (PR #44's original "uiSurface checked, reads correctly") rots the moment a new read is added — which is exactly what happened between 2026-06-11 and v1.8.0. FB-0058 therefore encodes the *grep-on-every-new-read* discipline, not a checked-once claim.

**SAFETY:** restores the `verifyEnabled`/`uiSurface` opt-out skip-gates (a skip that wasn't firing); strengthens existing behavior, downgrades nothing. Fail-safe — absent/null still defaults on (verify enabled); only an *explicit* `false` now correctly skips.
