---
name: doctor
description: >
  Verify that the flow plugin is correctly installed and configured for the
  current project. Runs a punch-list of PASS/FAIL checks: marketplace
  registered under the canonical 'flow' name, flow@flow enabled, project-root
  flow.config.json present + parses + matches the v1.2+ schema, no skill composes
  with a `disable-model-invocation` skill (a call the runtime rejects), the
  required, doc-path, and dependent slots have sensible values and their paths
  exist on disk (not all 33 of the schema's slots — see Check 2.3/2.4/2.7/2.8/2.9/2.11
  for exactly which; ephemeral paths created on first write and non-path config
  are intentionally excluded), any declared `statusDocs` status surfaces exist + are
  fenced, any undeclared `statusSurfaceCandidates` that carry status content are
  flagged for opt-in, any open PR for HEAD is body↔draft coherent (no stale
  `NOT READY TO MERGE` manifest on a ready PR), auto-loading rules visible to
  Claude Code, prerequisite CLI
  tools (gh, jq, git) installed, preflight + CI optionally wired. Each FAIL prints an actionable
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

**Guard against jq-absence FIRST (carve-out — jq-absence-handling-2026-06).** These checks read settings.json with `jq -e … ; then PASS; else FAIL`. When jq is absent it exits 127 (non-zero), the `if` goes false, and the FAIL branch fires **regardless of the actual config** — a false `[FAIL]` on a correct install (the observed Conductor bug). doctor's job is to diagnose a broken env, so it must NOT `exit`; instead it emits an honest `[SKIP]` here and the single real `[FAIL]` lands at Check 4.1. Every jq-reading check in Sections 1–3 carries this same `command -v jq` guard.

```sh
if ! command -v jq >/dev/null 2>&1; then
  echo "[SKIP] marketplace 'flow' registration — jq not on PATH (see Check 4.1); cannot read settings.json. A failure verdict here without jq would be false."
else
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
fi
```

The check uses `extraKnownMarketplaces.flow` (an exact-key JSON lookup) rather than a regex match — definitive, no false-positives from sibling marketplaces.

**Check 1.2 — flow@flow plugin enabled**

```sh
if ! command -v jq >/dev/null 2>&1; then
  echo "[SKIP] flow@flow enabled — jq not on PATH (see Check 4.1); cannot read settings.json. A failure verdict here without jq would be false."
else
USER_SETTINGS="$HOME/.claude/settings.json"
PROJECT_SETTINGS=".claude/settings.json"
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
fi
```

This is a direct JSON-key check — definitive, doesn't rely on the slash-command dispatcher's behavior.

**Check 1.3 — /flow:* skills visible (optional cross-check via SlashCommand if available)**

If the agent has the `SlashCommand` tool available, it CAN invoke `/help` via that tool and grep the returned text for `/flow:` entries — that's a useful cross-check that the registered + enabled plugin actually surfaces skills. If `SlashCommand` is not available in this session, skip this check and rely on Checks 1.1 + 1.2.

```
(Agent action: if SlashCommand tool is available, invoke `/help`, grep output for
'/flow:(ship|staff-review|workflow-help)'. Otherwise emit [SKIP] for this check.)
```

**Check 1.4 — skill composition targets are model-invocable (FB-0074)**

A skill can instruct the agent to run another skill (`Skill("flow:x")`) — flow's "composition, not reimplementation" idiom. But `disable-model-invocation: true` blocks *programmatic* invocation, not just auto-selection: the call is rejected at runtime and the composition degrades to its fallback on **every** run, silently. The two halves of the contract live in different files (call site vs. callee frontmatter), so only a cross-file lint catches it — this is the FB-0010 fan-out class. Flow shipped exactly this bug in `/flow:post-merge` → `/flow:land` and could not see it for two releases.

Runs over the installed plugin's skills, and over the project's own `.claude/skills/` when present (a consumer writing custom skills hits the same trap).

```sh
# Emit doctor's OWN [PASS]/[FAIL]/[WARN]/[SKIP] tokens (the final-line verdict is
# assembled by counting them). The lint's internal "[skill-composition-lint] …" lines
# are detail, not verdict — a check whose FAIL never registers in the verdict is the
# same never-registers-as-a-gate class this check exists to catch.
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  PLUGIN_SKILLS="${CLAUDE_PLUGIN_ROOT}/skills"
  L="${CLAUDE_PLUGIN_ROOT}/skills/doctor/lib/skill-composition-lint.py"
else
  PLUGIN_SKILLS="plugins/flow/skills"
  L="plugins/flow/skills/doctor/lib/skill-composition-lint.py"
fi
if [ ! -f "$L" ]; then
  echo "[SKIP] skill-composition lint — helper not found at $L"
  echo "       Fix: reinstall the flow plugin (/plugin install flow@flow)."
else
  for D in "$PLUGIN_SKILLS" ".claude/skills"; do
    if [ ! -d "$D" ]; then
      # Absent .claude/skills is normal (most projects write no custom skills); say so
      # rather than skipping silently, so "not scanned" can't read as "scanned, clean".
      echo "[SKIP] skill-composition lint — $D not present (no custom skills to lint)"
      continue
    fi
    OUT=$(python3 "$L" "$D" 2>&1); RC=$?
    printf '%s\n' "$OUT" | sed 's/^/       /'
    case "$RC" in
      0) echo "[PASS] skill-composition targets model-invocable ($D)" ;;
      # The lint's own output (printed above) carries the full remediation, including WHICH
      # half to change and why deleting the call is usually the wrong fix. Don't restate it
      # here — a second, shorter, differently-ordered list is how the two drift apart.
      1) echo "[FAIL] skill-composition — a Skill() call names a disable-model-invocation skill ($D)"
         echo "       That call is REJECTED at runtime, so the step silently never runs."
         echo "       Fix: see the [skill-composition-lint] FAIL detail above." ;;
      *) echo "[WARN] skill-composition lint could not run over $D (exit $RC) — composition is UNCHECKED, not clean." ;;
    esac
  done
fi
```

