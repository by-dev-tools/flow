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
