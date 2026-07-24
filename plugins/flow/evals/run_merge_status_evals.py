#!/usr/bin/env python3
"""Eval harness for /flow:post-merge's deterministic core + skill contract (FB-0072).

The skill orchestration (merge-detect → land → feedback-synth → cleanup → archive-verdict)
is prose the agent drives, but its LOAD-BEARING core is deterministic and pinned here:

  classify     — the three-state merge gate: MERGED / CLOSED-unmerged / OPEN. The whole
                 point of the gate is that a transient "can't tell yet" is NEVER the
                 terminal "will never merge" — so the unknown/empty case classifies OPEN.
  poll-verdict — the queue-safe poll policy: OPEN-at-cap gives up GRACEFULLY (distinct
                 from the CLOSED terminal fail), and cap==0 fail-fast on OPEN is also
                 graceful, never terminal. This is the false-fail-on-merge-queue fix.
  archive-check— the "safe to archive?" verdict over real git state in a temp repo.
  contract     — the SKILL wires the pieces the way the plan committed: human-invoked
                 (disable-model-invocation), CALLS /flow:land (composition, not
                 reimplementation), uses `branch -d` never `-D`, and writes NO feedbackPath
                 repo doc in v1 (user-scope stores only).
  schema       — the postMergeWaitSeconds slot exists and the slot count is 30 (a "N slots"
                 fan-out is the most-recurring bug class this repo tracks — FB-0010).

Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SKILLDIR = HERE.parent / "skills" / "post-merge"
HELPER = SKILLDIR / "lib" / "merge-status.py"
SKILL = SKILLDIR / "SKILL.md"
SCHEMA = HERE.parent / "schema" / "flow.config.schema.json"


def run(argv: list[str], stdin: str | None = None, cwd=None) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(HELPER), *argv], input=stdin,
                       capture_output=True, text=True, cwd=cwd)
    return p.returncode, (p.stdout or "").strip()


def git(repo, *a):
    subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)


def main() -> int:
    fails = 0
    total = 0

    def check(label, cond, detail=""):
        nonlocal fails, total
        total += 1
        print(f"{'PASS' if cond else 'FAIL'}  [{label}]{'' if cond else '  ' + detail}")
        if not cond:
            fails += 1

    # ---- classify: the three states + the load-bearing unknown→open default ----
    # The verdict is the printed WORD (the SKILL branches on stdout); classify always exits 0.
    _, out = run(["classify"], stdin='{"state":"MERGED","mergedAt":"2026-07-24T00:00:00Z"}')
    check("classify-merged", out == "merged", f"{out!r}")
    _, out = run(["classify"], stdin='{"state":"CLOSED","mergedAt":null}')
    check("classify-closed-terminal", out == "closed", f"{out!r}")
    _, out = run(["classify"], stdin='{"state":"OPEN","autoMergeRequest":{"enabledAt":"x"}}')
    check("classify-open", out == "open", f"{out!r}")
    # A mergedAt with a stale state still reads merged (merge queue can lag the state field).
    _, out = run(["classify"], stdin='{"state":"OPEN","mergedAt":"2026-07-24T00:00:00Z"}')
    check("classify-mergedAt-wins", out == "merged", f"{out!r}")
    # Unknown / empty / garbage MUST default to open (transient), never closed (terminal).
    for label, blob in [("empty", "{}"), ("garbage", "not json"), ("no-state", '{"foo":1}')]:
        _, out = run(["classify"], stdin=blob)
        check(f"classify-unknown-is-open-{label}", out == "open",
              f"{out!r} — unknown must be transient, not terminal")

    # ---- poll-verdict: the queue-safe policy (the printed word is the verdict) ----
    cases = [
        ("merged", 0, 150, "proceed"),
        ("closed", 0, 150, "terminal"),
        ("open", 20, 150, "wait"),
        ("open", 150, 150, "giveup-graceful"),   # cap reached → graceful, NOT terminal
        ("open", 999, 150, "giveup-graceful"),
        ("open", 0, 0, "giveup-graceful"),        # cap==0 fail-fast → graceful, NOT terminal
    ]
    for state, elapsed, cap, want_word in cases:
        _, out = run(["poll-verdict", "--state", state, "--elapsed", str(elapsed), "--cap", str(cap)])
        check(f"poll-{state}-{elapsed}-{cap}", out == want_word, f"{out!r} want {want_word!r}")
    # THE invariant that makes it merge-queue safe: an OPEN PR (never merged) can NEVER
    # produce the terminal verdict, at any elapsed. Terminal is reserved for CLOSED.
    for elapsed in (0, 75, 150, 10_000):
        _, out = run(["poll-verdict", "--state", "open", "--elapsed", str(elapsed), "--cap", "150"])
        check(f"poll-open-never-terminal-{elapsed}", out != "terminal", f"open→terminal at elapsed={elapsed}")

    # ---- archive-check: real git state ----
    with tempfile.TemporaryDirectory() as repo:
        git(repo, "init", "-q"); git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
        (Path(repo) / "a.txt").write_text("hi\n")
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "base")
        # Establish a real upstream (mirrors the real path: the merged branch / main tracks
        # a remote). `@{u}` needs the remote-tracking ref + branch.<b>.{remote,merge} config;
        # the init default branch name is version-dependent, so read it rather than assume.
        br = subprocess.run(["git", "-C", repo, "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
        # A real remote (self-URL) gives origin its fetch refspec, so `@{u}` resolves
        # `refs/heads/<br>` → the `refs/remotes/origin/<br>` tracking ref below.
        git(repo, "remote", "add", "origin", repo)
        git(repo, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*")
        git(repo, "update-ref", f"refs/remotes/origin/{br}", "HEAD")
        git(repo, "config", f"branch.{br}.remote", "origin")
        git(repo, "config", f"branch.{br}.merge", f"refs/heads/{br}")
        rc, out = run(["archive-check", "--cwd", repo])
        check("archive-clean-safe", rc == 0 and out == "safe", f"{out!r} rc={rc}")

        (Path(repo) / "a.txt").write_text("changed\n")     # uncommitted tracked change
        rc, out = run(["archive-check", "--cwd", repo])
        check("archive-dirty-notsafe", rc == 1 and "uncommitted" in out, f"{out!r} rc={rc}")
        git(repo, "checkout", "--", "a.txt")

        (Path(repo) / "stray.txt").write_text("x\n")        # untracked
        rc, out = run(["archive-check", "--cwd", repo])
        check("archive-untracked-notsafe", rc == 1 and "untracked" in out, f"{out!r} rc={rc}")
        (Path(repo) / "stray.txt").unlink()

        (Path(repo) / "b.txt").write_text("b\n")            # unpushed commit
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "ahead")
        rc, out = run(["archive-check", "--cwd", repo])
        check("archive-unpushed-notsafe", rc == 1 and "unpushed" in out, f"{out!r} rc={rc}")

    # A repo with NO upstream configured must report the "no upstream" reason (a real post-merge
    # state on the linked-worktree path where the remote head was auto-deleted).
    with tempfile.TemporaryDirectory() as repo2:
        git(repo2, "init", "-q"); git(repo2, "config", "user.email", "t@t"); git(repo2, "config", "user.name", "t")
        (Path(repo2) / "a.txt").write_text("hi\n")
        git(repo2, "add", "-A"); git(repo2, "commit", "-q", "-m", "base")
        rc, out = run(["archive-check", "--cwd", repo2])
        check("archive-no-upstream-notsafe", rc == 1 and "upstream" in out, f"{out!r} rc={rc}")

    # ---- SKILL contract (the composition + safety commitments the plan pinned) ----
    skill = SKILL.read_text(encoding="utf-8") if SKILL.exists() else ""
    check("skill-exists", bool(skill), "skills/post-merge/SKILL.md missing")
    check("skill-human-invoked", "disable-model-invocation: true" in skill,
          "post-merge must be human-invoked (like /flow:land), never auto-fire")
    check("skill-calls-land", 'Skill("flow:land")' in skill or "Skill('flow:land')" in skill,
          "must COMPOSE with /flow:land (call it), not reimplement reconciliation")
    check("skill-uses-helper", "merge-status.py" in skill, "must drive the deterministic helper")
    check("skill-safe-branch-delete", "branch -d" in skill and "branch -D" not in skill,
          "cleanup must use `git branch -d` (safe), never `-D`")
    # v1 writes user-scope stores only — assert the SPECIFIC negative phrasing (a bare "NOT"
    # substring is always present and can't catch a regression that adds a feedbackPath write).
    check("skill-no-feedbackpath-write", "does **NOT** write the repo `feedbackPath`" in skill,
          "v1 must state it does NOT write feedbackPath (user-scope stores only)")
    check("skill-queue-safe-wording", "postMergeWaitSeconds" in skill and "queue" in skill.lower(),
          "must document the queue-safe poll + the slot")

    # ---- registration fan-out + CI wiring (FB-0010 — mirror run_land_evals.py's reg/ci guards) ----
    ROOT = HERE.parent.parent.parent  # repo root (HERE = plugins/flow/evals)
    def has(rel, needle):
        p = ROOT / rel
        return p.exists() and needle in p.read_text(encoding="utf-8")
    check("reg-plugin-json", has("plugins/flow/.claude-plugin/plugin.json", "flow:post-merge"),
          "/flow:post-merge not registered in plugin.json")
    check("reg-marketplace", has(".claude-plugin/marketplace.json", "flow:post-merge"),
          "/flow:post-merge not registered in marketplace.json")
    check("reg-workflow-help", has("plugins/flow/skills/workflow-help/SKILL.md", "flow:post-merge"),
          "/flow:post-merge not listed in workflow-help")
    check("reg-workflow-doc", has("plugins/flow/docs/workflow.md", "flow:post-merge"),
          "/flow:post-merge not documented in workflow.md")
    check("ci-wired", has(".github/workflows/ci.yml", "run_merge_status_evals.py"),
          "run_merge_status_evals.py not wired into ci.yml (CI enumerates, doesn't glob)")

    # ---- schema slot + count ----
    if SCHEMA.exists():
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        props = schema.get("properties", {})
        slot = props.get("postMergeWaitSeconds", {})
        check("schema-slot-present", slot.get("type") == "integer" and "default" in slot,
              f"postMergeWaitSeconds slot: {slot}")
        check("schema-slot-default", slot.get("default") == 150, f"default={slot.get('default')}")
        check("schema-slot-count-30", len(props) == 30, f"slot count = {len(props)} (want 30)")
    else:
        check("schema-exists", False, "flow.config.schema.json missing")

    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