`[PASS]` per scanned directory is the healthy result. `[FAIL]` names the caller, the callee, and the file:line. Note the exit codes are distinguished: **1** is a real violation, anything else is a tool failure — reporting "could not run" as a violation would be a false accusation, and reporting it as a pass would be the failure-open. UNKNOWN targets (a `Skill()` naming something outside the scanned tree — another plugin, or a typo) are printed in the indented detail rather than suppressed, so `Skill("flow:lnad")` stays visible.

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
if ! command -v jq >/dev/null 2>&1; then
  echo "[SKIP] flow.config.json JSON validity — jq not on PATH (see Check 4.1); cannot parse. A failure verdict here without jq would be false."
elif [ -f flow.config.json ]; then
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
if ! command -v jq >/dev/null 2>&1; then
  echo "[SKIP] required-slot values — jq not on PATH (see Check 4.1); cannot read flow.config.json."
elif [ -f flow.config.json ] && jq -e . flow.config.json >/dev/null 2>&1; then
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

Existence-checks the doc-path slots a fresh project is expected to scaffold: `planPath`, `specPath`, `roadmapPath`, `historyPath`, `feedbackPath`, and — when `uiSurface` resolves `true` — `designLanguagePath` (FB-0098; previously absent from this loop despite 23+ dependent files across four staff-review lens agents, `plan-critic`, `planner`, `verify-build`, `staff-review`, `accessibility-review`, and `ship`; `template/base/core-docs/design-language.md` now ships a template for it). WARN, not FAIL — a missing doc is fixable by `bootstrap.sh` or a manual `touch`, never a hard block. **Deletion criterion:** delete the `designLanguagePath` loop entry if the slot ever leaves the schema.

The unset-slot fallback below builds `dev-docs/<slot>.md` — matching `flow.config.schema.json`'s own declared `default` for every doc-path slot, and the convention every *other* call site in the plugin already uses (16 sites across `ship`, `ship-spike`, `land`, `verify-build`, `staff-review`, `security-review`, `accessibility-review`, `audit-coverage`, `audit-skips`, `planner`, `docs` — all `dev-docs/`). Before FB-0098 this line was the *only* `core-docs/` outlier against that convention (FB-0098's own root cause, caught mid-fix: setting flow's own `flow.config.json` slots explicitly would have masked the symptom on this one dogfood repo while leaving the same false-WARN live for every other consumer with an unset slot — the fix belongs in the default, not the config).

**This loop is deliberately not exhaustive over all 33 schema slots** — see the frontmatter for the honest scope claim. Not existence-checked here, on purpose:
- `verifyFindingsPath`, `verifyReportPath`, `visualHistoryPath`, `lastHarvestedPath` — ephemeral or CREATED ON FIRST WRITE by design (not scaffolded by `bootstrap.sh`); a missing file is the correct steady state.
- `statusDocs`, `statusSurfaceCandidates` (Check 2.7/2.9), `flowRepoPath`, `contributionsQueuePath` (Check 2.8) — path-shaped but already existence/coherence-checked by a different check (arrays or dev-tooling paths, not scalar doc paths).
- `referenceGlob` — a glob, not a single path; a zero-match glob isn't inherently wrong.
- `rustWorkspaceDir` — directory path, Tauri/Rust-only, conditional on the optional `platform` hint; known gap, not fixed here — see `roadmap.md` § Exploration.
- All other slots (`defaultBranch`, `role`, `typecheckCmd`, `preflightCmd`, `uiSurface`, `reviewLenses`, `memoryHardCap`, `branchPrefix`, `platform`, `verifyEnabled`, `verifyBudgetCalls`, `contributionThreshold`, `postMergeWaitSeconds`, `sourceFilePatterns`, `uiFilePatterns`, `visualFilePatterns`, `a11yFilePatterns`) are non-path config (commands, enums, booleans, numbers, regexes) — existence-checking a path doesn't apply. `defaultBranch`/`typecheckCmd` (Check 2.3), `role` (Check 2.11), and `contributionThreshold` (Check 2.8) get a value-sanity check instead; the remaining 13 rely on schema type/enum validation only.

