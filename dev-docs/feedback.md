# Feedback Log

User feedback synthesized into actionable guidance. When the user gives feedback -- corrections, preferences, reactions, direction changes -- the relevant insight is captured here so it shapes all future work.

This is not a transcript. Each entry distills feedback into a rule or preference that applies going forward.

---

## How to Write an Entry

```
### FB-XXXX: [Short summary of the feedback]
**Date:** YYYY-MM-DD
**Source:** user correction | user preference | user direction | review feedback

**What was said:** Brief, factual summary of the feedback.

**Synthesized rule:** The actionable takeaway -- what to do differently going forward.

**Applies to:** [areas this affects: ux, code, architecture, workflow, etc.]
```

### Numbering
Increment from the last entry. Use `FB-0001`, `FB-0002`, etc.

### Source types
- **user correction** -- user fixed something you did wrong
- **user preference** -- user expressed a stylistic or process preference
- **user direction** -- user set strategic direction or priorities
- **review feedback** -- issues found during code/design review

---

## Entries

<!-- Add new entries below this line, newest first. -->

### FB-0004: Security regression tests must assert on what would leak, not on a proxy for it
**Date:** 2026-05-25
**Source:** review feedback (PR 3 engineer-lens dogfood)

**What was said:** PR 3 Phase 7's engineer lens caught that `test_absolute_outside_cwd_rejected` asserted `"/etc/hosts" not in result.stdout` — passes trivially because a content leak prints `127.0.0.1` (the host file's content), not the path string. A regression that drops the cwd check but doesn't print the path would pass the test silently. The dotdot-traversal test in the same file got it right: `"127.0.0.1" not in stdout and "::1" not in stdout`. Both rejection + accept tests were strengthened in the same Phase 7 fix commit to use content sentinels.

**Synthesized rule:** When writing a security regression test, identify what a real leak/breach would actually output, then assert on THAT. A real leak of `/etc/hosts` prints loopback addresses, not the path. A real leak of `~/.ssh/id_rsa` prints `-----BEGIN OPENSSH PRIVATE KEY-----`. A real shell injection prints `pwned` or creates a marker file. The path string is a proxy and proxies have escape hatches. When in doubt: write a deliberately-broken implementation locally, run the test, verify it FAILS. If the test passes with a known-broken implementation, the assert is vacuous.

**Applies to:** security regression testing, workflow

**Validation:** 1 BLOCKER caught in PR 3 Phase 7. Original assert: `"/etc/hosts" not in result.stdout or "outside" in combined.lower() or "external" in combined.lower()` — three disjuncts, any of which trivially satisfies. Replaced with `"127.0.0.1" not in result.stdout and "::1" not in result.stdout` — content-only, no escape hatch.

### FB-0003: Schema-without-implementation is a class of bug only dogfood catches
**Date:** 2026-05-24
**Source:** review feedback (PR 2 engineer-lens dogfood)

**What was said:** The Phase-7 engineer-lens review on PR 2 flagged that `memoryHardCap` was documented in `flow.config.schema.json` as configurable but `tools/memory/check.mjs` hardcoded `HARD_CAP = 30` and never read the config — a "false affordance" in the engineer lens's words. Same pattern with `branchPrefix`: documented in schema, no consumer in any skill. Both shipped through Phase 5's pre-commit greps cleanly because no static check correlates "slot documented in schema" against "slot read by something."

**Synthesized rule:** Every config slot landed in `flow.config.schema.json` must be paired with at least one consumer SKILL/agent/tool that reads it AT LANDING TIME — not "documented now, wired later." If a slot is genuinely future-only, mark it `"deprecated": "v1.x — not yet implemented"` in the schema description so consumers know. Treat schema-without-implementation as a contract lie equivalent to the loud-warning-vs-silent-no-op risk from PR 1. Pre-commit check: `for slot in $(jq -r '.properties | keys[]' schema/flow.config.schema.json); do if ! grep -q "$slot" plugins/flow/{skills,agents,tools,scripts}/; then echo "WARN: $slot documented but no consumer"; fi; done`.

