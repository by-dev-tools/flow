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
                 (disable-model-invocation), and CALLS /flow:land for doc-currency
                 (FB-0077: land's flag was cleared, so the Skill() call executes —
                 composition, not reimplementation and not a hand-off), uses `branch -d`
                 never `-D`, and writes NO feedbackPath repo doc in v1 (user-scope only).
  schema       — the postMergeWaitSeconds slot exists and the slot count is 33 (a "N slots"
                 fan-out is the most-recurring bug class this repo tracks — FB-0010).

Stdlib only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_utils import fenced_block

HERE = Path(__file__).parent
SKILLDIR = HERE.parent / "skills" / "post-merge"
HELPER = SKILLDIR / "lib" / "merge-status.py"
SKILL = SKILLDIR / "SKILL.md"
SCHEMA = HERE.parent / "schema" / "flow.config.schema.json"
SKILL_DOCTOR = HERE.parent / "skills" / "doctor" / "SKILL.md"


def run(argv: list[str], stdin: str | None = None, cwd=None) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(HELPER), *argv], input=stdin,
                       capture_output=True, text=True, cwd=cwd)
    return p.returncode, (p.stdout or "").strip()


def git(repo, *a):
    subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)


_LINT = None


def _lint():
    """Load skill-composition-lint.py by path (hyphenated name isn't importable).

    Reused, not re-implemented: this harness previously hand-rolled both a
    frontmatter head-split and a fenced-block walk. Both were the *pre-fix*
    versions of parsers the lint already hardened — the fence walk was a boolean
    ``` toggle, which the sibling run_skill_composition_evals.py pins fixtures
    against precisely because it misses ~~~ fences and closes early on nested
    delimiters. Two parsers for one job is the FB-0010 fan-out class living
    inside the evals meant to catch it.
    """
    global _LINT
    if _LINT is None:
        spec = importlib.util.spec_from_file_location(
            "skill_composition_lint",
            HERE.parent / "skills" / "doctor" / "lib" / "skill-composition-lint.py")
        _LINT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_LINT)
    return _LINT


_SLOT_SCAN = None
SLOT_SCAN_PATH = HERE.parent / "skills" / "doctor" / "lib" / "slot_count_scan.py"


