#!/usr/bin/env python3
"""Report WHICH VERSION of flow actually executed this pipeline run.

Why this exists (FB-0107). A `/flow:*` skill invoked from the flow checkout does
NOT run the code in the working tree. Claude Code resolves the skill from the
INSTALLED marketplace plugin, which in a cloud workspace was measured at 1.29.0
against a `main` at 1.41.0 -- a twelve-release gap no gate noticed, found by
accident during a pre-archive check. So a PR whose payload is a skill change
ships with zero execution evidence for that change, and the pipeline running
green is evidence about the PREVIOUS release.

The measured resolution rule, and the reason this reports FOUR rows and not one
version number:

    Everything CLAUDE CODE resolves comes from the INSTALLED tree.
    Everything the BASH TOOL resolves comes from the WORKING TREE.

`CLAUDE_PLUGIN_ROOT` is unset in Bash-tool calls and set in `!`-preprocessor
blocks, so the SAME `${CLAUDE_PLUGIN_ROOT}/...` string names different files
depending on who expands it. One run therefore draws from two versions at once:
SKILL.md prose, agent prompts and `!`-block scripts came from the installed tree
while the fenced-block helper libs came from the checkout. A single "plugin
version" line would not merely be ambiguous, it would be WRONG -- it would report
the installed version and imply the fresh engines never ran.

THREE DISTINCT NUMBERS, each labelled, because they mean different things and
were each independently stale when this was written:

    installed         what actually executed the skills, agents and `!`-blocks
    marketplace HEAD  what an update would fetch (the clone can be pinned too,
                      which is why a bare `/plugin install` can look like a fix
                      and change nothing)
    branch-declared   what this working tree claims to be

TWO PREDICATES, deliberately NOT collapsed into one `drift` boolean:

    report_drift      installed != branch-declared -> "did THIS branch's code run?"
                      This is what the PR body reports.
    update_available  installed != marketplace HEAD -> "is there a RELEASED
                      version I do not have?" This is what an updater acts on.

Collapsing them breaks the updater. A feature branch declares an UNRELEASED
version by construction, so `report_drift` is permanently true in the only
checkout an updater runs in: the silent no-op path becomes unreachable, an update
is attempted every session, and the warning keeps firing after a fully successful
update. A permanent warning is indistinguishable from the real staleness signal
this exists to surface.

Flow's "floor" is deliberately NOT a constant here. A CONSUMER repo can name a
fixed floor (health-tracker pins flow >= 1.32.0, the release that added the
`toolchain` manifest kind, and that capability stays shipped). Flow pinning
ITSELF has no fixed point -- the floor moves every release -- so a literal
FLOW_MIN in this repo would be an FB-0010 clause-2 fan-out value, wrong one
release after it was written. Flow's floor IS its branch-declared version.

Reports; never gates. Drift does not route to the draft manifest and does not
block a ship. Gating would halt every flow PR until its workspace updated, and a
STABLE reviewer is partly a feature: a ship pipeline with a bug that skips a
reviewer should not be the thing running its own ship, and a branch that breaks
ship could not ship itself.

Deletion criterion (FB-0088). Removable when BOTH hold: (a) `claude plugin
update` no longer requires a restart to apply, so "current" and "what this
session is running" stop being different facts; and (b) `CLAUDE_PLUGIN_ROOT`
resolves identically in the Bash tool and the `!`-expander, collapsing the two
executor arms into one. Until then nothing else can say which version graded a PR.

stdlib only. Never raises on malformed input: every failure becomes a labelled
row that says what could not be determined, because a provenance reporter that
crashes teaches the operator nothing and one that prints a blank row is worse.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

PROBE_LIB = "skills/ship/lib/manifest-triage.py"
CHECKOUT_PLUGIN = "plugins/flow"

# ---------------------------------------------------------------- source reads
#
# Every reader returns a `state` string and the states are kept DISTINCT --
# `absent` / `malformed` / `plugin_absent` / `no_versions` / `ok` never collapse
# into one "unknown" (FB-0082). Collapsing them is how a configuration failure
# reads as "this project simply has none of that", which is the whole silent-skip
# class: an empty resolution is a failure, not an empty set.


def read_installed(home: Path) -> dict:
    """The version that actually ran the skills, agents and `!`-blocks."""
    reg = home / ".claude" / "plugins" / "installed_plugins.json"
    if not reg.exists():
        return {"state": "registry_absent", "path": str(reg)}
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return {"state": "registry_malformed", "path": str(reg), "error": str(exc)}
    if not isinstance(data, dict):
        return {"state": "registry_malformed", "path": str(reg),
                "error": "top level is not an object"}
    entries = (data.get("plugins") or {}).get("flow@flow")
    if entries is None:
        return {"state": "plugin_absent", "path": str(reg)}
    if not isinstance(entries, list) or not entries:
        return {"state": "no_versions", "path": str(reg)}
    e = entries[0] if isinstance(entries[0], dict) else {}
    ver = e.get("version")
    if not ver:
        return {"state": "no_versions", "path": str(reg)}
    return {
        "state": "ok",
        "version": str(ver),
        # A dual user+project install resolves first-wins; say so rather than
        # presenting an arbitrary pick as the answer.
        "entry_count": len(entries),
        "install_path": e.get("installPath"),
        "git_sha": (e.get("gitCommitSha") or "")[:7] or None,
        "installed_at": e.get("installedAt"),
        "scope": e.get("scope"),
    }


def read_marketplace(home: Path) -> dict:
    """What an update would fetch.

    The third number, and not decoration: the marketplace CLONE can be pinned at
    the same stale commit as the install, in which case `/plugin install` has
    nothing newer to serve and silently changes nothing. That is measured
    behaviour -- health-tracker#116 observed a sandbox stay at 1.29.0 through
    `marketplace update` + `install`, moving only on `update`.
    """
    root = home / ".claude" / "plugins" / "marketplaces" / "flow"
    mf = root / ".claude-plugin" / "marketplace.json"
    if not mf.exists():
        return {"state": "clone_absent", "path": str(mf)}
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return {"state": "clone_malformed", "path": str(mf), "error": str(exc)}
    plugins = data.get("plugins") if isinstance(data, dict) else None
    ver = None
    if isinstance(plugins, list) and plugins and isinstance(plugins[0], dict):
        ver = plugins[0].get("version")
    if not ver and isinstance(data, dict):
        ver = (data.get("metadata") or {}).get("version")
    if not ver:
        return {"state": "no_version", "path": str(mf)}
    return {"state": "ok", "version": str(ver), "path": str(root),
            "git_sha": _git_sha(root)}


def _git_sha(root: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


@lru_cache(maxsize=8)
def _is_flow_checkout(root_str: str) -> bool:
    """Ground truth, not an environment variable (the FB-0085 lesson).

    Also the trust boundary roadmap:311 asks for: without this gate the reader
    would happily report a version out of ANY reviewed repository that happens to
    ship a `plugins/flow/.claude-plugin/plugin.json`.

    The marker is `plugins/flow/.claude-plugin/plugin.json` naming flow, which is
    deliberately the SAME spelling the 12 existing shipped call sites use
    (staff-review x3, accessibility-review x2, security-review x2, land x2,
    verify-build, ship-spike, doctor) and the one `run_doc_slot_resolution_evals.py`
    pins. A third spelling over a different marker file would be invisible to the
    check that guards this predicate -- and roadmap:309 already tracks collapsing
    these into one gated helper, so a new variant adds a site to that backlog
    instead of joining it. It is also the file the version is then read from, so
    gate and read agree by construction.

    Cached: `read_branch` and `surface_drift` each ask independently, and this is
    otherwise a repeated read + regex of the same bytes within one `collect()`.
    """
    pj = Path(root_str) / CHECKOUT_PLUGIN / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        return False
    try:
        return bool(re.search(r'"name"\s*:\s*"flow"', pj.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError):
        return False


def is_flow_checkout(root: Path) -> bool:
    return _is_flow_checkout(str(root))


def read_branch(root: Path) -> dict:
    """What this working tree claims to be -- flow's floor, by construction."""
    if not is_flow_checkout(root):
        return {"state": "not_flow_checkout", "root": str(root)}
    pj = root / CHECKOUT_PLUGIN / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        return {"state": "manifest_absent", "path": str(pj)}
    try:
        ver = json.loads(pj.read_text(encoding="utf-8")).get("version")
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return {"state": "manifest_malformed", "path": str(pj), "error": str(exc)}
    if not ver:
        return {"state": "no_version", "path": str(pj)}
    return {"state": "ok", "version": str(ver)}