```sh
if ! command -v jq >/dev/null 2>&1; then
  echo "[SKIP] doc-path slots — jq not on PATH (see Check 4.1); cannot read flow.config.json."
elif [ -f flow.config.json ] && jq -e . flow.config.json >/dev/null 2>&1; then
  # NOT `.uiSurface // true` — jq's `//` treats JSON `false` as "no value" too
  # (same as null/absent), so that form silently coerces an explicit
  # `uiSurface: false` back to true. `if ... == false` is the plugin's
  # established safe pattern (accessibility-review's Check 0.1 gate).
  UI_SURFACE=$(jq -r 'if .uiSurface == false then "false" else "true" end' flow.config.json)
  DOC_SLOTS="planPath specPath roadmapPath historyPath feedbackPath"
  [ "$UI_SURFACE" = "true" ] && DOC_SLOTS="$DOC_SLOTS designLanguagePath"
  for slot in $DOC_SLOTS; do
    P=$(jq -r ".${slot} // empty" flow.config.json)
    SLOT_WAS_SET=true
    if [ -z "$P" ]; then
      SLOT_WAS_SET=false
      # dev-docs/<kebab-case-slot>.md — matches the schema's declared per-slot
      # default, not the consumer-scaffold convention (core-docs/). camelCase ->
      # kebab-case so a compound slot name (designLanguagePath) builds
      # "design-language.md", not "designLanguage.md".
      BASE=$(echo "$slot" | sed 's/Path$//' | sed 's/\([a-z0-9]\)\([A-Z]\)/\1-\2/g' | tr '[:upper:]' '[:lower:]')
      P="dev-docs/${BASE}.md"
    fi
    if [ -f "$P" ]; then
      echo "[PASS] ${slot}: ${P} exists"
    elif [ "$SLOT_WAS_SET" = true ]; then
      # An explicitly-set slot pointing at a missing file: touching THAT path is
      # unambiguously correct — the project already told us where it wants this doc.
      echo "[WARN] ${slot}: ${P} does not exist yet"
      echo "       Fix: mkdir -p \$(dirname \"${P}\") && touch \"${P}\""
    else
      # Unset slot, resolved via the dev-docs/ fallback: do NOT lead with a
      # touch-a-stub-in-dev-docs/ instruction (staff-review UX finding) — a
      # consumer project almost always wants core-docs/ instead, and a reader
      # who mechanically runs a bolded "Fix:" line ends up with a stray stub
      # in the wrong directory. Point straight at the real remedy.
      echo "[WARN] ${slot}: ${P} does not exist yet (unset — resolved via the dev-docs/ default)"
      echo "       Fix: run bootstrap.sh to scaffold core-docs/*.md from"
      echo "       template/base/core-docs/*.md, then set '${slot}' to that path in flow.config.json."
      echo "       (Or, if this project deliberately uses dev-docs/ like flow's own repo:"
      echo "       mkdir -p dev-docs && touch \"${P}\".)"
    fi
  done
  if [ "$UI_SURFACE" != "true" ]; then
    echo "[PASS] designLanguagePath: uiSurface is false — design-language doc not required"
  fi
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

# Resolve the shared scan predicate the same way (mirrors Check 1.4/2.7's resolution).
# This is the SAME module `run_merge_status_evals.py` imports for flow's own internal
# sweep (FB-0079) — one wrap-tolerant regex, not two implementations that can drift.
LIB=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/doctor/lib/slot_count_scan.py" ]; then
  LIB="${CLAUDE_PLUGIN_ROOT}/skills/doctor/lib/slot_count_scan.py"
elif [ -f "plugins/flow/skills/doctor/lib/slot_count_scan.py" ]; then
  LIB="plugins/flow/skills/doctor/lib/slot_count_scan.py"
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "[SKIP] documented slot-count vs schema — jq not on PATH (see Check 4.1); cannot read the schema. A failure verdict here without jq would be false."
elif [ -z "$SCHEMA" ]; then
  echo "[SKIP] flow schema not reachable — install flow plugin (\$CLAUDE_PLUGIN_ROOT must point to a flow install) or run from the flow repo root"
elif [ -z "$LIB" ]; then
  echo "[SKIP] slot-count scan helper not reachable — install flow plugin (\$CLAUDE_PLUGIN_ROOT must point to a flow install) or run from the flow repo root"
