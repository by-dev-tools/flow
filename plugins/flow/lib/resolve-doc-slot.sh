#!/bin/sh
# resolve-doc-slot.sh -- the ONE way a flow surface resolves a doc-path config slot.
#
# WHY THIS EXISTS (FB-0101/FB-0102). Every doc-slot reader used to inline its own
# `[ -f "$X" ] && echo "$X" || echo "(no ... doc at $X)"`. Three properties made that
# a latent bug factory:
#
#   1. `[ -f ]` is FALSE on a directory. The moment a slot points at a fragmented
#      doc directory, the reader reports "(no doc)" and runs context-blind.
#   2. The fallback was SILENT. "(no feedback doc at X)" reads identically whether
#      the project legitimately has none or the slot is misconfigured -- so a
#      misconfiguration is indistinguishable from an empty set. That is exactly
#      FB-0082: /flow:critique-plan went document-blind when `referenceGlob` matched
#      nothing, and nobody noticed because a clean-looking verdict came back.
#   3. It was duplicated per-site, so fixing one site fixed one site.
#
# `.claude/rules/general.md` (Consistency discipline, item 1) requires every
# `|| echo "(no ...)"` fallback to be paired with a loud [WARN] branch. This script
# is that pairing, hoisted to one place so it cannot drift.
#
# CONTRACT -- one resolution line on stdout, one of SEVEN forms:
#
#   FILE <path> (N lines)
#   DIR <path> (N entries) - read with: cat <path>/<glob>
#   DIR <path> (scaffolded, 0 entries yet) - ...
#   ⚠️ EMPTY ...     (a directory with no entries AND no README -- nobody scaffolded it,
#                     OR a SET slot pointing at a zero-byte file -- probably truncated)
#   ⚠️ MISSING ...   (slot explicitly SET, resolves to nothing)
#   (no <slot> doc at <path> - unset slot, default path; project may have none)
#
# When `jq` is absent an additional warning line is printed BEFORE the resolution
# line, so callers must tolerate a leading notice rather than assuming exactly one
# line. (Stated because an earlier version of this header promised exactly one line
# while the jq branch already emitted two.)
#
# Two forms are quiet, and only these two: the unset-slot default, and the
# scaffolded-but-empty directory. Both are quiet for the same reason -- "no entries"
# is genuinely what "nothing has shipped yet" looks like, so warning there would fire
# on correct installs. An explicitly SET slot that resolves to nothing is never quiet.
#
# Exit status is always 0 -- this resolves context for a reader, it does not gate.
# The loudness is in the text, which is what lands in the model's context.
#
# SECURITY -- how callers must resolve THIS script. Every caller does:
#
#   R="${CLAUDE_PLUGIN_ROOT}/lib/resolve-doc-slot.sh"
#   [ -f "$R" ] || { <flow-checkout marker> && R=plugins/flow/lib/resolve-doc-slot.sh; }
#
# The second tier is a path relative to the WORKING DIRECTORY, i.e. to the repository
# under review. Ungated, a caller would `sh` a file that repository controls whenever
# CLAUDE_PLUGIN_ROOT is unset or the install predates this file -- and `sh <file>` ignores
# the exec bit, so a hostile repo need only commit plain text there. That is outside the
# flow.config.json trust boundary (which is repo-local and knowingly trusted); this is a
# repo the developer explicitly does NOT trust, which is why they pointed a reviewer at it.
#
# So the cwd tier is gated on the working tree actually BEING the flow checkout (a
# plugin.json naming "flow"). Consumers never take that tier; flow's own dogfooding still
# does. A caller that finds neither tier must print its loud not-found branch -- silently
# degrading to repo-supplied code is strictly worse than the loud branch.
# `run_doc_slot_resolution_evals.py` pins the gate at every call site.
#
# Usage: resolve-doc-slot.sh <slotName> <defaultPath> [entryGlob]

set -u

SLOT="${1:?usage: resolve-doc-slot.sh <slotName> <defaultPath> [entryGlob]}"
DEFAULT="${2:?usage: resolve-doc-slot.sh <slotName> <defaultPath> [entryGlob]}"
GLOB="${3:-*.md}"

# Match the repo's helper-output convention: every shared lib prefixes its warnings
# with its own name (`[verify-pr-body]`, `[status-docs]`, `[manifest-triage]`, ...) so a
# reader can tell WHICH component is complaining. This one fans out to 11 preludes.
WARN='⚠️ [resolve-doc-slot]'

# `jq` absent is not the same as "slot unset" -- say so rather than silently taking
# the default, which would mask a broken host as a configuration choice (FB-0009).
if ! command -v jq >/dev/null 2>&1; then
  printf '%s jq is not on PATH, so flow.config.json.%s was NOT read. Falling back to "%s". If this project configures %s elsewhere, this reader is looking in the wrong place.\n' \
    "$WARN" "$SLOT" "$DEFAULT" "$SLOT"
  P="$DEFAULT"
  SET=false
elif [ ! -f flow.config.json ]; then
  # No config at all. Not necessarily wrong (a project may run flow unconfigured), but
  # it must not be reported as "the slot is unset" -- that phrasing implies a config was
  # read and this key was absent from it.
  printf '%s no flow.config.json in %s, so no slot could be read. Falling back to "%s".\n' \
    "$WARN" "$(pwd)" "$DEFAULT"
  P="$DEFAULT"
  SET=false
