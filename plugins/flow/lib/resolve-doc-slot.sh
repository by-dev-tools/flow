#!/bin/sh
# resolve-doc-slot.sh -- the ONE way a flow surface resolves a doc-path config slot.
#
# WHY THIS EXISTS (FB-0100/FB-0101). Every doc-slot reader used to inline its own
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
# CONTRACT -- exactly one line on stdout, one of five forms:
#
#   FILE <path> (N lines)
#   DIR <path> (N entries) - read with: cat <path>/<glob>
#   WARN-EMPTY  ... with a leading warning marker
#   WARN-MISSING ... with a leading warning marker
#   (no <slot> doc at <path> - unset slot, default path; project may have none)
#
# The last form is the ONLY quiet one, and it is quiet because it is the only
# genuinely ambiguous case: an UNSET slot resolving to a default path that does not
# exist really is indistinguishable from "this project has none". An explicitly SET
# slot that resolves to nothing is never quiet again.
#
# Exit status is always 0 -- this resolves context for a reader, it does not gate.
# The loudness is in the text, which is what lands in the model's context.
#
# Usage: resolve-doc-slot.sh <slotName> <defaultPath> [entryGlob]

set -u

SLOT="${1:?usage: resolve-doc-slot.sh <slotName> <defaultPath> [entryGlob]}"
DEFAULT="${2:?usage: resolve-doc-slot.sh <slotName> <defaultPath> [entryGlob]}"
GLOB="${3:-*.md}"

WARN='⚠️'

# `jq` absent is not the same as "slot unset" -- say so rather than silently taking
# the default, which would mask a broken host as a configuration choice (FB-0009).
if ! command -v jq >/dev/null 2>&1; then
  printf '%s jq is not on PATH, so flow.config.json.%s was NOT read. Falling back to "%s". If this project configures %s elsewhere, this reader is looking in the wrong place.\n' \
    "$WARN" "$SLOT" "$DEFAULT" "$SLOT"
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
    printf 'DIR %s (%s entries) - read with: cat %s/%s\n' "$P" "$N" "$P" "$GLOB"
  else
    # EMPTY is a distinct state from MISSING, but it is genuinely AMBIGUOUS and this
    # message must not pretend otherwise: a freshly bootstrapped project has an empty
    # doc directory and that is correct, while an empty one in a repo with shipped
    # history means the slot is wrong or a migration failed. Naming a single cause
    # here would be a confident wrong diagnosis on whichever project it guessed
    # against -- and the first version of this script did exactly that, WARNing on a
    # correctly-scaffolded new project (caught by dogfooding bootstrap.sh).
    #
    # What is NOT ambiguous, and is the whole point, is the consequence: this run has
    # no context from this slot, and that must not be read as "there are no rules".
    printf '%s EMPTY: %s is a directory with 0 %s entries, so this run has NO %s context. Do NOT read that as "the project has no %s". Expected on a newly bootstrapped project; on a project with shipped work it means the slot is wrong or a migration did not finish.\n' \
      "$WARN" "$P" "$SLOT" "$SLOT" "$SLOT"
  fi
elif [ -f "$P" ]; then
  L=$(wc -l < "$P" 2>/dev/null | tr -d ' ')
  printf 'FILE %s (%s lines)\n' "$P" "${L:-0}"
elif [ "$SET" = true ]; then
  # The project explicitly named this path. Its absence is a configuration failure,
  # never an empty set -- CLAUDE.md: "Never silently no-op on a missing slot."
  printf '%s MISSING: flow.config.json sets %s to "%s", which resolves to neither a file nor a directory. This run has NO %s context. Fix the slot or create the doc -- do NOT read this as "the project has no %s".\n' \
    "$WARN" "$SLOT" "$P" "$SLOT" "$SLOT"
else
  printf '(no %s doc at %s - slot unset, default path; this project may legitimately have none)\n' "$SLOT" "$P"
fi
