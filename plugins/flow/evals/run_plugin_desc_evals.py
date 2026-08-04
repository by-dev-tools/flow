#!/usr/bin/env python3
"""Eval harness for the install-surface plugin/marketplace descriptions (FB-0078).

The bug it pins: `description` in `plugins/flow/.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json` is the text Claude Code renders in the `/plugin`
terminal UI. Every version bump had been APPENDING its release blurb to that field
instead of to `CHANGELOG.md`, so by v1.25.0 the plugin description was 27,711
characters — a full reverse-chronological changelog rendered as one wall of prose
in a pane sized for a paragraph. Nothing checked it, because a description that is
too long is still valid JSON and still installs.

(Named `plugin_desc` rather than `manifest_desc` because "manifest" already means
the NOT-READY PR manifest in this repo — see `run_manifest_triage_evals.py` and
`skills/ship/lib/manifest_contract.py`. Different thing entirely.)

What is pinned, over EVERY description field in both manifests:

  length   — a hard cap per field. This is the actual defect; everything else here
             is the fan-out around it.
  no-vers  — no version token. The append-a-blurb habit ALWAYS opened with one
             ("v1.21.0 adds …"), so banning the token catches the regrowth at its
             first sentence rather than at 27KB. Release notes belong in
             CHANGELOG.md; the description says what the plugin IS.
  parity   — plugin.json and the matching marketplace entry carry the SAME
             description (two copies of one contract — the FB-0010 fan-out class).
  no-list  — the description does NOT enumerate the plugin's skills. Claude Code
             already renders that inventory itself, from disk, in two places: the
             Discover tab's "Will install" section and the Installed tab's detail
             view (also `claude plugin details`). A hand-maintained copy in the
             description is redundant AND can go stale in a way the generated one
             cannot. Capability words, not a command catalog.
  version  — the version fields across the two manifests agree.
  frontmatter — the same no-version-token rule over every shipped skill's
             frontmatter `description:`. FB-0078's rule names the whole class
             ("any consumer-visible string flow writes but never reads back
             rendered"); measuring that class once in a history entry is the
             decaying-claim shape the rule itself warns about. Ships green today.
             Deliberately NOT a length cap — length is functional in trigger text,
             which is prompt input, not display copy — and deliberately NOT applied
             to SKILL.md bodies, which cite versions legitimately.

Calibration for the caps: measured against Anthropic's own official marketplace
(anthropics/claude-plugins-official, 276 plugins) — median description 176 chars,
p90 312, max 665, only 6 over 500, exactly 1 containing a version token. The docs
call the field a "Brief plugin description". MAX_PLUGIN_DESC sits above that p90;
MAX_MARKETPLACE_DESC is deliberately BELOW it, because the marketplace-level field
is a different population (one line on a tab listing marketplaces, not plugins) and
the p90 above does not describe it.

Stdlib only. Run:
    python3 plugins/flow/evals/run_plugin_desc_evals.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
PLUGIN_ROOT = HERE.parent                      # plugins/flow
ROOT = PLUGIN_ROOT.parent.parent               # repo root
PLUGIN_JSON = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SKILLS_DIR = PLUGIN_ROOT / "skills"
AGENTS_DIR = PLUGIN_ROOT / "agents"
CI = ROOT / ".github" / "workflows" / "ci.yml"
SELF = Path(__file__).name

# Caps, not targets — set so an ordinary rewording never trips the gate and an
# accreting changelog always does. See the docstring for why the two differ.
MAX_PLUGIN_DESC = 400
MAX_MARKETPLACE_DESC = 200

# A description naming a couple of skills in prose is fine; one naming a dozen is a
# catalog, and the catalog is the UI's job.
MAX_SKILL_MENTIONS = 2

# A `v`-prefixed decimal is never ordinary prose; a bare decimal needs all three
# components to count (so "WCAG 2.1 AA", "Python 3.7+", and "an 11-step loop" are
# not false positives). An earlier draft gated on a following release verb
# ("v1.21.0 adds …") — measured against the real pre-fix blurb it caught only 26 of
# 33 tokens, missing "v1.20.0 generalizes", "v1.9.1 hardens", "v1.2.5 sharpens" and
# four more. A closed verb list only recognizes the shape it already saw; this form
# is both simpler and strictly stronger (33/33, zero false positives on prose).
VERSION_TOKEN = re.compile(r"\bv\d+\.\d+(?:\.\d+)?\b|\b\d+\.\d+\.\d+\b")

# Stricter (full three-component release only) for skill frontmatter. Display copy has
# no legitimate reason to name any version, but trigger text does: `/flow:doctor`'s
# description says it checks the config "matches the v1.2+ schema", which is a
# capability statement about a compatibility floor, not a changelog. A release blurb —
# the thing actually being banned — always cites a complete release ("v1.21.0 adds …"),
# so requiring all three components keeps the check on target and off the legitimate use.
RELEASE_TOKEN = re.compile(r"\bv?\d+\.\d+\.\d+\b")

# Tolerate a UTF-8 BOM and leading blank lines before the opening `---`; a file that
# has frontmatter but that this regex can't see would make the check below pass
# vacuously for that file, which is the silent-skip class the harness exists to fight.
FRONTMATTER_DESC = re.compile(
    r"\A﻿?\s*---\n(?P<fm>.*?)\n---", re.DOTALL)
# The lookahead must match ANY sibling YAML key, including ones with `_` or digits —
# `[a-zA-Z-]+` stops at the underscore, so `some_key: v9.9.9` would be swallowed into
# the description and reported as a description violation.
FM_DESC_FIELD = re.compile(
    r"^description:\s*(?P<val>.*?)(?=\n[A-Za-z][\w-]*:|\Z)", re.DOTALL | re.MULTILINE)


def skill_mentions(text: str, skills: list[str]) -> list[str]:
    """Skills named in `text`, counting BOTH `/flow:<name>` and the bare slug.

    Counting only the `/flow:` form was the original shape and it was evadable in the
    most likely way: an author told "don't enumerate the skills" writes the bare list
    ("Bundles ship, staff-review, verify-build, …"), which carried 8 skills in 95
    chars and passed every check.

    The bare form counts for HYPHENATED slugs only — `staff-review`, `verify-build`,
    `audit-coverage` and friends read as command names wherever they appear. The
    single-word skills (`ship`, `land`, `doctor`, `contribute`) require the `/flow:`
    prefix, because they are also ordinary English a legitimate description will use,
    and a check that fires on prose gets edited away rather than obeyed. The rule is
    derived from the slug shape on disk, not a hand-maintained exemption list — that
    list would be the FB-0010 fan-out class this harness exists to prevent.
    """
    hits = []
    # Longest slug first, consuming each match, so `/flow:ship-spike` counts once as
    # `ship-spike` rather than also tripping the single-word `ship`. A failure message
    # naming a skill the text doesn't contain is the kind of wrong diagnostic that gets
    # a check edited away rather than obeyed.
    remaining = text
    for s in sorted(skills, key=len, reverse=True):
        prefix = "(?:/flow:)?" if "-" in s else "/flow:"
        pattern = rf"{prefix}\b{re.escape(s)}\b"
        if re.search(pattern, remaining):
            hits.append(s)
            remaining = re.sub(pattern, " ", remaining)
    return sorted(hits)


def frontmatter_description(skill_md: Path) -> str | None:
    """The `description:` value from a SKILL.md's YAML frontmatter.

    Returns None — distinctly from "" — when the file has no parseable frontmatter or
    no `description:` key, so the caller can report it rather than silently treating an
    unparseable file as clean.
    """
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    fm = FRONTMATTER_DESC.match(text)
    if not fm:
        return None
    field = FM_DESC_FIELD.search(fm.group("fm"))
    if not field:
        return None
    # Strip a YAML block-scalar indicator (`>`, `|`, with optional `-`/`+` chomp and
    # explicit indent digit) so the returned value is the text, not the syntax.
    val = re.sub(r"^[>|][-+]?\d?\s*", "", field.group("val").strip())
    return " ".join(val.split())


def main() -> int:
    fails = 0
    total = 0

    def check(label, cond, detail=""):
        nonlocal fails, total
        total += 1
        print(f"{'PASS' if cond else 'FAIL'}  [{label}]{'' if cond else '  ' + detail}")
        if not cond:
            fails += 1

    def bail():
        print(f"\n{total - fails} passed, {fails} failed")
        return 1

    for path in (PLUGIN_JSON, MARKETPLACE):
        if not path.exists():
            check(f"exists:{path.name}", False, f"{path} missing")
            return bail()

    # Malformed input is a clean FAIL, never a traceback (CLAUDE.md quality bar).
    try:
        plugin = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        mkt = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        check("manifests-parse", False, f"{type(e).__name__}: {e}")
        return bail()

    # Name the real problem once rather than letting a missing/empty `plugins` array
    # surface as three unrelated downstream failures.
    mkt_plugins = [p for p in (mkt.get("plugins") or []) if isinstance(p, dict)]
    check("marketplace-has-plugins", bool(mkt_plugins),
          "marketplace.json declares no usable plugins[] entry")
    if not mkt_plugins:
        return bail()

    plugin_desc = plugin.get("description", "")
    mkt_meta_desc = (mkt.get("metadata") or {}).get("description", "")
    # The entry `desc-parity` compares against: the one whose name matches plugin.json,
    # else the first. Parity is a same-plugin invariant, not an array-wide one — but a
    # silent fallback to [0] on a name mismatch would hide exactly the fan-out
    # `desc-parity` exists to catch, so the mismatch is its own reported failure.
    named_entry = next((p for p in mkt_plugins if p.get("name") == plugin.get("name")), None)
    check("parity-entry-found", named_entry is not None,
          f"no marketplace plugins[] entry named {plugin.get('name')!r} "
          f"(entries: {[p.get('name') for p in mkt_plugins]}) — falling back to [0]")
    parity_entry = named_entry or mkt_plugins[0]

    # EVERY description field, carrying its own cap — not just plugins[0] and not just
    # the two obvious fields. `.claude/rules/safety.md` points at this harness as THE
    # mechanized guard on the install surface, so a reader will assume it covers the
    # array; and parity protects the marketplace entry only for as long as parity
    # itself holds (the two fields serve different tabs and may legitimately diverge).
    all_descs = [
        ("plugin-json", plugin_desc, MAX_PLUGIN_DESC),
        *[(f"marketplace-plugin[{i}]", p.get("description") or "", MAX_PLUGIN_DESC)
          for i, p in enumerate(mkt_plugins)],
        ("marketplace-metadata", mkt_meta_desc, MAX_MARKETPLACE_DESC),
    ]

    skills = sorted(p.name for p in SKILLS_DIR.iterdir()
                    if p.is_dir() and (p / "SKILL.md").exists()) if SKILLS_DIR.is_dir() else []
    check("skills-found", len(skills) > 0, f"no skills discovered under {SKILLS_DIR}")

    for label, text, cap in all_descs:
        # ---- length: the defect this harness exists for ----
        check(f"len:{label}", 0 < len(text) <= cap,
              f"{label} description is {len(text)} chars (cap {cap}) — "
              "release notes go in CHANGELOG.md, not the description")
        # ---- no version token: catches the append-a-blurb habit at sentence 1 ----
        hits = VERSION_TOKEN.findall(text)
        check(f"no-version-token:{label}", not hits,
              f"description names {hits} — per-version notes belong in CHANGELOG.md")
        # ---- no skill catalog: Claude Code renders the inventory itself ----
        named = skill_mentions(text, skills)
        check(f"no-skill-catalog:{label}", len(named) <= MAX_SKILL_MENTIONS,
              f"description enumerates {len(named)} skills ({named[:4]}…) — the "
              "/plugin UI already lists components from disk (Discover 'Will install', "
              "Installed detail view, `claude plugin details`). Describe capability instead.")

    # ---- parity: two copies of one contract ----
    check("desc-parity", plugin_desc == parity_entry.get("description", ""),
          "plugin.json and the matching marketplace entry's description must be identical")

    # ---- version parity across the two manifests ----
    versions = {plugin.get("version"),
                (mkt.get("metadata") or {}).get("version"),
                parity_entry.get("version")}
    check("version-parity", len(versions) == 1 and None not in versions,
          f"version fields disagree: {versions}")

    # ---- the same rule over frontmatter descriptions (the rest of the class) ----
    # Agents as well as skills: an `agents/*.md` description is dispatch text loaded on
    # every agent selection — the same kind of consumer-visible string flow writes and
    # never reads back rendered. Sweeping one and not the other would half-cover the
    # very class FB-0078's rule names.
    surfaces = [("skill", sorted(SKILLS_DIR.glob("*/SKILL.md"))),
                ("agent", sorted(AGENTS_DIR.glob("*.md")))]
    for kind, paths in surfaces:
        descs = {p: frontmatter_description(p) for p in paths}
        # An unparseable file would otherwise read as clean — the silent-skip class.
        unparsed = sorted(p.name for p, d in descs.items() if d is None)
        check(f"{kind}-frontmatter-parsed", paths and not unparsed,
              f"no parseable frontmatter `description:` in {unparsed or f'(no {kind} files found)'} "
              "— an unreadable file must not count as clean")
        stamped = sorted(p.name for p, d in descs.items() if d and RELEASE_TOKEN.search(d))
        check(f"no-version-token:{kind}-frontmatter", not stamped,
              f"{kind} frontmatter description carries a release token: {stamped} — "
              "frontmatter description is trigger text loaded every invocation, not a changelog")

    # ---- CI wiring (the orphaned-eval guard) ----
    # Scoped to an executable `- run:` line, NOT a bare substring: ci.yml's own
    # join-check step argues that a bare grep would count a harness merely NAMED in a
    # comment as wired — this check must not commit the defect that one avoids.
    ci_text = CI.read_text(encoding="utf-8") if CI.exists() else ""
    check("ci-wired",
          bool(re.search(rf"^\s*-\s+run:\s+python3\s+\S*{re.escape(SELF)}\s*$",
                         ci_text, re.MULTILINE)),
          f"{SELF} not wired into ci.yml as a `- run:` step "
          "(CI enumerates, doesn't glob; a mention in a comment is not wiring)")

    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
