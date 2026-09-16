#!/usr/bin/env python3
"""Regression pin for skills/ship/lib/plugin-provenance.py + the currency hook.

Why this harness carries the whole behavioural load on its PR: flow's
`flow.config.json` sets `"platform": "library"`, which makes `/flow:verify-build`
self-skip (there is no runnable target to drive). So there is no behavioural gate
above this file — it IS the gate, not a supplement to one.

Everything here runs against SYNTHETIC state: a temp HOME holding a fabricated
`installed_plugins.json` + marketplace clone, and a temp repo root. Nothing reads
the real `~/.claude/plugins`, because a CI runner has no installed flow tree at
all and the one workspace that had the interesting state updates itself away from
it. The single real-host reading lives in
`fixtures/plugin-provenance/this-workspace-20260912.json` as a one-shot capture,
and is asserted here only for internal consistency — never re-derived.

Deletion criterion (FB-0088): this harness dies with the engine it pins. If
`plugin-provenance.py` is removed because Claude Code gained in-session plugin
reload and a single-version world (the engine's own deletion criterion), delete
this file in the same PR — do not leave it asserting the shape of something gone.
FB-0077 is the precedent: a check outlived the feature it protected and stayed
green over its absence for four releases.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOW = HERE.parent                      # plugins/flow
REPO = FLOW.parent.parent               # repo root
ENGINE = FLOW / "skills" / "ship" / "lib" / "plugin-provenance.py"
HOOK = REPO / ".claude" / "hooks" / "flow-plugin-currency.sh"
SHIP = FLOW / "skills" / "ship" / "SKILL.md"
SPIKE = FLOW / "skills" / "ship-spike" / "SKILL.md"
FIXTURES = HERE / "fixtures" / "plugin-provenance"
CAPTURE = FIXTURES / "this-workspace-20260912.json"


def live_branch_version() -> str:
    """The version the live checkout declares.

    The hook resolves its own root (it must — that is the point of it), so any test
    driving the hook with `cwd=REPO` compares against THIS file, not a fixture. Pinning
    a fixture version against it is a time bomb: every release PR bumps plugin.json, so
    the next bump made `report_drift` true and a "must be silent" assertion fail on a
    test that has nothing to do with versions. FB-0010 clause 2 — read the live value
    rather than re-stating it.
    """
    try:
        return json.loads(
            (REPO / "plugins" / "flow" / ".claude-plugin" / "plugin.json")
            .read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, json.JSONDecodeError):
        return "0.0.0"

# Imported, NOT re-typed. The row contract has four sites (engine, this harness, and
# the two SKILL.md copies); re-typing it here would mean that editing this file to match
# a reworded label silently stops pinning the engine's renderer at all -- FB-0010 clause
# 2, with the test as the thing that drifts. importlib because the engine's filename is
# hyphenated (the run_manifest_triage_evals.py pattern for exactly this).
_spec = importlib.util.spec_from_file_location("plugin_provenance", ENGINE)
_engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_engine)
ROW_LABELS = _engine.ROW_LABELS
# A floor, so the `for lab in ROW_LABELS` loops below cannot go VACUOUS if the tuple is
# ever emptied or trimmed — four tests would silently become no-ops while still printing
# PASS (FB-0104's vacuous-criterion class, FB-0010 clause 3). Asserted as
# self-consistency against the renderer, not as a pinned count.
assert len(ROW_LABELS) >= 4 and all(ROW_LABELS), \
    f"ROW_LABELS must be non-empty and hold every row label; got {ROW_LABELS!r}"

failures: list[str] = []
checks = 0


def check(cond: bool, msg: str) -> bool:
    global checks
    checks += 1
    if not cond:
        failures.append(msg)
    return bool(cond)


# ----------------------------------------------------------------- scaffolding


def make_home(td: Path, installed: dict | str | None, marketplace: str | None) -> Path:
    """A synthetic HOME. `installed`/`marketplace` of None means ABSENT, and a
    str means write it verbatim (so malformed JSON can be exercised)."""
    home = td / "home"
    (home / ".claude" / "plugins").mkdir(parents=True, exist_ok=True)
    if installed is not None:
        txt = installed if isinstance(installed, str) else json.dumps(installed)
        (home / ".claude" / "plugins" / "installed_plugins.json").write_text(txt)
    if marketplace is not None:
        mp = home / ".claude" / "plugins" / "marketplaces" / "flow" / ".claude-plugin"
        mp.mkdir(parents=True, exist_ok=True)
        (mp / "marketplace.json").write_text(marketplace)
    return home


def load_fixture(name: str) -> dict:
    """Fixtures are COMMITTED FILES, not inline dicts.

    The set of worlds an assertion covers is itself the contract -- "the four
    unreadable-registry states stay distinct" is a claim about which four -- so it
    belongs somewhere a human can read it without reverse-engineering this
    harness. Each fixture also carries its own `_comment` explaining why that
    world matters, and several carry an `expect` block asserted verbatim below.
    """
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def home_from_fixture(td: Path, name: str) -> tuple[Path, dict]:
    fx = load_fixture(name)
    reg = fx.get("registry_raw") if "registry_raw" in fx else fx.get("registry")
    mkt = fx.get("marketplace")
    home = make_home(td, reg, json.dumps(mkt) if mkt is not None else None)
    return home, fx


def registry(version: str, install_path: str = "/nonexistent") -> dict:
    return {"version": 2, "plugins": {"flow@flow": [
        {"scope": "user", "installPath": install_path, "version": version,
         "gitCommitSha": "abcdef1234567890"}]}}


def marketplace_json(version: str) -> str:
    return json.dumps({"name": "flow", "metadata": {"version": version},
                       "plugins": [{"name": "flow", "version": version}]})


def make_root(td: Path, branch_version: str | None, *, flow_marker: bool = True,
              skills: list[str] | None = None, agents: list[str] | None = None) -> Path:
    root = td / "root"
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(marketplace_json("0.0.0"))
    pf = root / "plugins" / "flow"
    (pf / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    if branch_version:
        # `flow_marker` controls the file the predicate ACTUALLY reads: the marker and
        # the version source are the same file by design, so a repo whose
        # plugins/flow/.claude-plugin/plugin.json does not name flow is not a flow
        # checkout and its version is never read.
        name = "flow" if flow_marker else "some-other-plugin"
        (pf / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": name, "version": branch_version}))
    probe = pf / "skills" / "ship" / "lib"
    probe.mkdir(parents=True, exist_ok=True)
    (probe / "manifest-triage.py").write_text("# probe\n")
    for s in skills or []:
        (pf / "skills" / s).mkdir(parents=True, exist_ok=True)
    (pf / "agents").mkdir(parents=True, exist_ok=True)
    for a in agents or []:
        (pf / "agents" / f"{a}.md").write_text("x\n")
    return root


def make_install_tree(td: Path, skills: list[str], agents: list[str]) -> Path:
    it = td / "installed"
    for s in skills:
        (it / "skills" / s).mkdir(parents=True, exist_ok=True)
    (it / "agents").mkdir(parents=True, exist_ok=True)
    for a in agents:
        (it / "agents" / f"{a}.md").write_text("x\n")
    (it / "skills" / "ship" / "lib").mkdir(parents=True, exist_ok=True)
    (it / "skills" / "ship" / "lib" / "manifest-triage.py").write_text("# probe\n")
    return it


def run(home: Path, root: Path, *, as_json: bool = True,
        plugin_root: str | None = None) -> tuple[int, str]:
    env = dict(os.environ)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    if plugin_root is not None:
        env["CLAUDE_PLUGIN_ROOT"] = plugin_root
    cmd = [sys.executable, str(ENGINE), "report", "--home", str(home), "--root", str(root)]
    if as_json:
        cmd.append("--json")
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(root))
    return p.returncode, p.stdout


def jrun(home: Path, root: Path, **kw) -> dict:
    rc, out = run(home, root, as_json=True, **kw)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


# --------------------------------------------------------------------- tests


def test_installed_states():
    """The four unreadable-registry states stay DISTINCT (FB-0082).

    Collapsing them into one "unknown" is how a configuration failure reads as
    "this project simply has none of that" -- the silent-skip class. An empty
    resolution is a failure, not an empty set. Driven by the four committed
    `installed-*.json` fixtures so the covered set is readable.
    """
    seen = {}
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        root = make_root(td, "1.43.0")
        for name in ("installed-missing.json", "installed-malformed.json",
                     "installed-nokey.json", "installed-empty.json"):
            home, _ = home_from_fixture(td / name.replace(".", "_"), name)
            d = jrun(home, root)
            seen[name] = (d.get("installed") or {}).get("state")
    check(len(set(seen.values())) == 4,
          f"the 4 unreadable-registry states must be DISTINCT, got {seen}")
    check(all(v for v in seen.values()), f"every state must be named, got {seen}")
    # POSITIVE pair: the healthy state must be reachable and distinct from all
    # four. A test that only proves failures differ passes in a world where the
    # engine can no longer report success at all (FB-0010 clause 3).
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        home, _ = home_from_fixture(td, "fully-in-sync.json")
        ok = (jrun(home, make_root(td, "1.43.0")).get("installed") or {}).get("state")
    check(ok == "ok", f"a healthy registry must report state 'ok', got {ok!r}")
    check(ok not in seen.values(), "'ok' must differ from every failure state")


def test_executor_arms():
    """libs follow CLAUDE_PLUGIN_ROOT; `!`-blocks always name the installed tree.

    This is the measured asymmetry the whole four-row design rests on: the same
    `${CLAUDE_PLUGIN_ROOT}/...` string resolves to different files depending on
    whether the Bash tool or Claude Code's `!`-expander did the expanding.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        home = make_home(td, registry("1.29.0"), marketplace_json("1.29.0"))
        root = make_root(td, "1.43.0")
        inst = make_install_tree(td, ["ship"], [])

        unset = jrun(home, root)                                   # Bash-tool arm
        setv = jrun(home, root, plugin_root=str(inst))             # !-expander arm

    check((unset.get("libs") or {}).get("state") == "checkout",
          f"CLAUDE_PLUGIN_ROOT unset must resolve libs to the checkout, got {unset.get('libs')}")
    check((setv.get("libs") or {}).get("state") == "installed",
          f"CLAUDE_PLUGIN_ROOT set must resolve libs to the installed tree, got {setv.get('libs')}")
    check((unset.get("libs") or {}).get("state") != (setv.get("libs") or {}).get("state"),
          "the two executor arms must differ — if they agree the four-row design is moot")
    check((unset.get("preprocessor") or {}).get("state") == "installed",
          "!-blocks resolve installed regardless of the Bash-tool env")
    check(unset.get("mixed_provenance") is True,
          "checkout libs + installed !-blocks IS mixed provenance and must be flagged")
    check(setv.get("mixed_provenance") is False,
          "a uniform run must NOT be flagged mixed — the positive pair for the line above")

    # unresolvable: neither tree serves the probe
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        root = td / "bare"
        (root / ".claude-plugin").mkdir(parents=True)
        (root / ".claude-plugin" / "marketplace.json").write_text(marketplace_json("1.0.0"))
        d = jrun(make_home(td, registry("1.29.0"), marketplace_json("1.29.0")), root)
    check((d.get("libs") or {}).get("state") == "unresolved",
          "with no probe lib anywhere, libs must report 'unresolved' — a hard failure, "
          "not staleness")


