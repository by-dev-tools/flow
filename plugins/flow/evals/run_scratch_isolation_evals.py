#!/usr/bin/env python3
"""
Regression harness for repo-local scratch + handoff stamping (FB-0082).

Two bugs shipped undetected because nothing here exercised them:

  * FORK TRANSPORT — a forked skill cannot see a /tmp handoff the parent wrote, so
    /flow:audit-skips read "no stage report to audit" on every ship from v1.13.0 to
    v1.22.0 and the whole skip-legitimacy gate no-opped silently.
  * CONCURRENT SESSIONS — /tmp/flow-* is one global namespace, so two sessions on two
    projects clobber each other's reviewer inputs (observed: a staff-review lens handed
    another project's diff).

Cases:
  scratch-*   the SHIPPED shell idiom, extracted and EXECUTED: repo-local, per-worktree,
              detached fallback, self-ignoring, concurrent-two-repos isolation. Tested
              via shell, not a Python twin -- an earlier draft tested a parallel Python
              resolver and passed while the shell path production runs was missing the
              self-ignore entirely.
  stamp-*     stamp/check semantics, incl. the four DISTINCT statuses (ok/absent/
              invalid/stale) and fail-closed on an absent stamp.
  block-*     the real audit-skips SKILL.md `!`-block, EXTRACTED AND EXECUTED against
              matching / foreign / absent handoffs. No prior harness executed a
              SKILL.md `!`-block; that is why the transport bug survived.
  contract-*  every shipped scratch site uses the canonical repo-local idiom, and no
              cross-boundary /tmp/flow-* write survives (FB-0010 grep-first defense).
  ci-*        this harness is wired into ci.yml (FB-0056 orphaned-harness lesson).

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import eval_utils

HERE = Path(__file__).parent
FLOW = HERE.parent
SCRATCH_PY = FLOW / "scripts" / "flow_scratch.py"
AUDIT_SKIPS_SKILL = FLOW / "skills" / "audit-skips" / "SKILL.md"
SHIP_SKILL = FLOW / "skills" / "ship" / "SKILL.md"
STAFF_SKILL = FLOW / "skills" / "staff-review" / "SKILL.md"
SEC_SKILL = FLOW / "skills" / "security-review" / "SKILL.md"
A11Y_SKILL = FLOW / "skills" / "accessibility-review" / "SKILL.md"
VERIFY_SKILL = FLOW / "skills" / "verify-build" / "SKILL.md"
REVIEW_BRIEF_SKILL = FLOW / "skills" / "review-brief" / "SKILL.md"
PROTOTYPE_SKILL = FLOW / "skills" / "prototype" / "SKILL.md"
AUDIT_COVERAGE_SKILL = FLOW / "skills" / "audit-coverage" / "SKILL.md"
AUTOPLAN_SKILL = FLOW / "skills" / "autoplan" / "SKILL.md"
SPIKE_SKILL = FLOW / "skills" / "ship-spike" / "SKILL.md"
SCHEMA = FLOW / "schema" / "flow.config.schema.json"
REPO = FLOW.parent.parent
CI = REPO / ".github" / "workflows" / "ci.yml"

_fails = []
_total = 0


def check(label, cond, detail=""):
    global _total
    _total += 1
    if cond:
        print(f"PASS  [{label}]")
    else:
        print(f"FAIL  [{label}] {detail}")
        _fails.append(label)


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


def seed_repo(path, branch="main"):
    """A minimal repo with a resolvable origin/<branch>, mirroring run_merge_status_evals."""
    git(path, "init", "-q", "-b", branch)
    git(path, "config", "user.email", "t@t")
    git(path, "config", "user.name", "t")
    (Path(path) / "a.py").write_text("x = 1\n", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "base")
    git(path, "update-ref", f"refs/remotes/origin/{branch}", "HEAD")
    return path


def run_py(args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRATCH_PY), *args],
        capture_output=True, text=True, cwd=str(cwd), check=False,
    )


def extract_blocks(skill_path):
    """Pull the `!`-block shell out of a SKILL.md (the fork's actual context command).

    Delegates to eval_utils.bang_blocks rather than re-spelling the regex. The local
    copy was the LOOSER form (`!`(.*?)`` + DOTALL) that eval_utils' own docstring names
    as the one of five harnesses that disagreed. Identical output on this file today, so
    the divergence was latent, not visible: one inline `` !`...` `` span added above the
    mechanical block and `blocks[0]` silently becomes that span, executing the wrong
    text while every check stays green.
    """
    return eval_utils.bang_blocks(Path(skill_path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- scratch
SHELL_IDIOM = (
    'FLOW_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)\n'
    '[ -n "$FLOW_ROOT" ] && FLOW_SCRATCH="$FLOW_ROOT/.flow" || FLOW_SCRATCH="${TMPDIR:-/tmp}/flow-detached"\n'
    'mkdir -p "$FLOW_SCRATCH"\n'
    '[ -f "$FLOW_SCRATCH/.gitignore" ] || printf \'# Created by flow. Ephemeral scratch; never committed.\\n*\\n\' > "$FLOW_SCRATCH/.gitignore"\n'
    'printf %s "$FLOW_SCRATCH"\n'
)


def resolve_via_shell(cwd):
    """Run the SHIPPED shell idiom, not a Python re-implementation.

    This distinction is load-bearing. An earlier version of this harness tested a
    parallel `flow_scratch.py` resolver, which passed while the shell path that
    production actually runs went unexercised -- and that path was missing the
    self-ignore entirely. Test the thing that ships.
    """
    r = subprocess.run(["bash", "-c", SHELL_IDIOM], capture_output=True, text=True,
                       cwd=str(cwd), check=False)
    return r.stdout.strip()


def test_scratch():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        seed_repo(a)
        seed_repo(b)

        pa = resolve_via_shell(a)
        pb = resolve_via_shell(b)
        check("scratch-repo-local", pa.endswith("/.flow") and str(Path(a).name) in pa,
              f"expected a repo-local .flow under {a}, got {pa}")

        # THE concurrent-session property: two projects, two scratch dirs, no sharing.
        check("scratch-two-repos-isolated", pa != pb, f"both repos resolved to {pa}")

        # Self-ignoring, so flow never dirties a consumer's git status. Asserted against
        # the SHELL path because that is the one every skill actually runs.
        check("scratch-self-ignores", (Path(pa) / ".gitignore").is_file(),
              "the shell idiom must create .flow/.gitignore")
        st = subprocess.run(["git", "-C", a, "status", "--porcelain"],
                            capture_output=True, text=True).stdout
        check("scratch-clean-status", ".flow" not in st,
              f"scratch dir must not appear in git status, got: {st!r}")

        # Detached (no repo) must not silently produce a repo-shaped shared path.
        with tempfile.TemporaryDirectory() as nonrepo:
            pn = resolve_via_shell(nonrepo)
            check("scratch-detached-distinct", not pn.endswith("/.flow") and "flow-detached" in pn,
                  f"detached run must fall back to a flow-detached path, got {pn}")


# ---------------------------------------------------------------------------- stamp
def test_stamp():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        seed_repo(a)
        seed_repo(b)
        stamp_a = json.loads(run_py(["stamp"], a).stdout)
        stamp_b = json.loads(run_py(["stamp"], b).stdout)
        check("stamp-fields", set(stamp_a) == {"repo", "branch", "head"}, str(stamp_a))
        check("stamp-distinguishes-repos", stamp_a["repo"] != stamp_b["repo"],
              "two repos must not share a stamp")

        h = Path(a) / ".flow" / "h.json"
        h.parent.mkdir(parents=True, exist_ok=True)

        h.write_text(json.dumps({"flow_stamp": stamp_a, "stages": []}), encoding="utf-8")
        r = run_py(["check", str(h)], a)
        check("stamp-ok", r.returncode == 0 and json.loads(r.stdout)["status"] == "ok", r.stdout)

        # A handoff from the OTHER project must be refused, not read.
        h.write_text(json.dumps({"flow_stamp": stamp_b, "stages": []}), encoding="utf-8")
        r = run_py(["check", str(h)], a)
        out = json.loads(r.stdout)
        check("stamp-foreign-refused", r.returncode == 2 and out["status"] == "stale", r.stdout)
        check("stamp-foreign-names-mismatch", "does not match this workspace" in out["reason"],
              out["reason"])

        # Fail CLOSED: no stamp at all is refused (cannot prove ownership).
        h.write_text(json.dumps({"stages": []}), encoding="utf-8")
        r = run_py(["check", str(h)], a)
        check("stamp-absent-stamp-refused", json.loads(r.stdout)["status"] == "stale", r.stdout)

        # A stale HEAD in the SAME repo is refused too (namespacing alone can't catch this).
        (Path(a) / "b.py").write_text("y = 2\n", encoding="utf-8")
        git(a, "add", "-A")
        git(a, "commit", "-q", "-m", "advance")
        h.write_text(json.dumps({"flow_stamp": stamp_a, "stages": []}), encoding="utf-8")
        r = run_py(["check", str(h)], a)
        check("stamp-stale-head-refused", json.loads(r.stdout)["status"] == "stale", r.stdout)

        # A symlinked spelling of the SAME repo root must NOT read as a mismatch. Both
        # sides normally derive the path from `git rev-parse`, but a symlinked worktree (or
        # macOS /var -> /private/var) can yield two spellings; a false stamp_error would
        # route a clean PR to draft, and a gate that cries wolf gets waived by habit.
        link = Path(a).parent / (Path(a).name + "-link")
        try:
            link.symlink_to(a)
        except (OSError, NotImplementedError):
            link = None
        if link is not None:
            # Re-derive: an earlier case advanced HEAD, so stamp_a is legitimately stale
            # and would mask what this case is actually testing.
            stamp_link = json.loads(run_py(["stamp"], a).stdout)
            stamp_link["repo"] = str(link)
            h.write_text(json.dumps({"flow_stamp": stamp_link, "stages": []}), encoding="utf-8")
            r = run_py(["check", str(h)], a)
            check("stamp-symlink-not-a-mismatch",
                  json.loads(r.stdout)["status"] == "ok", r.stdout)
            link.unlink()

        # The four statuses must stay DISTINCT — collapsing them is the original bug.
        r = run_py(["check", str(Path(a) / ".flow" / "nope.json")], a)
        check("stamp-absent-distinct", json.loads(r.stdout)["status"] == "absent", r.stdout)
        bad = Path(a) / ".flow" / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        r = run_py(["check", str(bad)], a)
        check("stamp-invalid-distinct", json.loads(r.stdout)["status"] == "invalid", r.stdout)


# ---------------------------------------------------------------------------- block
def test_audit_skips_block():
    """Execute the REAL `!`-block. First harness in this repo to do so."""
    blocks = extract_blocks(AUDIT_SKIPS_SKILL)
    check("block-extracted", len(blocks) >= 1, f"expected >=1 !-block, got {len(blocks)}")
    if not blocks:
        return
    block = blocks[0]
    check("block-not-tmp", "/tmp/flow-skip-audit-stages.json" not in block,
          "the handoff default must not be a /tmp path a fork cannot see")
    check("block-repo-local", ".flow/skip-audit-stages.json" in block, block[:200])

    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        seed_repo(a)
        seed_repo(b)
        # The block resolves the engine via CLAUDE_PLUGIN_ROOT; point it at this checkout.
        env_prefix = f'export CLAUDE_PLUGIN_ROOT="{FLOW}"\n'
        stages = Path(a) / ".flow" / "skip-audit-stages.json"
        stages.parent.mkdir(parents=True, exist_ok=True)

        def run_block(cwd):
            return subprocess.run(["bash", "-c", env_prefix + block],
                                  capture_output=True, text=True, cwd=str(cwd), check=False)

        # (1) absent handoff -> the legitimate standalone no-op
        r = run_block(a)
        check("block-absent-note", '"note"' in r.stdout,
              f"absent handoff must emit the note form; got {r.stdout[:200]}")

        # (2) correctly stamped handoff -> a real audit (NOT the note)
        stamp_a = json.loads(run_py(["stamp"], a).stdout)
        stages.write_text(json.dumps({
            "flow_stamp": stamp_a,
            "stages": [{"name": "audit-coverage", "status": "skipped",
                        "skip_reason": "no behavior in diff"}],
        }), encoding="utf-8")
        r = run_block(a)
        check("block-valid-audits", '"note"' not in r.stdout and '"stamp_error"' not in r.stdout,
              f"a valid stamped handoff must be audited; got {r.stdout[:250]}")

        # (3) FOREIGN handoff -> refused loudly, and NOT reported as a clean no-op.
        stamp_b = json.loads(run_py(["stamp"], b).stdout)
        stages.write_text(json.dumps({
            "flow_stamp": stamp_b,
            "stages": [{"name": "audit-coverage", "status": "skipped",
                        "skip_reason": "no behavior in diff"}],
        }), encoding="utf-8")
        r = run_block(a)
        check("block-foreign-refused", '"stamp_error"' in r.stdout,
              f"a foreign handoff must emit stamp_error; got {r.stdout[:250]}")
        check("block-foreign-not-note", '"note"' not in r.stdout,
              "a foreign handoff must NOT read as the clean standalone no-op")


# ------------------------------------------------------------- installed-plugin layout
def _seed_consumer(root):
    """A repo shaped like a CONSUMER project: flow.config.json, and NO plugins/flow.

    The absence is the whole point. Every case above runs inside this checkout or a
    bare temp repo with CLAUDE_PLUGIN_ROOT exported, so the block's fallback arm --
    a FLOW-REPO-RELATIVE `plugins/flow/...` path -- either resolves or is never
    reached. Neither shape can observe the bug.
    """
    Path(root).mkdir(parents=True, exist_ok=True)
    seed_repo(root)
    r = Path(root)
    (r / "flow.config.json").write_text(
        json.dumps({"planPath": "docs/plan.md", "platform": "library", "uiSurface": False}),
        encoding="utf-8")
    (r / "docs").mkdir(exist_ok=True)
    (r / "docs" / "plan.md").write_text("# plan\n\nmode: feature\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "consumer")
    git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    assert not (r / "plugins" / "flow").exists(), "fixture bug: consumer must not vendor flow"
    return r


def _write_stamped(repo, path):
    stamp = json.loads(run_py(["stamp"], repo).stdout)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "flow_stamp": stamp,
        "stages": [{"name": "audit-coverage", "status": "skipped",
                    "skip_reason": "no behavior in diff"}],
    }), encoding="utf-8")


def _arm(stdout):
    """Which resolution arm the block reports having used, or None.

    Cases (1) and (5) both used to assert only "AUDIT", so arm PRECEDENCE was pinned by
    fixture starvation (an empty config dir) rather than asserted. With the block
    reporting its own arm, a precedence inversion is visible.
    """
    try:
        return json.loads(stdout).get("plugin_root_arm")
    except ValueError:
        return None


def _classify(stdout):
    """Which branch of the block spoke: a real audit, or one of its refusal forms."""
    try:
        d = json.loads(stdout)
    except ValueError:
        return "NOT-JSON"
    for k in ("root_error", "jq_error", "stamp_unverifiable", "stamp_error",
              "engine_error", "note"):
        if k in d:
            return k
    return "AUDIT" if d.get("stages") else "EMPTY"


def test_installed_layout():
    """The block must reach its helpers when flow is INSTALLED, not checked out.

    This closes the gap that let the bug live for 35 releases. `/flow:audit-skips`
    resolved two helpers -- the stamp checker and the engine -- with the same two-arm
    shape: `$CLAUDE_PLUGIN_ROOT`, else `plugins/flow/...`. The second arm only exists
    in a flow checkout, so on any run where the host variable was absent BOTH helpers
    were unreachable and the gate reported `stamp_unverifiable` on every invocation.
    Reported against an installed 1.29.0 in a consumer repo and reproduced on 1.64.0.

    Every case below runs with CLAUDE_PLUGIN_ROOT **unset** and from a repo that does
    not vendor flow -- i.e. from OUTSIDE this harness's usual path vocabulary. A case
    drawn from the checkout cannot distinguish "resolution is complete" from
    "resolution only ever worked here" (general.md item 4).
    """
    blocks = extract_blocks(AUDIT_SKIPS_SKILL)
    if not blocks:
        check("installed-block-extracted", False, "no !-block in audit-skips/SKILL.md")
        return
    block = blocks[0]

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # A staged COPY of the plugin tree, standing in for ~/.claude/plugins/cache/...
        # A copy, not a symlink to this checkout: the point is a root that is not the
        # repo the block runs in.
        install = tmp / "cache" / "flow" / "flow" / "1.99.0"
        install.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(FLOW, install)
        consumer = _seed_consumer(tmp / "consumer")
        stages = consumer / ".flow" / "skip-audit-stages.json"
        _write_stamped(consumer, stages)

        def cfgdir(name, record):
            d = tmp / name / "plugins"
            d.mkdir(parents=True, exist_ok=True)
            if record is not None:
                (d / "installed_plugins.json").write_text(json.dumps(record), encoding="utf-8")
            return str(d.parent)

        good = cfgdir("cfg-good", {"version": 2, "plugins": {
            "flow@flow": [{"scope": "user", "installPath": str(install), "version": "1.99.0"}]}})
        empty = cfgdir("cfg-empty", None)
        # A record that names a real directory carrying a plugin manifest for a
        # DIFFERENT plugin. The identity gate must reject it rather than execute
        # whatever Python happens to sit at that path.
        imposter = tmp / "imposter"
        (imposter / ".claude-plugin").mkdir(parents=True)
        (imposter / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "notflow", "version": "9.9.9"}), encoding="utf-8")
        wrong = cfgdir("cfg-wrong", {"version": 2, "plugins": {
            "flow@flow": [{"scope": "user", "installPath": str(imposter)}]}})

        def run(cwd, cfg, cpr=None, **env_extra):
            env = dict(os.environ)
            env.pop("CLAUDE_PLUGIN_ROOT", None)
            if cpr is not None:
                env["CLAUDE_PLUGIN_ROOT"] = cpr
            env["CLAUDE_CONFIG_DIR"] = cfg
            env.update(env_extra)
            r = subprocess.run(["bash", "-c", block], capture_output=True, text=True,
                               cwd=str(cwd), env=env, check=False)
            return _classify(r.stdout), r.stdout

        # (1) THE POSITIVE. Consumer repo, CPR unset, install record present.
        got, out = run(consumer, good)
        check("installed-layout-resolves", got == "AUDIT",
              f"a consumer-layout run with CPR unset must audit; got {got}: {out[:220]}")
        check("installed-layout-resolves-via-record", _arm(out) == "install-record",
              f"with CPR unset it must resolve via the INSTALL RECORD, not another arm; "
              f"got arm={_arm(out)}")

        # (2) THE PAIRED MUTATION for (1). Nothing names the install -> the gate must
        # refuse. Named separately so the failure message says WHICH assertion died.
        got, no_root_out = run(consumer, empty)
        check("installed-layout-no-record-refuses", got == "stamp_unverifiable",
              f"with no resolvable root the gate must refuse; got {got}: {no_root_out[:220]}")
        check("installed-layout-no-record-not-audit", got != "AUDIT",
              "an unresolvable plugin root must NEVER produce an audit -- fail closed")

        # (3) The identity gate. A record pointing at a non-flow tree is not a root.
        got, out = run(consumer, wrong)
        check("installed-layout-imposter-refused", got == "stamp_unverifiable",
              f"an installPath whose plugin.json is not flow must be rejected; got {got}")

        # (4) An unresolved root must say SO, not name a path that never existed.
        # Without this the operator is told a helper is missing from "/scripts/..." and
        # debugs a filesystem instead of an install. Reuses case (2)'s stdout -- the
        # inputs are byte-identical, so re-running the block would be a second ~15ms
        # subprocess to recover output we already hold.
        # Pin the DECISION, not one phrasing: the refusal must (a) attribute the failure
        # to flow being unable to locate ITSELF -- not to the handoff, which is the wrong
        # story and was the original message's lede -- and (b) end on something the
        # operator can DO. Its two siblings in the same block (root_error, jq_error) both
        # end on a remedy; this one shipped a three-mechanism enumeration and no fix.
        check("installed-layout-names-the-root-failure",
              "find its own installation" in no_root_out,
              f"the refusal must say flow could not locate its own install, not blame the "
              f"handoff; got {no_root_out[:260]}")
        check("installed-layout-refusal-carries-a-remedy",
              "Fix:" in no_root_out and "CLAUDE_PLUGIN_ROOT" in no_root_out,
              f"the refusal must end on an actionable fix naming CLAUDE_PLUGIN_ROOT; "
              f"got {no_root_out[:260]}")
        # And it must not assert a search it never performed: with no record on disk, the
        # message may not claim to have read one. (The block's own closing rule: say what
        # the gate detected, not what it hoped to prevent.)
        check("installed-layout-refusal-honest-about-the-record",
              "no install record" in no_root_out,
              f"with no record present the message must say so, not claim it searched one; "
              f"got {no_root_out[:260]}")

        # (5) CPR still wins when the host does set it, from a consumer layout.
        got, out = run(consumer, empty, cpr=str(install))
        check("installed-layout-cpr-still-honoured", got == "AUDIT",
              f"an explicit CLAUDE_PLUGIN_ROOT must still resolve; got {got}: {out[:220]}")
        check("installed-layout-cpr-wins-precedence", _arm(out) == "host-var",
              f"an explicit CLAUDE_PLUGIN_ROOT must take precedence over the record; "
              f"got arm={_arm(out)}")

        # (6) The arm that MASKED the bug, pinned so it cannot regress: inside the flow
        # checkout with CPR unset and no install record, arm 3 resolves. This is the
        # dogfooding path; it passing is not evidence about (1), which is the whole
        # lesson of this test existing.
        # NOTE this case needs CLAUDE_CONFIG_DIR pointed at an EMPTY dir. In real
        # dogfooding arm 2 wins here too: the SessionStart currency hook keeps flow
        # installed, so a flow checkout normally has an install record and arm 3 is
        # effectively unreachable (measured by the efficiency pass). That is a
        # security property worth having -- arm 2 shadows the cwd-relative arm on any
        # machine with flow installed -- but it means arm 3 can only be exercised by
        # hiding the record, which is what `empty` does.
        #
        # try/finally: this is the one case that writes inside the LIVE checkout, so a
        # raising check must not leave a stray file behind for the rest of the harness.
        stray = REPO / ".flow" / "_eval-stages.json"
        try:
            _write_stamped(REPO, stray)
            got, out = run(REPO, empty, FLOW_SKIP_AUDIT_STAGES=".flow/_eval-stages.json")
        finally:
            stray.unlink(missing_ok=True)
        check("checkout-cpr-unset-resolves", got == "AUDIT",
              f"arm 3 (flow checkout) must still resolve with CPR unset; got {got}: {out[:220]}")
        check("checkout-cpr-unset-uses-checkout-arm", _arm(out) == "checkout",
              f"with no host var and no record, the checkout arm must be the one that "
              f"resolved; got arm={_arm(out)}")

        # (7) THE NEWLY-REACHABLE STATE, pinned because this change created it.
        # Arm 1 used to gate on the engine file itself; it now gates on the MANIFEST, so
        # a root carrying a manifest but no engine is ACCEPTED rather than falling
        # through to another tree. That is deliberate, and it means the engine's own
        # failure is the only thing reporting it -- so assert the failure is routed as
        # engine_error (which blocks) and NOT as a note or a clean audit. Without this
        # the branch the diff removed would have been replaced by nothing at all.
        half = tmp / "half-install"
        (half / ".claude-plugin").mkdir(parents=True)
        # The name here is incidental, NOT the thing under test: arm 1 gates only on the
        # manifest EXISTING (the two identity greps are arms 2 and 3, which is why
        # installed-arm-identity-gated asserts >= 2). Written realistically so the fixture
        # looks like a real half-install, but this case would pass with any name -- said
        # out loud so it does not read as testing a gate that is not there.
        (half / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "flow", "version": "1.99.0"}), encoding="utf-8")
        shutil.copytree(install / "scripts", half / "scripts")   # stamp checker present
        # ...engine deliberately absent: no skills/audit-skips/lib/skip-audit-checks.py
        got, out = run(consumer, empty, cpr=str(half))
        check("installed-layout-engine-absent-is-engine-error", got == "engine_error",
              f"a resolved root with no engine must route as engine_error; got {got}: {out[:220]}")
        check("installed-layout-engine-absent-not-audit", got not in ("AUDIT", "note"),
              f"a missing engine must never read as an audit or as nothing-to-audit; got {got}")

        # (8) THE REGISTRY HAS MORE THAN ONE READER, SO PIN THAT THEY AGREE.
        # ship/lib/plugin-provenance.py::read_installed parses the same host-private file
        # to answer "which flow ran this pipeline". This shell cannot CALL it (the
        # circularity is the whole bug), but it can be asserted to SELECT THE SAME ENTRY
        # from one fixture -- otherwise /flow:audit-skips can resolve and audit while the
        # PR's provenance rows name a different installPath, two shipped surfaces
        # disagreeing about which flow is running.
        prov = FLOW / "skills" / "ship" / "lib" / "plugin-provenance.py"
        if prov.exists():
            fake_home = tmp / "prov-home"
            (fake_home / ".claude" / "plugins").mkdir(parents=True)
            (fake_home / ".claude" / "plugins" / "installed_plugins.json").write_text(
                json.dumps(eval_utils.installed_registry("1.99.0", install)), encoding="utf-8")
            pr = subprocess.run(
                [sys.executable, "-c",
                 "import json,sys;sys.path.insert(0,sys.argv[1]);"
                 "import importlib.util as u;"
                 "s=u.spec_from_file_location('pp',sys.argv[2]);m=u.module_from_spec(s);"
                 "s.loader.exec_module(m);"
                 "print(json.dumps(m.read_installed(__import__('pathlib').Path(sys.argv[3]))))",
                 str(prov.parent), str(prov), str(fake_home)],
                capture_output=True, text=True, check=False)
            try:
                picked = json.loads(pr.stdout).get("install_path") or json.loads(pr.stdout).get("path")
            except (ValueError, AttributeError):
                picked = None
            check("registry-readers-agree", picked is not None and str(install) in str(picked),
                  "read_installed must select the same installPath this block's arm 2 does; "
                  f"it returned {pr.stdout[:200]} stderr={pr.stderr[:160]}")


# ------------------------------------------------------- fork-skill roster (FB-0141)
def test_fork_skill_roster():
    """Every `context: fork` skill is either ported to the three-arm resolver or on a
    named known-broken ledger.

    Split out of test_installed_layout: these are static assertions over shipped text and
    need neither the staged install nor a temp repo, and this file's convention is one
    `test_*` per concern.
    """
    # ---- THE ROSTER, not just this one site. ----
    # test_contracts() below already states the rule for a deliberately-duplicated shell
    # idiom: "a guard covering 3 of 6 sites is the exact fan-out-contradiction class this
    # harness exists to prevent." The three-arm resolver is a second such idiom, and a
    # guard reading only audit-skips covers 1 of N. So DERIVE the site list from disk
    # (the run_root_anchor_evals.py fork_skills() shape) and name every un-ported skill
    # as an explicit exemption. Two things then go red that would otherwise not:
    # a port that misses a skill, and a NEW fork skill written with the two-arm shape.
    #
    # The exemptions are a LEDGER OF KNOWN-BROKEN, not an approval. Each is a live
    # FB-0141 instance; audit-plan and audit-completion are the WORST of them (no
    # fallback at all, so an unset CLAUDE_PLUGIN_ROOT means extract_session.py never
    # runs and the reviewer audits an EMPTY session context, then reports "No issues
    # flagged" -- fail-OPEN, where audit-skips failed closed). Deleting a line here
    # without porting the resolver is how the class gets quietly closed.
    blocks = extract_blocks(AUDIT_SKIPS_SKILL)
    block = blocks[0] if blocks else ""
    PORTED = {"audit-skips"}
    EXEMPT = {
        "audit-plan": "FB-0141, UNPORTED + fail-OPEN: no fallback; unset CPR -> empty session context",
        "audit-completion": "FB-0141, UNPORTED + fail-OPEN: no fallback; unset CPR -> empty session context",
        "critique-plan": "FB-0141, UNPORTED: flow-repo-relative arm for extract_session + walk-pin-lint",
        "audit-coverage": "FB-0141, UNPORTED: flow-repo-relative arm for three libs",
    }
    forks = []
    for skill_md in sorted(FLOW.glob("skills/*/SKILL.md")):
        head = skill_md.read_text(encoding="utf-8", errors="replace").split("\n---", 1)[0]
        if any(ln.strip() == "context: fork" for ln in head.splitlines()):
            forks.append((skill_md.parent.name, skill_md))
    names = {n for n, _ in forks}
    # EXACT, not a floor. The sibling harness states the rule: "an exact count, not a
    # floor. A floor lets a future preamble be added WITHOUT a guard and still pass."
    # Derived from the ledger rather than hardcoded, so there is no number to go stale.
    check("roster-count-exact", len(forks) == len(PORTED) + len(EXEMPT),
          f"found {len(forks)} `context: fork` skills on disk but the ledger accounts for "
          f"{len(PORTED) + len(EXEMPT)} ({sorted(n for n, _ in forks)}). A zero here would "
          "mean the scan itself is broken, making every assertion below vacuously true.")
    # A fork skill that is neither ported nor on the ledger is an unreviewed instance.
    unaccounted = sorted(names - PORTED - set(EXEMPT))
    check("roster-every-fork-skill-accounted", not unaccounted,
          f"fork skill(s) {unaccounted} are neither ported nor listed as a known FB-0141 "
          "exemption. If you added a fork skill, resolve its helpers off the three-arm "
          "resolver; if it genuinely needs none, add it to EXEMPT with the reason.")
    # And the ledger may not outlive the thing it describes: a retired or renamed skill
    # left on it would silently shrink the roster's coverage.
    stale = sorted(set(EXEMPT) - names)
    check("roster-no-stale-exemptions", not stale,
          f"EXEMPT names {stale}, which no longer exist as fork skills -- re-point or drop them")
    # Each exemption must still BE the thing it claims to be. If someone ports one of
    # these and forgets the ledger, this goes red rather than leaving a false claim.
    for name in sorted(EXEMPT):
        md = FLOW / "skills" / name / "SKILL.md"
        if not md.exists():
            continue
        body = md.read_text(encoding="utf-8", errors="replace")
        # NEGATIVE half: it has not grown the install-record arm.
        check(f"roster-exempt-still-unported-{name}",
              "installed_plugins.json" not in body,
              f"{name} now reads the install record, i.e. it HAS been ported -- move it "
              "from EXEMPT to PORTED and give it the executed cases above")
        # POSITIVE half, and it is the load-bearing one (general.md item 3 + the CV1
        # corollary). The negative above pins ONE mechanism's literal, so a port that
        # sources a shared helper -- the ci-gate.sh / serve-preview.sh idiom this repo
        # already prefers for "four copies of one shell sequence" -- would never contain
        # it, and the exemption would stay green while claiming the skill is unported.
        # The tripwire built to keep the class OPEN would be the thing asserting it.
        # What all four genuinely share is the broken shape itself: a python3 invocation
        # rooted directly at ${CLAUDE_PLUGIN_ROOT} with no root indirection. Any port
        # replaces that target with an $FPR-style variable, however the resolver is
        # spelled. (audit-plan/audit-completion have NO plugins/flow literal at all --
        # they have no fallback -- so the obvious positive could not be spelled that way.)
        check(f"roster-exempt-still-has-broken-shape-{name}",
              "${CLAUDE_PLUGIN_ROOT}/" in body,
              f"{name} no longer invokes anything at a bare ${{CLAUDE_PLUGIN_ROOT}}/ path, "
              "so it appears PORTED by some mechanism -- move it from EXEMPT to PORTED. "
              "(For audit-coverage, which has three helpers, read this as 'not FULLY "
              "ported' rather than 'not ported'.)")

    # The shipped text must carry all three arms. A negative-only assertion would pass
    # if someone deleted the resolver outright (general.md item 3), so these are the
    # POSITIVE pins for the mechanism the executed cases above exercise.
    check("installed-arm-host-var", 'CLAUDE_PLUGIN_ROOT:-' in block, "arm 1 missing")
    check("installed-arm-record", "installed_plugins.json" in block, "arm 2 missing")
    check("installed-arm-checkout",
          'plugins/flow/.claude-plugin/plugin.json' in block, "arm 3 missing")
    check("installed-arm-identity-gated",
          block.count('grep -q \'"name": *"flow"\'') >= 2,
          "every candidate root must be identity-checked against its own plugin.json")
    # Both helpers must hang off ONE root. Two independent resolvers is what made the
    # stamp checker and the engine fail together while looking like separate bugs.
    check("installed-one-root-two-helpers",
          '"$FPR/scripts/flow_scratch.py"' in block
          and '"$FPR/skills/audit-skips/lib/skip-audit-checks.py"' in block,
          "SCRATCH_PY and H must both resolve off $FPR")




# ------------------------------------------------------------------------- contract
def test_contracts():
    idiom = "git rev-parse --show-toplevel"

    # EVERY copy of the shell idiom, not just the reviewer trio. The idiom is
    # deliberately duplicated (a sourced helper is unreachable in Bash-tool fenced
    # blocks, where CLAUDE_PLUGIN_ROOT is unset), which is the same justified
    # duplication as the FB-0008 BASE-resolution block. Duplication is only safe
    # while something pins every copy — a guard covering 3 of 6 sites is the exact
    # fan-out-contradiction class this harness exists to prevent.
    idiom_sites = [("staff", STAFF_SKILL), ("sec", SEC_SKILL), ("a11y", A11Y_SKILL),
                   ("ship", SHIP_SKILL), ("verify", VERIFY_SKILL),
                   ("review-brief", REVIEW_BRIEF_SKILL), ("ship-spike", SPIKE_SKILL),
                   ("prototype", PROTOTYPE_SKILL),
                   # 9th site, added with the Tier-2 argument channel (FB-0116). A guard
                   # covering 8 of 9 is the fan-out class this harness exists to prevent.
                   ("audit-coverage", AUDIT_COVERAGE_SKILL),
                   # 10th site (D1 Phase 3). Caught by /flow:security-review, not by this
                   # harness: autoplan shipped the ONLY `mkdir -p "$ROOT/.flow"` in the
                   # tree with no adjacent `[ -L ]` guard, and a hardcoded roster cannot
                   # notice a site nobody added to it. The roster is the fan-out defence
                   # AND the fan-out risk — adding a .flow writer means adding it here.
                   ("autoplan", AUTOPLAN_SKILL)]
    for name, path in idiom_sites:
        t = path.read_text(encoding="utf-8")
        check(f"contract-{name}-idiom", idiom in t and '"$FLOW_SCRATCH/' in t,
              f"{path.name} must resolve a repo-local scratch dir via the canonical idiom")

    # The detached-fallback literal must agree across every shell copy AND the Python
    # module, or the two halves of the contract silently diverge.
    detached = "${TMPDIR:-/tmp}/flow-detached"
    py = SCRATCH_PY.read_text(encoding="utf-8")
    check("contract-detached-python", "flow-detached" in py,
          "flow_scratch.py must document the shell idiom's 'flow-detached' fallback")
    for name, path in idiom_sites:
        t = path.read_text(encoding="utf-8")
        if "flow-detached" in t:
            check(f"contract-{name}-detached-literal", detached in t,
                  f"{path.name} detached fallback must read exactly {detached}")

    # SHELL_IDIOM above is this harness's own copy, so drift between it and the SKILLs
    # would otherwise pass green — the same false-confidence shape this PR exists to
    # remove. Pin the one line that copy asserts behaviourally (the self-ignore) at
    # every site, so a SKILL that drops it fails here.
    for name, path in idiom_sites:
        t = path.read_text(encoding="utf-8")
        check(f"contract-{name}-self-ignores", '"$FLOW_SCRATCH/.gitignore"' in t,
              f"{path.name} must create .flow/.gitignore itself — the Python helper is "
              f"never called from these blocks, so a self-ignore only there never runs")

    # The CWE-59 refusal is the guard with the worst failure mode of the three (writes
    # land outside the repo), and it was the LAST to be pinned — FB-0100 added it for
    # ship-spike alone, i.e. 1 of 7 sites, the exact shape the comment above forbids.
    for name, path in idiom_sites:
        t = path.read_text(encoding="utf-8")
        check(f"contract-{name}-symlink-guard", 'if [ -L "$FLOW_SCRATCH" ]' in t,
              f"{path.name} must refuse to write scratch through a symlink (CWE-59) — "
              f"mkdir -p exits 0 on a symlink-to-dir and FOLLOWS it")

    for name, path in [("staff", STAFF_SKILL), ("sec", SEC_SKILL), ("a11y", A11Y_SKILL)]:
        t = path.read_text(encoding="utf-8")
        check(f"contract-{name}-no-tmp-write", f"> /tmp/flow-{name}-diff.patch" not in t,
              f"{path.name} must not write its diff to /tmp")
        check(f"contract-{name}-provenance", "flow-review-context" in t,
              f"{path.name} must stamp the diff with repo/branch/head")

    # ---- the stage handoff, pinned across BOTH copies -----------------------
    # ship/SKILL.md Step 2a.1 and ship-spike/SKILL.md Step 2a.1 each write the handoff
    # in shell (a sourced helper is unreachable from a Bash-tool fenced block, where
    # CLAUDE_PLUGIN_ROOT is unset), so the block is duplicated by necessity. FB-0100
    # first pinned these guards against the SPIKE copy only — which left ship, the
    # ORIGINAL the spike copy was made from, free to drop its symlink refusal or its
    # read-back with this harness still green. A one-sided pin on a two-sided
    # duplication is not a pin; loop both.
    handoff_sites = [("ship", SHIP_SKILL), ("ship-spike", SPIKE_SKILL)]
    for name, path in handoff_sites:
        t_ = path.read_text(encoding="utf-8")
        check(f"contract-{name}-handoff-repo-local",
              "$FLOW_SCRATCH/skip-audit-stages.json" in t_ and "flow_stamp" in t_,
              f"{path.name} Step 2a.1 must write a stamped, repo-local handoff")
        check(f"contract-{name}-stamp-routing", "stamp_error" in t_,
              f"{path.name} must route a stamp_error rather than accepting it as legitimate")
        for label, needle in [("jq-stamp", "jq -nc --arg repo"),
                              ("readback", 'jq . "$STAGES" >/dev/null'),
                              # CWE-59 has TWO halves and the container guard is only
                              # the first. A `.flow` that is a real directory can still
                              # contain a symlinked `skip-audit-stages.json`, which the
                              # heredoc would follow and truncate. Pin the sink guard too.
                              ("sink-guard", 'rm -f "$STAGES" "$STAGES.tmp"'),
                              ("sink-guard-gitignore",
                               '[ -L "$FLOW_SCRATCH/.gitignore" ] && rm -f')]:
            check(f"contract-{name}-handoff-{label}", needle in t_,
                  f"{path.name}'s handoff block must keep the {label} — {needle!r} absent")
        # A substring needle is ORDER-BLIND, and for this guard order IS the contract:
        # placed after the .gitignore creation it prevents nothing (the redirect has
        # already followed a dangling symlink) and it regresses the self-ignore. The
        # first shipped version of this guard had exactly that bug, in both copies —
        # which the presence-only needle passed. Assert the sequence, not just the text.
        check(f"contract-{name}-handoff-sink-guard-precedes-write",
              t_.index('rm -f "$STAGES" "$STAGES.tmp"')
              < t_.index("""|| printf '# Created by flow."""),
              f"{path.name}: the sink unlinks must run BEFORE .flow/.gitignore is "
              f"created, or the guard runs twelve lines too late")

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    props = schema["properties"]
    for slot, want in [("verifyFindingsPath", ".flow/verify-findings.json"),
                       ("verifyReportPath", ".flow/verify-report.html")]:
        check(f"contract-schema-{slot}", props[slot].get("default") == want,
              f"{slot} default is {props[slot].get('default')!r}, want {want!r}")

    # FB-0010: no cross-boundary /tmp/flow-* write may survive anywhere in the shipped
    # surface. Transient stderr captures inside one fenced block are exempt (named).
    # Exempt ONLY transients that never cross a fork boundary. Deliberately does NOT
    # include `flow-verify` or `flow-staff-review-marker`: both matched nothing after this
    # PR migrated them, so leaving them here would pre-authorise a regression that
    # reintroduced the very cross-boundary handoff this check exists to catch.
    exempt = ("-err", "flow-detached", "flow-pr-body", "flow-sd-region")
    # Scan roots deliberately WIDER than the plugin's skills+agents. The first version of
    # this guard covered only those two, and `template/base/flow.config.json.example` --
    # the file every new consumer copies -- kept the old /tmp default past a green check.
    # A guard narrower than the contract it defends is the failure it is meant to catch.
    repo = FLOW.parent.parent
    roots = [FLOW / "skills", FLOW / "agents", FLOW / "schema", repo / "template"]
    survivors = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(list(root.rglob("*.md")) + list(root.rglob("*.json")) + list(root.rglob("*.example"))):
            if "evals/fixtures" in str(p):
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if "/tmp/flow-" not in line:
                    continue
                if any(e in line for e in exempt):
                    continue
                # Test LIVE USE, not mention. Explanatory prose ("why repo-local and not
                # /tmp") must stay legal, or the guard punishes documenting the fix. A
                # survivor is the path actually being USED: assigned, redirected into, or
                # given as a JSON/schema value. That is falsifiable, unlike a keyword
                # allowlist that a future real write could hide behind.
                if not re.search(r'(=\s*"?/tmp/flow-|>\s*"?/tmp/flow-|:\s*"/tmp/flow-|"\s*/tmp/flow-[\w.-]+"\s*[,\]])', line):
                    continue
                survivors.append(f"{p.relative_to(repo)}:{i}")
    check("contract-no-tmp-survivors", not survivors,
          "cross-boundary /tmp handoffs remain: " + ", ".join(survivors[:6]))