elif ! jq -e . flow.config.json >/dev/null 2>&1; then
  # Malformed JSON is the dangerous one: `jq -r ... 2>/dev/null || true` swallows the
  # parse error, P comes back empty, and the quiet unset-slot line then tells the reader
  # the project "may legitimately have none" -- a reassuring sentence over a broken
  # config. Fail loud instead.
  printf '%s flow.config.json is present but does NOT parse as JSON, so NO slot could be read and every path below is a guess. Falling back to "%s" for %s. Fix the config first.\n' \
    "$WARN" "$DEFAULT" "$SLOT"
  P="$DEFAULT"
  SET=false
else
  P=$(jq -r ".${SLOT} // empty" flow.config.json 2>/dev/null || true)
  if [ -n "$P" ]; then SET=true; else SET=false; P="$DEFAULT"; fi
fi

if [ -d "$P" ]; then
  # Fragmented (one-file-per-entry) form. Count real entries -- a README or a
  # leading-underscore helper is not an entry.
  N=$(find "$P" -maxdepth 1 -type f -name "$GLOB" \
        ! -name 'README.md' ! -name '_*' 2>/dev/null | wc -l | tr -d ' ')
  if [ "${N:-0}" -gt 0 ]; then
    # `ls -v` (version sort) when the entries are version-named, else `ls -r` for
    # newest-first: a date-prefixed directory sorts oldest-first, and a version-named
    # one sorts v1.10.0 before v1.9.0. Both would mislead a reader following the hint.
    case "$GLOB" in
      v*) BROWSE="ls -v $P" ;;
      *)  BROWSE="ls -r $P" ;;
    esac
    printf 'DIR %s (%s entries, one file per entry) - browse: %s | select: grep -rl <topic> %s | all %s: cat %s/%s\n' \
      "$P" "$N" "$BROWSE" "$P" "$N" "$P" "$GLOB"
  elif [ -f "$P/README.md" ]; then
    # SCAFFOLDED: a doc directory holding only its README is exactly what bootstrap.sh
    # creates, so this is the CORRECT state on day one of every new project -- not a
    # fault. Quiet for the same reason the unset-slot case is quiet: "no entries yet"
    # really is indistinguishable from "nothing has shipped yet", because that is what
    # it means.
    #
    # The README is a disambiguator, not a heuristic: bootstrap.sh always writes it, so
    # its presence means someone set this directory up deliberately. /flow:doctor Check
    # 2.4 gets this same answer by CALLING this script. An earlier cut instead softened
    # the warning text here and put a README carve-out only in doctor, so one identical
    # on-disk state produced [PASS] there and a warning in every reviewer prelude -- two
    # copies of one predicate, disagreeing. A warning that fires on 100% of correct
    # installs also teaches readers to ignore warnings, which costs more than it saves.
    printf 'DIR %s (scaffolded, no entries yet) - the correct state for a new project, not a misconfiguration\n' "$P"
  else
    # Neither entries nor a README: nobody scaffolded this and nothing wrote to it.
    # That is a real fault -- a wrong slot, or a migration that did not finish -- and
    # it is now distinguishable from the scaffolded case above, so this message can
    # name a cause instead of hedging between two.
    printf '%s EMPTY: %s is a directory with 0 entries and no README.md, so nothing scaffolded it and this run has NO %s context. Do NOT read that as "the project has no such doc" -- flow.config.json.%s is probably wrong, or a migration did not finish.\n' \
      "$WARN" "$P" "$SLOT" "$SLOT"
  fi
elif [ -f "$P" ]; then
  L=$(wc -l < "$P" 2>/dev/null | tr -d ' ')
  if [ -s "$P" ]; then
    printf 'FILE %s (%s lines)\n' "$P" "${L:-0}"
  elif [ "$SET" = true ]; then
    printf '%s EMPTY: flow.config.json sets %s to "%s", which exists but is a ZERO-BYTE file, so this run has NO %s context. Do NOT read that as "the project has no such doc" -- a merge or a migration probably truncated it.\n' \
      "$WARN" "$SLOT" "$P" "$SLOT"
  else
    # Unset slot + an empty file at the default path: same genuine ambiguity as the
    # unset-and-absent case below, so it stays quiet for the same reason.
    printf '(no %s doc at %s - the default path exists but is empty; this project may legitimately have none)\n' "$SLOT" "$P"
  fi
elif [ "$SET" = true ]; then
  # The project explicitly named this path. Its absence is a configuration failure,
  # never an empty set -- CLAUDE.md: "Never silently no-op on a missing slot."
  printf '%s MISSING: flow.config.json sets %s to "%s", which resolves to neither a file nor a directory. This run has NO %s context. Fix the slot or create the doc -- do NOT read this as "the project has no %s".\n' \
    "$WARN" "$SLOT" "$P" "$SLOT" "$SLOT"
else
  printf '(no %s doc at %s - slot unset, default path; this project may legitimately have none)\n' "$SLOT" "$P"
fi