def test_split_predicates():
    """report_drift and update_available must be computed INDEPENDENTLY.

    Driven by four committed fixtures, each asserted against its OWN `expect`
    block -- so the expected values live next to the world that produces them and
    a reader can see the disagreement case without running anything.

    The load-bearing one is `branch-ahead-marketplace-insync`: the case that
    actually occurred. Collapsing these predicates into one boolean makes an
    updater fire forever on any feature branch, because a branch declares an
    unreleased version by construction.
    """
    for name in ("branch-ahead-marketplace-insync.json", "fully-in-sync.json",
                 "marketplace-ahead.json", "clone-absent.json"):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            home, fx = home_from_fixture(td, name)
            d = jrun(home, make_root(td, fx.get("branch_version", "1.43.0")))
        for field, want in (fx.get("expect") or {}).items():
            got = d.get(field)
            check(got is want if want is None or isinstance(want, bool) else got == want,
                  f"{name}: {field} must be {want!r}, got {got!r}")
    check(bool(load_fixture("branch-ahead-marketplace-insync.json").get("expect")),
          "the disagreement fixture must declare an expect block, or it asserts nothing")


def test_row_labels():
    """All four labels present, and no unlabelled version row.

    Asserted by LABEL, never by count: revision 1 of the plan pinned "exactly
    THREE rows" and was already stale by the time it was reviewed. A pinned count
    is itself a fan-out value (FB-0010 clause 2).
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        rc, out = run(make_home(td, registry("1.29.0"), marketplace_json("1.29.0")),
                      make_root(td, "1.43.0"), as_json=False)
    check(rc == 0, f"report must exit 0, got {rc}")
    for lab in ROW_LABELS:
        check(lab in out, f"row label missing from the rendered report: {lab!r}")
    check("| Flow — plugin version |" not in out,
          "an unlabelled 'plugin version' row is the ambiguity this engine removes")


def test_both_polarities():
    """Every row renders an affirmative when healthy AND a warning when not.

    FB-0010 clause 3: a warning alone is a negative assertion, satisfiable by
    deleting the row. It passes in two opposite worlds — "no drift" and "the row
    is gone" — so the positive it protects has to be asserted too. Not
    hypothetical here: `skill-does-not-CALL-land` was exactly this shape without
    its pair and stayed green over a deleted feature for four releases.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        _, drift = run(make_home(td / "d", registry("1.29.0"), marketplace_json("1.41.0")),
                       make_root(td / "d", "1.43.0"), as_json=False)
        inst = make_install_tree(td / "s", ["ship"], [])
        _, clean = run(make_home(td / "s", registry("1.43.0"), marketplace_json("1.43.0")),
                       make_root(td / "s", "1.43.0"), as_json=False,
                       plugin_root=str(inst))

    for lab in ROW_LABELS:
        drow = next((l for l in drift.splitlines() if lab in l), "")
        crow = next((l for l in clean.splitlines() if lab in l), "")
        check("⚠️" in drow, f"drift run: row {lab!r} must carry a warning, got {drow!r}")
        check("✓" in crow, f"clean run: row {lab!r} must carry an affirmative, got {crow!r}")
        check("⚠️" not in crow, f"clean run: row {lab!r} must NOT warn, got {crow!r}")