# ------------------------------------------------------------- executor arms


def resolve_libs(plugin_root: str | None, root: Path, installed: dict) -> dict:
    """Run the REAL two-arm ladder every fenced-block helper call in the skills
    uses, and report which arm fires:

        X="${CLAUDE_PLUGIN_ROOT}/skills/..."; [ -f "$X" ] || X="plugins/flow/skills/..."

    Written installed-first, but `CLAUDE_PLUGIN_ROOT` is unset in Bash-tool calls,
    so in the flow checkout it EXECUTES checkout-only. Many `${CLAUDE_PLUGIN_ROOT}`
    reference sites in the skills carry this fallback and many are bare; a bare one
    in a FENCED block expands to `/skills/...` and hard-fails rather than going
    stale, while a bare one in a `!`-block is fine because `CPR` is set there.

    No count is stated here on purpose. An earlier draft asserted "32 of 144", and
    it was wrong twice over: the classifier was a LINE-local grep for a
    BLOCK-scoped property (a correctly-guarded multi-line ladder, e.g.
    `critique-plan/SKILL.md`'s pin lint, counts as bare), and it did not split by
    executor context -- the very axis this file establishes -- so it conflated
    harmless `!`-block bare refs with fenced-block ones that hard-fail. It was also
    a fan-out constant across five files that went stale inside one PR (144 on
    `main`, 164 at that PR's own HEAD). Measure it when you need it, with the
    executor context, and do not carve the answer into prose:
    `git grep -n 'CLAUDE_PLUGIN_ROOT' -- plugins/flow/skills/`.

    WHAT THE PROBE ESTABLISHES, precisely: it resolves ONE file (`PROBE_LIB`), so
    the row reports which arm the ladder fires for a site that HAS a fallback. It
    is not a survey of every helper call, and a bare-ref site is not covered by it.
    """
    if plugin_root:
        cand = Path(plugin_root) / PROBE_LIB
        if cand.is_file():
            return {"state": "installed", "probe": str(cand),
                    "version": installed.get("version")}
    cand = root / CHECKOUT_PLUGIN / PROBE_LIB
    if cand.is_file():
        return {"state": "checkout", "probe": str(cand)}
    return {"state": "unresolved", "probe": PROBE_LIB}