def _slot_scan():
    """Load slot_count_scan.py by path — the module `/flow:doctor` Check 2.5 also
    invokes (as a subprocess, since Check 2.5 runs from a shell block), so this
    harness and the consumer-facing check run the identical predicate rather than
    two implementations that can silently drift (the exact FB-0079 class)."""
    global _SLOT_SCAN
    if _SLOT_SCAN is None:
        spec = importlib.util.spec_from_file_location("slot_count_scan", SLOT_SCAN_PATH)
        _SLOT_SCAN = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_SLOT_SCAN)
    return _SLOT_SCAN




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
    # Anchored to the FRONTMATTER block. A whole-file substring test false-passes here:
    # the SKILL's prose quotes `disable-model-invocation: true` while narrating the FB-0077
    # history, so the string survives even after the flag itself is flipped. Verified by
    # mutation — the bare form did not catch the flip.
    check("skill-human-invoked",
          bool(re.search(r"^disable-model-invocation:\s*true\s*$",
                         _lint()._frontmatter(skill), re.M)),
          "post-merge must stay human-invoked, never auto-fire — it is the human gate above "
          "/flow:land now that land's own flag is cleared (FB-0077)")
    # This check has now been inverted TWICE, and the history is why it is worth reading.
    # v1.21.0 asserted post-merge CALLS Skill("flow:land") — but land was
    # disable-model-invocation: true, so the call was rejected on every run and §3 silently
    # degraded to its fallback; the check was pinning a bug. FB-0074 inverted it to assert the
    # call is ABSENT, which pinned the *concession* — §3 rewritten as "ask the human" — and made
    # /flow:post-merge a reminder to run another command. FB-0077 cleared land's flag (its §1a
    # merged-PR gate is the real never-auto-fire guard) and restored the call, so the assertion
    # returns to its original polarity, now against a callee that can actually be invoked.
    #
    # Only a FENCED call counts: the SKILL discusses `Skill("flow:land")` in prose while
    # narrating this history, so a whole-file substring test would pass on that narration
    # alone — the same bare-substring trap that let the FB-0074 concession sail through
    # run_land_evals' flag check. Fence detection comes from the lint's own scan(), which
    # handles ``` and ~~~ and tracks the opening delimiter; a local boolean toggle (what
    # this harness used to carry) silently misses a call inside a ~~~ block.
    _calls = _lint().scan(SKILLDIR.parent)["calls"]
    check("skill-CALLS-land",
          any(c["caller"] == "post-merge" and _lint()._bare(c["target"]) == "land"
              for c in _calls),
          "§3 must emit an executable Skill(\"flow:land\") call (FB-0077) — delegation downgraded "
          "to a hand-off is the defect, not the fix; land is model-invocable so this executes")
    check("skill-still-delegates-to-land", "/flow:land" in skill,
          "must DELEGATE doc-currency to /flow:land, not reimplement it")
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
    # NOTE (FB-0078): this fan-out used to include the two manifests' `description`
    # fields. Dropped — Claude Code generates the plugin's component inventory from
    # disk for the /plugin UI, so a hand-maintained skill catalog inside `description`
    # was a redundant copy that could go stale. The docs are the catalog sites.
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
        # Deliberately a hard-coded literal, not a computed value: this is the
        # FB-0010 tripwire that forces every slot addition to walk the "N slots"
        # fan-out (docs/workflow.md, template/base/CLAUDE.md.template).
        # 30 -> 32 at v1.26.0 (visualFilePatterns + a11yFilePatterns, FB-0079).
        # 32 -> 33 at D1 Phase 0 (role slot, FB-0081).
        check("schema-slot-count-33", len(props) == 33, f"slot count = {len(props)} (want 33)")
        # And no shipped surface may contradict it. Deliberately WRAP-TOLERANT: the
        # literal is matched across newlines, because the survivor that slipped this
        # PR's first sweep was `all 30\n  slots` wrapped inside doctor/SKILL.md's
        # frontmatter — invisible to a line-oriented `grep -n '30 slots'`. Grepping the
        # old VALUE also misses the class; this greps the SHAPE. The predicate itself
        # now lives in slot_count_scan.py, shared with /flow:doctor Check 2.5 — see
        # the shell-parity check below for why that sharing is the point.
        root = Path(__file__).resolve().parents[3]
        stale, scanned = _slot_scan().scan_paths(
            [root / "plugins", root / "template"], expected=len(props),
            exclude_substrings=("evals/", "plan-critic.md"),  # harnesses + the prose
                                                               # example teaching the failure
            root=root)
        # Vacuous-pass guard: an empty sweep (moved dirs, installed-plugin layout)
        # would otherwise go green having measured nothing — the exact class this
        # same commit fixed in the jq-parity check.
        check("slot-count-sweep-scanned-files", scanned > 0,
              f"sweep scanned {scanned} files under {root} — it measured nothing")
        check("no-stale-slot-count-in-shipped-surfaces", not stale,
              "shipped surfaces contradict the schema count: " + "; ".join(stale))

        # ---- the hoisted predicate itself: prove the wrap-tolerant case, and prove
        # doctor's Check 2.5 shell block actually delegates to it rather than having
        # regrown its own line-oriented grep (the exact regression this PR closes) ----
        with tempfile.TemporaryDirectory() as scratch:
            wrapped = Path(scratch) / "WRAPPED.md"
            # The literal FB-0079 shape: the number and "slots" separated by a newline
            # inside what would be YAML frontmatter — invisible to `grep -n`.
            wrapped.write_text("---\nname: x\ndescription: all 30\n  slots\n---\n")
            lib_stale, lib_scanned = _slot_scan().scan_paths([wrapped], expected=len(props))
            check("slot-count-scan-catches-wrapped-fixture",
                  lib_scanned == 1 and any("30" in s for s in lib_stale),
                  f"scan_paths() did not catch a newline-wrapped '30\\n  slots' "
                  f"(scanned={lib_scanned}, stale={lib_stale}) — the exact FB-0079 miss")

            doctor_skill_text = SKILL_DOCTOR.read_text(encoding="utf-8") if SKILL_DOCTOR.exists() else ""
            check("doctor-check-2.5-invokes-shared-scan",
                  "slot_count_scan.py" in doctor_skill_text,
                  "Check 2.5 must invoke the shared slot_count_scan.py predicate, not "
                  "a private grep — otherwise the consumer-facing check can silently "
                  "regrow the exact line-oriented gap FB-0079 fixed internally")
            block = fenced_block(doctor_skill_text, "Check 2.5 —")
            check("doctor-check-2.5-block-extractable", block is not None,
                  "could not extract Check 2.5's executable shell block")
            if block is not None:
                # Run the REAL shell block (not a grep of its text) against the same
                # wrapped fixture, from a temp cwd, pointed at this checkout's plugin
                # root via CLAUDE_PLUGIN_ROOT so SCHEMA + LIB resolve without touching
                # the real repo's own CLAUDE.md. This is the parity guarantee: if
                # Check 2.5 ever regrows a private line-oriented grep, this check goes
                # red on the exact fixture the library-only check above already passes.
                (Path(scratch) / "CLAUDE.md").write_text("all 30\n  slots\n")
                plugin_root = HERE.parent  # plugins/flow
                env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(plugin_root))
                proc = subprocess.run(["sh", "-c", block], cwd=scratch, env=env,
                                       capture_output=True, text=True, timeout=10)
                out = proc.stdout
                check("doctor-check-2.5-shell-catches-wrapped-fixture",
                      "[WARN]" in out and "30" in out,
                      f"Check 2.5's real shell block did not flag a newline-wrapped "
                      f"'30\\n  slots' in CLAUDE.md (stdout={out!r})")

                # PASS-path regression case (staff-review altitude lens): the WARN case
                # above never exercises RC=0's SCANNED_COUNT= extraction, so a future
                # rewording of slot_count_scan.py's human-readable line could silently
                # blank that field and nothing here would catch it. Separate scratch
                # dir — a clean, matching count, not the wrapped-stale fixture above.
                with tempfile.TemporaryDirectory() as clean_scratch:
                    (Path(clean_scratch) / "CLAUDE.md").write_text(
                        f"this project uses {len(props)} slots\n")
                    proc_pass = subprocess.run(["sh", "-c", block], cwd=clean_scratch, env=env,
                                                capture_output=True, text=True, timeout=10)
                    out_pass = proc_pass.stdout
                    check("doctor-check-2.5-shell-pass-path-renders-scanned-count",
                          "[PASS]" in out_pass and "scanned 1 file(s)" in out_pass,
                          f"Check 2.5's real shell block did not render a real scanned "
                          f"count on a clean, matching doc (stdout={out_pass!r}) — the "
                          f"SCANNED_COUNT= extraction may have silently gone blank")
    else:
        check("schema-exists", False, "flow.config.schema.json missing")

    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
