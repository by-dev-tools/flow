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
import glob
import json
import os
import re
import subprocess
import sys
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


def is_flow_checkout(root: Path) -> bool:
    """Ground truth, not an environment variable (the FB-0085 lesson).

    Also the trust boundary roadmap:311 asks for: without this gate the reader
    would happily report a version out of ANY reviewed repository that happens to
    ship a `plugins/flow/.claude-plugin/plugin.json`.
    """
    mf = root / ".claude-plugin" / "marketplace.json"
    if not mf.exists():
        return False
    try:
        return bool(re.search(r'"name"\s*:\s*"flow"', mf.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError):
        return False


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
    so in the flow checkout it EXECUTES checkout-only. 32 of the 144
    `${CLAUDE_PLUGIN_ROOT}` references in the skills carry this fallback; the
    other 112 are bare, and a bare one in a fenced block expands to `/skills/...`
    and hard-fails rather than going stale.
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

    This is also the reason "just always run from the working tree" is the wrong
    blanket fix: comparing against an installed tree is the ONLY way to observe
    a packaging/loading bug, so bypassing installation makes the whole class
    unobservable rather than fixed.
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
            out[f"{kind}_missing_from_installed"] = []
            out[f"{kind}_missing_from_checkout"] = []
            out.setdefault("warnings", []).append(f"{kind}: a tree was unreadable")
            continue
        out[f"{kind}_missing_from_installed"] = sorted(chk - inst)
        out[f"{kind}_missing_from_checkout"] = sorted(inst - chk)
    return out


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

L_INSTALLED = "Flow — installed version (ran the skills, agents + `!`-blocks)"
L_MARKET = "Flow — marketplace HEAD (what an update would fetch)"
L_LIBS = "Flow — helper libs, fenced Bash blocks"
L_PRE = "Flow — scripts via `!`-preprocessor blocks"
ROW_LABELS = (L_INSTALLED, L_MARKET, L_LIBS, L_PRE)


def _row(label: str, value: str, note: str) -> str:
    return f"| {label} | {value} | {note} |"


def render_rows(d: dict) -> list[str]:
    inst, mkt, br = d["installed"], d["marketplace_head"], d["branch"]
    libs, pre = d["libs"], d["preprocessor"]
    rows = []

    # -- installed
    if inst.get("state") == "ok":
        val = inst["version"] + (f" (`{inst['git_sha']}`)" if inst.get("git_sha") else "")
        if d["report_drift"] is True:
            gap = d.get("release_gap")
            gap_txt = f" ({gap} release{'s' if gap != 1 else ''})" if gap else ""
            note = (f"⚠️ DRIFT: this branch declares {br.get('version')}{gap_txt}. "
                    "The prose and reviewers that ran this pipeline are NOT this branch.")
        elif d["report_drift"] is False:
            note = "✓ matches this branch"
        elif br.get("state") == "not_flow_checkout":
            note = "✓ installed and running (no in-repo copy to compare against)"
        else:
            note = f"⚠️ cannot compare — branch manifest: {br.get('state')}"
    else:
        val = "UNDETERMINED"
        note = (f"⚠️ the installed version could NOT be read ({inst['state']}). "
                "Do not assume this run was current; check `claude plugin list`.")
    rows.append(_row(L_INSTALLED, val, note))

    # -- marketplace HEAD
    if mkt.get("state") == "ok":
        val = mkt["version"] + (f" (`{mkt['git_sha']}`)" if mkt.get("git_sha") else "")
        if d["update_available"] is True:
            note = ("⚠️ differs from the installed version — an update is available and "
                    "has not been applied.")
        elif d["update_available"] is False and d["report_drift"] is True:
            note = ("⚠️ the clone is pinned at the installed version — `plugin install` "
                    "alone would NOT move it; the marketplace needs refreshing first.")
        elif d["update_available"] is False:
            note = "✓ current"
        else:
            note = "⚠️ cannot compare against the installed version"
    else:
        val = "UNDETERMINED"
        note = f"⚠️ the marketplace clone could NOT be read ({mkt['state']})."
    rows.append(_row(L_MARKET, val, note))

    # -- fenced-block libs
    if libs.get("state") == "installed":
        v = libs.get("version")
        rows.append(_row(L_LIBS, f"installed tree{f' ({v})' if v else ''}",
                         "✓ same version as the prose"))
    elif libs.get("state") == "checkout":
        note = ("⚠️ MIXED PROVENANCE: the libs ran from the working tree while the prose "
                "came from the installed version above — one run, two versions."
                if d["mixed_provenance"] else
                "✓ resolved from the working tree (`CLAUDE_PLUGIN_ROOT` is unset in Bash-tool calls)")
        rows.append(_row(L_LIBS, "working tree", note))
    else:
        rows.append(_row(L_LIBS, "UNRESOLVED",
                         "⚠️ neither the installed tree nor the checkout served the probe lib — "
                         "helper calls in this run would have hard-failed."))

    # -- !-preprocessor blocks
    if pre.get("state") == "installed":
        v = pre.get("version")
        if d["report_drift"] is True:
            note = ("⚠️ a script this branch MODIFIED did not run here — "
                    "`CLAUDE_PLUGIN_ROOT` IS set in this context, so the installed copy won.")
        else:
            note = "✓ same version as the prose"
        rows.append(_row(L_PRE, f"installed{f' ({v})' if v else ''}", note))
    else:
        rows.append(_row(L_PRE, "UNDETERMINED",
                         f"⚠️ the installed tree could not be read ({pre.get('reason')}), so "
                         "`!`-block resolution is unknown."))
    return rows


def render_block(d: dict) -> str:
    """The un-invocable-surface callout. Only emitted when there is something to
    say, but when it IS emitted it names every surface -- a truncated list would
    be a quieter version of the failure being reported.
    """
    sd = d.get("surface_drift") or {}
    if sd.get("state") != "ok":
        return ""
    ms = sd.get("skills_missing_from_installed") or []
    ma = sd.get("agents_missing_from_installed") or []
    if not ms and not ma:
        return ""
    iv = d["installed"].get("version", "the installed version")
    out = [
        "<!-- flow:provenance -->",
        f"**⚠️ Surfaces this branch declares that were NOT INVOCABLE in this run** "
        f"(absent from {iv}, so the runtime has no tool for them — a model asked to "
        f"run one would wrongly conclude it does not exist):",
        "",
    ]
    if ms:
        out.append("- Skills: " + ", ".join(f"`{s}`" for s in ms))
    if ma:
        out.append("- Agents: " + ", ".join(f"`{a}`" for a in ma))
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

    print("\n".join(render_rows(data)))
    block = render_block(data)
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
