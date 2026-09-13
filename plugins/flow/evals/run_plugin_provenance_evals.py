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

ROW_LABELS = (
    "Flow — installed version (ran the skills, agents + `!`-blocks)",
    "Flow — marketplace HEAD (what an update would fetch)",
    "Flow — helper libs, fenced Bash blocks",
    "Flow — scripts via `!`-preprocessor blocks",
)

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
    if flow_marker:
        (root / ".claude-plugin" / "marketplace.json").write_text(marketplace_json("0.0.0"))
    else:
        (root / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": "not-flow", "plugins": []}))
    pf = root / "plugins" / "flow"
    (pf / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    if branch_version:
        (pf / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "flow", "version": branch_version}))
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
    check(bool((load_fixture("branch-ahead-marketplace-insync.json").get("expect") or {})),
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


def test_graceful_degradation():
    """Never a traceback, never an empty report — always a labelled row saying
    what could not be determined. A provenance reporter that crashes fails a ship
    over a documentation line; one that prints a blank row is worse, because
    blank reads as 'nothing to report' when the truth is 'could not tell'."""
    cases = {
        "registry absent": (None, marketplace_json("1.43.0")),
        "registry malformed": ("{{{", marketplace_json("1.43.0")),
        "plugin absent": ({"version": 2, "plugins": {}}, marketplace_json("1.43.0")),
        "clone absent": (registry("1.29.0"), None),
    }
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        root = make_root(td, "1.43.0")
        for name, (reg, mkt) in cases.items():
            home = make_home(td / name.replace(" ", "_"), reg, mkt)
            rc, out = run(home, root, as_json=False)
            check(rc == 0, f"{name}: must exit 0, got {rc}")
            check(out.strip() != "", f"{name}: must not print an empty report")
            check("⚠️" in out, f"{name}: must say loudly what it could not read")
            check("Traceback" not in out, f"{name}: must not leak a traceback")
            for lab in ROW_LABELS:
                check(lab in out, f"{name}: row {lab!r} must still render")


def test_decoy_repo_refused():
    """A repo that is not the flow checkout gets no version read out of it.

    The trust boundary roadmap:311 asks for. Without the ground-truth gate this
    reader would happily report a version out of ANY reviewed repository that
    ships a plugins/flow/.claude-plugin/plugin.json.
    """
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        decoy = make_root(td, "9.9.9", flow_marker=False)
        d = jrun(make_home(td, registry("1.29.0"), marketplace_json("1.29.0")), decoy)
        rc, out = run(make_home(td, registry("1.29.0"), marketplace_json("1.29.0")),
                      decoy, as_json=False)
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


def test_hook_single_predicate():
    """The hook asks the engine; it does not re-derive the comparison.

    doctor's first cut at a shared predicate re-derived it inline, and the two
    copies disagreed inside a single commit — one identical on-disk state
    producing [PASS] in one surface and ⚠️ in another.
    """
    txt = HOOK.read_text(encoding="utf-8")
    check("plugin-provenance.py" in txt, "the hook must call the provenance engine")
    check("update_available" in txt, "the hook must read update_available from the engine")
    # It must NOT compare version strings itself.
    body = "\n".join(l for l in txt.splitlines() if not l.strip().startswith("#"))
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
    body = [l for l in txt.splitlines() if not l.strip().startswith("#")]
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
    check("marketplace.json" in txt and '"name"' in txt,
          "the hook must gate on the repo marker, not on an environment variable")
    # Against the non-comment BODY: the hook deliberately NAMES this variable in a
    # comment, explaining that gating on it is the bug #116 fixed. A check that
    # forbade the string outright would forbid documenting the hazard, which is
    # the opposite of what it is for.
    check("CLAUDE_CODE_REMOTE" not in "\n".join(body),
          "the env-var gate is the bug #116 fixed — do not reintroduce it in executable code")
    # It must never wedge a session start.
    check(txt.rstrip().endswith("exit 0"), "the hook must end with `exit 0`")


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
            # A checkout that IS flow but has no engine: the hook must say it
            # cannot tell, not assume "current".
            run_cwd = td / "noengine"
            (run_cwd / ".claude-plugin").mkdir(parents=True, exist_ok=True)
            (run_cwd / ".claude-plugin" / "marketplace.json").write_text(marketplace_json("1.0.0"))
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
        home, _ = home_from_fixture(td / "s1", "fully-in-sync.json")

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
        home2, _ = home_from_fixture(td / "s2", "marketplace-ahead.json")
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
        home, _ = home_from_fixture(td, "fully-in-sync.json")
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
        home, _ = home_from_fixture(td / "d1", "marketplace-ahead.json")

        rc, so, se, calls = drive(home, cwd=REPO, fail=True)
        check(rc == 0, f"a failed update must still exit 0, got {rc}")
        check("FAILED" in se and "Do NOT assume" in se,
              f"a failed update must be loud, got {se!r}")

        rc, so, se, calls = drive(home, cwd=REPO, strip_path=True)
        check(rc == 0, f"absent claude must still exit 0, got {rc}")
        check("not on PATH" in se, f"absent claude must be loud, got {se!r}")
        check(calls == [], "absent claude must invoke nothing")

        rc, so, se, calls = drive(home, cwd=REPO, hide_engine=True)
        check(rc == 0, f"absent engine must still exit 0, got {rc}")
        check("provenance engine missing" in se or "cannot tell" in se,
              f"absent engine must say it cannot tell, got {se!r}")


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
               test_row_labels, test_both_polarities, test_graceful_degradation,
               test_decoy_repo_refused, test_surface_drift, test_contracts,
               test_hook_single_predicate, test_hook_loud_failure,
               test_hook_fast_path, test_hook_dry_run,
               test_hook_degrades_safely, test_capture_fixture, test_ci_wired):
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
