#!/usr/bin/env python3
"""Eval harness for /flow:retro's deterministic core + skill contract (FB-0072).

The skill orchestration (merge-detect → land → feedback-synth → cleanup → archive-verdict)
is prose the agent drives, but its LOAD-BEARING core is deterministic and pinned here:

  classify     — the three-state merge gate: MERGED / CLOSED-unmerged / OPEN. The whole
                 point of the gate is that a transient "can't tell yet" is NEVER the
                 terminal "will never merge" — so the unknown/empty case classifies OPEN.
  poll-verdict — the queue-safe poll policy: OPEN-at-cap gives up GRACEFULLY (distinct
                 from the CLOSED terminal fail), and cap==0 fail-fast on OPEN is also
                 graceful, never terminal. This is the false-fail-on-merge-queue fix.
  archive-check— the "safe to archive?" verdict over real git state in a temp repo.
  group        — (v1.69.0) a batch of merged PRs closes out in ONE run: `parse-prs`
                 normalizes the argument, `select` picks "merged since the last retro"
                 from a per-repo watermark (excluding the `docs: land` PRs a previous retro
                 produced), `advance` moves that watermark monotonically, and `branch-plan`
                 decides per-PR cleanup against REAL git state in a temp repo (remote tip must
                 equal the PR's headRefOid; forks and other-worktree checkouts are never touched).
  contract     — the SKILL wires the pieces the way the plan committed: MODEL-invocable with an
                 AUTO-INVOCATION clause (v1.69.0; was human-only), and CALLS /flow:land for doc-currency
                 (FB-0077: land's flag was cleared, so the Skill() call executes —
                 composition, not reimplementation and not a hand-off), uses `branch -d`
                 never `-D`, and writes NO feedbackPath repo doc in v1 (user-scope only).
  schema       — the postMergeWaitSeconds slot exists and the slot count is 39 (a "N slots"
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from eval_utils import fenced_block

HERE = Path(__file__).parent
SKILLDIR = HERE.parent / "skills" / "retro"
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


    # ---- group handling (v1.69.0): parse-prs / select / advance / branch-plan ----
    rc, out = run(["parse-prs", "151", "#153", "155,156", "151"])
    check("parse-prs-normalizes-and-dedups", rc == 0 and out.split() == ["151", "153", "155", "156"],
          f"{out!r} rc={rc}")
    # A URL names an owner/repo; reducing it to a number would act on the WRONG repo's PR.
    rc, out = run(["parse-prs", "https://github.com/other/repo/pull/12"])
    check("parse-prs-refuses-a-url-it-would-misattribute", rc == 2 and out == "", f"{out!r} rc={rc}")
    rc, out = run(["parse-prs", "151 153"])
    check("parse-prs-splits-one-quoted-string", rc == 0 and out.split() == ["151", "153"], f"{out!r} rc={rc}")
    # A non-number must be REFUSED, and a refusal must be distinguishable from an empty group.
    for label, toks in [("junk", ["x;rm"]), ("zero", ["0"]), ("word", ["abc"]), ("neg", ["-5"])]:
        rc, out = run(["parse-prs", *toks])
        check(f"parse-prs-refuses-{label}", rc == 2 and out == "", f"{toks} → rc={rc} out={out!r}")
    rc, _ = run(["parse-prs"])
    check("parse-prs-empty-is-error-not-empty-group", rc == 2, f"rc={rc}")

    def select(prs, wm=None, extra=()):
        with tempfile.TemporaryDirectory() as d:
            wmf = Path(d) / "last_retro.json"
            if wm is not None:
                wmf.write_text(json.dumps({"o/r": wm}))
            rc, out = run(["select", "--watermark-file", str(wmf), "--repo", "o/r", *extra],
                          stdin=json.dumps(prs))
            return rc, out.split()

    now = datetime.now(timezone.utc)
    ts = lambda days: (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    prs = [
        {"number": 10, "title": "feat: a", "mergedAt": ts(1)},
        {"number": 11, "title": "docs: land #10 — post-merge currency", "mergedAt": ts(0.9)},
        {"number": 12, "title": "feat: b", "mergedAt": ts(0.5)},
        {"number": 5, "title": "feat: old", "mergedAt": ts(30)},
        {"number": 13, "title": "docs: landing page copy", "mergedAt": ts(0.4)},
    ]
    # a land-shaped TITLE alone is attacker-writable; with a known head ref the exclusion needs both.
    spoof = prs + [{"number": 14, "title": "docs: land #99 — x", "mergedAt": ts(0.3), "headRefName": "feature/x"},
                   {"number": 15, "title": "docs: land #98 — post-merge currency", "mergedAt": ts(0.2),
                    "headRefName": "claude/land-98"}]
    rc, got = select(spoof)
    check("select-land-title-needs-a-land-head-when-known", got == ["10", "12", "13", "14"], f"{got}")
    rc, got = select(prs)
    # first run in a repo: last 7 days only (NOT the whole history), docs: land excluded, oldest first
    # 13 is "docs: landing page copy": a real PR whose title merely starts like a land PR — must stay in.
    check("select-first-run-bounded-and-excludes-land", got == ["10", "12", "13"], f"{got}")
    rc, got = select(prs, wm={"since": ts(0.95), "done": []})
    check("select-after-watermark", got == ["12", "13"], f"{got}")
    # boundary: a PR AT the watermark instant is excluded iff it is in `done`
    at = ts(0.5)
    rc, got = select(prs, wm={"since": at, "done": [12]})
    check("select-boundary-done-is-excluded", got == ["13"], f"{got}")  # 13 merged later: still newer
    rc, got = select(prs, wm={"since": at, "done": []})
    check("select-boundary-not-done-is-included", got == ["12", "13"], f"{got}")
    # cap: oldest first, and the truncation is announced, never silent
    many = [{"number": 100 + i, "title": f"feat {i}", "mergedAt": ts(3 - i * 0.01)} for i in range(5)]
    with tempfile.TemporaryDirectory() as d:
        proc = subprocess.run([sys.executable, str(HELPER), "select", "--watermark-file", f"{d}/w.json",
                               "--repo", "o/r", "--cap", "2"], input=json.dumps(many),
                              capture_output=True, text=True)
    check("select-cap-takes-oldest-and-says-so",
          proc.stdout.split() == ["100", "101"] and "3 more" in proc.stderr,
          f"{proc.stdout!r} / {proc.stderr!r}")
    rc, _ = select("not-a-list-of-prs")
    check("select-garbage-input-is-empty-group-not-crash", rc == 0, f"rc={rc}")
    # a watermark for ANOTHER repo must not filter this one (the file is user-scope, cross-project)
    with tempfile.TemporaryDirectory() as d:
        wmf = Path(d) / "w.json"
        wmf.write_text(json.dumps({"other/repo": {"since": ts(0.1), "done": []}}))
        rc, out = run(["select", "--watermark-file", str(wmf), "--repo", "o/r"], stdin=json.dumps(prs))
    check("select-watermark-is-per-repo", out.split() == ["10", "12", "13"], f"{out!r}")

    # advance: monotonic, per-repo, boundary-aware
    with tempfile.TemporaryDirectory() as d:
        wmf = Path(d) / "sub" / "last_retro.json"
        rc, out = run(["advance", "--watermark-file", str(wmf), "--repo", "o/r"],
                      stdin=json.dumps([{"number": 1, "mergedAt": "2026-11-01T00:00:00Z"},
                                        {"number": 2, "mergedAt": "2026-11-02T00:00:00Z"},
                                        {"number": 3, "mergedAt": "2026-11-02T00:00:00Z"}]))
        rec = json.loads(wmf.read_text())["o/r"]
        check("advance-writes-newest-and-its-boundary-prs",
              rc == 0 and rec == {"since": "2026-11-02T00:00:00Z", "done": [2, 3]}, f"{rec}")
        run(["advance", "--watermark-file", str(wmf), "--repo", "o/r"],
            stdin=json.dumps([{"number": 9, "mergedAt": "2026-10-01T00:00:00Z"}]))
        check("advance-never-moves-backwards",
              json.loads(wmf.read_text())["o/r"]["since"] == "2026-11-02T00:00:00Z", wmf.read_text())
        run(["advance", "--watermark-file", str(wmf), "--repo", "o/r"],
            stdin=json.dumps([{"number": 4, "mergedAt": "2026-11-02T00:00:00Z"}]))
        check("advance-same-instant-unions-done",
              json.loads(wmf.read_text())["o/r"]["done"] == [2, 3, 4], wmf.read_text())
        run(["advance", "--watermark-file", str(wmf), "--repo", "x/y"],
            stdin=json.dumps([{"number": 7, "mergedAt": "2026-11-05T00:00:00Z"}]))
        whole = json.loads(wmf.read_text())
        check("advance-keeps-other-repos", set(whole) == {"o/r", "x/y"}, f"{sorted(whole)}")
        rc, out = run(["advance", "--watermark-file", str(wmf), "--repo", "o/r"], stdin="[]")
        check("advance-empty-is-no-change", rc == 0 and out == "no-change", f"{out!r}")

    # branch-plan against REAL git state: bare origin + clone + linked worktree
    with tempfile.TemporaryDirectory() as d:
        origin, repo, wt = f"{d}/origin.git", f"{d}/repo", f"{d}/wt"
        subprocess.run(["git", "init", "-q", "--bare", origin], check=True, capture_output=True)
        subprocess.run(["git", "clone", "-q", origin, repo], check=True, capture_output=True)
        git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
        git(repo, "checkout", "-q", "-b", "main")
        (Path(repo) / "a").write_text("a\n"); git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "base")
        git(repo, "push", "-q", "origin", "main")

        def sha(ref="HEAD"):
            return subprocess.run(["git", "-C", repo, "rev-parse", ref], capture_output=True,
                                  text=True).stdout.strip()

        def branch(name):
            git(repo, "checkout", "-q", "-b", name, "main")
            (Path(repo) / f"{name}.txt").write_text(name); git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", name); git(repo, "push", "-q", "origin", name)
            tip = sha(); git(repo, "checkout", "-q", "main"); return tip

        a, b, c = branch("feat-a"), branch("feat-b"), branch("feat-c")
        git(repo, "worktree", "add", "-q", wt, "feat-c")

        def plan(name, oid, fork=False, default="main"):
            blob = {"headRefName": name, "headRefOid": oid, "isCrossRepository": fork}
            rc, out = run(["branch-plan", "--default-branch", default, "--cwd", repo], stdin=json.dumps(blob))
            return json.loads(out)

        pa = plan("feat-a", a)
        check("branch-plan-remote-tip-equals-head-is-delete", pa["remote"] == "delete", f"{pa}")
        # THE squash-merge case: local branch exists, not an ancestor of main → `-d` would refuse,
        # so the plan must say the local branch is a delete CANDIDATE only; the SKILL reports the refusal.
        check("branch-plan-local-reports-tip-match", pa["local"] == "delete" and pa["tip_matches"] is True, f"{pa}")
        # remote moved after the merge → never delete
        git(repo, "checkout", "-q", "feat-b"); (Path(repo) / "late").write_text("x"); git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "late"); git(repo, "push", "-q", "origin", "feat-b")
        git(repo, "checkout", "-q", "main")
        pb = plan("feat-b", b)
        check("branch-plan-remote-moved-is-not-deleted", pb["remote"] == "moved", f"{pb}")
        pc = plan("feat-c", c)
        check("branch-plan-other-worktree-is-named-not-deleted",
              pc["local"].startswith("worktree:") and os.path.realpath(wt) == os.path.realpath(pc["local"][9:]),
              f"{pc}")
        pf = plan("feat-a", a, fork=True)
        check("branch-plan-fork-is-never-cleaned", pf["remote"] == "skip-fork" and pf["local"] == "skip-fork", f"{pf}")
        pg = plan("feat-zzz", a)
        check("branch-plan-missing-branches", pg["remote"] == "gone" and pg["local"] == "absent", f"{pg}")
        pn = plan("feat-a", "")
        check("branch-plan-no-headRefOid-is-unverified-never-delete", pn["remote"] == "unverified", f"{pn}")
        check("branch-plan-default-branch-is-never-a-target",
              plan("main", a)["remote"] == "skip-default", f"{plan('main', a)}")
        for ll in ("develop", "staging", "release/1.x", "release-2", "gh-pages", "hotfix/a"):
            pl = plan(ll, a)
            check(f"branch-plan-long-lived-never-a-target-{ll}", pl["remote"] == "skip-long-lived"
                  and pl["local"] == "skip-long-lived", f"{pl}")
        check("branch-plan-ordinary-name-not-mistaken-for-long-lived",
              plan("feat-a", a)["remote"] == "delete", f"{plan('feat-a', a)}")
        for bad in ("-D", "a b", "x;y", "$(id)"):
            pu = plan(bad, a)
            check(f"branch-plan-unsafe-name-refused-{bad!r}", pu["remote"] == "unsafe-name", f"{pu}")
        # ls-remote matches by ref SUFFIX: a namespaced sibling `a/feat-n` must not stand in for `feat-n`.
        n_tip = branch("feat-n")
        git(repo, "push", "-q", "origin", "feat-n:refs/heads/a/feat-n")   # sibling at the SAME tip
        git(repo, "push", "-q", "origin", ":refs/heads/feat-n")           # ...and the real branch is gone
        pn2 = plan("feat-n", n_tip)
        check("branch-plan-ls-remote-suffix-sibling-is-not-the-branch", pn2["remote"] == "gone", f"{pn2}")
        # checked out HERE → 'current'
        git(repo, "checkout", "-q", "feat-a")
        check("branch-plan-current-branch", plan("feat-a", a)["local"] == "current", f"{plan('feat-a', a)}")
        git(repo, "checkout", "-q", "main")

    # ---- SKILL contract (the composition + safety commitments the plan pinned) ----
    skill = SKILL.read_text(encoding="utf-8") if SKILL.exists() else ""
    check("skill-exists", bool(skill), "skills/retro/SKILL.md missing")
    # Anchored to the FRONTMATTER block. A whole-file substring test false-passes here:
    # the SKILL's prose quotes `disable-model-invocation: true` while narrating the FB-0077
    # history, so the string survives even after the flag itself is flipped. Verified by
    # mutation — the bare form did not catch the flip.
    # v1.69.0 INVERTED this check. FB-0077 pinned retro as the human gate above /flow:land; in
    # practice the flag only blocked the user it was meant to serve (a chat "run the retro" got a
    # refused Skill() call, once per PR). The guard was never the flag — it is §2's merged-PR gate.
    # The flag is now `false`, DECLARED (an absent flag also parses invocable, so a deletion would
    # lose the recorded decision), and the WHEN is pinned as an AUTO-INVOCATION clause, because
    # nothing mechanical bounds timing and the clause is the only thing that does.
    fm = _lint()._frontmatter(skill)
    check("skill-model-invocable-declared",
          bool(re.search(r"^disable-model-invocation:\s*false\s*$", fm, re.M)),
          "retro must declare disable-model-invocation: false (v1.69.0) so the model can run a "
          "retro the user asks for in chat")
    check("skill-has-auto-invocation-clause", "AUTO-INVOCATION" in fm,
          "model-invocable without an AUTO-INVOCATION clause leaves nothing saying WHEN — the "
          "flag no longer does")
    # The clause must carry BOTH halves: when to fire, and when NOT to (mid-loop / before a merge).
    check("skill-clause-fires-on-ask-or-landed-batch",
          "asks for a retro" in fm and "have merged" in fm.replace("\n", " ").replace("  ", " "),
          "clause must name both triggers: the user asking in words, and PRs having merged")
    check("skill-clause-forbids-mid-loop",
          "NEVER invoke" in fm and "mid-loop" in fm and "end of /flow:ship" in fm.replace("\n", " ").replace("  ", " "),
          "clause must forbid firing mid-loop / at the end of /flow:ship / ahead of a merge")
    # The safety the clause leans on must still exist: §2 refuses non-merged, in the shipped blocks.
    check("skill-merge-gate-still-refuses-closed",
          "CLOSED without merging" in skill and 'closed) CLOSED=' in skill,
          "§2 must still classify and refuse closed-unmerged PRs — it is the guard the flag used to stand in for")
    # This check has now been inverted TWICE, and the history is why it is worth reading.
    # v1.21.0 asserted post-merge (now /flow:retro) CALLS Skill("flow:land") — but land was
    # disable-model-invocation: true, so the call was rejected on every run and §3 silently
    # degraded to its fallback; the check was pinning a bug. FB-0074 inverted it to assert the
    # call is ABSENT, which pinned the *concession* — §3 rewritten as "ask the human" — and made
    # /flow:retro a reminder to run another command. FB-0077 cleared land's flag (its §1a
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
          any(c["caller"] == "retro" and _lint()._bare(c["target"]) == "land"
              for c in _calls),
          "§3 must emit an executable Skill(\"flow:land\") call (FB-0077) — delegation downgraded "
          "to a hand-off is the defect, not the fix; land is model-invocable so this executes")
    check("skill-still-delegates-to-land", "/flow:land" in skill,
          "must DELEGATE doc-currency to /flow:land, not reimplement it")
    check("skill-uses-helper", "merge-status.py" in skill, "must drive the deterministic helper")
    check("skill-safe-branch-delete", "branch -d" in skill and "branch -D" not in skill,
          "cleanup must use `git branch -d` (safe), never `-D`")
    # ---- v1.69.0 group contract. Every negative is paired with the positive it protects. ----
    check("skill-group-argument", "[<PR#> …]" in skill and "parse-prs" in skill,
          "retro must accept a LIST of PRs and normalize it through the helper")
    check("skill-no-argument-does-not-prompt",
          "**do not ask.**" in skill and "confirm the number with the user" not in skill,
          "a bare /flow:retro must resolve the default group without a confirmation prompt")
    check("skill-default-group-uses-watermark", " select --watermark-file " in skill and "last_retro.json" in skill,
          "the default group must come from the per-repo watermark helper")
    check("skill-land-called-once-with-the-group",
          "ONCE for the group" in skill and "passing every number in `TODO`" in skill,
          "the land call must carry the whole group (one docs PR), not run per PR")
    check("skill-cleanup-uses-branch-plan", " branch-plan --default-branch " in skill,
          "per-PR cleanup must go through the deterministic branch-plan decision")
    check("skill-remote-delete-is-verified-against-headRefOid",
          "headRefOid" in skill and 'refs/heads/$BR:$OID' in skill,
          "remote head deletion must be gated on the tip equalling the PR's headRefOid")
    check("skill-leaves-squash-merged-branches-and-says-so",
          "LEFT BEHIND" in skill and "never force-deletes" in skill,
          "a branch `-d` refuses must be REPORTED as left behind, not force-deleted")
    check("skill-skips-other-worktrees", "checked out in another worktree" in skill and "worktree:*" in skill,
          "branches checked out in other worktrees must be skipped and named")
    check("skill-landing-pr-match-is-not-title-only",
          'select(.isCrossRepository == false)' in skill and 'select(.baseRefName == $b)' in skill
          and 'test("(^|/)land-[0-9]")' in skill,
          "'already landed' must require a same-repo, default-based land-<N> PR, not merely a title naming #N")
    check("skill-remote-delete-is-leased-and-protected-checked",
          "--force-with-lease=" in skill and ".protected" in skill and "does not match the repo gh resolved" in skill
          and "git push origin --delete" not in "\n".join(re.findall(r"```sh\n(.*?)```", skill, re.S)),
          "remote delete must be fully-qualified, leased on headRefOid, fail-closed on protection + repo match")
    # §6 / §6b are PROSE rules the agent executes — pinned here as text, which is weaker than a
    # behavioral test (stated in the PR body), but a deletion of any condition now fails CI.
    _flat = " ".join(skill.split())   # the prose is hard-wrapped; compare on whitespace-normalized text
    check("skill-verdict-requires-all-four-inputs",
          "ONLY when ALL hold" in _flat and "§5 left no local branch behind" in _flat
          and "§2 left nothing out" in _flat and "never a ✅" in _flat and "🚫 not fully closed out" in _flat,
          "the ✅ line must stay conditional on git-state, branch cleanup, landing PRs AND PRs left out of §2")
    check("skill-watermark-advance-conditions-are-all-named",
          "**default**" in _flat and "doc-currency-satisfied" in _flat and "§2 left nothing out" in _flat
          and "page of merged PRs was full" in _flat and "An explicit-list run never moves it" in _flat,
          "§6b must keep every advance condition: default group, all reconciled, nothing left out, page not full, never explicit")
    check("skill-keeps-fork-guard", "skip-fork" in skill and "fork PR" in skill,
          "fork PRs must never have their head branch deleted from origin")
    # Fenced blocks only: the prose NAMES the forbidden form while explaining it.
    _code = "\n".join(re.findall(r"```[a-z]*\n(.*?)```", skill, re.S))
    check("skill-iterates-with-while-read-not-for-in-var",
          "while read -r N" in _code and not re.search(r"for \w+ in \$\w+", _code),
          "zsh does not word-split an unquoted variable — iterate with while-read, not `for x in $LIST`")
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
    check("reg-workflow-help", has("plugins/flow/skills/workflow-help/SKILL.md", "flow:retro"),
          "/flow:retro not listed in workflow-help")
    check("reg-workflow-doc", has("plugins/flow/docs/workflow.md", "flow:retro"),
          "/flow:retro not documented in workflow.md")
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
        # 33 -> 34 at FB-0102 (changelogPath). That slot had been READ by
        # /flow:land for several releases while absent from the schema, so
        # consumers could not discover it and it silently fell back forever --
        # indistinguishable from having chosen the default. Declaring it was a
        # precondition for repointing it at a one-file-per-release directory.
        # 34 -> 36 with dispatchBackend + sensitivePaths (the orchestrator suite).
        # 39 with ciWaitSeconds (v1.64.0); 41 with captureBackend + chatImagePath
        # (v1.65.0). Two concurrent branches each swept 38 -> their own number and
        # both were right in isolation; the merged tree is neither. This check is
        # what forced the question at rebase rather than after merge.
        check("schema-slot-count-41", len(props) == 41, f"slot count = {len(props)} (want 41)")
        # And no shipped surface may contradict it. Deliberately WRAP-TOLERANT: the
        # literal is matched across newlines, because the survivor that slipped this
        # PR's first sweep was `all 30\n  slots` wrapped inside doctor/SKILL.md's
        # frontmatter — invisible to a line-oriented `grep -n '30 slots'`. Grepping the
        # old VALUE also misses the class; this greps the SHAPE. The predicate itself
        # now lives in slot_count_scan.py, shared with /flow:doctor Check 2.5 — see
        # the shell-parity check below for why that sharing is the point.
        root = Path(__file__).resolve().parents[3]
        stale, scanned = _slot_scan().scan_paths(
            # README.md is a SHIPPED surface (CLAUDE.md's artifact table lists it) and this
            # sweep never read it -- which is exactly why "A 24-slot flow.config.json" sat in
            # the most-read file in the repo against a 37-slot schema while this check stayed
            # green for release after release. A sweep that omits the front page is not a sweep.
            [root / "plugins", root / "template", root / "README.md"], expected=len(props),
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

            # CV1 — the THIRD separator escape. `README.md:89` read "A 24-slot
            # `flow.config.json`" against a 37-slot schema while every sweep above went
            # green: `\d+\s+slots?` cannot match a hyphen. Paired with the two shapes that
            # must NOT match, because "be more tolerant" is satisfiable by matching
            # everything -- both were real false positives on the first, looser fix.
            hyph = Path(scratch) / "HYPH.md"
            hyph.write_text("- **A 30-slot `flow.config.json`** ships today.\n")
            h_stale, h_scanned = _slot_scan().scan_paths([hyph], expected=len(props))
            check("slot-count-scan-catches-hyphenated-fixture",
                  h_scanned == 1 and any("30-slot" in s for s in h_stale),
                  f"scan_paths() did not catch 'A 30-slot' (scanned={h_scanned}, "
                  f"stale={h_stale}) — the exact CV1 miss, in the most-read shipped file")
            quiet = Path(scratch) / "QUIET.md"
            quiet.write_text("(FB-0058 boolean-slot footgun) and the Step 4 config-slot "
                             "consumers are not counts.\n")
            q_stale, q_scanned = _slot_scan().scan_paths([quiet], expected=len(props))
            # PAIRED NEGATIVE for the hyphen support, and it is the one that was missing: the
            # positive above ("30-slot" against 37) passed even while the comparison was broken,
            # because a broken comparison flags EVERY hyphenated form whatever its number. Only
            # a correct-count hyphenated fixture can tell the two apart (general.md item 4 --
            # validate the instrument on the case where it must stay quiet, too).
            okhyph = Path(scratch) / "OKHYPH.md"
            okhyph.write_text(f"- **A {len(props)}-slot `flow.config.json`** ships today.\n")
            ok_stale, ok_scanned = _slot_scan().scan_paths([okhyph], expected=len(props))
            check("slot-count-scan-does-not-flag-a CORRECT hyphenated count",
                  ok_scanned == 1 and not ok_stale,
                  f"a hyphenated count that MATCHES the schema was reported stale: {ok_stale} "
                  "— the matcher reads the hyphen but the comparison does not")
            check("slot-count-scan-does-not-flag-hyphenated-compound-adjectives",
                  q_scanned == 1 and not q_stale,
                  "an issue number followed by a hyphenated compound adjective is not a "
                  f"slot count; flagging it is how a scanner stops being read: {q_stale}")

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
