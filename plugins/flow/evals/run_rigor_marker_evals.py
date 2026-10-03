#!/usr/bin/env python3
"""Eval harness for /flow:ship's rigor-marker.py (the simplify+staff-review evidence marker).

Pins the contract /flow:ship Step 1.0 keys on:

  write→check ok    — a marker written with (branch, source_sha) passes check with the same pair.
  branch-mismatch   — same source_sha, different branch → exit 1 + "branch-mismatch".
  source-drift      — same branch, different source_sha → exit 1 + "source-drift".
  missing           — no marker file → exit 1 + "missing".
  source-sha stable — `source-sha` is deterministic (two calls agree) and a 64-char hex digest.

Uses an explicit --path in a temp dir (no /tmp pollution, no reliance on the default
branch-slug path). Stdlib only.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from eval_utils import bang_blocks, git_repo  # noqa: E402

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "ship" / "lib" / "rigor-marker.py"


def run(argv: list[str], cwd=None) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *argv],
                          capture_output=True, text=True, check=False, cwd=cwd)
    return proc.returncode, (proc.stdout + proc.stderr)


def main() -> int:
    fails = 0
    total = 0

    def check(label, cond, detail=""):
        nonlocal fails, total
        total += 1
        if cond:
            print(f"PASS  [{label}]")
        else:
            fails += 1
            print(f"FAIL  [{label}] {detail}")

    # sha256 of no input — what an empty fingerprint hashes to, and what both sides
    # compared equal on before the degrade paths were guarded.
    EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    with tempfile.TemporaryDirectory() as tmp:
        marker = str(Path(tmp) / "marker.json")
        SHA = "a" * 64

        rc, _ = run(["write", "--branch", "feature/x", "--source-sha", SHA, "--path", marker])
        check("write-ok", rc == 0, f"write rc={rc}")

        rc, out = run(["check", "--branch", "feature/x", "--source-sha", SHA, "--path", marker])
        check("check-ok", rc == 0 and "ok" in out, f"rc={rc} out={out!r}")

        rc, out = run(["check", "--branch", "feature/OTHER", "--source-sha", SHA, "--path", marker])
        check("branch-mismatch", rc == 1 and "branch-mismatch" in out, f"rc={rc} out={out!r}")

        rc, out = run(["check", "--branch", "feature/x", "--source-sha", "b" * 64, "--path", marker])
        check("source-drift", rc == 1 and "source-drift" in out, f"rc={rc} out={out!r}")

        rc, out = run(["check", "--branch", "feature/x", "--source-sha", SHA,
                       "--path", str(Path(tmp) / "nope.json")])
        check("missing", rc == 1 and "missing" in out, f"rc={rc} out={out!r}")

    # source-sha determinism + shape (runs against this repo's real git state).
    rc1, o1 = run(["source-sha"])
    rc2, o2 = run(["source-sha"])
    d1, d2 = o1.strip(), o2.strip()
    check("source-sha-deterministic", rc1 == 0 and rc2 == 0 and d1 == d2, f"{d1!r} vs {d2!r}")
    check("source-sha-is-hex64", len(d1) == 64 and all(c in "0123456789abcdef" for c in d1), f"{d1!r}")

    # Meaningful diff-hashing test: a SEEDED temp git repo with an origin/main ref, so the
    # real `git diff origin/main` path is exercised even under CI's depth-1 checkout (where
    # the in-repo run above degrades to the empty-input hash). A tracked source change MUST
    # move the fingerprint; commit-invariance MUST hold (committing the change keeps it).
    def git(repo, *a):
        subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)
    with tempfile.TemporaryDirectory() as repo:
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
        (Path(repo) / "a.py").write_text("x = 1\n")
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "base")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")  # fake remote-tracking ref
        _, h_base = run(["source-sha", "--default-branch", "main"], cwd=repo)
        (Path(repo) / "a.py").write_text("x = 2\n")  # uncommitted tracked source change
        _, h_dirty = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("source-sha-detects-source-change", h_base.strip() != h_dirty.strip(),
              f"{h_base.strip()!r} vs {h_dirty.strip()!r}")
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "change")  # commit it
        _, h_committed = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("source-sha-commit-invariant", h_committed.strip() == h_dirty.strip(),
              f"committed {h_committed.strip()!r} != dirty {h_dirty.strip()!r}")

        # The new-file transition the old algorithm got WRONG (Swift cold-run + dogfound): a
        # brand-new source file is UNTRACKED pre-commit, TRACKED post-commit. Hashing raw bytes
        # for untracked but the diff PATCH for tracked flipped the fingerprint across that
        # commit → false source-drift at ship Step 1.0a on every new-file PR. Content-hashing
        # must keep it stable.
        (Path(repo) / "new_file.py").write_text("z = 3\n")  # untracked new source file
        _, h_untracked = run(["source-sha", "--default-branch", "main"], cwd=repo)
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "add new_file")
        _, h_newcommit = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("source-sha-untracked-to-committed-invariant",
              h_untracked.strip() == h_newcommit.strip(),
              f"untracked {h_untracked.strip()!r} != committed {h_newcommit.strip()!r}")
        # And the new file's content must actually be IN the fingerprint (not silently dropped).
        check("source-sha-new-file-detected", h_untracked.strip() != h_committed.strip(),
              f"new untracked file did not move the fingerprint: {h_untracked.strip()!r}")

    # ------------------------------------------------------ CV1 follow-up, item 2
    # FIXTURES FIRST. The fingerprint is the evidence that /simplify + /flow:staff-review ran on
    # THIS source. It was computed through `sourceFilePatterns` alone, which matches no `.md`
    # path at all -- so on #172, 0 of 13 changed `.md` files were in it, and the two SHIPPED
    # skill prose files could be rewritten after staff-review with the gate still reading "ok".
    # Prompt and skill prose IS deployed surface in this plugin (CLAUDE.md: "Prompt changes are
    # code changes"), so this is the rigor gate failing open on the surface flow mostly is.
    #
    # Each arm below varies ONE thing inside ONE repo. Writing flow.config.json differently
    # between two arms would move the fingerprint by itself -- flow.config.json matches
    # `sourceFilePatterns` -- and the test would pass for that reason instead of the slot's.
    # So the config is committed in the BASE and only the prose file is added afterwards.
    def seeded_repo(repo, config=None):
        """Base commit (a.py + optional flow.config.json) with an origin/main ref.

        Seeding goes through `eval_utils.git_repo`, not a hand-rolled init/config/commit: the
        hand-rolled copy was both a duplicate AND already behind, since `git_repo` passes
        `-b main` and this did not. eval_utils' own docstring states the policy -- five older
        harnesses keep private copies so the eventual hoist is a deletion, and NEW harnesses
        import -- and this file already imports from it further down, which is what made the
        copy indefensible rather than merely redundant.
        """
        files = {"a.py": "x = 1\n"}
        if config is not None:
            files["flow.config.json"] = config
        git_repo(Path(repo), files)
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        rc, h = run(["source-sha", "--default-branch", "main"], cwd=repo)
        return h.strip()

    def add_and_hash(repo, relpath, body="prose\n"):
        f = Path(repo) / relpath
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
        rc, h = run(["source-sha", "--default-branch", "main"], cwd=repo)
        return h.strip()

    # (1) Shipped skill prose must be IN the fingerprint.
    with tempfile.TemporaryDirectory() as repo:
        h0 = seeded_repo(repo)
        h1 = add_and_hash(repo, "skills/audit-coverage/SKILL.md")
        check("doc-builtin-shipped-prose-moves-the-fingerprint", h0 != h1,
              "a changed skills/**/SKILL.md left the fingerprint untouched, so skill prose can "
              "be rewritten after staff-review and the rigor gate still reads ok")
        h2 = add_and_hash(repo, "agents/auditor.md")
        check("doc-builtin-covers-agents-too", h1 != h2,
              "an agents/*.md change left the fingerprint untouched")

    # (2) PAIRED NEGATIVE, and the one that decides the design: a dev-tracking doc must NOT
    # move it. /flow:ship Step 5 rewrites planPath in the same commit that carries the code, so
    # if plan/history/feedback docs entered the fingerprint the gate would report source-drift
    # on EVERY ship run -- a gate that always fires is one people learn to click past.
    with tempfile.TemporaryDirectory() as repo:
        h0 = seeded_repo(repo)
        h1 = add_and_hash(repo, "dev-docs/plan.md")
        check("dev-tracking-docs-do-NOT-move-the-fingerprint", h0 == h1,
              "a dev-docs/ edit moved the fingerprint; every ship run rewrites the plan doc, so "
              "the rigor gate would report source-drift on all of them")
        h2 = add_and_hash(repo, "notes/scratch.md")
        check("...nor does an arbitrary non-surface .md", h0 == h2,
              "an unrelated .md moved the fingerprint: the union is matching every doc, not "
              "declared surface")

    # (3) The configurable slot, both directions, one repo per slot state.
    with tempfile.TemporaryDirectory() as repo:
        h0 = seeded_repo(repo, config='{"behaviorBearingDocPatterns": "(^|/)prompts/.*[.]md$"}\n')
        h1 = add_and_hash(repo, "prompts/system.md")
        check("doc-slot-set-brings-a-consumer-surface-in", h0 != h1,
              "behaviorBearingDocPatterns was set and a matching prose file still did not reach "
              "the fingerprint -- the slot is declared for coverage but ignored for rigor")
    with tempfile.TemporaryDirectory() as repo:
        h0 = seeded_repo(repo, config='{}\n')
        h1 = add_and_hash(repo, "prompts/system.md")
        check("doc-slot-UNSET-leaves-it-out (paired)", h0 == h1,
              "with the slot unset a prompts/ file entered the fingerprint anyway, so the slot "
              "is not what is doing the work and the measurement above proves nothing")

    # (4) An invalid slot must WARN, not silently narrow (general.md item 1). The builtin half
    # must survive it: a config typo cannot be allowed to quietly restore the doc-blind gate.
    with tempfile.TemporaryDirectory() as repo:
        h0 = seeded_repo(repo, config='{"behaviorBearingDocPatterns": "(^|/)[prompts/"}\n')
        rc, out = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("invalid-doc-slot-still-exits-0", rc == 0, f"rc={rc} out={out!r}")
        check("invalid-doc-slot-is-announced", "doc" in out.lower() and
              ("warn" in out.lower() or "invalid" in out.lower()),
              f"an unusable behaviorBearingDocPatterns was swallowed; the operator cannot tell "
              f"a narrowed fingerprint from a working one: {out!r}")
        h1 = add_and_hash(repo, "skills/x/SKILL.md")
        check("invalid-doc-slot-keeps-the-builtin-half", h0 != h1,
              "a bad config value took the shipped builtin down with it, silently restoring the "
              "doc-blind fingerprint this fix exists to close")

    # (4b) FILE CLASS in the digest. The loop now covers `.md` paths, and `read_bytes()` on a
    # symlink to /dev/zero raises MemoryError -- not an OSError, so it escaped the handler,
    # crashed the process, and left an EMPTY fingerprint that compares equal to the other
    # side's empty fingerprint. Symlinks and non-regular files feed a sentinel instead. Flagged
    # as undeclared by /flow:audit-coverage at this PR's own merge gate.
    with tempfile.TemporaryDirectory() as repo:
        h0 = seeded_repo(repo)
        body = "deployed prose\n"
        (Path(repo) / "skills").mkdir(parents=True, exist_ok=True)
        (Path(repo) / "skills" / "real.md").write_text(body)
        rc, h_regular = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("file-class: a matched regular file is in the fingerprint",
              h_regular.strip() != h0, "adding skills/real.md did not move the digest")
        # Same CONTENT, reached through a symlink: the digest must still move, because the
        # bytes are deliberately not followed.
        (Path(repo) / "skills" / "real.md").unlink()
        (Path(repo) / "target.txt").write_text(body)
        (Path(repo) / "skills" / "real.md").symlink_to(Path(repo) / "target.txt")
        rc, h_link = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("file-class: a symlink to identical content is NOT followed",
              h_link.strip() != h_regular.strip(),
              "the digest is unchanged, so the symlink's target was read — which is the path "
              "that could crash on a device file and empty the fingerprint")
        check("file-class: and it still exits 0 with a real digest, never empty",
              rc == 0 and len(h_link.strip()) == 64,
              f"rc={rc} digest={h_link.strip()!r}")

    # (4c) An invalid `sourceFilePatterns` used to raise out of a function contracted to
    # always exit 0, leaving an empty fingerprint. It must degrade to the documented default,
    # loudly. Also flagged as undeclared by the merge-gate coverage audit.
    with tempfile.TemporaryDirectory() as repo:
        seeded_repo(repo)
        (Path(repo) / "b.py").write_text("y = 2\n")
        rc_bad, out_bad = run(["source-sha", "--default-branch", "main",
                               "--source-pattern", "(["], cwd=repo)
        rc_def, out_def = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("invalid sourceFilePatterns still exits 0", rc_bad == 0, f"rc={rc_bad}")
        check("...and is ANNOUNCED, not swallowed",
              "sourceFilePatterns" in out_bad and "WARN" in out_bad,
              f"a malformed slot degraded silently: {out_bad[:200]!r}")
        bad_digest = [l for l in out_bad.splitlines() if len(l.strip()) == 64]
        check("...and yields the DEFAULT-pattern digest, never an empty one",
              bool(bad_digest) and bad_digest[-1].strip() == out_def.strip(),
              f"expected the default-pattern digest {out_def.strip()[:16]}, got "
              f"{(bad_digest[-1].strip()[:16] if bad_digest else None)} — an empty or divergent "
              f"fingerprint is the fail-open this guard exists to close")

    # (4d) The slot-refusal ladder. Each refusal must return the builtin set ALONE plus exactly
    # one warning — never a silently narrowed pattern list and never a crash.
    sys.path.insert(0, str(HERE.parent / "lib"))
    import doc_patterns as dp  # noqa: E402
    for label, slot in (("non-string", 12345),
                        ("over the length cap", "x" * (dp.MAX_SLOT_LEN + 1)),
                        ("invalid regex", "(^|/)[oops"),
                        ("nested quantifier", "(a+)+$")):
        if isinstance(slot, str):
            pats, warns = dp.doc_patterns_list(slot=slot)
        else:
            continue  # a non-string can only arrive via the config file; covered below
        check(f"slot refusal ({label}): builtin set only",
              len(pats) == 1 and pats[0].pattern == dp.DOC_BUILTIN,
              f"got {[x.pattern for x in pats]}")
        check(f"slot refusal ({label}): exactly one warning, naming the slot",
              len(warns) == 1 and dp.SLOT in warns[0] and "NOT applied" in warns[0],
              f"got {warns}")
    # PAIRED POSITIVE: a valid slot is APPLIED, and an inline flag now scopes to itself
    # instead of being refused (the altitude fix).
    pats_ok, warns_ok = dp.doc_patterns_list(slot=r"(?i)(^|/)prompts/.*[.]md$")
    m = lambda path: any(x.search(path) for x in pats_ok)
    check("a valid slot (even with an inline flag) IS applied",
          len(pats_ok) == 2 and not warns_ok and m("PROMPTS/SYS.MD"),
          f"pats={len(pats_ok)} warns={warns_ok}")
    check("...and the flag does NOT leak to the builtin clause",
          not m("SKILLS/X/SKILL.MD") and m("skills/x/SKILL.md"),
          "the inline flag escaped its own pattern — the leak the union shape caused")
    # And the refusal ladder's config-file paths (unparseable / non-object / non-string).
    for label, raw in (("unparseable JSON", "{not json"),
                       ("not an object", "[1,2,3]"),
                       ("non-string slot", '{"behaviorBearingDocPatterns": 12345}')):
        with tempfile.TemporaryDirectory() as cfgdir:
            (Path(cfgdir) / "flow.config.json").write_text(raw)
            pats, warns = dp.doc_patterns_list(root=cfgdir)
            check(f"config refusal ({label}): builtin only + one warning",
                  len(pats) == 1 and len(warns) == 1 and "NOT applied" in warns[0],
                  f"pats={len(pats)} warns={warns}")

    # (4e) THE IMPORT-GUARD DEGRADE — the one state in which the doc-blind gate this whole
    # change exists to close silently returns. A partial install, a truncated file, or a
    # SyntaxError in `lib/doc_patterns.py` used to traceback out of a function contracted to
    # always exit 0, leaving SRC_SHA="" in the caller's $( ) on BOTH sides, where the two empty
    # fingerprints compare equal and the gate prints `ok`. Flagged as undeclared by
    # /flow:audit-coverage at this PR's merge gate (round four).
    #
    # The real module is never touched: rigor-marker resolves its import as
    # `parents[3]/"lib"`, so a copy at <tmp>/skills/ship/lib/ imports from <tmp>/lib/.
    import shutil
    with tempfile.TemporaryDirectory() as fake, tempfile.TemporaryDirectory() as repo:
        fake_lib = Path(fake) / "skills" / "ship" / "lib"
        fake_lib.mkdir(parents=True)
        shutil.copy(SCRIPT, fake_lib / "rigor-marker.py")
        (Path(fake) / "lib").mkdir()
        # A SyntaxError, not a missing file: the case the broadened `except Exception` exists
        # for, and the one an ImportError-only guard let escape.
        (Path(fake) / "lib" / "doc_patterns.py").write_text("def (this is not python\n")
        broken = str(fake_lib / "rigor-marker.py")

        def run_broken(argv, cwd):
            pr = subprocess.run([sys.executable, broken, *argv], capture_output=True,
                                text=True, check=False, cwd=cwd)
            return pr.returncode, (pr.stdout + pr.stderr)

        h_base = seeded_repo(repo)
        (Path(repo) / "b.py").write_text("y = 2\n")          # source-only change
        rc_src, out_src = run_broken(["source-sha", "--default-branch", "main"], repo)
        _, healthy_src = run(["source-sha", "--default-branch", "main"], cwd=repo)
        d_src = [l.strip() for l in out_src.splitlines() if len(l.strip()) == 64]
        check("broken doc_patterns: still exits 0", rc_src == 0, f"rc={rc_src}")
        check("broken doc_patterns: ANNOUNCES the degrade, naming the module",
              "doc_patterns" in out_src and "WARN" in out_src,
              f"a partial install degraded silently: {out_src[:220]!r}")
        check("broken doc_patterns: produces a real digest, NOT the empty-input hash",
              bool(d_src) and d_src[-1] != EMPTY_SHA, f"got {d_src[-1:]!r}")
        check("broken doc_patterns: a source-only tree digests IDENTICALLY to a healthy run",
              bool(d_src) and d_src[-1] == healthy_src.strip(),
              f"the degrade changed more than the doc half: {d_src[-1:]!r} vs "
              f"{healthy_src.strip()!r}")
        # ...and with a doc-shaped file present, the degraded digest MUST differ — that is the
        # whole consequence the warning claims, asserted rather than trusted.
        (Path(repo) / "skills").mkdir(parents=True, exist_ok=True)
        (Path(repo) / "skills" / "x.md").write_text("deployed prose\n")
        rc_doc, out_doc = run_broken(["source-sha", "--default-branch", "main"], repo)
        _, healthy_doc = run(["source-sha", "--default-branch", "main"], cwd=repo)
        d_doc = [l.strip() for l in out_doc.splitlines() if len(l.strip()) == 64]
        check("broken doc_patterns: prose is DROPPED from the fingerprint (the stated cost)",
              bool(d_doc) and d_doc[-1] != healthy_doc.strip(),
              "the degraded and healthy digests match over a changed .md, so either the warning "
              "overstates the cost or the healthy path never included prose")
        check("...and the PAIRED positive: the healthy run DID widen for that .md",
              healthy_doc.strip() != healthy_src.strip(),
              "the healthy digest did not move when a doc-shaped file changed, so this arm "
              "proves nothing about the degrade")

    # (5) ONE definition of the builtin. The shell literal in audit-coverage/SKILL.md and the
    # Python constant are two readers of one contract (general.md item 2); assert byte-equality
    # rather than trusting they were copied correctly.
    sys.path.insert(0, str(HERE.parent / "lib"))
    import doc_patterns  # noqa: E402
    skill = (HERE.parent / "skills" / "audit-coverage" / "SKILL.md").read_text(encoding="utf-8")
    shell_literals = re.findall(r"DOC_BUILTIN='([^']*)'", "\n".join(bang_blocks(skill)))
    check("the shell declares the builtin exactly once", len(shell_literals) == 1,
          f"found {len(shell_literals)} DOC_BUILTIN literals in audit-coverage's bang blocks: "
          f"{shell_literals} — two copies is the fan-out this check exists to prevent")
    check("doc-builtin-is-byte-identical-in-shell-and-python",
          bool(shell_literals) and shell_literals[0] == doc_patterns.DOC_BUILTIN,
          f"shell={shell_literals[:1]!r} python={doc_patterns.DOC_BUILTIN!r} — the coverage gate "
          f"and the rigor gate would disagree about what counts as deployed prose")

    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