def resolve_preprocessor(installed: dict) -> dict:
    """Where a `${CLAUDE_PLUGIN_ROOT}` reference inside a `!`-preprocessor block
    lands.

    `!`-blocks are expanded by Claude Code itself, which DOES set
    `CLAUDE_PLUGIN_ROOT` -- so they resolve from the installed tree even for a
    script the branch modified, and `audit-plan` / `critique-plan` carry no
    fallback, so a script a branch ADDS hard-fails there instead of degrading.

    `basis` is explicit: the executor rule is an established measurement
    (FB-0107), not something re-measured per run. A reader must be able to tell a
    cited fact from a fresh observation.
    """
    if installed.get("state") == "ok":
        return {"state": "installed", "version": installed.get("version"),
                "basis": "measured-rule:FB-0107"}
    return {"state": "unresolved", "basis": "measured-rule:FB-0107",
            "reason": installed.get("state")}


def surface_drift(installed: dict, root: Path) -> dict:
    """Skills and agents this branch declares that the installed tree does not
    have -- i.e. NOT INVOCABLE at all in this run, which is a harder failure than
    staleness: a model asked to run one concludes the skill does not exist.

    SCOPE, stated precisely because an earlier draft over-claimed it: this compares
    two directory LISTINGS, so what it detects is INVENTORY drift -- a surface the
    branch declares that the stale install simply does not contain. It does NOT
    detect a loading bug (the `paths:`-never-activates class): a surface can be
    present in both trees and still fail to register, and this check would call
    that clean. Observing THAT needs the runtime's registered set, which is the
    routed doctor "registered vs activates" upgrade, not a listing diff.

    So the honest version of the argument against "just always run from the working
    tree" rests on the other two reasons, which do hold on their own: it would make
    `/flow:ship` grade its own homework, and a branch that breaks ship could not
    ship itself. Inventory drift is a real thing this reports; it is not the whole
    packaging class.
    """
    ip = installed.get("install_path")
    if installed.get("state") != "ok" or not ip:
        return {"state": "unknown", "reason": installed.get("state")}
    ipath = Path(ip)
    if not ipath.is_dir():
        return {"state": "install_path_missing", "path": ip}
    if not is_flow_checkout(root):
        return {"state": "not_flow_checkout"}
    out: dict = {"state": "ok"}
    for kind, sub, suffix in (("skills", "skills", ""), ("agents", "agents", ".md")):
        inst = _names(ipath / sub, suffix)
        chk = _names(root / CHECKOUT_PLUGIN / sub, suffix)
        if inst is None or chk is None:
            # NOT state "ok" with empty lists. That made "I could not check whether your
            # new skills were invocable" render identically to "they all were" -- the
            # collapse this module's docstring forbids, and the emptied lists then
            # suppressed the callout entirely.
            out[f"{kind}_missing_from_installed"] = []
            out[f"{kind}_missing_from_checkout"] = []
            out["state"] = "partially_unreadable"
            out.setdefault("unreadable", []).append(kind)
            continue
        out[f"{kind}_missing_from_installed"] = sorted(chk - inst)
        out[f"{kind}_missing_from_checkout"] = sorted(inst - chk)
    return out