def test_running_version_beats_the_registry():
    """What RAN is read from PATH, not from the registry — they can disagree.

    Found live, in this engine's own ship run. `claude plugin update` rewrites the
    registry immediately but "requires a restart to apply", so a session that started
    before the update keeps executing the OLD tree while the registry advertises the
    new one. Observed: registry 1.41.0, session still running 1.29.0, both version
    directories present in the cache. The headline row — labelled "the version that
    ran this pipeline" — was reporting a version that had not run: exactly the failure
    this module exists to prevent, reproduced inside it.

    PATH is the reliable signal because Claude Code prepends the resolved plugin's
    `bin` directory at session start, pinning it to what the process actually loaded.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        home = make_home(td, registry("1.41.0"), marketplace_json("1.41.0"))
        root = make_root(td, "1.43.0")
        binp = home / ".claude" / "plugins" / "cache" / "flow" / "flow" / "1.29.0" / "bin"
        binp.mkdir(parents=True, exist_ok=True)
        env_path = f"{binp}{os.pathsep}/usr/bin"

        def with_path(as_json):
            env = dict(os.environ, PATH=env_path, HOME=str(home))
            env.pop("CLAUDE_PLUGIN_ROOT", None)
            cmd = [sys.executable, str(ENGINE), "report", "--home", str(home),
                   "--root", str(root)] + (["--json"] if as_json else [])
            return subprocess.run(cmd, capture_output=True, text=True, env=env,
                                  cwd=str(root)).stdout

        d = json.loads(with_path(True))
        out = with_path(False)

    check(d.get("ran_version") == "1.29.0",
          f"the RUNNING version must come from PATH, got {d.get('ran_version')!r}")
    check(d.get("ran_version_source") == "PATH",
          f"source must be PATH when derivable, got {d.get('ran_version_source')!r}")
    check((d.get("installed") or {}).get("version") == "1.41.0",
          "the registry value must still be reported — both facts matter")
    check(d.get("restart_pending") is True,
          "a registry/PATH disagreement IS the restart-pending state and must be named")
    check(d.get("release_gap") == 14,
          f"the gap must measure what RAN against the branch, got {d.get('release_gap')}")
    check("1.29.0" in out.splitlines()[0],
          f"the headline row must show the version that RAN:\n{out.splitlines()[0]}")
    check("NOT applied" in out,
          "the installed-but-unapplied update must be stated, not silently dropped")

    # POSITIVE pair: with no plugin bin on PATH the engine falls back to the registry
    # and SAYS it did, rather than silently reporting a version it cannot source.
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        home = make_home(td, registry("1.41.0"), marketplace_json("1.41.0"))
        root = make_root(td, "1.43.0")
        d2 = jrun(home, root)
    check(d2.get("ran_version") == "1.41.0",
          "with no PATH signal, fall back to the registry")
    check(d2.get("ran_version_source") == "registry",
          f"the fallback must be LABELLED, got {d2.get('ran_version_source')!r}")
    check(d2.get("restart_pending") is False,
          "no disagreement is possible when there is only one source")


def test_healthy_run_does_not_cry_wolf():
    """The EXPECTED steady state of every flow branch must not warn.

    A flow feature branch declares the next, unreleased minor, so `report_drift` is
    true on every branch by construction. An earlier draft keyed the ⚠️ on that, which
    made all four rows warn on every healthy PR forever -- violating the engine's own
    stated rule ("a permanent warning is indistinguishable from the real staleness
    signal this exists to surface") at the render while honouring it in the predicate.
    A reader who sees four warnings on twenty consecutive PRs stops reading them, and
    then the genuine 14-release gap arrives looking exactly like healthy.

    The discriminator is `release_gap`, NOT `update_available` -- and that distinction
    is the point of this test. In the real failure this engine exists to expose, the
    marketplace clone was pinned at the same stale commit as the install, so
    `update_available` was FALSE. Keying severity on it would render the flagship
    failure as informational. Both directions are asserted below, because either one
    alone passes on a renderer that is uniformly quiet or uniformly loud.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        inst = make_install_tree(td / "h", ["ship"], ["auditor"])
        # HEALTHY: install == marketplace == latest release; branch one minor ahead.
        healthy = make_home(td / "h", registry("1.42.0", install_path=str(inst)),
                            marketplace_json("1.42.0"))
        root = make_root(td / "h", "1.43.0", skills=["ship"], agents=["auditor"])
        _, out = run(healthy, root, as_json=False, plugin_root=str(inst))
        d = jrun(healthy, root, plugin_root=str(inst))
    check(d.get("report_drift") is True,
          "the healthy branch case must still REPORT drift in JSON — the fix is about "
          "severity in the render, not about hiding the fact")
    check(d.get("release_gap") == 1, f"healthy gap must be 1, got {d.get('release_gap')}")
    check("⚠️" not in out,
          f"a current install one unreleased minor behind must NOT warn, got:\n{out}")
    check("ℹ️" in out, "the expected-unreleased case must be stated, not silently dropped")
    check("not released yet" in out,
          "the informational note must say WHY it is expected")
    check("claude plugin marketplace update" not in out,
          "no remedy footnote on a healthy run — there is nothing to remedy")

    # STALE, with update_available FALSE (the real 1.29.0 shape: clone pinned too).
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        inst = make_install_tree(td / "s", ["ship"], ["auditor"])
        stale = make_home(td / "s", registry("1.29.0", install_path=str(inst)),
                          marketplace_json("1.29.0"))
        root = make_root(td / "s", "1.43.0", skills=["ship"], agents=["auditor"])
        d2 = jrun(stale, root)
        _, out2 = run(stale, root, as_json=False)
    check(d2.get("update_available") is False,
          "this fixture's whole point: nothing newer to fetch LOCALLY, yet 14 releases behind")
    check("⚠️" in out2,
          f"a 14-release gap MUST warn even though update_available is False:\n{out2}")
    check("claude plugin marketplace update" in out2,
          "a warning run must carry the remedy footnote — a warning a reader cannot act "
          "on teaches them to ignore warnings")
    check("restart" in out2.lower(),
          "the drift note must say updating cannot fix THIS run")


def test_no_internal_state_leaks_to_the_reader():
    """No raw state identifier reaches the rendered report.

    FB-0082 keeps `registry_absent` / `registry_malformed` / `plugin_absent` /
    `no_versions` DISTINCT in code. An earlier draft rendered all four behind one
    sentence plus the raw token, so to a reader they WERE one state -- the same rule
    violated one layer up, in the copy. FB-0075 sets the bar for this surface: plain
    language for a reader who is not an engineer.
    """
    raw = ("registry_absent", "registry_malformed", "plugin_absent", "no_versions",
           "clone_absent", "clone_malformed", "not_flow_checkout")
    seen_sentences = set()
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        root = make_root(td, "1.43.0")
        for name in ("installed-missing.json", "installed-malformed.json",
                     "installed-nokey.json", "installed-empty.json",
                     "clone-absent.json"):
            home, _ = home_from_fixture(td / name.replace(".", "_"), name)
            _, out = run(home, root, as_json=False)
            for tok in raw:
                check(tok not in out,
                      f"{name}: raw state {tok!r} must not reach the reader — map it to "
                      f"a plain sentence")
            first = next((l for l in out.splitlines() if "⚠️" in l), "")
            seen_sentences.add(first.split("|")[-2].strip() if "|" in first else first)
    # POSITIVE pair: the plain sentences must actually DIFFER per state, or the map has
    # merely renamed one collapsed message.
    check(len(seen_sentences) >= 4,
          f"the unreadable states must render DISTINCT sentences, got "
          f"{len(seen_sentences)}: {seen_sentences}")


def test_callout_splits_rule_skills_from_command_skills():
    """An absent rule-skill and an absent command skill fail DIFFERENTLY.

    A rule-skill auto-loads on matching paths; nothing invokes it, so "a model asked to
    run one would conclude it does not exist" is simply untrue of it. Its real
    consequence is stronger: the rules meant to govern the run were never applied. An
    earlier draft attached only the milder consequence, to a live list in which four of
    five entries were rule-skills.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        inst = make_install_tree(td, ["ship"], ["auditor"])
        home = make_home(td, registry("1.29.0", install_path=str(inst)),
                         marketplace_json("1.29.0"))
        root = make_root(td, "1.43.0", skills=["ship", "a-rule", "a-command"],
                         agents=["auditor"])
        # a-rule carries `paths:` in frontmatter; a-command does not.
        sk = root / "plugins" / "flow" / "skills"
        (sk / "a-rule" / "SKILL.md").write_text(
            "---\nname: a-rule\npaths:\n  - '**/*.py'\n---\nbody\n")
        (sk / "a-command" / "SKILL.md").write_text(
            "---\nname: a-command\ndescription: does a thing\n---\nbody\n")
        _, out = run(home, root, as_json=False)
    check("Rule-skills that did NOT load" in out,
          f"the callout must name the rule-skill failure mode:\n{out}")
    check("not governed by them" in out,
          "the rule-skill consequence must be that the run was ungoverned")
    check("a-rule" in out and "a-command" in out, "both skills must be listed")
    rule_line = next((l for l in out.splitlines() if "Rule-skills" in l), "")
    cmd_line = next((l for l in out.splitlines() if "not invocable" in l), "")
    check("a-rule" in rule_line and "a-command" not in rule_line,
          f"a-rule belongs in the rule-skill bullet only, got {rule_line!r}")
    check("a-command" in cmd_line and "a-rule" not in cmd_line,
          f"a-command belongs in the command bullet only, got {cmd_line!r}")
    # NEGATIVE pair: a `paths:` in PROSE must not promote a command skill.
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        inst = make_install_tree(td, ["ship"], [])
        root = make_root(td, "1.43.0", skills=["ship", "prose-only"])
        (root / "plugins" / "flow" / "skills" / "prose-only" / "SKILL.md").write_text(
            "---\nname: prose-only\n---\nSome body text mentioning paths: nope\n")
        _, out2 = run(make_home(td, registry("1.29.0", install_path=str(inst)),
                                marketplace_json("1.29.0")), root, as_json=False)
    check("prose-only" in out2, "the skill must still be listed")
    rl = next((l for l in out2.splitlines() if "Rule-skills" in l), "")
    check("prose-only" not in rl,
          "a `paths:` in prose must not promote a command skill to rule-skill")


def test_graceful_degradation():
    """Never a traceback, never an empty report -- always a labelled row saying what
    could not be determined. A provenance reporter that crashes fails a ship over a
    documentation line; one that prints a blank row is worse, because blank reads as
    "nothing to report" when the truth is "could not tell".

    Driven by the committed fixtures rather than a second inline copy of the same
    worlds -- the harness's own principle, and it picks up `installed-empty.json`
    (the `no_versions` world) which the inline version never rendered.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        root = make_root(td, "1.43.0")
        for name in ("installed-missing.json", "installed-malformed.json",
                     "installed-nokey.json", "installed-empty.json",
                     "clone-absent.json"):
            home, _ = home_from_fixture(td / name.replace(".", "_"), name)
            rc, out = run(home, root, as_json=False)
            check(rc == 0, f"{name}: must exit 0, got {rc}")
            check(out.strip() != "", f"{name}: must not print an empty report")
            check("⚠️" in out, f"{name}: must say loudly what it could not read")
            check("Traceback" not in out, f"{name}: must not leak a traceback")
            for lab in ROW_LABELS:
                check(lab in out, f"{name}: row {lab!r} must still render")


def test_decoy_repo_refused():
    """A repo whose flow plugin manifest does not name flow gets no version read.

    WHAT THIS ESTABLISHES, and what it does not. The marker is
    `plugins/flow/.claude-plugin/plugin.json` naming flow -- the same spelling the 12
    existing shipped call sites use. So a reviewed repo that ships no such manifest,
    or one naming a different plugin, is correctly refused: that is what is asserted
    below.

    It does NOT establish that a FORGED manifest is distinguished. A hostile repo can
    commit `plugins/flow/.claude-plugin/plugin.json` with `"name": "flow"` and this
    reader will report its version. That is a pre-existing limitation of the marker
    idiom across all 13 sites, not something this engine introduced, and roadmap:309
    already tracks the real fix (gate on `git config --get remote.origin.url` rather
    than on a committed file's contents). Stated here rather than left implied,
    because a test named "decoy refused" would otherwise imply a guarantee the marker
    cannot give. The exposure is bounded: this engine only READS a version string, it
    never executes anything from the reviewed repo.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        decoy = make_root(td, "9.9.9", flow_marker=False)
        home = make_home(td, registry("1.29.0"), marketplace_json("1.29.0"))
        d = jrun(home, decoy)
        rc, out = run(home, decoy, as_json=False)
    check((d.get("branch") or {}).get("state") == "not_flow_checkout",
          f"a non-flow checkout must report not_flow_checkout, got {d.get('branch')}")
    check("9.9.9" not in json.dumps(d), "the decoy version must never be read")
    check("9.9.9" not in out, "the decoy version must never be rendered")
    check(rc == 0 and out.strip(), "a consumer project still gets a real report")


def test_surface_drift():
    """Skills/agents the branch declares that the installed tree lacks.

    Harder than staleness: absent from the registry means the runtime has no tool
    for them, and a model asked to run one concludes the skill does not exist.
    This comparison is also the reason "always run from the working tree" is the
    wrong blanket fix — bypassing installation makes the whole packaging/loading
    class unobservable rather than fixed.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        inst = make_install_tree(td, ["ship", "doctor"], ["auditor"])
        home = make_home(td, registry("1.29.0", install_path=str(inst)),
                         marketplace_json("1.29.0"))
        root = make_root(td, "1.43.0", skills=["ship", "doctor", "exploration", "general"],
                         agents=["auditor", "lens-experience"])
        d = jrun(home, root)
        rc, out = run(home, root, as_json=False)
    sd = d.get("surface_drift") or {}
    check(sd.get("state") == "ok", f"surface drift must resolve, got {sd.get('state')}")
    check(sd.get("skills_missing_from_installed") == ["exploration", "general"],
          f"missing skills wrong: {sd.get('skills_missing_from_installed')}")
    check(sd.get("agents_missing_from_installed") == ["lens-experience"],
          f"missing agents wrong: {sd.get('agents_missing_from_installed')}")
    check("flow:provenance" in out and "exploration" in out and "lens-experience" in out,
          "the un-invocable callout must NAME every missing surface, not summarise a count")
    # POSITIVE pair: with the trees aligned the callout must be ABSENT, so the
    # assertion above cannot be satisfied by an engine that always emits it.
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        inst = make_install_tree(td, ["ship"], ["auditor"])
        _, out2 = run(make_home(td, registry("1.43.0", install_path=str(inst)),
                                marketplace_json("1.43.0")),
                      make_root(td, "1.43.0", skills=["ship"], agents=["auditor"]),
                      as_json=False)
    check("flow:provenance" not in out2,
          "aligned trees must emit NO un-invocable callout")


def test_contracts():
    """Both ship and ship-spike carry the rows and call the engine.

    Looping BOTH files, deliberately. FB-0100's guards were first pinned against
    the SPIKE copy only, leaving ship — the original the copy was made from —
    free to drop the same property with the harness still green. A one-sided pin
    on a two-sided duplication is not a pin.
    """
    for name, path in (("ship", SHIP), ("ship-spike", SPIKE)):
        txt = path.read_text(encoding="utf-8")
        check("plugin-provenance.py" in txt,
              f"{name}/SKILL.md must invoke plugin-provenance.py")
        for lab in ROW_LABELS:
            check(lab in txt, f"{name}/SKILL.md must carry the row label {lab!r}")
        # The installed-else-checkout fallback is NOT optional: CLAUDE_PLUGIN_ROOT
        # is unset in Bash-tool calls, so a bare ${CLAUDE_PLUGIN_ROOT} path fails
        # outright in the flow repo itself.
        check("plugins/flow/skills/ship/lib/plugin-provenance.py" in txt,
              f"{name}/SKILL.md must carry the checkout fallback for the engine path")


def hook_body() -> list[str]:
    """The hook's non-comment lines. Two contract tests need this; the hook
    deliberately NAMES forbidden patterns in comments (e.g. CLAUDE_CODE_REMOTE,
    explaining that gating on it is the bug #116 fixed), so a check that scanned the
    whole file would forbid documenting the hazard."""
    return [l for l in HOOK.read_text(encoding="utf-8").splitlines()
            if not l.strip().startswith("#")]


def test_hook_never_executes_the_checkout():
    """The SessionStart hook must resolve its engine from the INSTALLED tree only.

    SECURITY. This hook fires automatically with no approval prompt, and the approved
    command string in settings.json does not change when repo content does. A
    checkout-resolved engine would therefore make `gh pr checkout <external-PR>` plus a
    new session equal arbitrary code execution as the user — and flow takes external
    PRs, so that is a live path.

    Paired assertions (FB-0010 clause 3): the negative alone would pass on a hook that
    resolves no engine at all.
    """
    body = "\n".join(hook_body())
    check("installed_plugins.json" in body,
          "the hook must resolve the engine via the installed-plugin registry")
    check("installPath" in body,
          "the engine path must come from the registry's installPath, not from the repo")
    # NEGATIVE: no repo-relative engine path in executable code.
    check("plugins/flow/skills/ship/lib/plugin-provenance.py" not in body,
          "the hook must NOT name a checkout-relative engine path in executable code — "
          "that is the arbitrary-code-execution path")
    check("NOT falling back" in HOOK.read_text(encoding="utf-8"),
          "the refusal must be explained where the next maintainer will read it")


def test_version_string_cannot_forge_the_table():
    """A reviewed repo cannot inject markdown into the provenance table.

    The version in `plugins/flow/.claude-plugin/plugin.json` is controlled by the
    repository under review, and ship pastes this renderer's stdout verbatim into the
    PR body. Unsanitised, a contributor could close the cell and render a forged
    "✓ matches this branch" row while `<!--` swallowed the real warnings into an HTML
    comment — reproduced before the fix. FB-0107 designates the PR body as where a
    reviewer forms the belief that a gate ran, so forging it is the confidence
    inversion this whole module exists to prevent.
    """
    payload = ("1.0.0 | X |\n| Flow version that ran this pipeline | 9.9.9 | "
               "✓ matches this branch |\n<!-- ")
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        root = make_root(td, "1.0.0")
        (root / "plugins" / "flow" / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "flow", "version": payload}))
        home = make_home(td, registry("1.29.0"), marketplace_json("1.29.0"))
        rc, out = run(home, root, as_json=False)
        d = jrun(home, root)
    check(rc == 0, "a hostile version string must not crash the reporter")
    check("<!--" not in out, "the payload must not open an HTML comment")
    check("| 9.9.9 |" not in out, "the payload must not forge a table row")
    rows = [l for l in out.splitlines() if l.startswith("|")]
    labelled = [l for l in rows if any(lab in l for lab in ROW_LABELS)
                or "New skills + agents" in l]
    check(len(rows) == len(labelled),
          f"every rendered row must carry a known label; got {len(rows)} rows, "
          f"{len(labelled)} labelled:\n{out}")
    check("|" not in (d.get("branch") or {}).get("version", ""),
          "the delimiter must be stripped at READ time, not just at render time")
    check("\n" not in (d.get("branch") or {}).get("version", ""),
          "newlines must be stripped at read time")


