# Missing-`jq` Handling Across Flow Skills — Findings & Recommendation

*Investigation into how flow skills behave when `jq` is absent from PATH, and whether they should fail loud instead of silently degrading to defaults.*

**Date:** 2026-06-29
**Status:** point-in-time findings, **no fix shipped** — this surfaces the shape only. Not maintained; the skill count below (16) predates the current 17. Index: [`dev-docs/README.md`](../README.md).
**Scope:** all 16 skills under `plugins/flow/skills/`. No fix shipped — this surfaces the shape.

> **Update (2026-08-13):** the fix landed in branch `fix-jq-absence-fail-fast` (uniform fail-fast with the two carve-outs recommended in §4, plus the fork-skill `!`-span routed-warning variant — see below). Regression-pinned by `plugins/flow/evals/run_jq_guard_evals.py`. One nuance the original findings under-specified: the 6 "unguarded" skills split by architecture — inline skills (security-review, accessibility-review, contribute) take the `/flow:ship` Step 1.5 `exit 1` guard, but the three `context: fork` skills (audit-coverage, audit-skips, critique-plan) read config in load-time `!` spans where a body `exit` can't reach, so they fail loud by emitting a **routed warning payload** (the existing ROOT-UNRESOLVED / `root_error` pattern), not an exit. The doctor false-FAIL class was also broader than Section 1: Checks 2.2 and 2.5 had the identical `jq -e … else [FAIL]` shape and are now guarded too.
**Triggering observation:** on a freshly-provisioned Conductor cloud workspace (no `jq` in the base image), `/flow:doctor` reported a **false** Section-1 FAIL ("marketplace not registered", "flow@flow not enabled") while flow skills were demonstrably loaded. Root cause: every `jq -e` check returned 127 (command-not-found), the `if` condition went false, and the FAIL branch fired — a false negative on a correct install.
**Lineage:** direct extension of PR #44 (`3d0883e`, v1.10.2) — "jq `// true` silently inverts explicit verifyEnabled/uiSurface false." Same root-cause family: **a jq fallback masking a real signal.** That fix addressed the boolean-slot case; this finding addresses the jq-*absent* case, which defaults *every* slot read wrong at once.

---

## TL;DR

- **The divergence is real and is itself the FB-0010 bug class** ("consistency that depends on author memory"). Of the 13 jq-using skills: 4 fail-fast (BLOCKING), 1 warns-and-degrades, 1 (doctor) detects jq too late to prevent its own false-FAIL, and **7 have no guard at all** and silently degrade.
- **Silent default-substitution is never correct-enough for a config-reading skill.** Every degrade site either gates a decision (early-exit, skip-gate), writes a file, or scopes a reviewer's diff/patterns. On missing jq the project's real config is replaced by hardcoded defaults with **no signal** — the reviewer diffs the wrong base, scans the wrong files, or reads the wrong docs, and reports green.
- **Recommendation: uniform fail-fast** `command -v jq` guard (the existing `/flow:ship` Step 1.5 shape) at the top of every jq-using skill, with **two carve-outs**: (1) `/flow:doctor` cannot exit — its job is to diagnose — so it must detect jq-absence *first* and convert downstream jq checks to explicit `[SKIP]`; (2) `/flow:staff-review` should split its guard (keep `gh` warn-only, promote `jq` to BLOCKING).
- Fresh sandboxes routinely lack jq, so the fail-fast message must carry an actionable install hint. `/flow:ship` Step 1.5 ([ship/SKILL.md:126](plugins/flow/skills/ship/SKILL.md)) is the model.

---

## 1. Per-skill jq-handling map