else
  # Guard malformed schema with explicit FAIL (don't let jq error string flow into ACTUAL).
  ACTUAL=$(jq -r '.properties | keys | length' "$SCHEMA" 2>/dev/null)
  if ! [ "$ACTUAL" -gt 0 ] 2>/dev/null; then
    echo "[FAIL] schema at $SCHEMA is not valid JSON or lacks a .properties object"
    echo "       Fix: jq -e '.properties | keys' \"$SCHEMA\"   (will print the parse error)"
  else
    # Scope the doc scan to the union of flow's own convention (dev-docs/) and the
    # consumer template's convention (CLAUDE.md, README.md, core-docs/, plus the
    # CLAUDE.md.template that consumers may not yet have renamed, and bootstrap.sh —
    # a plausible top-level leftover if a consumer downloaded it into their project
    # root to bootstrap flow. Staff-review's engineer lens found this does NOT close
    # the specific FB-0079 corollary-3 instance — the template's own bootstrap.sh
    # never lands at a project's root via the copy step, and the historical stale
    # comment lived at `template/base/bootstrap.sh`, already covered by the
    # *internal* sweep's separate recursive scan (a different runtime, different
    # scan root). Kept anyway as a harmless, zero-cost addition, not a closed gap.)
    # docs/ covers this repo's own consumer-facing guides. Only emit SKIP if NONE
    # exist — an empty scan with no docs is itself a silent-skip class FB-0010 catches.
    # Build scan-target list as positional params (POSIX-portable; works in
    # both bash and zsh — bash word-splits unquoted vars but zsh does NOT, so
    # an earlier "$SCAN_TARGETS" string-join silently no-op'd under zsh and
    # reported vacuous PASS. The exact FB-0010 silent-skip class this check
    # is supposed to catch. Positional params via "$@" are portable.)
    set --
    for t in CLAUDE.md CLAUDE.md.template README.md CHANGELOG.md bootstrap.sh docs core-docs dev-docs; do
      [ -e "$t" ] && set -- "$@" "$t"
    done
    if [ $# -eq 0 ]; then
      echo "[SKIP] no project docs found to scan for slot-count consistency (looked for CLAUDE.md, CLAUDE.md.template, README.md, CHANGELOG.md, bootstrap.sh, docs/, core-docs/, dev-docs/)"
    else
      # Delegate to the shared, wrap-tolerant predicate (slot_count_scan.py) rather
      # than a line-oriented grep. A line-oriented grep is exactly what missed
      # `all 30\n  slots` wrapped across a newline inside doctor/SKILL.md's own
      # frontmatter (FB-0079) — that miss is invisible to ANY line-oriented tool,
      # so this check must run the same regex-over-full-file-text logic, not a
      # shell-native re-derivation of it that can silently diverge again.
      OUT=$(python3 "$LIB" --expected "$ACTUAL" "$@" 2>&1); RC=$?
      case "$RC" in
        0) # Extracted from a dedicated machine-parseable trailer line ("SCANNED_COUNT=N"),
           # not by word position in the human-readable sentence above it — a future rewording
           # of that sentence can't silently shift which field carries the count.
           SCANNED=$(printf '%s\n' "$OUT" | sed -n 's/^\[slot-count-scan\] SCANNED_COUNT=//p')
           case "$SCANNED" in ''|*[!0-9]*) SCANNED="an unparsed count — see raw output: $OUT" ;; esac
           echo "[PASS] documented slot count matches schema ($ACTUAL slots; scanned $SCANNED file(s) across $# path(s))" ;;
        1) echo "[WARN] documented slot count contradicts schema (schema has $ACTUAL slots; survivors below)"
           printf '%s\n' "$OUT" | sed -n 's/^\[slot-count-scan\] STALE /         /p'
           echo "       (some may be intentional historical narrative — e.g., 'schema bumped from 13 to 16')"
           echo "       Fix: update each line to '$ACTUAL slots' (grep-first-edit-second; FB-0010 discipline), OR move historical numbers behind a comment marker (# prefix) so the check ignores them." ;;
        2) echo "[SKIP] slot-count scan measured 0 files across $# path(s) — nothing to verify" ;;
        *) echo "[WARN] slot-count scan could not run (exit $RC) — treat as unchecked, not a verified clean"
           printf '%s\n' "$OUT" | sed 's/^/       /' ;;
      esac
    fi
  fi
fi
```

**Check 2.6 — roadmap/plan "current version" matches the manifest (doc-currency; SECONDARY to the ship gate)**

A manual mirror of the **automatic** doc-currency gate `/flow:ship` runs at Step 5b on every ship. The ship gate is the enforcement; this check only lets a human spot drift *between* ships — you do not rely on running doctor for currency. A FAIL means the forward-looking docs went stale.

```sh
VSRC=""
for cand in plugins/flow/.claude-plugin/plugin.json .claude-plugin/plugin.json package.json; do
  [ -f "$cand" ] && { VSRC="$cand"; break; }
done
if [ -z "$VSRC" ]; then
  echo "[Check 2.6] N/A — no versioned manifest in this project (doc-currency is version-agnostic here)."
else
  VER=$(jq -r '.version // empty' "$VSRC" 2>/dev/null)
  if [ -z "$VER" ]; then
    echo "[Check 2.6] N/A — could not read .version from $VSRC (jq missing, or no version field)."
  else
    ROADMAP=$(jq -r '.roadmapPath // "dev-docs/roadmap.md"' flow.config.json 2>/dev/null); [ -z "$ROADMAP" ] && ROADMAP=dev-docs/roadmap.md
    PLAN=$(jq -r '.planPath // "dev-docs/plan.md"' flow.config.json 2>/dev/null); [ -z "$PLAN" ] && PLAN=dev-docs/plan.md
    sect() { awk -v H="$1" 'index($0,H){f=1;next} f&&/^## /{exit} f' "$2"; }
    # Anchor on the "**Plugin at vX**" headline (mirror of ship Step 5b) so the Recently-shipped
    # enumeration can't mask a stale headline; fall back to the section when no such line exists.
    has_ver() { line=$(printf '%s\n' "$1" | grep -E '^\*\*Plugin at '); if [ -n "$line" ]; then printf '%s' "$line" | grep -qF "$VER"; else printf '%s' "$1" | grep -qF "$VER"; fi; }
    FAIL=""
    s=$(sect "## Now" "$ROADMAP"); [ -z "$s" ] && s=$(head -40 "$ROADMAP" 2>/dev/null); has_ver "$s" || FAIL="$FAIL roadmap(Now)"
    s=$(sect "## Current Focus" "$PLAN"); [ -z "$s" ] && s=$(head -40 "$PLAN" 2>/dev/null); has_ver "$s" || FAIL="$FAIL plan(CurrentFocus)"
    if [ -n "$FAIL" ]; then echo "[Check 2.6] FAIL — current version $VER ($VSRC) not on the 'Plugin at vX' line in:$FAIL. Fix: reconcile per /flow:ship Step 5a."; else echo "[Check 2.6] PASS — docs reference current version $VER."; fi
  fi