# ------------------------------------------------------------------- span integrity
def _handoff_stage_names(text):
    """Stage names from a SKILL.md's `cat > "$STAGES" <<'EOF'` heredoc, in order."""
    m = re.search(r"""cat > "\$STAGES" <<'EOF'\n(.*?)\nEOF\n""", text, re.S)
    if not m:
        return []
    return re.findall(r'\{"name":\s*"([a-z-]+)"', m.group(1))


def test_handoff_rows():
    """The handoff-to-engine join, pinned behaviourally (FB-0100).

    THE FAILURE THIS EXISTS TO CATCH. ship and ship-spike each write their own stage
    rows; `skip-audit-checks.py` decides what each row means. Nothing connected the
    two, so a row naming a stage the engine does not know classifies as
    `NEEDS-JUDGMENT: unknown stage` — which reads, in the summary the agent sees, like
    an ordinary judgment call rather than "this row was never checked against
    anything". A silent no-op wearing a verdict's clothes: the shape of FB-0082 and of
    the defect FB-0100 closes.

    A string-presence grep cannot catch it — the `contract-*-handoff-*` checks above
    assert each file's guards in isolation and would pass just as green with a
    `preflight` row the engine had never heard of. So this drives the REAL engine with
    every row name found in either handoff and asserts none falls through.
    """
    ship_rows = _handoff_stage_names(SHIP_SKILL.read_text(encoding="utf-8"))
    spike_rows = _handoff_stage_names(SPIKE_SKILL.read_text(encoding="utf-8"))
    check("handoff-ship-rows-extractable", len(ship_rows) >= 7, f"ship rows: {ship_rows}")
    check("handoff-spike-rows-extractable", len(spike_rows) >= 7, f"spike rows: {spike_rows}")

    engine = FLOW / "skills" / "audit-skips" / "lib" / "skip-audit-checks.py"
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        names = sorted(set(ship_rows) | set(spike_rows))
        rep = d / "rows.json"
        rep.write_text(json.dumps(
            {"stages": [{"name": n, "status": "skipped", "skip_reason": "doc-only"} for n in names]}),
            encoding="utf-8")
        (d / "cfg.json").write_text("{}", encoding="utf-8")
        (d / "files.txt").write_text("dev-docs/history.md\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(engine), "--report", str(rep), "--config", str(d / "cfg.json"),
             "--files-from", str(d / "files.txt"), "--branch", "b", "--head-sha", "deadbee"],
            capture_output=True, text=True, check=False)
        try:
            out = json.loads(proc.stdout)
        except ValueError:
            out = {"stages": []}
            check("handoff-engine-ran", False, f"engine failed: {proc.stderr[:200]}")
        unknown = [s["name"] for s in out.get("stages", [])
                   if "unknown stage" in (s.get("reason") or "")]
        check("handoff-rows-all-known-to-engine", not unknown,
              f"handoff rows the engine does not recognize (they audit nothing and say "
              f"NEEDS-JUDGMENT while doing it): {unknown}")

    # The two handoffs are allowed to differ — but only in ways someone wrote down.
        # ship-spike is a SUPERSET of ship: everything ship reports, plus the rows only
        # spike mode has an opinion about. Pinning the delta as a literal is what makes the
        # asymmetry VISIBLE — change either file's rows and this fails naming the other.
        #
        # RESTORED after being lost in an edit (staff-review, v1.38.0). Without these two,
        # the only surviving row assertion was `len(spike_rows) >= 7` against 8 rows — so
        # DELETING a stage row from either handoff passed green, including the `security`
        # row this PR added so spike-mode security skips get audited at all. A contract
        # satisfiable by deletion, inside the PR whose thesis is mechanical pinning
        # (.claude/rules/general.md § Consistency discipline, item 3).
        missing = sorted(set(ship_rows) - set(spike_rows))
        check("handoff-spike-covers-every-ship-stage", not missing,
              f"ship-spike's handoff omits stages ship audits: {missing}. Spike mode skips "
              f"MORE than feature mode, so it cannot audit less")
        extra = sorted(set(spike_rows) - set(ship_rows))
        check("handoff-spike-delta-is-declared", extra == ["preflight"],
              f"the spike/ship row delta is {extra}, expected ['preflight'] — if that is a "
              f"deliberate change, update this literal AND say why in the history entry. "
              f"`preflight` is spike-only today by scope choice, not by principle: ship's "
              f"Step 1c runs the same gate and the engine can check it there too")

        # And no row may buy itself out of its stage's real check by claiming a MODE.
        # `_MODE_SKIP_OK` is the closed two-member allowlist; every other row must be
        # refused. Asserted over the LIVE row sets, so a stage added to either handoff
        # is covered the day it lands — the denylist this replaced left `preflight`
        # and `verify-build` open on the day they were added.
        rep2 = d / "rows-mode.json"
        rep2.write_text(json.dumps(
            {"stages": [{"name": n, "status": "skipped", "skip_reason": "spike"} for n in names]}),
            encoding="utf-8")
        proc2 = subprocess.run(
            [sys.executable, str(engine), "--report", str(rep2), "--config", str(d / "cfg.json"),
             "--files-from", str(d / "files.txt"), "--branch", "b", "--head-sha", "deadbee"],
            capture_output=True, text=True, check=False)
        out2 = json.loads(proc2.stdout) if proc2.stdout.strip() else {"stages": []}
        excused = [s["name"] for s in out2.get("stages", [])
                   if s.get("mechanical") != "SHOULD-RE-RUN"
                   and s["name"] not in ("simplify", "staff-review")]
        check("handoff-no-row-is-excused-by-claiming-a-mode", not excused,
              f"these handoff rows accept 'spike' as a skip reason and should not: {excused}")