def test_hook_single_predicate():
    """The hook asks the engine; it does not re-derive the comparison.

    doctor's first cut at a shared predicate re-derived it inline, and the two
    copies disagreed inside a single commit — one identical on-disk state
    producing [PASS] in one surface and ⚠️ in another.
    """
    txt = HOOK.read_text(encoding="utf-8")
    check("plugin-provenance.py" in txt, "the hook must call the provenance engine")
    check("update_available" in txt, "the hook must read update_available from the engine")
    check("report_drift" in txt,
          "the hook must also READ report_drift — it is the only in-session surface "
          "resolved from the checkout, so the only one that can report drift on a "
          "session whose installed prose is too old to")
    body = "\n".join(hook_body())
    check('"$INST" = "$MKT"' not in body and '"$INST" != "$MKT"' not in body,
          "the hook must not compare versions itself — one predicate, one place")


def test_hook_loud_failure():
    """`claude plugin update` is the one command that must fail LOUD.

    It is the line that pulls marketplace HEAD, so swallowing its exit status
    makes a hijacked or unreachable marketplace indistinguishable from a clean
    run. A silent-on-failure auto-updater is strictly worse than none: it
    manufactures confidence about the version, which is FB-0107's failure shape
    one level up. Ported from health-tracker#116 with its rationale.
    """
    txt = HOOK.read_text(encoding="utf-8")
    body = hook_body()
    upd = [l for l in body if "plugin update flow@flow" in l]
    check(bool(upd), "the hook must invoke `plugin update flow@flow`")
    # POSITIVE: the failure branch and its warning exist.
    check(any("if ! " in l and "plugin update flow@flow" in l for l in upd),
          "the update must sit inside an `if ! ...` failure branch")
    check("FAILED" in txt and "Do NOT assume" in txt,
          "a failed update must print a warning naming what may be stale")
    # NEGATIVE, paired with the positives above: never swallowed.
    for l in upd:
        check("|| true" not in l,
              f"the update must NOT be suffixed `|| true`: {l.strip()!r}")
    # The gate is ground truth, not an env var (the FB-0085 lesson).
    check("plugins/flow/.claude-plugin/plugin.json" in txt and '"name"' in txt,
          "the hook must gate on the repo marker file — and on the SAME spelling the 12 "
          "existing shipped sites use, or it is invisible to the eval that guards this "
          "predicate")
    # Against the non-comment BODY: the hook deliberately NAMES this variable in a
    # comment, explaining that gating on it is the bug #116 fixed. A check that
    # forbade the string outright would forbid documenting the hazard, which is
    # the opposite of what it is for.
    check("CLAUDE_CODE_REMOTE" not in "\n".join(body),
          "the env-var gate is the bug #116 fixed — do not reintroduce it in executable code")
    # It must never wedge a session start.
    check(txt.rstrip().endswith("exit 0"), "the hook must end with `exit 0`")