fi
```

**Fix on FAIL:** reconcile the docs (Step 5a). Normally this never fails standalone, because the ship gate (5b) blocks any ship that would leave them stale — doctor just surfaces drift early if it somehow occurred (e.g. a hand-edit outside the pipeline).

**Check 2.7 — declared status surfaces (`statusDocs`) exist and are fenced**

If the project declares `flow.config.json.statusDocs` (extra forward-looking status surfaces — e.g. a `CLAUDE.md` / `README.md` status line — reconciled every ship by `/flow:ship` Step 5a/5b), each declared path must exist and contain its marker fence pair `<!-- {marker} -->` … `<!-- /{marker} -->`. A declared-but-unfenced or missing surface is caught here at setup instead of as a hard BLOCKER at the next ship's Step 5b. This is a **bespoke** check — `statusDocs` is an array of `{path, marker}` objects, NOT a scalar path slot, so it is not part of the Check 2.4 path-existence loop.

```sh
# Resolve the shared helper (plugin-shipped under CLAUDE_PLUGIN_ROOT, or local in the flow repo).
SDHELP=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/status-docs.py" ]; then
  SDHELP="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/status-docs.py"
elif [ -f "plugins/flow/skills/ship/lib/status-docs.py" ]; then
  SDHELP="plugins/flow/skills/ship/lib/status-docs.py"
fi

if [ ! -f flow.config.json ] || ! jq -e . flow.config.json >/dev/null 2>&1; then
  : # Checks 2.1/2.2 already reported the missing/malformed config; nothing to add here.
elif [ -z "$SDHELP" ]; then
  echo "[SKIP] statusDocs check — status-docs.py helper not reachable (install the flow plugin or run from the flow repo root)"
else
  # `entries` exits non-zero + prints to stderr on a malformed statusDocs array.
  SD_ENTRIES=$(python3 "$SDHELP" entries flow.config.json 2>/tmp/flow-doctor-sd-err)
  if [ $? -ne 0 ]; then
    echo "[FAIL] statusDocs is malformed in flow.config.json"
    echo "       $(cat /tmp/flow-doctor-sd-err 2>/dev/null)"
    echo "       Fix: each statusDocs entry needs a string 'path' (and optional 'marker', default flow:status)."
  elif [ -z "$SD_ENTRIES" ]; then
    echo "[PASS] statusDocs: none declared (optional — plan/roadmap currency still enforced by the ship gate)"
  else
    # `check` prints one line per entry and exits 1 if any file is missing or unfenced.
    SD_OUT=$(python3 "$SDHELP" check flow.config.json 2>&1)
    if [ $? -eq 0 ]; then
      echo "[PASS] statusDocs: all declared surfaces exist and are fenced"
      printf '%s\n' "$SD_OUT" | sed 's/^/         /'
    else
      echo "[FAIL] statusDocs: a declared status surface is missing or unfenced"
      printf '%s\n' "$SD_OUT" | sed 's/^/         /'
      echo "       Fix: wrap the file's status region in the marker fences, e.g.:"
      echo "           <!-- flow:status -->"
      echo "           Phase 2 — HealthKit integration in progress."
      echo "           <!-- /flow:status -->"
      echo "       (Keep your existing status text between the fences — flow edits only that region.)"
      echo "       OR remove the entry from flow.config.json.statusDocs."
      echo "       (An unfenced declared surface is a hard BLOCKER at /flow:ship Step 5b.)"
    fi
  fi
  rm -f /tmp/flow-doctor-sd-err
fi
```

**Check 2.8 — lesson-contribution slots (`flowRepoPath` etc.) are coherent (FB-0059)**

The lesson-harvest loop (`/flow:ship` + `/flow:ship-spike` Step 4c enqueues flow-generalizable lessons; `/flow:contribute` drains them into a PR against the flow repo). Harvest works with no config (it falls back to user-scope defaults), but the **drain** needs `flowRepoPath` set to a real flow checkout. This check verifies the slots are coherent so a misconfigured drain fails at setup, not mid-run.

```sh
if [ ! -f flow.config.json ] || ! jq -e . flow.config.json >/dev/null 2>&1; then
  : # 2.1/2.2 already reported config problems.