def _is_rule_skill(root: Path, name: str) -> bool:
    """True when a skill AUTO-LOADS on matching paths rather than being invoked.

    The marker is a `paths:` key in the SKILL.md frontmatter -- a plain frontmatter
    read, never a judgment call. This distinction matters because the two kinds fail
    DIFFERENTLY when absent from the installed tree, and reporting only the milder
    consequence is what render_block did before: for a command skill the failure is
    "you cannot invoke it"; for a rule-skill NOTHING invokes it, so the failure is
    that the rules meant to govern the run were never loaded. Attaching the command
    consequence to a rule-skill states something simply untrue of it.
    """
    f = root / CHECKOUT_PLUGIN / "skills" / name / "SKILL.md"
    try:
        head = f.read_text(encoding="utf-8")[:2000]
    except (OSError, UnicodeDecodeError):
        return False
    # Frontmatter only: stop at the closing fence so a `paths:` mentioned in prose
    # cannot promote a command skill.
    if head.startswith("---"):
        end = head.find("\n---", 3)
        head = head[:end] if end != -1 else head
    return bool(re.search(r"^\s*paths\s*:", head, re.MULTILINE))


def _names(d: Path, suffix: str) -> set[str] | None:
    try:
        if suffix:
            return {p.name[: -len(suffix)] for p in d.iterdir() if p.name.endswith(suffix)}
        return {p.name for p in d.iterdir() if p.is_dir()}
    except OSError:
        return None


# ------------------------------------------------------------------- assembly


def _minor_delta(a: str | None, b: str | None) -> int | None:
    """Release count between two versions. Flow bumps MINOR per release, so the
    minor delta IS the release count. Returns None on anything non-semver rather
    than guessing -- an invented release count in a provenance report is the kind
    of confident falsehood this file exists to prevent.
    """
    if not a or not b:
        return None
    pa, pb = a.split("."), b.split(".")
    if len(pa) < 2 or len(pb) < 2:
        return None
    try:
        if int(pa[0]) != int(pb[0]):
            return None
        return abs(int(pb[1]) - int(pa[1]))
    except ValueError:
        return None


def collect(home: Path, root: Path, plugin_root: str | None) -> dict:
    installed = read_installed(home)
    marketplace = read_marketplace(home)
    branch = read_branch(root)
    libs = resolve_libs(plugin_root, root, installed)
    pre = resolve_preprocessor(installed)
    drift_surfaces = surface_drift(installed, root)

    iv = installed.get("version") if installed.get("state") == "ok" else None
    bv = branch.get("version") if branch.get("state") == "ok" else None
    mv = marketplace.get("version") if marketplace.get("state") == "ok" else None

    # Both predicates are None-when-undeterminable, NOT False. "I could not tell"
    # and "they match" must stay distinguishable, or an unreadable registry reads
    # as a clean run -- the exact confidence-inverting shape of FB-0107.
    report_drift = None if (iv is None or bv is None) else (iv != bv)
    update_available = None if (iv is None or mv is None) else (iv != mv)

    return {
        "installed": installed,
        "marketplace_head": marketplace,
        "branch": branch,
        "libs": libs,
        "preprocessor": pre,
        "surface_drift": drift_surfaces,
        "report_drift": report_drift,
        "update_available": update_available,
        "release_gap": _minor_delta(iv, bv),
        "mixed_provenance": libs.get("state") == "checkout" and pre.get("state") == "installed",
    }


