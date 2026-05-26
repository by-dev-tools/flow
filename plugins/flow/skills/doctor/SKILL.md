---
name: doctor
description: >
  Verify that the flow plugin is correctly installed and configured for the
  current project. Runs a punch-list of PASS/FAIL checks: marketplace
  registered under the canonical 'flow' name, flow@flow enabled, project-root
  flow.config.json present + parses + matches the v1.2+ schema, all 14 slots
  have sensible values, auto-loading rules visible to Claude Code, the paths
  named in slots actually exist on disk, prerequisite CLI tools (gh, jq, git)
  installed, preflight + CI optionally wired. Each FAIL prints an actionable
  fix command. Returns exit 0 only on all-pass. Use after `bash bootstrap.sh`
  to confirm the scaffold took, OR any time something feels off ("is flow set
  up right?", "did install work?", "/flow:* skills not showing up", "checks
  not running"). Auto-triggers on those phrases or on explicit invocation.
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Bash
---

# flow doctor

Runs verification checks for a project's flow setup. Each check is a single line in the output: `[PASS]` / `[FAIL]` / `[WARN]` + a short label. FAILs always include a fix-it hint. The skill exits 0 only when all checks pass.

## When to invoke

- After running `bash bootstrap.sh` on a fresh project (verify the scaffold took).
- After running `/plugin marketplace add` + `/plugin install` (verify install).
- When `/flow:*` skills don't appear in `/help`.
- When workflow gates don't fire as expected (stale-base, CI checks, etc.).
- The user says any of: "is flow set up right?", "did install work?", "check the project", "verify the setup", "why isn't /flow:X showing up?", "/flow:doctor".

## Project context (resolved at invocation)

- Project root: !`pwd`
- Current branch: !`git branch --show-current 2>/dev/null || echo "(not a git repo)"`
- flow.config.json present: !`[ -f flow.config.json ] && echo "YES" || echo "NO"`

## Run all checks

Run the following checks in order. For each check: print `[PASS]` or `[FAIL]` or `[WARN]` followed by the label, then on FAIL/WARN the next-line indented hint.

### Section 1: install surface

**Check 1.1 — marketplace registered under canonical name**

```sh
if /plugin marketplace list 2>/dev/null | grep -qE '^flow($|[[:space:]])'; then
  echo "[PASS] marketplace 'flow' registered"
else
  echo "[FAIL] marketplace 'flow' not found in /plugin marketplace list"
  echo "       Fix: /plugin marketplace add by-dev-tools/flow"
  echo "       (Most common cause: stale 'extraKnownMarketplaces.<old-name>' in ~/.claude/settings.json"
  echo "        — re-adding registers under the correct name regardless.)"
fi
```

The above grep pattern uses `^flow($|[[:space:]])` to word-anchor — avoids false-positive matches on a sibling marketplace named `flow-experimental` or similar. Per `dev-docs/feedback.md` FB-0005.

**Check 1.2 — flow@flow plugin enabled**

```sh
if /help 2>/dev/null | grep -qE '/flow:(ship|staff-review|workflow-help)'; then
  echo "[PASS] flow@flow plugin is enabled and skills are visible"
else
  echo "[FAIL] flow@flow not visible in /help output"
  echo "       Fix (one of):"
  echo "         - /plugin install flow@flow                         (user-scope)"
  echo "         - Edit .claude/settings.json: enabledPlugins.flow@flow = true   (project-scope)"
fi
```

### Section 2: project config

**Check 2.1 — flow.config.json at repo root**

```sh
if [ -f flow.config.json ]; then
  echo "[PASS] flow.config.json exists at repo root"
else
  echo "[FAIL] flow.config.json not found at repo root"
  echo "       Fix: bash <flow-checkout>/template/base/bootstrap.sh --stack <web|swift|tauri-rust-ts>"
  echo "       (Or manually: copy template/base/flow.config.json.example, strip \$comment-* keys.)"
fi
```

**Check 2.2 — flow.config.json parses as valid JSON**

```sh
if [ -f flow.config.json ]; then
  if jq -e . flow.config.json >/dev/null 2>&1; then
    echo "[PASS] flow.config.json parses as valid JSON"
  else
    echo "[FAIL] flow.config.json is malformed JSON"
    echo "       Fix: jq -e . flow.config.json   (will print the parse error + line number)"
    echo "       Common cause: leftover \$comment-* key without the bootstrap.sh jq-strip."
  fi
fi
```

**Check 2.3 — required slots have sensible values**

```sh
if [ -f flow.config.json ] && jq -e . flow.config.json >/dev/null 2>&1; then
  # typecheckCmd: warn-only (unset means /flow:ship prints a loud warning at ship time)
  TC=$(jq -r '.typecheckCmd // empty' flow.config.json)
  if [ -n "$TC" ]; then
    echo "[PASS] typecheckCmd set: $TC"
  else
    echo "[WARN] typecheckCmd not set — /flow:ship will skip typecheck re-run with a loud warning"
    echo "       Fix (optional): set 'typecheckCmd' in flow.config.json to your project's typecheck command"
    echo "       Examples: 'npm run typecheck', 'tsc --noEmit', 'cargo check --workspace'"
  fi

  # defaultBranch: optional (3-tier fallback chain handles unset)
  DB=$(jq -r '.defaultBranch // empty' flow.config.json)
  if [ -n "$DB" ]; then
    echo "[PASS] defaultBranch set: $DB"
  else
    echo "[PASS] defaultBranch unset (will resolve via git symbolic-ref or fall back to 'main')"
  fi
fi
```

**Check 2.4 — doc-path slots point at existing files (or paths that will be auto-created)**

```sh
if [ -f flow.config.json ] && jq -e . flow.config.json >/dev/null 2>&1; then
  for slot in planPath specPath roadmapPath historyPath feedbackPath; do
    P=$(jq -r ".${slot} // empty" flow.config.json)
    [ -z "$P" ] && P="core-docs/$(echo $slot | sed 's/Path//').md"   # defaults
    if [ -f "$P" ]; then
      echo "[PASS] ${slot}: ${P} exists"
    else
      echo "[WARN] ${slot}: ${P} does not exist yet"
      echo "       Fix: mkdir -p \$(dirname \"${P}\") && touch \"${P}\""
      echo "       (Or let bootstrap.sh create it from template/base/core-docs/*.md)"
    fi
  done
fi
```

### Section 3: auto-loading rules (the load-bearing enforcement mechanism)

**Check 3.1 — project-side rules present**

```sh
if [ -f .claude/rules/safety.md ]; then
  echo "[PASS] .claude/rules/safety.md present (will auto-load on safety-critical edits)"
else
  echo "[WARN] .claude/rules/safety.md not present"
  echo "       Fix: bash <flow-checkout>/template/base/bootstrap.sh --stack <stack>"
  echo "       (Or manually copy template/base/.claude/rules/safety.md.template)"
fi
```

**Check 3.2 — plugin-shipped auto-load rules are reachable**

```sh
# Plugin-shipped rules live at ${CLAUDE_PLUGIN_ROOT}/rules/{general,plan-discipline,documentation,exploration}.md
# Claude Code auto-loads them on path matches when flow@flow is enabled.
# We can verify by checking the plugin's marketplace registration (passed in check 1.1+1.2 above).
if /plugin marketplace list 2>/dev/null | grep -qE '^flow($|[[:space:]])' && /help 2>/dev/null | grep -qE '/flow:'; then
  echo "[PASS] plugin-shipped rules (general/plan-discipline/documentation/exploration) auto-load via flow@flow"
fi
```

### Section 4: prerequisite CLI tools

**Check 4.1 — required tools on PATH**

```sh
for tool in git jq gh; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "[PASS] $tool installed: $(command -v "$tool")"
  else
    echo "[FAIL] $tool not on PATH"
    case "$tool" in
      git)  echo "       Fix: install git via your platform's package manager." ;;
      jq)   echo "       Fix: brew install jq (macOS) | apt install jq (Debian/Ubuntu)" ;;
      gh)   echo "       Fix: brew install gh (macOS) | apt install gh (Debian/Ubuntu) | https://cli.github.com"
            echo "       Then: gh auth login" ;;
    esac
  fi
done
```

### Section 5: optional infrastructure

**Check 5.1 — preflight script (project-shaped; flow doesn't bundle)**

```sh
if [ -f tools/preflight/check.mjs ] || [ -f tools/preflight/check.sh ]; then
  echo "[PASS] tools/preflight/check.{mjs,sh} present"
else
  echo "[WARN] no preflight script at tools/preflight/check.{mjs,sh}"
  echo "       Optional but recommended. Fix: bootstrap.sh ships a stack-specific preflight runner."
fi
```

**Check 5.2 — CI workflow**

```sh
if [ -d .github/workflows ] && [ -n "$(ls -A .github/workflows 2>/dev/null)" ]; then
  echo "[PASS] .github/workflows/ has CI workflows"
else
  echo "[WARN] no CI workflows at .github/workflows/"
  echo "       Optional but recommended. Fix: bootstrap.sh ships a stack-specific ci.yml."
fi
```

## Summary

After running all sections, emit a summary line:

```
═══ flow:doctor summary ═══
  Section 1 (install):       <N PASS / N FAIL>
  Section 2 (project config): <N PASS / N WARN / N FAIL>
  Section 3 (auto-load rules): <N PASS / N WARN>
  Section 4 (CLI tools):     <N PASS / N FAIL>
  Section 5 (optional infra): <N PASS / N WARN>

  Overall: [READY] / [READY with WARN-level items] / [NOT READY — N FAILs blocking]
```

Exit code:
- `0` — all `PASS` and `WARN` checks; no `FAIL`.
- `1` — any `FAIL`. The output names the fix for each FAIL.

## What doctor does NOT check

- Whether the consumer correctly filled `{{PLACEHOLDER}}` values in CLAUDE.md / README.md / safety.md. These are judgment calls; doctor can't verify "the right project name."
- Whether `flow.config.json.typecheckCmd` actually runs typecheck successfully — only that the slot is set. The /flow:ship pipeline executes it.
- Whether the project actually follows the loop end-to-end — that's `/flow:workflow-help` + reading workflow.md territory.
- Anything about the consumer's product correctness. Doctor verifies the SETUP, not the WORK.

## When to escalate

If doctor's output doesn't match what you observe (e.g., it says PASS but `/flow:staff-review` is broken):
- Check `dev-docs/feedback.md` in the flow repo for known issues.
- File a follow-up flow PR with the discrepancy under FB-XXXX format.
- Run `claude plugin validate <flow-checkout>` to confirm the manifest is intact.