else
  FRP=$(jq -r '.flowRepoPath // empty' flow.config.json)
  if [ -z "$FRP" ]; then
    echo "[PASS] flowRepoPath: unset — /flow:contribute disabled (harvest still enqueues to user-scope storage)"
  else
    FRP_EXP=$(echo "$FRP" | sed "s#^~#$HOME#")
    if [ -d "$FRP_EXP" ] && [ -f "$FRP_EXP/.claude-plugin/marketplace.json" ]; then
      echo "[PASS] flowRepoPath: $FRP is a flow checkout (.claude-plugin/marketplace.json present)"
    else
      echo "[FAIL] flowRepoPath: $FRP is not a flow checkout (no .claude-plugin/marketplace.json)"
      echo "       Fix: point flowRepoPath at your local flow repo root, or unset it to disable /flow:contribute."
    fi
  fi
  # Queue parent must be writable (defaults to ~/.claude/...; honored by the scripts + FLOW_CONTRIB_DIR env).
  QRP=$(jq -r '.contributionsQueuePath // empty' flow.config.json | sed "s#^~#$HOME#")
  [ -z "$QRP" ] && QRP="$HOME/.claude/plugins/data/flow/contributions"
  QPARENT=$(dirname "$QRP")
  if mkdir -p "$QRP" 2>/dev/null; then
    echo "[PASS] contributionsQueuePath: $QRP is writable"
  else
    echo "[WARN] contributionsQueuePath: cannot create $QRP — harvest enqueue will fail. Fix: ensure $QPARENT is writable."
  fi
  # Threshold sane (0–1) if set.
  TH=$(jq -r '.contributionThreshold // empty' flow.config.json)
  if [ -n "$TH" ] && ! awk -v th="$TH" 'BEGIN{exit !(th>=0 && th<=1)}' 2>/dev/null; then
    echo "[FAIL] contributionThreshold: $TH out of range (must be 0–1). Fix: set a value like 0.6."
  fi
fi
```

**Check 2.9 — undeclared status surfaces (`statusSurfaceCandidates`) that carry status content (setup-time opt-in nudge)**

The `statusDocs` gate (Check 2.7 + `/flow:ship` Step 5a/5b) only sees surfaces a project **declared**. But the orientation doc a fresh agent reads first (`CLAUDE.md`, `AGENTS.md`, `README.md`, …) commonly carries a forward-looking status line **nobody declared** — so it silently rots after a merge, invisible to the pipeline. `/flow:ship` Step 5a.5 catches drift at ship time via best-effort LLM judgment; this check catches the durable case **once, at setup**, so a project opts into Tier 2 auto-reconcile before the next ship's Step 5a.5 keeps nagging. **Warn-only** (consistent with doctor's other soft checks) — an undeclared candidate carrying status content is a suggestion, not a failure; the drift judgment lives in the ship pipeline, not here.

```sh
SSCAN=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/status-surface-scan.py" ]; then
  SSCAN="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/status-surface-scan.py"
elif [ -f "plugins/flow/skills/ship/lib/status-surface-scan.py" ]; then
  SSCAN="plugins/flow/skills/ship/lib/status-surface-scan.py"
fi

if [ ! -f flow.config.json ] || ! jq -e . flow.config.json >/dev/null 2>&1; then
  : # 2.1/2.2 already reported config problems.
elif [ -z "$SSCAN" ]; then
  echo "[SKIP] statusSurfaceCandidates check — status-surface-scan.py helper not reachable (install the flow plugin or run from the flow repo root)"
else
  # `candidates` prints undeclared candidate files that EXIST (exit 1 loud on a malformed config).
  CANDS=$(python3 "$SSCAN" candidates flow.config.json 2>/tmp/flow-doctor-sss-err)
  if [ $? -ne 0 ]; then
    echo "[FAIL] statusSurfaceCandidates is malformed in flow.config.json"
    echo "       $(cat /tmp/flow-doctor-sss-err 2>/dev/null)"
    echo "       Fix: statusSurfaceCandidates must be an array of non-empty path strings (or omit it for the default list)."
  elif [ -z "$CANDS" ]; then
    echo "[PASS] statusSurfaceCandidates: no undeclared orientation docs present (or all are already declared in statusDocs)"
  else
    # Of the undeclared candidates present, flag those whose slice is non-empty (carry status-looking content).
    # while-read (NOT `for c in $CANDS`): zsh does not word-split an unquoted var, so the `for` form
    # silently iterates once over the whole blob under zsh — the exact FB-0010 silent-skip class.
    WITH_STATUS=""
    while IFS= read -r c; do
      [ -z "$c" ] && continue
      if [ -n "$(python3 "$SSCAN" slice "$c" 2>/dev/null)" ]; then
        WITH_STATUS="$WITH_STATUS $c"
      fi
    done <<EOF
$CANDS
EOF
    if [ -z "$WITH_STATUS" ]; then
      echo "[PASS] statusSurfaceCandidates: undeclared docs present ($(printf '%s' "$CANDS" | tr '\n' ' ')) but none carry status-looking content"
    else
      echo "[WARN] undeclared orientation doc(s) carry status content:$WITH_STATUS"
      echo "       These auto-load into every session and will go stale after a merge (Step 5a.5 nags on drift, but only reconciles DECLARED surfaces)."
      echo "       Fix (opt into Tier 2 auto-reconcile): wrap the status region in the marker fences and declare the file, e.g.:"
      echo "           <!-- flow:status -->"
      echo "           Phase 2 — HealthKit integration in progress. ▶ Next: notifications."
      echo "           <!-- /flow:status -->"
      echo "       then add {\"path\":\"<file>\",\"marker\":\"flow:status\"} to flow.config.json.statusDocs."
      echo "       (Warn-only — leaving it undeclared is fine; Step 5a.5 still catches drift and routes it to a draft.)"
    fi
  fi
  rm -f /tmp/flow-doctor-sss-err