def test_span_integrity():
    """No inner backtick in ANY shipped `!`-span, across every SKILL.md.

    A `!`-block is delimited by a SINGLE backtick, so one backtick inside it terminates
    the span and everything after is emitted as literal prose instead of executing. The
    failure is invisible: the skill still renders, still produces a verdict, and the
    verdict is computed from inputs that were never read.

    This has now happened three times (`#86` shipped it into audit-skips, audit-coverage
    AND critique-plan simultaneously, silently inerting three gates). Twice it was found
    by accident. `contract-*` above greps the idiom sites for string PRESENCE, which
    cannot catch this — presence in a truncated span is still presence. So this asserts
    the property that actually matters: every span is intact. Blanket, not per-file, so a
    new skill inherits the check instead of relying on its author remembering.
    """
    for p in sorted((FLOW / "skills").rglob("SKILL.md")):
        lines = p.read_text(encoding="utf-8").split("\n")
        inblock, start, bad = False, 0, []
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if not inblock:
                if s == "!`":
                    inblock, start, bad = True, i, []
                continue
            if s == "`":
                # One assertion per SPAN, not per line — a per-line check would emit
                # hundreds of PASSes and bury the signal.
                check(f"span-intact-{p.parent.name}-L{start}", not bad,
                      f"inner backtick(s) at {p.parent.name}/SKILL.md line(s) "
                      f"{', '.join(map(str, bad))} truncate the !-span opened at {start}")
                inblock = False
                continue
            if "`" in line:
                bad.append(i)
        if inblock:
            check(f"span-closed-{p.parent.name}-L{start}", False,
                  f"{p.parent.name}/SKILL.md: !-span opened at {start} is never closed")


