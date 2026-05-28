---
name: doctor
description: >
  Verify that the flow plugin is correctly installed and configured for the
  current project. Runs a punch-list of PASS/FAIL checks: marketplace
  registered under the canonical 'flow' name, flow@flow enabled, project-root
  flow.config.json present + parses + matches the v1.2+ schema, all 17 slots
  have sensible values, auto-loading rules visible to Claude Code, the paths
  named in slots actually exist on disk, prerequisite CLI tools (gh, jq, git)
  installed, preflight + CI optionally wired. Each FAIL prints an actionable
  fix command. Emits a final-line verdict ([READY] / [READY with WARN] /
  [NOT READY]) so the bottom line is scannable. Use after `bash bootstrap.sh`
  to confirm the scaffold took, OR any time something feels off ("is flow set
  up right?", "did install work?", "/flow:* skills not showing up", "checks
  not running"). Auto-triggers on those phrases or on explicit invocation.
disable-model-invocation: false
allowed-tools: Read, Glob, Grep, Bash
---

# flow doctor

Runs verification checks for a project's flow setup. Each check is a single line in the output: `[PASS]` / `[FAIL]` / `[WARN]` + a short label. FAILs always include a fix-it hint. The skill ends with a final-line verdict (`[READY]` / `[READY with WARN-level items]` / `[NOT READY]`) — see the contract at the bottom of this file.

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

**IMPORTANT:** these checks read Claude Code's settings.json files directly via `jq`. `/plugin marketplace list` and `/help` are slash commands (not shell commands), so they cannot be invoked from a Bash block — invoking them would attempt to resolve `/plugin` as an executable path and silently fail (returning empty, which would invert the check and FAIL on correctly-installed flow). Per the PR-D-class silent-skip lesson + FB-0008.

**Check 1.1 — marketplace registered under canonical 'flow' name**

```sh
USER_SETTINGS="$HOME/.claude/settings.json"
PROJECT_SETTINGS=".claude/settings.json"
MARKETPLACE_FOUND=""
for f in "$USER_SETTINGS" "$PROJECT_SETTINGS"; do
  if [ -f "$f" ] && jq -e '.extraKnownMarketplaces.flow // empty' "$f" >/dev/null 2>&1; then
    MARKETPLACE_FOUND="$f"
    break
  fi
done

if [ -n "$MARKETPLACE_FOUND" ]; then
  echo "[PASS] marketplace 'flow' registered in $MARKETPLACE_FOUND"
else
  echo "[FAIL] marketplace 'flow' not registered in user-scope ($USER_SETTINGS) or project-scope ($PROJECT_SETTINGS)"
  echo "       Fix: in a Claude Code session, run: /plugin marketplace add by-dev-tools/flow"
  echo "       (Most common cause: stale 'extraKnownMarketplaces.<old-name>' entry pointing"
  echo "        at the right URL but under the wrong key — re-adding registers under 'flow'.)"
fi
```

The check uses `extraKnownMarketplaces.flow` (an exact-key JSON lookup) rather than a regex match — definitive, no false-positives from sibling marketplaces.

**Check 1.2 — flow@flow plugin enabled**

```sh
ENABLED_AT=""
for f in "$USER_SETTINGS" "$PROJECT_SETTINGS"; do
  if [ -f "$f" ] && jq -e '.enabledPlugins."flow@flow" == true' "$f" >/dev/null 2>&1; then
    ENABLED_AT="$f"
    break
  fi
done

if [ -n "$ENABLED_AT" ]; then
  echo "[PASS] flow@flow enabled in $ENABLED_AT"
else
  echo "[FAIL] flow@flow not enabled in user-scope ($USER_SETTINGS) or project-scope ($PROJECT_SETTINGS)"
  echo "       Fix (one of):"
  echo "         - User-scope:    /plugin install flow@flow   (in any Claude Code session)"
  echo "         - Project-scope: add to .claude/settings.json:"
  echo "                          \"enabledPlugins\": { \"flow@flow\": true }"
fi
```

This is a direct JSON-key check — definitive, doesn't rely on the slash-command dispatcher's behavior.

**Check 1.3 — /flow:* skills visible (optional cross-check via SlashCommand if available)**

If the agent has the `SlashCommand` tool available, it CAN invoke `/help` via that tool and grep the returned text for `/flow:` entries — that's a useful cross-check that the registered + enabled plugin actually surfaces skills. If `SlashCommand` is not available in this session, skip this check and rely on Checks 1.1 + 1.2.

```
(Agent action: if SlashCommand tool is available, invoke `/help`, grep output for
'/flow:(ship|staff-review|workflow-help)'. Otherwise emit [SKIP] for this check.)
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

**Check 2.5 — documented slot count matches schema source-of-truth (FB-0010 fan-out check)**

If the consumer's CLAUDE.md, README.md, or any project doc references "N slots" as a literal count, that count must match `jq '.properties | keys | length'` on the schema. Stale counts after a contract change are the most-recurring fan-out bug class flow has surfaced (FB-0010); cheap to mechanize here.

```sh
# Resolve schema path: plugin-shipped (consumer scope) under CLAUDE_PLUGIN_ROOT,
# or local if running inside the flow repo itself.
SCHEMA=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/schema/flow.config.schema.json" ]; then
  SCHEMA="${CLAUDE_PLUGIN_ROOT}/schema/flow.config.schema.json"
elif [ -f "plugins/flow/schema/flow.config.schema.json" ]; then
  SCHEMA="plugins/flow/schema/flow.config.schema.json"
fi

if [ -z "$SCHEMA" ]; then
  echo "[SKIP] flow schema not reachable — install flow plugin (\$CLAUDE_PLUGIN_ROOT must point to a flow install) or run from the flow repo root"
else
  # Guard malformed schema with explicit FAIL (don't let jq error string flow into ACTUAL).
  ACTUAL=$(jq -r '.properties | keys | length' "$SCHEMA" 2>/dev/null)
  if ! [ "$ACTUAL" -gt 0 ] 2>/dev/null; then
    echo "[FAIL] schema at $SCHEMA is not valid JSON or lacks a .properties object"
    echo "       Fix: jq -e '.properties | keys' \"$SCHEMA\"   (will print the parse error)"
  else
    # Scope the doc scan to the union of flow's own convention (dev-docs/) and the
    # consumer template's convention (CLAUDE.md, README.md, core-docs/, plus the
    # CLAUDE.md.template that consumers may not yet have renamed). docs/ covers
    # this repo's own consumer-facing guides. Only emit SKIP if NONE exist —
    # an empty scan with no docs is itself a silent-skip class FB-0010 catches.
    # Build scan-target list as positional params (POSIX-portable; works in
    # both bash and zsh — bash word-splits unquoted vars but zsh does NOT, so
    # an earlier "$SCAN_TARGETS" string-join silently no-op'd under zsh and
    # reported vacuous PASS. The exact FB-0010 silent-skip class this check
    # is supposed to catch. Positional params via "$@" are portable.)
    set --
    for t in CLAUDE.md CLAUDE.md.template README.md CHANGELOG.md docs core-docs dev-docs; do
      [ -e "$t" ] && set -- "$@" "$t"
    done
    if [ $# -eq 0 ]; then
      echo "[SKIP] no project docs found to scan for slot-count consistency (looked for CLAUDE.md, CLAUDE.md.template, README.md, CHANGELOG.md, docs/, core-docs/, dev-docs/)"
    else
      # Portable across BSD + GNU: extract the FIRST "N slots" pair on each grep
      # output line via grep -oE (works around grep-prefix line-number digits that
      # confused an earlier sed-anchor attempt, and works around the gawk-only
      # 3-arg match() that an even earlier awk attempt silently no-op'd on BSD —
      # both of those earlier attempts were silent-skip bugs of the exact class
      # FB-0010 catches, fixed before this PR shipped).
      STALE=$(grep -rEn '([0-9]+) slots?' "$@" 2>/dev/null \
        | grep -vE ":[[:space:]]*#" \
        | while IFS= read -r line; do
            N=$(printf '%s\n' "$line" | grep -oE '[0-9]+ slots?' | head -n1 | grep -oE '^[0-9]+')
            if [ -n "$N" ] && [ "$N" != "$ACTUAL" ]; then
              printf '%s\n' "$line"
            fi
          done)
      if [ -z "$STALE" ]; then
        echo "[PASS] documented slot count matches schema ($ACTUAL slots; scanned $# path(s))"
      else
        echo "[WARN] documented slot count contradicts schema (schema has $ACTUAL slots; survivors below)"
        echo "       Survivors (some may be intentional historical narrative — e.g., 'schema bumped from 13 to 16'):"
        printf '%s\n' "$STALE" | sed 's/^/         /'
        echo "       Fix: update each line to '$ACTUAL slots' (grep-first-edit-second; FB-0010 discipline), OR move historical numbers behind a comment marker (# prefix) so the check ignores them."
      fi
    fi
  fi
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

Plugin-shipped rules live at `${CLAUDE_PLUGIN_ROOT}/rules/{general,plan-discipline,documentation,exploration}.md` and auto-load on path matches when `flow@flow` is enabled. Inferred-PASS if Checks 1.1 + 1.2 both passed above (those gate the entire plugin-rule-reachability). If 1.1 or 1.2 failed, emit `[SKIP] (depends on Section 1 passing)`.

```sh
# Re-test based on prior section's findings:
if [ -n "$MARKETPLACE_FOUND" ] && [ -n "$ENABLED_AT" ]; then
  echo "[PASS] plugin-shipped rules (general/plan-discipline/documentation/exploration) auto-load via flow@flow"
else
  echo "[SKIP] plugin-shipped rules check — depends on Section 1 (marketplace + enabled) passing first"
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

Final-line verdict (the skill's contract — not an exit code, since skill bodies are agent prompts not processes):

- `[READY] flow is correctly set up; all checks pass.`
- `[READY with WARN-level items] flow is functional; N optional items can be addressed at your discretion.`
- `[NOT READY] N FAIL(s) block flow from working correctly. Address each FAIL's fix above before proceeding.`

Always emit the verdict as the FINAL line so the agent/user can scan to the bottom for the bottom line.

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