def make_home_with_engine(td: Path, version: str, mkt_version: str) -> Path:
    """A synthetic HOME whose INSTALLED tree actually contains the engine.

    Required since the hook was hardened to resolve its engine only from the installed
    plugin (never from the checkout — see test_hook_never_executes_the_checkout). A
    fixture without an installed engine now exercises the refusal path, not the
    behaviour under test, so the two must be built differently and deliberately.
    """
    inst = td / "cachetree"
    lib = inst / "skills" / "ship" / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    (lib / "plugin-provenance.py").write_text(ENGINE.read_text(encoding="utf-8"))
    (lib / "manifest-triage.py").write_text("# probe\n")
    return make_home(td, registry(version, install_path=str(inst)),
                     marketplace_json(mkt_version))


def _hook_driver(td: Path):
    """Shared PATH-shim `claude` that LOGS its invocations, so 'attempted no
    update' is asserted against a real call log rather than inferred from output.
    """
    shim = td / "bin"
    shim.mkdir(exist_ok=True)
    log = td / "calls.log"
    (shim / "claude").write_text(
        "#!/bin/bash\necho \"claude $*\" >> %s\n"
        "case \"$*\" in\n"
        "  'plugin update'*) [ \"$FAIL_UPDATE\" = 1 ] && exit 1 ; exit 0 ;;\n"
        "  *) exit 0 ;;\nesac\n" % log)
    (shim / "claude").chmod(0o755)

    def drive(home: Path, *, cwd: Path, fail: bool = False, dry: bool = False,
              strip_path: bool = False, hide_engine: bool = False):
        log.write_text("")
        if strip_path:
            # Drop only the directories that PROVIDE `claude`, keeping bash and
            # python3 reachable. A blanket PATH wipe would test "the harness
            # cannot start" rather than "the hook handles an absent claude" --
            # a green-looking test of the wrong thing.
            path = os.pathsep.join(
                d for d in os.environ["PATH"].split(os.pathsep)
                if d and not os.path.exists(os.path.join(d, "claude")))
        else:
            path = f"{shim}{os.pathsep}{os.environ['PATH']}"
        env = dict(os.environ, PATH=path, HOME=str(home))
        if fail:
            env["FAIL_UPDATE"] = "1"
        if dry:
            env["FLOW_CURRENCY_DRY_RUN"] = "1"
        run_cwd = cwd
        if hide_engine:
            # A checkout that IS flow but has no engine: the hook must say it cannot
            # tell, not assume "current". It must satisfy the hook's gate (the flow
            # plugin manifest naming flow) while lacking the engine — otherwise the
            # hook exits at the gate and this asserts nothing.
            run_cwd = td / "noengine"
            (run_cwd / "plugins" / "flow" / ".claude-plugin").mkdir(parents=True, exist_ok=True)
            (run_cwd / "plugins" / "flow" / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "flow", "version": "1.43.0"}))
        p = subprocess.run(["bash", str(HOOK)], capture_output=True, text=True,
                           env=env, cwd=str(run_cwd))
        calls = [l for l in log.read_text().splitlines() if l.strip()]
        return p.returncode, p.stdout, p.stderr, calls

    return drive