# -------------------------------------------------------------------- render
#
# Every row has BOTH polarities. A drift warning alone is a negative assertion --
# it passes in two opposite worlds, "no drift" and "the row was deleted" -- so
# each row must also state the affirmative it protects (FB-0010 clause 3). That
# is not hypothetical in this repo: `skill-does-not-CALL-land` was a negative
# without its pair, and deleting the protected feature turned it green for four
# releases.

# Plain-language reason per unreadable state. FB-0082 keeps the STATES distinct in
# code; without this map every one of them rendered behind the same sentence plus an
# opaque token like `(registry_absent)`, so to the reader they WERE one state -- the
# same rule violated one layer up, in the copy. And FB-0075's bar for this surface is
# a reader who is not an engineer.
_REASON = {
    "registry_absent": "Claude Code has no plugin registry on this machine",
    "registry_malformed": "the plugin registry file is corrupt",
    "plugin_absent": "the registry exists but flow is not installed in it",
    "no_versions": "flow is listed in the registry but records no version",
    "clone_absent": "flow's marketplace has never been downloaded here",
    "clone_malformed": "the downloaded marketplace file is corrupt",
    "no_version": "the marketplace file records no version",
    "manifest_absent": "this branch has no flow plugin manifest",
    "manifest_malformed": "this branch's flow plugin manifest is corrupt",
}


def _why(state: str | None) -> str:
    return _REASON.get(state or "", f"an unrecognised problem ({state})")


L_INSTALLED = "Flow version that ran this pipeline"
L_MARKET = "Latest released version available to this machine"
L_LIBS = "Helper scripts — which copy ran"
L_PRE = "Scripts Claude Code ran for itself"
ROW_LABELS = (L_INSTALLED, L_MARKET, L_LIBS, L_PRE)

# The remedy footnote, emitted ONCE under the table when anything warns. Six warning
# states used to state a problem and stop; a reader who cannot act on a warning learns
# only to ignore it.
REMEDY = (
    "> To re-run these gates against this branch's own code: "
    "`claude plugin marketplace update flow && claude plugin update flow@flow`, "
    "restart Claude Code, then re-run `/flow:ship`. "
    "**Nothing here blocks this merge** — these rows report, they do not gate."
)


def _row(label: str, value: str, note: str) -> str:
    return f"| {label} | {value} | {note} |"


def _paren(base: str, extra: str | None, tick: str = "") -> str:
    """`base (extra)` when extra is present, else `base`. Four rows need this and
    two of them were spelling it as a nested f-string."""
    return f"{base} ({tick}{extra}{tick})" if extra else base


def _stale(d: dict) -> bool:
    """Is the install genuinely behind RELEASED versions?

    This is the severity discriminator, and picking it correctly is the whole
    difference between a signal and noise. `update_available` is the WRONG test here,
    though it is the intuitive one: in the very case this file exists to expose --
    1.29.0 installed, twelve releases behind, with the marketplace clone pinned at the
    same stale commit -- there is nothing newer to fetch LOCALLY, so
    `update_available` is False. Keying severity on it would render the flagship
    failure as informational.

    `release_gap` is the honest test. A flow feature branch declares the next,
    unreleased minor, so a gap of 1 against a fully current install is the EXPECTED
    steady state of every branch and must not warn -- this module's own rule is that
    "a permanent warning is indistinguishable from the real staleness signal this
    exists to surface", and an earlier draft warned on all four rows of every healthy
    PR, violating it at the render while honouring it in the predicate. A gap above 1
    means releases exist that this install does not have.
    """
    gap = d.get("release_gap")
    return bool(d.get("report_drift")) and (gap is None or gap > 1)


