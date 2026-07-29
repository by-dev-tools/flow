#!/usr/bin/env python3
"""
Regression harness for repo-local scratch + handoff stamping (FB-0075).

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
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
FLOW = HERE.parent
SCRATCH_PY = FLOW / "scripts" / "flow_scratch.py"
AUDIT_SKIPS_SKILL = FLOW / "skills" / "audit-skips" / "SKILL.md"
SHIP_SKILL = FLOW / "skills" / "ship" / "SKILL.md"
STAFF_SKILL = FLOW / "skills" / "staff-review" / "SKILL.md"
SEC_SKILL = FLOW / "skills" / "security-review" / "SKILL.md"
A11Y_SKILL = FLOW / "skills" / "accessibility-review" / "SKILL.md"
VERIFY_SKILL = FLOW / "skills" / "verify-build" / "SKILL.md"
SCHEMA = FLOW / "schema" / "flow.config.schema.json"
CI = FLOW.parent.parent / ".github" / "workflows" / "ci.yml"

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
    """Pull the `!`-block shell out of a SKILL.md (the fork's actual context command)."""
    return re.findall(r"!`(.*?)`", Path(skill_path).read_text(encoding="utf-8"), re.S)


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
                   ("ship", SHIP_SKILL), ("verify", VERIFY_SKILL)]
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

    for name, path in [("staff", STAFF_SKILL), ("sec", SEC_SKILL), ("a11y", A11Y_SKILL)]:
        t = path.read_text(encoding="utf-8")
        check(f"contract-{name}-no-tmp-write", f"> /tmp/flow-{name}-diff.patch" not in t,
              f"{path.name} must not write its diff to /tmp")
        check(f"contract-{name}-provenance", "flow-review-context" in t,
              f"{path.name} must stamp the diff with repo/branch/head")

    ship = SHIP_SKILL.read_text(encoding="utf-8")
    check("contract-ship-handoff-repo-local",
          "$FLOW_SCRATCH/skip-audit-stages.json" in ship and "flow_stamp" in ship,
          "ship Step 2a must write a stamped, repo-local handoff")
    check("contract-ship-stamp-routing", "stamp_error" in ship,
          "ship must route a stamp_error rather than accepting it as legitimate")

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    props = schema["properties"]
    for slot, want in [("verifyFindingsPath", ".flow/verify-findings.json"),
                       ("verifyReportPath", ".flow/verify-report.html")]:
        check(f"contract-schema-{slot}", props[slot].get("default") == want,
              f"{slot} default is {props[slot].get('default')!r}, want {want!r}")

    # FB-0010: no cross-boundary /tmp/flow-* write may survive anywhere in the shipped
    # surface. Transient stderr captures inside one fenced block are exempt (named).
    exempt = ("-err", "flow-detached", "flow-pr-body", "flow-sd-region",
              "flow-staff-review-marker", "flow-verify")
    survivors = []
    for p in list((FLOW / "skills").rglob("*.md")) + list((FLOW / "agents").rglob("*.md")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "/tmp/flow-" in line and "FB-0075" not in line:
                if not any(e in line for e in exempt):
                    survivors.append(f"{p.relative_to(FLOW)}:{i}")
    check("contract-no-tmp-survivors", not survivors,
          "cross-boundary /tmp handoffs remain: " + ", ".join(survivors[:6]))


def test_ci():
    check("ci-wired", "run_scratch_isolation_evals.py" in CI.read_text(encoding="utf-8"),
          "an unwired harness gives zero regression protection (FB-0056)")


def main():
    test_scratch()
    test_stamp()
    test_audit_skips_block()
    test_contracts()
    test_ci()
    print(f"\n{_total - len(_fails)}/{_total} checks passed.")
    if _fails:
        print("FAILED: " + ", ".join(_fails))
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