fi
```

**Check 2.10 — live PR body↔draft coherence for HEAD (FB-0067)**

If an **open** PR exists for the current branch, assert the coherence invariant `/flow:ship` Step 7b enforces: **a PR that is NOT a draft must not carry the `🚫 NOT READY TO MERGE` manifest.** A PR that drifted into that state between ship and merge (a blocker cleared out-of-band + a hand-edited body that silently failed) is the recurring FB-0067 bug — this check catches it at the merge gate. FAIL is actionable: reconcile the body via the ship reconcile fast-path, never a hand-edit.

```sh
# gh is required; Check 4.1 reports it missing. Guard here so this check SKIPs cleanly.
if ! command -v gh >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  echo "[SKIP] live-PR coherence — gh/jq not on PATH (see Check 4.1)"
else
  BR=$(git branch --show-current 2>/dev/null)
  # Source the shared helper (single source of truth for pr-coherence.py path resolution
  # + live-PR fetch, incl. the projectCards→REST fallback) rather than re-deriving the
  # path here — the exact fan-out contradiction FB-0010 warns against.
  VPB=""
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh" ]; then
    VPB="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh"
  elif [ -f "plugins/flow/skills/ship/lib/verify-pr-body.sh" ]; then
    VPB="plugins/flow/skills/ship/lib/verify-pr-body.sh"
  fi
  if [ -z "$BR" ]; then
    echo "[SKIP] live-PR coherence — not on a branch (detached HEAD)"
  elif [ -z "$VPB" ]; then
    echo "[SKIP] live-PR coherence — verify-pr-body.sh helper not reachable (install the flow plugin or run from the flow repo root)"
  else
    . "$VPB"
    # Discovering WHICH PR to check (by branch) is doctor's own job — the shared helper
    # only knows how to fetch a PR it's given a number for. Only OPEN PRs (a merged/
    # closed PR's body is immutable history, not a merge-gate concern).
    LIST_OUT=$(gh pr list --head "$BR" --state open --json number --limit 1 2>&1)
    LIST_RC=$?
    if [ "$LIST_RC" -ne 0 ]; then
      # A fetch FAILURE (auth/network) must never read as a silent PASS — that's the
      # exact silent-skip shape this whole PR exists to eliminate, one level up.
      echo "[WARN] live-PR coherence — could not list PRs for '$BR' (gh exit $LIST_RC); cannot confirm no-PR vs fetch-failure — treat as unchecked, not a pass"
      echo "       $LIST_OUT" | head -3 | sed 's/^/       /'
    else
      NUM=$(printf '%s' "$LIST_OUT" | jq -r '.[0].number // empty' 2>/dev/null)
      if [ -z "$NUM" ]; then
        echo "[PASS] live-PR coherence — no open PR for '$BR' (nothing to check)"
      else
        # Three-way, mirroring the provenance sibling below: rc 2 means "could not
        # verify" (e.g. a partial plugin dir where pr-coherence.py's
        # manifest_contract sibling is absent), NOT "the PR is incoherent".
        # Printing a definitive FAIL there is the false-BLOCKER the resolver guard
        # in verify-pr-body.sh exists to prevent.
        flow_assert_pr_coherent "$NUM" >/dev/null 2>&1
        COH_RC=$?
        case "$COH_RC" in
          0) echo "[PASS] live-PR coherence — PR #$NUM body↔draft state coherent" ;;
          1) echo "[FAIL] live-PR coherence — PR #$NUM is NOT a draft but its body still carries the not-ready sentinel"
             echo "       This PR would merge looking not-ready. Do NOT hand-edit the body (that is the silent-write path that caused this)."
             echo "       Fix: run the /flow:ship reconcile fast-path (Step 7c) to re-render the body + reconcile draft state from the current gate." ;;
          *) echo "[WARN] live-PR coherence — could not verify PR #$NUM (checker exit $COH_RC); treat as UNCHECKED, not a pass"
             echo "       Usual cause: a partial/stale plugin dir (pr-coherence.py present, manifest_contract.py missing). Reinstall the plugin." ;;
        esac
      fi
      # FB-0074 — same re-fetch, second invariant. Ship asserts Test-plan provenance at
      # 7b, but a body hand-edited AFTER ship is never caught there; that is exactly why
      # the FB-0067 coherence invariant is checked here and in /flow:land as well as at
      # ship. Checking one at three points and its sibling at one was an incomplete
      # fan-out, not a design choice.
      if [ -n "$NUM" ]; then
        flow_assert_test_plan_provenance "$NUM" >/dev/null 2>&1; TPRC=$?
        case "$TPRC" in
          0) echo "[PASS] live-PR Test-plan provenance — PR #$NUM's Test plan matches the renderer's stamp + digest" ;;
          1) echo "[FAIL] live-PR Test-plan provenance — PR #$NUM's Test plan was hand-authored or its checkboxes were edited after rendering"
             echo "       Its boxes are self-assertion, not machine verdicts. Fix: re-render via /flow:ship Step 7c and re-publish." ;;
          *) echo "[WARN] live-PR Test-plan provenance — could not verify for PR #$NUM (gh/checker unavailable) — unchecked, not clean" ;;
        esac
      fi
    fi
  fi
fi
```

**Check 2.11 — `role` slot resolution (D1 prototype-first trigger dependency, FB-0081 Phase 0)**

Reports the resolved `role` slot so a human can confirm it's set (or intentionally unset) without opening `flow.config.json`. This slot has no consumer yet (Phase 0 only — see `dev-docs/handoffs/d1-prototype-first-gate.md`); this check is informational, never a FAIL. A value outside the enum is warned, not silently accepted, since nothing enforces the schema's enum at runtime — a plain `jq` read of a typo'd value would otherwise report as if it resolved cleanly.

```sh
if ! command -v jq >/dev/null 2>&1; then
  echo "[SKIP] role slot resolution — jq not on PATH (see Check 4.1); cannot read flow.config.json."