def test_ci():
    check("ci-wired", "run_scratch_isolation_evals.py" in CI.read_text(encoding="utf-8"),
          "an unwired harness gives zero regression protection (FB-0056)")



def test_producer_blocks():
    """EXTRACT and EXECUTE ship/SKILL.md's producer blocks (FB-0107 / FB-0108).

    This is the one verification shape that survives FB-0107. Dogfooding through
    /flow:ship exercises the INSTALLED plugin, which on flow's own workspaces lags `main` by
    many releases (measured at 1.29.0 vs 1.41.0 when this was written -- the point is the
    LAG, not those two numbers, which is why this comment does not depend on them staying
    current). So a PR whose entire payload is a change to /flow:* behaviour would ship with
    zero execution evidence for that behaviour. These cases run the shipped
    shell text from the REPO TREE, so the evidence is about this branch.

    EXTRACTED, not retyped. An earlier version of this test docstringed itself "extract and
    execute" and then reproduced the block as Python string literals, so a drift in the
    shipped text -- a changed redirect, a dropped scratch-path, a reordered call -- left the
    EXECUTED test green. That is the parallel-twin hazard this repo names twice already
    (`resolve_via_shell`'s docstring here, and `_load_triage`'s in the sibling harness). The
    block under test is now read off disk and only its `<placeholder>` slots substituted.
    """
    print("\n[producer] ship/SKILL.md producer blocks, EXTRACTED from disk and EXECUTED")
    root = FLOW.parent.parent
    triage = FLOW / "skills" / "ship" / "lib" / "manifest-triage.py"
    src = SHIP_SKILL.read_text(encoding="utf-8")

    # Pair a CALL-1 block (scratch-path) with the CALL-2 block that consumes it. The split
    # across two blocks IS the contract: the Write tool runs between them, and a Write
    # cannot happen inside a shell block. An earlier single-block form could never succeed
    # -- scratch-path unlinks its targets, then add-entry read them in the same block with
    # no Write in between -- and this test found that only because it executes the shipped
    # text instead of a retyped twin.
    fenced = re.findall(r"```sh\n(.*?)```", src, re.S)
    pair = None
    for i, blk in enumerate(fenced):
        if "scratch-path" not in blk:
            continue
        for nxt in fenced[i + 1:i + 3]:
            if "add-entry" in nxt and "--finding-file" in nxt:
                pair = (blk, nxt)
                break
        if pair:
            break
    check("producer-CALL1-CALL2-pair-found", pair is not None,
          "no scratch-path block is followed by an add-entry block")
    if pair is None:
        return
    call1, call2 = pair

    def prep(script):
        script = script.replace('"${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"',
                                f'"{triage}"')
        script = re.sub(r'--branch "\$\(git branch --show-current\)"', '--branch evalprod', script)
        return re.sub(r'--branch "\$BRANCH"', '--branch evalprod', script)

    names = re.findall(r"--name ([a-z0-9-]+\.txt)", call1)
    check("producer-CALL1-names-its-slugs", len(names) >= 1, str(names))
    scratch = root / ".flow"
    man = scratch / "manifest-evalprod.md"
    man.unlink(missing_ok=True)

    # CALL 2 WITHOUT the Write: the shipped `|| exit 1` must stop it and append nothing.
    for n in names:
        (scratch / n).unlink(missing_ok=True)
    r1 = subprocess.run(["sh", "-c", prep(call2) + "\necho REACHED_END\n"],
                        capture_output=True, text=True, cwd=str(root))
    check("producer-CALL2-STOPS-when-the-Write-never-ran", r1.returncode != 0, r1.stdout + r1.stderr)
    check("producer-CALL2-does-not-reach-its-end", "REACHED_END" not in r1.stdout, r1.stdout)
    check("producer-nothing-appended-on-that-path",
          not man.exists() or not man.read_text(encoding="utf-8").strip(),
          man.read_text(encoding="utf-8") if man.exists() else "(absent)")

    # CALL 1 -> Write -> CALL 2, each its OWN process with no inherited shell state.
    r2 = subprocess.run(["sh", "-c", prep(call1)], capture_output=True, text=True, cwd=str(root))
    check("producer-CALL1-exits-zero", r2.returncode == 0, r2.stderr)
    paths = [ln for ln in r2.stdout.split() if ln.startswith("/")]
    check("producer-CALL1-prints-absolute-paths", len(paths) == len(names), r2.stdout)
    if len(paths) == len(names):
        evil = 'Declared criterion (too vague): "`GET /users/:id` returns 404 $(id) works"'
        Path(paths[0]).write_text(evil, encoding="utf-8")
        for extra in paths[1:]:
            Path(extra).write_text("name the observable predicate", encoding="utf-8")
        man.unlink(missing_ok=True)
        # Substitute the `<slug.txt>` placeholders with the paths CALL 1 actually printed —
        # that substitution IS what the agent does when it pastes them, and it is the only
        # thing this test is allowed to fill in. Everything else is the shipped text.
        c2 = prep(call2)
        # Placeholders name the slug inside a descriptive form, e.g.
        # "<absolute path CALL 1 printed for rigor-finding.txt>". Substitute on the SLUG so
        # this keeps working if the surrounding wording changes — the slug is the contract.
        for n, real in zip(names, paths):
            c2 = re.sub(r'"<[^>]*' + re.escape(n) + r'[^>]*>"', f'"{real}"', c2)
        c2 = re.sub(r'"<the absolute path CALL 1 printed>"', f'"{paths[0]}"', c2)
        check("producer-CALL2-has-no-unsubstituted-placeholder-left", "<" not in c2.split("add-entry")[1],
              c2)
        r3 = subprocess.run(["sh", "-c", c2], capture_output=True, text=True, cwd=str(root))
        check("producer-CALL2-succeeds-once-the-Write-happened", r3.returncode == 0,
              r3.stdout + r3.stderr)
        body = man.read_text(encoding="utf-8") if man.exists() else ""
        check("producer-appended-to-the-manifest-FILE", body.strip().startswith("- ["), body)
        check("producer-metacharacters-land-as-literal-text", evil in body, body)
        check("producer-payload-did-not-execute", "uid=" not in body + r3.stdout, body + r3.stdout)

    man.unlink(missing_ok=True)
    (scratch / "manifest-evalprod2.md").unlink(missing_ok=True)
    for n in names:
        (scratch / n).unlink(missing_ok=True)

    # And the shipped text carries the guard at every producer site, so the executed
    # behaviour above is not an artefact of which block this test happened to pick.
    for m in re.finditer(r'"\$TRIAGE" (add-entry|record-attempt|waive)', src):
        tail = src[m.start():m.start() + 700]
        stop = tail.find("```")
        window = tail[:stop] if stop != -1 else tail
        check(f"producer-shipped-{m.group(1)}-checks-exit-status",
              "|| exit 1" in window or "|| {" in window or "exit 3 is NOT a failure" in window,
              window[:160])


def main():
    test_scratch()
    test_stamp()
    test_audit_skips_block()
    test_installed_layout()
    test_fork_skill_roster()
    test_producer_blocks()
    test_contracts()
    test_handoff_rows()
    test_span_integrity()
    test_ci()
    print(f"\n{_total - len(_fails)}/{_total} checks passed.")
    if _fails:
        print("FAILED: " + ", ".join(_fails))
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