def test_hook_fast_path():
    """Outside the flow checkout, and when already current, the hook does nothing.

    "Attempted no update" is asserted against the shim's CALL LOG, not inferred
    from quiet output -- silence and inaction are different claims.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        drive = _hook_driver(td)
        other = td / "other"
        other.mkdir()
        # Built from the LIVE declared version, not a fixture, so a release bump
        # cannot turn "a current install must be silent" red.
        live = live_branch_version()
        home = make_home_with_engine(td / "s1", live, live)

        rc, so, se, calls = drive(home, cwd=other)
        check(rc == 0 and so == "" and se == "" and calls == [],
              f"outside the flow checkout the hook must do nothing, got rc={rc} "
              f"out={so!r} err={se!r} calls={calls}")

        rc, so, se, calls = drive(home, cwd=REPO)
        check(rc == 0, f"fast path must exit 0, got {rc}")
        check(so == "", f"the hook must never write to stdout, got {so!r}")
        check(se == "", f"a current install must be silent, got {se!r}")
        check(not any("plugin update" in c for c in calls),
              f"a current install must attempt NO plugin update, got {calls}")

        # POSITIVE pair: with an update genuinely available it MUST act -- else
        # "attempted no update" would pass in a world where it never updates.
        home2 = make_home_with_engine(td / "s2", "1.29.0", "1.43.0")
        rc, so, se, calls = drive(home2, cwd=REPO)
        check(rc == 0 and so == "", f"update path: rc={rc} stdout={so!r}")
        check(any("plugin update flow@flow" in c for c in calls),
              f"an available update must be applied, got {calls}")
        check("restart required" in se,
              "the hook must state that THIS session is not fixed by the update")


def test_hook_dry_run():
    """FLOW_CURRENCY_DRY_RUN mutates nothing and is NOT silent even when current.

    The dry run exists because the real update is not freely re-runnable in the
    workspace where the evidence lives -- applying it destroys the only record of
    the stale state. It reports unconditionally: without the clone refresh the
    comparison is computed against possibly-pinned local data, so a silent exit
    is the one output a dry run must never produce, being indistinguishable from
    "verified current".
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        drive = _hook_driver(td)
        live = live_branch_version()
        home = make_home_with_engine(td, live, live)
        rc, so, se, calls = drive(home, cwd=REPO, dry=True)
    check(rc == 0 and so == "", f"dry run: rc={rc} stdout={so!r}")
    check("dry-run" in se, "dry run must announce itself")
    check(calls == [], f"dry run must invoke NOTHING, got {calls}")
    check("restart required" in se, "dry run must still surface the restart caveat")


