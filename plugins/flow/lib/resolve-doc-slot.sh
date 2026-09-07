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
# CONTRACT -- one resolution line on stdout, one of six forms:
#
#   FILE <path> (N lines)
#   DIR <path> (N entries) - read with: cat <path>/<glob>
#   DIR <path> (scaffolded, 0 entries yet) - ...
#   ⚠️ EMPTY ...     (a directory with no entries AND no README -- nobody scaffolded it)
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
    printf 'DIR %s (scaffolded, 0 entries yet) - nothing has been written here yet\n' "$P"
  else
    # Neither entries nor a README: nobody scaffolded this and nothing wrote to it.
    # That is a real fault -- a wrong slot, or a migration that did not finish -- and
    # it is now distinguishable from the scaffolded case above, so this message can
    # name a cause instead of hedging between two.
    printf '%s EMPTY: %s is a directory with 0 %s entries and no README.md, so nothing scaffolded it and this run has NO %s context. Do NOT read that as "the project has no %s" -- the slot is probably wrong, or a migration did not finish.\n' \
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
