#!/usr/bin/env bash
# flow bootstrap — one-command project scaffolding.
#
# Usage:
#   bash bootstrap.sh --stack <web|swift|tauri-rust-ts> [--project <name>] [--flow-dir <path>]
#
#   --stack:     required. one of web | swift | tauri-rust-ts.
#   --project:   optional. project name for placeholder fill. defaults to basename of cwd.
#   --flow-dir:  optional. path to a local flow checkout. defaults to the parent of this script
#                (i.e. you ran it from a flow checkout). If you fetched bootstrap.sh standalone
#                via curl, pass --flow-dir explicitly or set FLOW_DIR env.
#
# What this does:
#   1. Copies template/base/* into your project (cp -n — never overwrites).
#   2. Overlays template/stacks/<stack>/* (cp -Rn).
#   3. Strips $comment-* keys from the flow.config.json example so it parses cleanly.
#   4. Prints a "next steps" punch list — fill placeholders, then run /flow:doctor.
#
# What this does NOT do:
#   - Auto-fill placeholders ({{PROJECT_NAME}}, {{ONE_LINE_DESCRIPTION}}, {{SAFETY_PATH_*}},
#     etc.). Those are judgment calls the adopter makes by editing CLAUDE.md / README.md /
#     .claude/rules/safety.md directly. Filling them by hand is part of the onboarding moment.
#   - Install the flow plugin. That's a Claude Code action — run
#     `/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow` in a Claude session.
#   - Initialize git, npm, etc. Do those per your stack's own onboarding.
#
# Idempotent: re-running on a project where some files exist will skip those (cp -n).
# To overwrite intentionally, edit the file directly or rm first.

set -eu
# -e: exit on real errors (cp permission-denied, missing source, jq failure).
#     cp -n returns 0 on skip, so idempotency is preserved.
# -u: catch unset variables.
TAG="[flow-bootstrap]"

# --- arg parse ---------------------------------------------------------------
STACK=""
PROJECT="$(basename "$(pwd)")"
FLOW_DIR="${FLOW_DIR:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --stack)     STACK="$2"; shift 2 ;;
    --project)   PROJECT="$2"; shift 2 ;;
    --flow-dir)  FLOW_DIR="$2"; shift 2 ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "$TAG unknown arg: $1" >&2
      echo "       run with --help for usage" >&2
      exit 2
      ;;
  esac
done

# --- validate stack ----------------------------------------------------------
case "$STACK" in
  web|swift|tauri-rust-ts) ;;
  "")
    echo "$TAG ⚠️ --stack is required (one of: web | swift | tauri-rust-ts)" >&2
    echo "       run with --help for usage" >&2
    exit 2
    ;;
  *)
    echo "$TAG ⚠️ unknown stack: '$STACK' (must be one of: web | swift | tauri-rust-ts)" >&2
    exit 2
    ;;
esac

# --- locate flow checkout ----------------------------------------------------
if [ -z "$FLOW_DIR" ]; then
  # Default: assume this script lives at <flow-root>/template/base/bootstrap.sh
  FLOW_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
fi

if [ ! -d "$FLOW_DIR/template/base" ]; then
  echo "$TAG ⚠️ FLOW_DIR does not look like a flow checkout: $FLOW_DIR" >&2
  echo "       expected $FLOW_DIR/template/base/ to exist." >&2
  echo "       Either run from inside a flow checkout, or pass --flow-dir <path>." >&2
  exit 2
fi

if [ ! -d "$FLOW_DIR/template/stacks/$STACK" ]; then
  echo "$TAG ⚠️ stack overlay missing: $FLOW_DIR/template/stacks/$STACK" >&2
  exit 2
fi

# --- prereq checks (warn, don't block — same shape as /flow:doctor) ----------
MISSING=""
command -v jq  >/dev/null 2>&1 || MISSING="$MISSING jq"
command -v git >/dev/null 2>&1 || MISSING="$MISSING git"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "$TAG ⚠️ missing required CLI tools:$MISSING" >&2
  echo "       Install before continuing — these are required by flow at runtime:" >&2
  echo "         macOS:        brew install$MISSING" >&2
  echo "         Debian/Ubuntu: apt install$MISSING" >&2
  echo "       jq is also required for the flow.config.json comment strip below." >&2
  exit 2