**Applies to:** workflow, schema design, config-slot contracts

**Validation:** 2 of 13 slots in PR 2's schema (memoryHardCap, branchPrefix) had no consumer at first commit; engineer-lens caught both. Both wired in Phase 7 fix commit. The remaining 11 slots had at least one consumer.

### FB-0002: Validator-pass doesn't mean runtime-safe; the dispatcher is its own contract
**Date:** 2026-05-24
**Source:** review feedback (PR 2 engineer-lens dogfood)

**What was said:** Phase 7 caught that `/flow:ship`'s Phase-6 backfill invoked `Skill("flow:security-review")` and `Skill("flow:accessibility-review")` but the SKILL.md's `allowed-tools` frontmatter didn't list `Skill`. `claude plugin validate .` passed (the manifest is syntactically clean); the cwd-constraint test passed; the smoke install passed. The bug would have surfaced only at runtime when the dispatcher denied the tool call. This is a class of bug the validator can't catch and pre-commit greps would miss.

**Synthesized rule:** When a SKILL invokes a tool (`Skill`, `Agent`, `Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `TaskCreate`, `TaskUpdate`, etc.), explicitly verify that tool is in the SKILL's `allowed-tools` frontmatter. The frontmatter is the dispatcher's contract; `claude plugin validate` validates manifest syntax, not tool-allowlist correctness. Recommended pre-commit grep:
```sh
for skill in plugins/flow/skills/*/SKILL.md; do
  ALLOWED=$(awk '/^allowed-tools:/{print; exit}' "$skill")
  for tool in Skill Agent Bash Edit Write Read Glob Grep TaskCreate TaskUpdate; do
    if grep -qE "\\b${tool}\\(" "$skill" && ! echo "$ALLOWED" | grep -qE "\\b${tool}\\b"; then
      echo "WARN: $skill invokes $tool but allowed-tools omits it"
    fi
  done
done
```

**Applies to:** workflow, plugin skill development, pre-commit checks

**Validation:** 1 BLOCKER caught in PR 2's Phase 7 dogfood (Skill missing from ship.md). PR 1 had no Skill invocations so this class was latent until PR 2.

### FB-0001: Dogfood the workflow even when not all skills exist yet
**Date:** 2026-05-24
**Source:** user direction

**What was said:** After PR 1 was opened, the user said: "even though all the skills may not be officially built out yet, follow the prompts from the skills in workflow.md to review the PR, taking it through all the stages of the intended workflow that we are implementing."

**Synthesized rule:** When a PR builds the workflow infrastructure itself, dogfood every loop step that *can* be run (manually or by emulating the planned skill's prompt via Agent subagents). Don't skip a step because the named skill doesn't exist yet — the loop's value is the *steps*, not the skill packaging. Concrete pattern: spawn 3-4 parallel review-lens Agents (engineer, push-further, security, plan-critic emulation) with the equivalent of the planned SKILL.md prompts; triage findings via the same BLOCKER / NIT / FOLLOW-UP scheme; apply BLOCKER + cheap NIT inline; route FOLLOW-UPs to plan.md; write the history.md entry; push the fix commit so the PR auto-updates.

Don't pre-empt this rule with "no skill, no review" — that defeats the point of building flow at all. Bootstrap exception (manual cold-read) is the *fallback* when even manual review isn't feasible, not the *default* when a manual review would be cheap.

**Applies to:** workflow, code review, agent self-feedback discipline

**Validation:** the walk-through-the-loop pass on PR 1 caught 3 BLOCKERs the pre-merge cold-read missed (manifest redundancy, two stale `agents/auditor.md` references in shipped prompts, `eval` vs `sh -c`). All three would have been consumer-visible bugs if shipped.