| Skill | Guard site | Policy today | Behavior on missing jq |
|---|---|---|---|
| `ship` | [Step 1.5, SKILL.md:121](plugins/flow/skills/ship/SKILL.md) | **BLOCKING** | `exit 1` + macOS/Debian/Other install hint ✓ |
| `ship-spike` | [SKILL.md:43](plugins/flow/skills/ship-spike/SKILL.md) | **BLOCKING** | `exit 1` + install hint ✓ |
| `land` | [SKILL.md:52](plugins/flow/skills/land/SKILL.md) | **BLOCKING** | `exit 1` + install hint ✓ |
| `verify-build` | [Step 1.0, SKILL.md:75](plugins/flow/skills/verify-build/SKILL.md) | **BLOCKING** | `exit 1` + install hint ✓ |
| `staff-review` | [Step 1.5, SKILL.md:68](plugins/flow/skills/staff-review/SKILL.md) | **WARN-only** | proceeds; prints "jq missing → slot reads silently degrade to defaults", then degrades anyway |
| `doctor` | [Check 4.1, SKILL.md:391](plugins/flow/skills/doctor/SKILL.md) | **DETECT-LATE** | Sections 1–3 run *before* 4.1 and **false-FAIL**; 4.1 then correctly reports jq missing — too late |
| `security-review` | — | **NONE** | silent: `BASE`→`main`, `sourceFilePatterns`→default, spec/feedback paths→defaults |
| `accessibility-review` | — | **NONE** | silent: `BASE`→`main`, `a11yFilePatterns`→`uiFilePatterns`→default (two reads since PR #95's slot split), `uiSurface`→TRUE, design-language/feedback→defaults |
| `audit-coverage` | — | **NONE** | silent: `planPath`→default, `BASE`→`main`, `sourceFilePatterns`→default |
| `audit-skips` | — | **NONE** | silent: `planPath`→default, `BASE`→`main` |
| `contribute` | — | **NONE** | every slot→empty via `get()`; `flowRepoPath` empty disables contribute (arguably OK) but `contributionThreshold`/`contributionsQueuePath` silently fall to defaults |
| `critique-plan` | — | **NONE** | `referenceGlob`→`core-docs/*.md` default; reviewer reads wrong reference docs |
| `workflow-help` | — | **NONE** | `defaultBranch`→`main` (read-only display — only misinforms, takes no action) |
| `audit-plan` | n/a | **NO JQ** | unaffected |
| `audit-completion` | n/a | **NO JQ** | unaffected |
| `log-disagreement` | n/a | **NO JQ** | unaffected |

Totals: **4 BLOCKING · 1 WARN · 1 DETECT-LATE · 7 NONE · 3 jq-free.** The four most consequential write/PR skills are correct; the entire reviewer family (security, a11y, coverage, skips, critique) — the skills whose *whole job* is to read the diff against the right base with the right patterns — is unguarded.

---

## 2. The two failure shapes

### Shape A — inverted conditional (`jq -e … ; if`) → false branch

```sh
if [ -f "$f" ] && jq -e '.extraKnownMarketplaces.flow // empty' "$f" >/dev/null 2>&1; then
  ...PASS...
else
  ...FAIL...   # <- taken when jq is MISSING (exit 127), not just when key absent
fi
```

When jq is absent the command exits 127 (non-zero), the `if` goes false, and the **negative branch fires regardless of the actual config**. This is the observed `/flow:doctor` false-FAIL. It produces a **wrong conclusion** (not an empty/handled value).

**Sites (all in `doctor/SKILL.md`):**
- Check 1.1 marketplace-registered, [SKILL.md:54](plugins/flow/skills/doctor/SKILL.md) → false "not registered"
- Check 1.2 flow@flow-enabled, [SKILL.md:77](plugins/flow/skills/doctor/SKILL.md) → false "not enabled"
- Section 3 plugin-rules, [SKILL.md:379](plugins/flow/skills/doctor/SKILL.md) → re-tests `$MARKETPLACE_FOUND`/`$ENABLED_AT`, so it **inherits** the false-FAIL and emits a false `[SKIP]`
- Check 2.2 config-parses, [SKILL.md:123](plugins/flow/skills/doctor/SKILL.md) → false "malformed JSON" on valid config
- Checks 2.3/2.4/2.7/2.8 are each gated on `jq -e . flow.config.json` ([SKILL.md:136](plugins/flow/skills/doctor/SKILL.md), [:160](plugins/flow/skills/doctor/SKILL.md), [:287](plugins/flow/skills/doctor/SKILL.md), [:327](plugins/flow/skills/doctor/SKILL.md)) → the guard goes false → checks silently skip or report the "missing/malformed config" branch

The cruel irony: doctor's own jq-presence check (Check 4.1) is correct, but it lives in **Section 4**, after Sections 1–3 have already printed the false verdict. The `[NOT READY]` final-line verdict is then computed from poisoned inputs.

### Shape B — empty-capture default-substitution → wrong-but-plausible value

```sh
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@…@@')
[ -z "$BASE" ] && BASE=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$BASE" ] && BASE=main
```

When jq is absent, `$(jq …)` captures the empty string (jq never ran, so the in-jq `// "main"` never executed either). The trailing `[ -z ]` shell guard then substitutes the **hardcoded default**, silently. The same shape covers the path/pattern slots:

```sh
SPEC=$(cat flow.config.json | jq -r '.specPath // empty'); [ -z "$SPEC" ] && SPEC="dev-docs/spec.md"
SOURCE_PATTERN=$(jq -r '.sourceFilePatterns // empty' …); [ -z "$SOURCE_PATTERN" ] && SOURCE_PATTERN='\.(ts|…)$'
```

**The core defect:** the fallback chain cannot distinguish *"jq missing"* (an error — the real value is unknown) from *"slot legitimately unset"* (default is correct). Both converge on the default. So a project that configured `defaultBranch: develop`, custom `sourceFilePatterns`, or a non-default `specPath` gets the default substituted with no warning — and the reviewer proceeds confidently against the wrong base / wrong files / wrong docs.

**Silent-degradation sites (Shape B):**

| Site | Slot | Default substituted | Consequence on wrong value |
|---|---|---|---|
| [security-review/SKILL.md:46](plugins/flow/skills/security-review/SKILL.md) | `defaultBranch` | `main` | diff vs wrong base → wrong/empty diff → may early-exit "doc-only" and skip a real review |
| [security-review/SKILL.md:54](plugins/flow/skills/security-review/SKILL.md) | `sourceFilePatterns` | builtin regex | security scan includes/excludes the wrong files |
| [security-review/SKILL.md:35-36](plugins/flow/skills/security-review/SKILL.md) | `specPath`, `feedbackPath` | `dev-docs/*` | reviewer reads wrong/absent context docs |
| [accessibility-review/SKILL.md:55](plugins/flow/skills/accessibility-review/SKILL.md) | `defaultBranch` | `main` | as above |
| [accessibility-review/SKILL.md:64](plugins/flow/skills/accessibility-review/SKILL.md) | `a11yFilePatterns` → `uiFilePatterns` (PR #95 split) | builtin | a11y scan scopes the wrong files |
| [accessibility-review/SKILL.md:33](plugins/flow/skills/accessibility-review/SKILL.md) | `uiSurface` | `TRUE` | a project that set `uiSurface:false` gets the a11y review run anyway (low harm — runs unnecessarily) |
| [accessibility-review/SKILL.md:35-36](plugins/flow/skills/accessibility-review/SKILL.md) | `designLanguagePath`, `feedbackPath` | `dev-docs/*` | wrong/absent context |
| [audit-coverage/SKILL.md:34,41,44](plugins/flow/skills/audit-coverage/SKILL.md) | `planPath`, `defaultBranch`, `sourceFilePatterns` | defaults | coverage audit reads wrong plan, diffs wrong base, scopes wrong files |
| [audit-skips/SKILL.md:49,63](plugins/flow/skills/audit-skips/SKILL.md) | `planPath`, `defaultBranch` | defaults | skip-audit reads wrong plan, diffs wrong base |
| [critique-plan/SKILL.md:13](plugins/flow/skills/critique-plan/SKILL.md) | `referenceGlob` | `core-docs/*.md` | critique reads wrong reference docs (or none) |
| [staff-review/SKILL.md (Step 1a + frontmatter + Step 4)](plugins/flow/skills/staff-review/SKILL.md) | `defaultBranch` + slot reads | defaults | warns, then degrades — see §3 |
| [contribute/SKILL.md:30,33](plugins/flow/skills/contribute/SKILL.md) | `contributionThreshold`, `contributionsQueuePath` | `0.6`, `~/.claude/…` | queue split-brain / wrong threshold |
| [workflow-help/SKILL.md:19](plugins/flow/skills/workflow-help/SKILL.md) | `defaultBranch` | `main` | display-only — misinforms an onboarding user, takes no action |

---

## 3. Is degrade-to-default ever correct-enough?

Walked every degrade site against this question. **No — with one near-miss.**

- **Reviewers (security, a11y, coverage, skips, critique):** every one uses the slot to *scope what gets reviewed* — the diff base, the file patterns, the plan, the reference docs. Wrong scope = a review that reports green while never looking at the right thing. This is strictly worse than a loud failure: a missing review surfaces; a wrong-scoped review masquerades as a real one. Not acceptable.
- **`contribute`:** `flowRepoPath`→empty correctly disables the skill (graceful). But `contributionsQueuePath`→default while the project configured a custom queue causes a **split-brain** the skill already warns about elsewhere ([SKILL.md:36](plugins/flow/skills/contribute/SKILL.md) comment). So even here, silent default is a latent bug.
- **`staff-review` (the documented WARN-only rationale):** [SKILL.md:82](plugins/flow/skills/staff-review/SKILL.md) argues jq degradation is "fine for non-fatal slot reads." This is the weakest claim in the codebase. The slot reads include `defaultBranch` (Step 1a stale-base + diff base) and `designLanguagePath`/feedback context — degrading those means staff-review diffs the wrong base (the exact FB-0008 phantom-deletion failure the same file's Step 1a is built to prevent) and reads the wrong design-language doc. Not graceful. The `gh` half of that guard *is* genuinely graceful (PR detection falls to LOCAL-ONLY safely), but `jq` is not.
- **`workflow-help` (the one near-miss):** it only *displays* the loop + slot values; it writes nothing and gates nothing. A wrong `defaultBranch: main` is cosmetic. **But** the entire purpose of `/flow:workflow-help` is to show a newcomer the project's *real* config — showing `main` when it's actually `develop` defeats the point. So even the read-only case warrants at least a warning.

**Conclusion:** silent default-substitution on missing jq is a latent wrong-result everywhere it occurs. There is no skill where it is affirmatively correct.

---

## 4. Recommendation: uniform fail-fast, two carve-outs

### Primary: a shared fail-fast `command -v jq` guard at the top of every jq-using skill

Adopt the existing `/flow:ship` Step 1.5 shape ([ship/SKILL.md:115-135](plugins/flow/skills/ship/SKILL.md)) verbatim in `security-review`, `accessibility-review`, `audit-coverage`, `audit-skips`, `critique-plan`, and `contribute`. POSIX-portable, prints the macOS/Debian/Other install hint, `exit 1`. This collapses the divergence to a single policy and matches the FB-0009 lineage already cited by the four BLOCKING skills.

**Why fail-fast over "distinguish unset from missing" (the option-3 alternative):** you *could* check `command -v jq` once, set a flag, and branch each `// default` site on it. But that re-introduces per-site logic that depends on the author remembering to wire the flag at every read — precisely the FB-0010 "consistency that depends on author memory" failure this whole investigation is an instance of. A single top-of-file guard is one site, not N.

**Why not a single sourced preflight helper** (the option-2 alternative): attractive for DRY, but flow skills are standalone SKILL.md files with inline shell; there is no established "source a shared .sh" pattern in the plugin, and introducing one is a larger surface change than copying a 15-line guard. The guard is already duplicated across 4 skills deliberately ("the consistency itself is the value" — [ship-spike/SKILL.md:56](plugins/flow/skills/ship-spike/SKILL.md)). Extending that duplication is consistent with the established call. A helper is a reasonable *future* refactor but shouldn't gate this fix.

### Carve-out 1 — `doctor` cannot exit; detect jq first, then `[SKIP]`

`/flow:doctor`'s job is to diagnose a broken environment, so it must not `exit 1` on missing jq — that would make the tool useless in exactly the situation it exists for. Instead:

1. Move a jq-presence probe to the **very top** (before Section 1).
2. If jq is missing: emit one loud `[FAIL] jq not on PATH` with the install hint (the Check 4.1 message), and convert every downstream jq-dependent check to `[SKIP] (jq not installed — cannot read settings.json / flow.config.json)` instead of running it.
3. The final-line verdict becomes `[NOT READY]` for the *right* reason (jq missing) with honest `[SKIP]`s, not a pile of false `[FAIL]`s.

This is the minimal change that kills the false-FAIL while preserving doctor's diagnostic role.

### Carve-out 2 — `staff-review`: split the guard

Keep `gh` warn-only (it degrades to LOCAL-ONLY safely, as documented). Promote the `jq` half to BLOCKING — the slot reads it feeds (diff base, design-language doc) are load-bearing, not "non-fatal." Update the [SKILL.md:82](plugins/flow/skills/staff-review/SKILL.md) rationale paragraph, which currently asserts jq degradation is fine.

### Consumer impact

Fresh sandboxes (Conductor, CI checkouts, minimal containers) routinely ship without jq. Fail-fast is the right default *because* of this, not despite it — a loud install hint on first invocation is a 10-second fix; a silently-wrong security review is a shipped bug. Every guard must carry the install hint; the ship Step 1.5 message is the model.

---

## 5. Tradeoff if you'd diverge from uniform fail-fast

The only defensible divergence is `/flow:workflow-help`: since it's read-only display, a WARN-and-show-defaults (rather than hard exit) lets a user still see the loop documentation even without jq. If chosen, the warning must be explicit ("⚠️ jq missing — slot values below are defaults, not this project's config"). I'd still lean fail-fast for consistency, but this is the one skill where warn-only causes no wrong *action*. Everywhere else, the divergence is the bug.

---

## 6. Suggested fix sequencing (for a future PR, not this pass)

1. One eval/fixture first (per the quality bar): a doctor run with jq stubbed off PATH must not emit any false `[FAIL]` in Sections 1–3.
2. Add the BLOCKING guard to the 6 unguarded action skills.
3. Reorder doctor + convert jq-dependent checks to `[SKIP]` on jq-absence.
4. Split staff-review's guard; rewrite its rationale paragraph.
5. Grep-sweep (FB-0010): confirm no remaining `jq -r '… // …'` slot read lacks an upstream presence guard, and no `jq -e … ; if` conditional can false-branch on 127.