fi

# --- begin scaffold ----------------------------------------------------------
PROJECT_ROOT="$(pwd)"
echo "$TAG bootstrapping flow scaffold:"
echo "         project root:  $PROJECT_ROOT"
echo "         project name:  $PROJECT"
echo "         stack:         $STACK"
echo "         flow checkout: $FLOW_DIR"
echo ""

# --- Step A: template/base/ files (with cp -n — never overwrites) -----------
echo "$TAG Step A: copying template/base/ scaffolding..."
mkdir -p "$PROJECT_ROOT/.claude/rules" "$PROJECT_ROOT/core-docs"

copied=0
skipped=0
copy_n() {
  src="$1"; dest="$2"
  if [ -e "$dest" ]; then
    echo "         · skip (exists): ${dest#"$PROJECT_ROOT/"}"
    skipped=$((skipped+1))
  else
    cp "$src" "$dest"
    echo "         · copy:          ${dest#"$PROJECT_ROOT/"}"
    copied=$((copied+1))
  fi
}

copy_n "$FLOW_DIR/template/base/CLAUDE.md.template"                       "$PROJECT_ROOT/CLAUDE.md"
copy_n "$FLOW_DIR/template/base/README.md.template"                       "$PROJECT_ROOT/README.md"
copy_n "$FLOW_DIR/template/base/.gitignore.template"                      "$PROJECT_ROOT/.gitignore"
copy_n "$FLOW_DIR/template/base/.claude/settings.json.example"            "$PROJECT_ROOT/.claude/settings.json"
copy_n "$FLOW_DIR/template/base/.claude/rules/safety.md.template"         "$PROJECT_ROOT/.claude/rules/safety.md"
for f in "$FLOW_DIR/template/base/core-docs/"*.md; do
  copy_n "$f" "$PROJECT_ROOT/core-docs/$(basename "$f")"
done

# --- Step B: flow.config.json from example, with $comment-* keys stripped ---
echo ""
echo "$TAG Step B: generating flow.config.json (strips \$comment-* keys from example)..."
if [ -e "$PROJECT_ROOT/flow.config.json" ]; then
  echo "         · skip (exists): flow.config.json"
  skipped=$((skipped+1))
else
  # jq filter: drop any top-level key starting with $comment-
  jq 'with_entries(select(.key | startswith("$comment") | not))' \
    "$FLOW_DIR/template/base/flow.config.json.example" \
    > "$PROJECT_ROOT/flow.config.json"
  echo "         · created:       flow.config.json (clean JSON, 14 slots)"
  copied=$((copied+1))
fi

# --- Step C: stack overlay ---------------------------------------------------
echo ""
echo "$TAG Step C: overlaying template/stacks/$STACK/..."
mkdir -p "$PROJECT_ROOT/tools" "$PROJECT_ROOT/.github/workflows"

# Overlay each tree per-file via copy_n. We can't use `cp -Rn dir/. dest/` because
# BSD cp (macOS default) returns exit 1 when dest files exist — incompatible with
# `set -e`. Per-file copy_n is idempotent + portable + reports cleanly.
copy_tree() {
  src_root="$1"; dest_root="$2"
  if [ ! -d "$src_root" ]; then return 0; fi
  # find every regular file under src_root, compute its dest path, copy_n each.
  while IFS= read -r src_file; do
    rel="${src_file#"$src_root/"}"
    dest_file="$dest_root/$rel"
    mkdir -p "$(dirname "$dest_file")"
    copy_n "$src_file" "$dest_file"
  done < <(find "$src_root" -type f)
}

# Overlay .claude/ (web + tauri have skills/link, rules/ui+dev-server; swift only has .append)
if [ -d "$FLOW_DIR/template/stacks/$STACK/.claude" ]; then
  copy_tree "$FLOW_DIR/template/stacks/$STACK/.claude" "$PROJECT_ROOT/.claude"