def test_hook_degrades_safely():
    """Absent `claude`, absent engine, and a failing update: loud, and exit 0.

    A session start must never be wedged, and it must never be quietly wrong.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        drive = _hook_driver(td)
        home = make_home_with_engine(td / "d1", "1.29.0", "1.43.0")

        rc, so, se, calls = drive(home, cwd=REPO, fail=True)
        check(rc == 0, f"a failed update must still exit 0, got {rc}")
        check("FAILED" in se and "Do NOT assume" in se,
              f"a failed update must be loud, got {se!r}")

        rc, so, se, calls = drive(home, cwd=REPO, strip_path=True)
        check(rc == 0, f"absent claude must still exit 0, got {rc}")
        check("not on PATH" in se, f"absent claude must be loud, got {se!r}")
        check(calls == [], "absent claude must invoke nothing")

        # No engine in the INSTALLED tree: the hook must refuse rather than fall back
        # to the checkout copy, and must say why.
        bare = make_home(td / "d2", registry("1.29.0"), marketplace_json("1.43.0"))
        rc, so, se, calls = drive(bare, cwd=REPO)
        check(rc == 0, f"absent installed engine must still exit 0, got {rc}")
        check("NOT falling back" in se,
              f"absent installed engine must refuse the checkout copy loudly, got {se!r}")
        check(not any("plugin update" in c for c in calls),
              "with no engine the hook must not blind-update")


def test_hook_field_parse_no_shift():
    """An EMPTY field must not shift the fields after it.

    Found by driving the hook against a malformed registry: the field list was
    tab-delimited, tab is an IFS *whitespace* character, so `read` collapsed runs of
    it and a missing installed version silently vanished -- shifting every later
    field left, so the warning reported the MARKETPLACE version as the installed
    one. The predicate is field 1 and was unaffected, so the impact was cosmetic --
    but a shifted version number inside a diagnostic *about version confusion* is
    the worst place for one, and FB-0082's rule is that `absent` must stay
    distinguishable rather than quietly becoming another value.

    Two paired assertions, because the positive alone would pass on a tab-delimited
    implementation that merely happened to have no empty fields in the fixture.
    """
    txt = HOOK.read_text(encoding="utf-8")
    check("IFS='|'" in txt,
          "the field split must use a NON-whitespace delimiter, or empty fields collapse")
    check('IFS="$(printf \'\\t\')" read -r AVAIL' not in txt,
          "the tab-delimited field read must not come back — it drops empty fields")

    # Behavioural: a registry with no readable version must report the install as
    # unreadable and must NOT print the marketplace version in its place.
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        drive = _hook_driver(td)
        # A PARSEABLE registry whose entry records no version: installPath still
        # resolves (so the hook finds the installed engine and reaches the field
        # parse), while `installed.version` comes back empty — the exact empty-field
        # case. A corrupt registry cannot be used here: the hook would fail to resolve
        # installPath and refuse before parsing anything, testing the refusal path
        # instead of the parse.
        home = make_home_with_engine(td / "bad", "1.29.0", "9.9.9")
        reg = home / ".claude" / "plugins" / "installed_plugins.json"
        d = json.loads(reg.read_text())
        d["plugins"]["flow@flow"][0].pop("version")
        reg.write_text(json.dumps(d))
        rc, so, se, calls = drive(home, cwd=REPO)
    check(rc == 0, f"an unreadable registry must still exit 0, got {rc}")
    check("unreadable" in se,
          f"an unreadable install must be NAMED unreadable, got {se!r}")
    check("installed (9.9.9)" not in se,
          "the marketplace version must never be printed as the installed version "
          "(the field-shift bug)")
    check("UNKNOWN" in se and "same as 'no'" in se.lower().replace("not ", "not "),
          "an undeterminable comparison must say UNKNOWN and explicitly distinguish "
          f"itself from 'no', got {se!r}")
    check(not any("plugin update" in c for c in calls),
          f"an undeterminable comparison must not blind-update, got {calls}")


def test_capture_fixture():
    """The one-shot capture is internally consistent and carries no host paths.

    Asserted, never re-derived: this state cannot be reproduced (the workspace
    updates itself away from it and a CI runner never had it), so the check is
    that the committed artifact says what the PR claims it says.
    """
    if not check(CAPTURE.exists(), f"the one-shot capture is missing: {CAPTURE}"):
        return
    raw = CAPTURE.read_text(encoding="utf-8")
    d = json.loads(raw)
    p = d.get("provenance") or {}
    check((p.get("installed") or {}).get("version") == "1.29.0",
          "the capture must record installed 1.29.0")
    check((p.get("marketplace_head") or {}).get("version") == "1.29.0",
          "the capture must record marketplace HEAD 1.29.0 (the clone was pinned too)")
    check((p.get("branch") or {}).get("version") == "1.41.0",
          "the capture must record the branch version at capture time")
    check((p.get("libs") or {}).get("state") == "checkout",
          "the capture must record libs resolving from the working tree")
    check((p.get("preprocessor") or {}).get("state") == "installed",
          "the capture must record !-blocks resolving from the installed tree")
    check(p.get("report_drift") is True and p.get("update_available") is False,
          "the capture's whole point is report_drift=True with update_available=False")
    check(p.get("release_gap") == 12, "the capture must record the 12-release gap")
    sd = p.get("surface_drift") or {}
    check(sd.get("skills_missing_from_installed") ==
          ["documentation", "exploration", "general", "plan-discipline", "review-brief"],
          "the capture must list the 5 un-invocable skills")
    check(sd.get("agents_missing_from_installed") == ["lens-experience"],
          "the capture must list the un-invocable agent")
    check("/home/" not in raw and "vercel-sandbox" not in raw,
          "a committed fixture must not carry an absolute home path")


def test_ci_wired():
    """This harness must actually run in CI. An eval nobody executes is not a pin
    — it is a file that looks like one."""
    ci = REPO / ".github" / "workflows" / "ci.yml"
    if not check(ci.exists(), "ci.yml missing"):
        return
    check("run_plugin_provenance_evals.py" in ci.read_text(encoding="utf-8"),
          "run_plugin_provenance_evals.py must be wired into .github/workflows/ci.yml")


def main() -> int:
    for fn in (test_installed_states, test_executor_arms, test_split_predicates,
               test_running_version_beats_the_registry,
               test_healthy_run_does_not_cry_wolf,
               test_no_internal_state_leaks_to_the_reader,
               test_callout_splits_rule_skills_from_command_skills,
               test_row_labels, test_both_polarities, test_graceful_degradation,
               test_decoy_repo_refused, test_surface_drift, test_contracts,
               test_hook_single_predicate, test_hook_loud_failure,
               test_hook_never_executes_the_checkout,
               test_version_string_cannot_forge_the_table,
               test_hook_fast_path, test_hook_dry_run,
               test_hook_degrades_safely, test_hook_field_parse_no_shift,
               test_capture_fixture, test_ci_wired):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{fn.__name__} raised {type(exc).__name__}: {exc}")
    if failures:
        print(f"[plugin-provenance] FAIL — {len(failures)} of {checks} checks failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"[plugin-provenance] PASS — {checks} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