elif [ ! -f flow.config.json ]; then
  echo "[PASS] role unset — classic plan gate (no flow.config.json; see Check 2.1)"
elif jq -e . flow.config.json >/dev/null 2>&1; then
  ROLE=$(jq -r '.role // empty' flow.config.json)
  case "$ROLE" in
    "") echo "[PASS] role unset — classic plan gate (no role-based behavior active yet)" ;;
    designer|engineer) echo "[PASS] role: $ROLE (informational only — no flow skill reads this yet)" ;;
    *) echo "[WARN] role: \"$ROLE\" is not a recognized value (expected 'designer' or 'engineer')"
       echo "       Fix: set flow.config.json's \"role\" to 'designer' or 'engineer', or unset it for classic behavior." ;;
  esac
fi
# else: flow.config.json exists but doesn't parse — Check 2.2 already reports this FAIL;
# no duplicate/conflicting message here (same silent-defer convention as Checks 2.3/2.4).
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

Plugin-shipped rules ship as path-activated skills at `${CLAUDE_PLUGIN_ROOT}/skills/{general,plan-discipline,documentation,exploration}/SKILL.md` (`paths:` frontmatter + `user-invocable: false`) and auto-load on path matches when `flow@flow` is enabled. This check asks the loader itself, not disk presence or an inferred pass from Section 1 — a component can be present on disk and still not be what the running Claude Code actually reports (FB-0085: this exact gap is why the 4 rules never loaded for any consumer despite always being on disk).

```sh
if ! command -v claude >/dev/null 2>&1; then
  echo "[SKIP] plugin-shipped rule-skills check — 'claude' CLI not on PATH; cannot query the loader"
else
  DETAILS_RAW=$(claude plugin details flow@flow 2>&1)
  DETAILS_RC=$?
  DETAILS_OUT=$(printf '%s' "$DETAILS_RAW" | tr -d '\000-\010\013\014\016-\037')
  SKILLS_LINE=$(echo "$DETAILS_OUT" | grep -E "^[[:space:]]*Skills \(")
  if [ -z "$SKILLS_LINE" ] && [ "$DETAILS_RC" -ne 0 ]; then
    echo "[WARN] plugin-shipped rule-skills check — 'claude plugin details flow@flow' errored (exit $DETAILS_RC): $DETAILS_OUT"
  elif [ -z "$SKILLS_LINE" ]; then
    echo "[SKIP] plugin-shipped rule-skills check — 'claude plugin details flow@flow' returned no Skills line (is flow@flow installed?)"
  else
    MISSING=""
    for s in general plan-discipline documentation exploration; do
      echo "$SKILLS_LINE" | grep -qE "(^|[, ])$s(,|$| )" || MISSING="$MISSING $s"
    done
    if [ -z "$MISSING" ]; then
      echo "[PASS] plugin-shipped rule-skills (general/plan-discipline/documentation/exploration) reported by the loader"
    else
      echo "[FAIL] plugin-shipped rule-skills missing from the loader's own report:$MISSING"
      echo "       Fix: /plugin marketplace update flow && /plugin install flow@flow"
    fi
  fi
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

**Check 5.3 — project run skill (prerequisite for `/flow:verify-build`)**

`/flow:verify-build` wraps bundled `/verify` + `/run`. Both work best with a per-project launch recipe scaffolded by Anthropic's bundled `/run-skill-generator` at `.claude/skills/run-<name>/`. Without it, heuristic launch may fail on non-trivial projects.

```sh
# Gate on verifyEnabled: if disabled, skip the check entirely.
VERIFY_ENABLED="true"
if [ -f flow.config.json ] && jq -e . flow.config.json >/dev/null 2>&1; then
  # NOT `.verifyEnabled // true` — jq's `//` treats boolean false as empty, so an
  # explicit `verifyEnabled: false` would resolve to true and the skip below never fires.
  VERIFY_ENABLED=$(jq -r 'if .verifyEnabled == false then "false" else "true" end' flow.config.json)
fi

if [ "$VERIFY_ENABLED" = "false" ]; then
  echo "[SKIP] project run skill — flow.config.json.verifyEnabled=false; /flow:verify-build disabled"
else
  # Use shell glob expansion via nullglob-ish guard for portability.
  RUN_SKILLS=$(ls -d .claude/skills/run-*/ 2>/dev/null)
  if [ -n "$RUN_SKILLS" ]; then
    FIRST=$(echo "$RUN_SKILLS" | head -n1)
    echo "[PASS] project run skill present at $FIRST"
    echo "       Powers /flow:verify-build via bundled /run + /verify."
  else
    echo "[WARN] no .claude/skills/run-*/ found — /flow:verify-build will rely on heuristic launch"
    echo "       Fix: run /run-skill-generator (Anthropic bundled skill) to scaffold a per-project"
    echo "       launch recipe. Required for non-trivial projects (env files, DBs, multi-step builds,"
    echo "       non-standard scheme/package selection). Optional for simple Vite/CLI/Next-style apps."
    echo "       Set flow.config.json.verifyEnabled=false to opt out of verify-build entirely."
  fi
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