fi

# Overlay tools/ (all 3 stacks have preflight)
if [ -d "$FLOW_DIR/template/stacks/$STACK/tools" ]; then
  copy_tree "$FLOW_DIR/template/stacks/$STACK/tools" "$PROJECT_ROOT/tools"
  # Preflight scripts must be executable. Don't swallow real chmod failures —
  # if find finds zero matches, find returns 0 with no exec; if chmod fails on
  # a real file (permission issue), `set -e` catches it so the consumer notices
  # at scaffold time rather than at first /flow:ship.
  if [ -d "$PROJECT_ROOT/tools/preflight" ]; then
    find "$PROJECT_ROOT/tools/preflight" -type f \( -name "*.sh" -o -name "*.mjs" \) -exec chmod +x {} \;
  fi
fi

# Overlay .github/
if [ -d "$FLOW_DIR/template/stacks/$STACK/.github" ]; then
  copy_tree "$FLOW_DIR/template/stacks/$STACK/.github" "$PROJECT_ROOT/.github"
fi

# Append stack-specific .gitignore entries (idempotent via marker check)
APPEND="$FLOW_DIR/template/stacks/$STACK/.gitignore.append"
if [ -f "$APPEND" ]; then
  MARKER="# flow-stack-$STACK additions"
  if grep -qF "$MARKER" "$PROJECT_ROOT/.gitignore" 2>/dev/null; then
    echo "         · skip .gitignore append (already present, marker found)"
    skipped=$((skipped+1))
  else
    {
      echo ""
      echo "$MARKER"
      cat "$APPEND"
    } >> "$PROJECT_ROOT/.gitignore"
    echo "         · appended .gitignore entries (marker: $MARKER)"
    copied=$((copied+1))
  fi
fi

# Swift-only: append safety.md additions (idempotent via marker)
if [ "$STACK" = "swift" ] && [ -f "$FLOW_DIR/template/stacks/swift/.claude/rules/safety.md.append" ]; then
  SAFETY_MARKER="## Swift-stack additions"
  if grep -qF "$SAFETY_MARKER" "$PROJECT_ROOT/.claude/rules/safety.md" 2>/dev/null; then
    echo "         · skip safety.md append (already present, marker found)"
  else
    {
      echo ""
      cat "$FLOW_DIR/template/stacks/swift/.claude/rules/safety.md.append"
    } >> "$PROJECT_ROOT/.claude/rules/safety.md"
    echo "         · appended safety.md (marker: $SAFETY_MARKER)"
  fi
fi

# --- summary + next steps ----------------------------------------------------
echo ""
echo "$TAG scaffold complete: $copied file(s) created, $skipped skipped."
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "Next steps (manual — these require your judgment):"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "  1. Fill placeholders in CLAUDE.md + README.md + .claude/rules/safety.md:"
echo "       grep -rEn '\\{\\{[A-Z_]+\\}\\}' CLAUDE.md README.md .claude/rules/safety.md"
echo "     Each {{NAME}} should be replaced with a project-specific value."
echo "     (See the placeholder table in docs/bootstrap.md Step 4 if uncertain.)"
echo ""
echo "  2. Verify the flow.config.json slot values match your project:"
echo "       cat flow.config.json"
echo "     Especially typecheckCmd, defaultBranch, and the paths block."
echo ""
echo "  3. Install the flow plugin in Claude Code (one-time per machine):"
echo "       /plugin marketplace add by-dev-tools/flow"
echo "       /plugin install flow@flow"
echo ""
echo "  4. Verify the setup end-to-end:"
echo "       (in a Claude Code session in this project)"
echo "       /flow:doctor"
echo "     All checks should pass. If any fail, the output names the fix."
echo ""
echo "  5. Try your first PR using the loop:"
echo "       cat $FLOW_DIR/docs/first-pr.md   (or fetch from by-dev-tools/flow)"
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
exit 0