def render_rows(d: dict) -> list[str]:
    inst, mkt, br = d["installed"], d["marketplace_head"], d["branch"]
    libs, pre = d["libs"], d["preprocessor"]
    stale = _stale(d)
    rows = []

    # -- what actually ran
    if inst.get("state") == "ok":
        val = _paren(inst["version"], inst.get("git_sha"), "`")
        if d["report_drift"] is True and stale:
            gap = d.get("release_gap")
            gap_txt = f", {gap} releases back" if gap else ""
            note = (f"⚠️ NOT this branch{gap_txt}. This branch declares "
                    f"{br.get('version')}, so the skill instructions and reviewers that "
                    "ran here are an older release. Updating cannot fix THIS run — "
                    "`plugin update` applies on restart, so re-running ship in a NEW "
                    "session is what regenerates these rows.")
        elif d["report_drift"] is True:
            note = (f"ℹ️ expected — this branch declares {br.get('version')}, which is not "
                    "released yet, and the install is otherwise current.")
        elif d["report_drift"] is False:
            note = "✓ matches this branch"
        elif br.get("state") == "not_flow_checkout":
            note = "✓ installed and running"
        else:
            note = f"⚠️ cannot compare — {_why(br.get('state'))}"
    else:
        val = "UNKNOWN"
        note = (f"⚠️ could not be read: {_why(inst.get('state'))}. Do not assume this run "
                "was current; check `claude plugin list`.")
    rows.append(_row(L_INSTALLED, val, note))

    # -- latest released
    if mkt.get("state") == "ok":
        val = _paren(mkt["version"], mkt.get("git_sha"), "`")
        if d["update_available"] is True:
            note = "⚠️ newer than what ran — an update is available and was not applied."
        elif d["update_available"] is False and stale:
            # Claim "pinned" only when the two commits actually MATCH. Pinning is not
            # locally inferable in general (there is no remote signal here), so an
            # unevidenced assertion would send the reader to run a refresh that may
            # change nothing. With matching shas the claim is grounded.
            same = (inst.get("git_sha") and inst.get("git_sha") == mkt.get("git_sha"))
            if same:
                note = ("⚠️ the downloaded marketplace sits at the same old commit as the "
                        "install, so `plugin install` alone will not move it — refresh the "
                        "marketplace first.")
            else:
                note = ("⚠️ no newer release is available locally, yet the install is behind "
                        "this branch — refresh the marketplace before concluding it is current.")
        elif d["update_available"] is False:
            note = "✓ current — nothing newer to fetch"
        else:
            note = f"⚠️ cannot compare — {_why(mkt.get('state'))}"
    else:
        val = "UNKNOWN"
        note = f"⚠️ could not be read: {_why(mkt.get('state'))}."
    rows.append(_row(L_MARKET, val, note))

    # -- fenced-block helper scripts
    if libs.get("state") == "installed":
        rows.append(_row(L_LIBS, _paren("the installed copy", libs.get("version")),
                         "✓ same version as the skill instructions"))
    elif libs.get("state") == "checkout":
        note = ("⚠️ TWO VERSIONS IN ONE RUN: these ran from your working tree while the "
                "skill instructions above came from the older installed copy."
                if d["mixed_provenance"] and stale else
                "✓ ran from your working tree")
        rows.append(_row(L_LIBS, "your working tree", note))
    else:
        rows.append(_row(L_LIBS, "NOT FOUND",
                         "⚠️ the helper script this check looks for was in neither the "
                         "installed copy nor this checkout, so helper calls in this run "
                         "may not have resolved."))

    # -- !-preprocessor scripts
    if pre.get("state") == "installed":
        if d["report_drift"] is True and stale:
            note = ("⚠️ these came from the older installed copy, so any such script this "
                    "branch changed would not have run here.")
        else:
            note = "✓ same version as the skill instructions"
        rows.append(_row(L_PRE, _paren("the installed copy", pre.get("version")), note))
    else:
        rows.append(_row(L_PRE, "UNKNOWN",
                         f"⚠️ could not be determined: {_why(pre.get('reason'))}."))
    return rows


L_SURFACES = "New skills + agents — were they available"


