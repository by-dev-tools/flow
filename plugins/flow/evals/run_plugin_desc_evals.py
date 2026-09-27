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


def load_rule_skills():
    """`plugins/flow/lib/rule_skills.py` -- the single definition of the rule-skill contract.

    importlib because this harness must pin the module the SHIPPED code imports, not a
    re-implementation of it: a restatement here could agree with the spec while disagreeing
    with `plugin-provenance.py` and `/flow:doctor`, and nothing would notice.
    """
    import importlib.util
    target = PLUGIN_ROOT / "lib" / "rule_skills.py"
    spec = importlib.util.spec_from_file_location("flow_rule_skills", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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

    # ---- the four rule-skills: the contract that makes model invocation possible ----
    # FB-0124. These four are `user-invocable: false` background knowledge: a plugin cannot
    # ship `.claude/rules/*.md` (no `rules/` plugin component), so the ONLY way they reach a
    # session is Claude reading the description and deciding to load the body. From v1.33.0
    # to v1.49.0 every one of them ended with "Not user-invocable -- path-activated only.",
    # which told the model the skill was not its to invoke, and carried `paths:`, which
    # NARROWS a description-driven activation rather than triggering one.
    #
    # The roster AND the predicate live in `plugins/flow/lib/rule_skills.py` -- imported
    # here, imported by `plugin-provenance.py`, and invoked by `/flow:doctor` Check 3.2.
    # This eval therefore pins THE CODE DOCTOR RUNS, not a Python restatement of doctor's
    # shell (`.claude/rules/general.md` item 4's corollary -- pin a claim at the layer where
    # it is CLAIMED). Both /simplify cleanup lenses flagged the five-copy version.
    #
    # Every negative in `violations()` is paired with a positive, because a prohibition
    # satisfiable by deletion is not a check (item 3): "no suppressant" passes just as well
    # when the description, or the whole skill, is gone.
    rs = load_rule_skills()

    bad = {n: v for n, v in rs.audit(SKILLS_DIR).items() if v}
    check("rule-skill-contract", not bad,
          f"rule-skill contract violated: {bad} — see plugins/flow/lib/rule_skills.py for "
          f"what each token means; this is the same predicate /flow:doctor Check 3.2 runs")
    # The roster itself must not silently empty, or the audit above passes vacuously
    # (FB-0104's vacuous-criterion class): a zero-length roster yields `bad == {}`.
    check("rule-skill-roster-nonempty", len(rs.RULE_SKILLS) >= 4 and all(rs.RULE_SKILLS),
          f"RULE_SKILLS must name every rule-skill; got {rs.RULE_SKILLS!r}")

    # ---- NEGATIVE CONTROL: prove `violations()` can FAIL ----
    # A measurement that can only return "clean" is not a measurement (item 4). The four
    # real files are expected to pass, so passing over them cannot distinguish a working
    # predicate from a vacuous one. Each case below is a MINIMAL frontmatter that isolates
    # ONE clause -- deliberately not four copies of the same retired description, which is
    # what the first draft carried and which exercised one regex branch four times.
    NEG = [
        ("suppressant", "---\nname: x\ndescription: Does a thing. Use when testing. "
                        "Not user-invocable — path-activated only.\nuser-invocable: false\n---\n",
         "suppressant-in-description"),
        ("paths", "---\nname: x\ndescription: Does a thing. Use when testing.\n"
                  "user-invocable: false\npaths:\n  - '**/*'\n---\n", "has-paths"),
        ("dmi", "---\nname: x\ndescription: Does a thing. Use when testing.\n"
                "user-invocable: false\ndisable-model-invocation: true\n---\n",
         "disable-model-invocation"),
        ("not-model-only", "---\nname: x\ndescription: Does a thing. Use when testing.\n---\n",
         "not-user-invocable-false"),
        ("no-trigger", "---\nname: x\ndescription: Formatting rules for narrative docs.\n"
                       "user-invocable: false\n---\n", "no-trigger-clause"),
        ("no-description", "---\nname: x\nuser-invocable: false\n---\n", "no-description"),
        ("over-cap", "---\nname: x\ndescription: " + "y" * (rs.DESC_HARD_CAP + 1) +
                     " Use when testing.\nuser-invocable: false\n---\n",
         f"description-over-{rs.DESC_HARD_CAP}"),
        ("absent", None, "missing"),
    ]
    for label, text, expected in NEG:
        got = rs.violations(text)
        check(f"negative-control-rejects:{label}", expected in got,
              f"violations() FAILED to report {expected!r} for the {label} case (got {got}) — "
              "the predicate would have passed a description that cannot trigger, so it is "
              "not a check")
    # And the POSITIVE control on the predicate itself: a compliant frontmatter must yield
    # NO violations. Without this the negatives above all pass a `return ["everything"]` stub.
    check("positive-control-accepts-compliant",
          rs.violations("---\nname: x\ndescription: Does a thing. Use when testing.\n"
                        "user-invocable: false\n---\n") == [],
          "violations() reported a problem with a compliant frontmatter — the negative "
          "controls above would pass even a predicate that rejects everything")

    # ---- claim lint: no shipped surface may call a rule-skill path-activated ----
    # The altitude fix for FB-0124. Correcting nine occurrences by hand is symptom-level:
    # the sweep was performed from memory, and it MISSED two — including
    # `template/base/core-docs/roadmap.md`, which `bootstrap.sh` copies into every consumer
    # repo, so a wrong line there is wrong forever in every project that already adopted
    # flow. Found by /simplify's altitude lens, not by the sweep.
    #
    # This makes the tenth occurrence impossible rather than the ninth corrected: fail when
    # a path-activation phrase appears near any rule-skill name across shipped surfaces. The
    # roster comes from rule_skills.RULE_SKILLS, so adding a rule-skill extends the lint for
    # free.
    #
    # `.claude/rules/*.md` is deliberately NOT swept: project-scope rules genuinely ARE
    # path-activated, and that is the distinction every corrected doc now draws.
    CLAIM = re.compile(r"path-activat\w*|auto-load(?:ing|s|ed)?\b|fires? on (?:a )?path", re.IGNORECASE)
    NEAR = 110          # chars either side — a claim ABOUT a rule-skill sits close to its name.

    # Negation is checked in a WINDOW AROUND THE CLAIM, never over the whole line. A
    # line-scoped exemption is unsound and was measurably so: the first version of this
    # lint exempted any line containing "by judgment", so re-introducing
    # "Auto-loading `documentation` rule fires on path match" into a sentence that later
    # said "loads it by judgment" passed clean. A check that cannot fail is worse than no
    # check (`.claude/rules/general.md` item 4) — so the negation must sit next to the
    # claim it negates, which is where a real correction puts it anyway.
    NEGATED = re.compile(
        r"\bnot\b|\bno longer\b|\brather than\b|\bnever\b|\bcannot\b|\bwithout\b|"
        r"\bARE\b|model-invoked|by judgment|used to|through v1\.5|until v1\.5|was \*\*false\*\*|"
        r"claimed", re.IGNORECASE)
    NEG_WIN = 70        # chars either side of the CLAIM phrase

    # Surfaces that genuinely DO auto-load and are not rule-skills — the consumer's own
    # CLAUDE.md block, the statusDocs orientation files, project-scope .claude/rules. Matched
    # against the claim window, not the line.
    OTHER_MECHANISM = re.compile(
        r"statusSurfaceCandidates|orientation|status surface|auto-loads? into (?:every|a) session|"
        r"\.claude/rules|safety\.md|auto-load rules present|CLAUDE\.md", re.IGNORECASE)

    lint_roots = [ROOT / "README.md", ROOT / "docs", ROOT / "template",
                  PLUGIN_ROOT / "docs", PLUGIN_ROOT / "skills", PLUGIN_ROOT / "agents"]

    def path_activation_claims(body: str) -> list[str]:
        """Lines asserting that a RULE-SKILL is path-activated / auto-loading.

        Targeted, not an NLP judge: it matches a claim phrase, requires a rule-skill name
        within NEAR chars, and clears only on a negation or other-mechanism marker inside
        NEG_WIN chars of the claim itself.
        """
        hits = []
        for line in body.splitlines():
            for cm in CLAIM.finditer(line):
                win = line[max(0, cm.start() - NEG_WIN): cm.end() + NEG_WIN]
                if NEGATED.search(win) or OTHER_MECHANISM.search(win):
                    continue
                near = line[max(0, cm.start() - NEAR): cm.end() + NEAR]
                if any(re.search(rf"\b{re.escape(n)}\b", near) for n in rs.RULE_SKILLS):
                    hits.append(line.strip()[:110])
                    break
        return hits

    # ---- claim lint: no shipped surface may call a rule-skill path-activated ----
    # The altitude fix for FB-0124. Correcting occurrences by hand is symptom-level: the
    # sweep was performed from memory and MISSED FIVE — two found by /simplify's altitude
    # lens (including `template/base/core-docs/roadmap.md`, which `bootstrap.sh` copies into
    # every consumer repo, so a wrong line there is wrong forever in every project that
    # already adopted flow), and three more in `docs/first-pr.md` found by this lint on its
    # first run. That is the argument for the lint in one sentence.
    #
    # `.claude/rules/*.md` is deliberately NOT swept: project-scope rules genuinely ARE
    # path-activated, and that distinction is what every corrected doc now draws.
    offenders = []
    for root in lint_roots:
        files = sorted(root.rglob("*.md")) if root.is_dir() else ([root] if root.is_file() else [])
        for f in files:
            if ".claude/rules" in f.as_posix():
                continue
            try:
                body = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            offenders += [f"{f.relative_to(ROOT)}: {h}" for h in path_activation_claims(body)]
    check("no-path-activation-claim-near-a-rule-skill", not offenders,
          "shipped surface(s) still call a rule-skill path-activated or auto-loading — they "
          "are model-invoked, so the claim is false: " + "; ".join(sorted(set(offenders))[:4]))

    # ---- the lint's OWN known-positive / known-negative pair ----
    # Not a probe of the regex in isolation: run the real predicate over real sentences.
    # The first version of this lint checked only that its patterns matched a probe string,
    # which is why it could pass while the predicate it fronted did not fire at all.
    MUST_FLAG = [
        "Auto-loading `documentation` rule fires on path match and carries the format contract.",
        "The four portable rules (`general`, `plan-discipline`) — path-activated skills.",
        "- **4 auto-loading rules** that attach by file path — plan-discipline, documentation.",
        # The exact shape that defeated version 1: a false claim beside an exempting phrase.
        "Auto-loading `documentation` rule fires on path match — Claude loads it by judgment later.",
    ]
    for i, sentence in enumerate(MUST_FLAG):
        check(f"claim-lint-flags-known-positive:{i}", bool(path_activation_claims(sentence)),
              f"the lint did NOT flag a sentence that plainly makes the forbidden claim "
              f"({sentence[:70]!r}) — it cannot be trusted to have found nothing")
    MUST_PASS = [
        "The `general` rule-skill is model-invoked, not path-activated.",
        "Your own `.claude/rules/*.md` are the path-activated ones that fire deterministically.",
        "This CLAUDE.md block auto-loads into every session.",
        "`documentation` applies wherever the project keeps its docs; Claude loads it by judgment.",
    ]
    for i, sentence in enumerate(MUST_PASS):
        check(f"claim-lint-passes-known-negative:{i}", not path_activation_claims(sentence),
              f"the lint flagged a CORRECT sentence ({sentence[:70]!r}) — a lint that fires on "
              f"the fix teaches authors to route around it")

    # ---- the [UNCHECKED] marker's own contract, asserted over doctor's shipped text ----
    # FB-0124 introduced this marker class. Its rules were prose with nothing verifying them,
    # in a PR whose thesis is that unverified prose claims survive twenty releases
    # (/simplify's altitude lens made that point, and it landed).
    doctor = (SKILLS_DIR / "doctor" / "SKILL.md").read_text(encoding="utf-8")

    def echo_blocks(text: str, marker: str) -> list[tuple[str, str]]:
        """[(first line, the contiguous echo block it heads)] for each `marker` emission.

        Bounded to CONSECUTIVE echo lines, not a fixed character window: a fixed window
        spilled into the next check's text and read ITS `Fix:` as this line's, which failed
        the rule over a line that satisfied it. The block is the unit the reader sees.
        """
        out, lines = [], text.splitlines()
        for i, line in enumerate(lines):
            if not line.lstrip().startswith(f'echo "{marker}'):
                continue
            block = [line]
            for nxt in lines[i + 1:]:
                if nxt.lstrip().startswith("echo "):
                    block.append(nxt)
                else:
                    break
            out.append((line.strip(), "\n".join(block)))
        return out

    unchecked = echo_blocks(doctor, "[UNCHECKED]")
    unchecked_emissions = [first for first, _ in unchecked]
    # POSITIVE: the class is actually used. Without this the rules below are satisfiable by
    # deleting every emission (item 3 — a prohibition satisfiable by deletion is not a check).
    check("unchecked-class-in-use", len(unchecked_emissions) >= 1,
          "doctor emits no [UNCHECKED] line — the marker class, its table, and its rules are "
          "then dead prose, and rule-skill activation is being reported as something it isn't")
    # RULE 1: every [UNCHECKED] names the mechanism that would make it checkable. That
    # clause is also the line's deletion criterion, so it is what keeps the class from
    # becoming the drawer every unverifiable check goes into.
    for em, block in unchecked:
        check(f"unchecked-names-its-mechanism:{em[14:44].strip()}",
              "Checkable by:" in block,
              f"an [UNCHECKED] line carries no 'Checkable by:' clause — that clause IS the "
              f"deletion criterion, and without it the marker excuses itself: {em[:80]}")
    # RULE 2: [UNCHECKED] is reserved for what NO consumer can act on. A condition with a
    # consumer-side fix is a [WARN] worded "UNCHECKED, not clean" — the shape this file
    # already uses elsewhere. An [UNCHECKED] carrying a `Fix:` has conflated the two axes.
    for em, block in unchecked:
        check(f"unchecked-is-not-consumer-fixable:{em[14:44].strip()}",
              "Fix:" not in block,
              f"an [UNCHECKED] line offers a consumer-side 'Fix:' — if the consumer can act, "
              f"it belongs in the verdict arithmetic as [WARN] 'UNCHECKED, not clean', not "
              f"outside it: {em[:80]}")
    # And the verdict line must surface the count inline, so unchecked items stay visible
    # rather than being buried by living outside the arithmetic.
    check("unchecked-count-is-inline-on-the-verdict",
          "(N unchecked)" in doctor,
          "doctor's [READY] contract must print the unchecked count inline — keeping "
          "[UNCHECKED] out of the arithmetic without surfacing it loses the signal entirely")

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