def render_surface_row(d: dict) -> str:
    """A labelled row for the surface-inventory dimension when it could not be checked.

    Without this, `state` of `unknown` / `install_path_missing` / `partially_unreadable`
    produced NO output anywhere, so "I could not check whether your new skills were
    invocable" was indistinguishable from "they all were". The healthy and
    drift-detected cases stay in render_block; this row exists for the
    could-not-tell cases, which previously had no surface at all.
    """
    sd = d.get("surface_drift") or {}
    st = sd.get("state")
    if st == "ok" and not sd.get("unreadable"):
        return ""
    if st == "not_flow_checkout":
        return ""
    why = {
        "unknown": "the registry records no install location",
        "install_path_missing": "the recorded install location does not exist",
        "partially_unreadable": "a skills/agents directory could not be read "
                                f"({', '.join(sd.get('unreadable') or [])})",
    }.get(st, f"an unrecognised problem ({st})")
    return _row(L_SURFACES, "UNKNOWN",
                f"⚠️ could not be checked: {why}. This is NOT the same as 'all of this "
                "branch's skills and agents were available'.")


def render_remedy(rows: list[str]) -> str:
    """The remedy footnote, once, only when something warned."""
    return REMEDY if any("⚠️" in r for r in rows) else ""


def render_block(d: dict, root: Path) -> str:
    """The un-invocable-surface callout, split by how each surface FAILS.

    Only emitted when there is something to say, but when it IS emitted it names
    every surface -- a truncated list would be a quieter version of the failure being
    reported.
    """
    sd = d.get("surface_drift") or {}
    if sd.get("state") != "ok":
        return ""
    ms = sd.get("skills_missing_from_installed") or []
    ma = sd.get("agents_missing_from_installed") or []
    if not ms and not ma:
        return ""
    iv = d["installed"].get("version", "the installed version")

    rules, commands = [], []
    for name in ms:
        (rules if _is_rule_skill(root, name) else commands).append(name)

    out = ["<!-- flow:provenance -->",
           f"**⚠️ Surfaces this branch declares that were ABSENT from {iv}, so they took no "
           f"part in this run:**", ""]
    if rules:
        out.append(
            "- **Rule-skills that did NOT load — this run was not governed by them.** "
            + ", ".join(f"`{s}`" for s in rules)
            + ". These auto-load on matching paths rather than being invoked, so nothing "
              "reports their absence: the rules simply were not applied.")
    if commands:
        out.append(
            "- **Skills that were not invocable.** " + ", ".join(f"`{s}`" for s in commands)
            + ". The runtime has no tool for them, so a model asked to run one would "
              "wrongly conclude it does not exist.")
    if ma:
        out.append(
            "- **Agents that were not spawnable.** " + ", ".join(f"`{a}`" for a in ma)
            + ". A reviewer lens or helper this branch adds could not have run.")
    out += ["", "<!-- /flow:provenance -->"]
    return "\n".join(out)


# ---------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Report which flow version actually executed this run (FB-0107).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report", help="Flow-run table rows, or --json")
    r.add_argument("--json", action="store_true", help="machine-readable provenance")
    r.add_argument("--home", default=None,
                   help="override HOME (used by the eval harness; default $HOME)")
    r.add_argument("--root", default=None,
                   help="override the repo root (default: git toplevel, else cwd)")
    a = ap.parse_args(argv)

    home = Path(a.home) if a.home else Path(os.environ.get("HOME", "~")).expanduser()
    if a.root:
        root = Path(a.root)
    else:
        try:
            out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                 capture_output=True, text=True, timeout=10)
            root = Path(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() \
                else Path.cwd()
        except (OSError, subprocess.SubprocessError):
            root = Path.cwd()

    data = collect(home, root, os.environ.get("CLAUDE_PLUGIN_ROOT") or None)

    if a.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0

    rows = render_rows(data)
    surface_row = render_surface_row(data)
    if surface_row:
        rows.append(surface_row)
    print("\n".join(rows))
    remedy = render_remedy(rows)
    if remedy:
        print()
        print(remedy)
    block = render_block(data, root)
    if block:
        print()
        print(block)
    return 0


if __name__ == "__main__":
    # Exit 0 even on an internal error: this is a REPORTER inside a ship
    # pipeline. A traceback here would fail a ship over a provenance line, and a
    # blank row would be worse than a loud one -- it would read as "nothing to
    # report" when the truth is "could not tell".
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"| Flow — provenance | UNDETERMINED | ⚠️ the provenance reporter "
              f"itself failed ({type(exc).__name__}: {exc}). Treat this run's flow "
              f"version as UNKNOWN. |")
        sys.exit(0)
