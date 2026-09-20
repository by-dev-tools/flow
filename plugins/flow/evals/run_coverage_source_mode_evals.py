#!/usr/bin/env python3
"""Eval harness for /flow:audit-coverage's SOURCE-TREE input mode.

Why this mode exists (measured, n=1): `dev-docs/research/2026-09-16-d1-auto-plan-quality-spike.md`.
An auto-written Spec-walk plan scored 0/13 vacuous while under-declaring 10 real behaviors,
because the pre-execution reviewers read the PLAN and the BRIEF and *nothing read the approved
prototype's code*. audit-coverage's judgment is not diff-specific ("for each user-perceptible
behavior change, check whether any declared criterion would cause someone to test it",
SKILL.md:129-130, scoped to declared-vs-built completeness only) — only its INPUT is. So the
fix is a second input path, not a fourth reviewer.

The bug class this harness pins is the one the feature is about, turned inward:

  **a coverage gate that reports "clean" over source it never read.**

That is not hypothetical here. While planning this change we measured that the shared
`sourceFilePatterns` default (the diff block's filter) matches ts/js/py/go/... and contains
NO html — so naively reusing it on the reference prototype (`annotation-layer.html`) filters
the file list to empty and renders a clean `[audit-coverage] SKIPPED`. The feature would have
reported "no undeclared changes" over a prototype it never opened. `.claude/rules/general.md`
§ Consistency item 4: a measurement that can only return "clean" is not a measurement — so
§5 below runs the real block against the REAL prototype and asserts all ten spike-documented
behavior anchors survive assembly, and then validates that probe against a truncated context
it must FAIL on. A probe that cannot return not-clean is not a probe either.

Sections:
  §1  diff mode is unchanged — the mode gate is a provable NO-OP with no argument, asserted
      by running the block against a gate-stripped copy of itself (needs no git ref, so it
      keeps working after this merges — see the note at the section)
  §2  a single named file is read VERBATIM, never pattern-filtered (the .html hole), paired
      with a zero-byte file that must NOT come back clean
  §3  a directory is walked with the prototype pattern set, and the walk really filters
  §4  SOURCE-UNRESOLVED is its own outcome — never SKIPPED, never silence (FB-0074 shape),
      plus §4b's paired positive: the real SKIPPED path still works
  §5  THE INSTRUMENT TEST — the known-positive case, plus the probe's own negative control
  §6  the cap is DERIVED (2x the diff cap), cross-checked against the diff block's literal,
      and paired with a loud SOURCE-TRUNCATED warning that does not always fire
  §7  path safety: containment + newline refusal, paired with a legitimate path that is ACCEPTED
  §8  registration self-guards (skill prose, CI wiring)

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_coverage_source_mode_evals.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PLUGIN = HERE.parent
REPO = PLUGIN.parent.parent
SKILL = PLUGIN / "skills" / "audit-coverage" / "SKILL.md"
PROTOTYPE = PLUGIN / "skills" / "verify-build" / "lib" / "annotation-layer.html"

_failures: list[str] = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


# ---------------------------------------------------------------------------
# Block extraction — read the SHIPPED shell, never a restatement of it. A fixture
# that restates the guard lets the eval pass while the artifact drifts (the lesson
# run_root_anchor_evals.py records in its own docstring).
# ---------------------------------------------------------------------------
_BLOCK_RE = re.compile(r"^!`\n(.*?)^`$", re.MULTILINE | re.DOTALL)


def blocks() -> list[str]:
    return _BLOCK_RE.findall(SKILL.read_text(encoding="utf-8"))


ALL = blocks()
# criteria, diff, source — in document order.
check("SKILL.md carries exactly three dynamic blocks (criteria, diff, source)",
      len(ALL) == 3, f"found {len(ALL)}")
if len(ALL) != 3:
    print("\ncannot continue without the three blocks."); sys.exit(1)
CRITERIA_BLOCK, DIFF_BLOCK, SOURCE_BLOCK = ALL

check("the third block is the source block (names SOURCE-UNRESOLVED)",
      "SOURCE-UNRESOLVED" in SOURCE_BLOCK and "ARGUMENTS" in SOURCE_BLOCK)
check("the second block is the diff block (names the diff skip line)",
      "SKIPPED — no behavior-bearing source files" in DIFF_BLOCK)


def run(block: str, cwd: Path, arguments=None, project_dir=None) -> str:
    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("ARGUMENTS", None)
    if arguments is not None:
        env["ARGUMENTS"] = arguments
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    proc = subprocess.run(["sh", "-c", block], cwd=str(cwd), env=env,
                          capture_output=True, text=True, timeout=60)
    return proc.stdout + proc.stderr


def git_repo(path: Path, files: dict) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, capture_output=True)
    for rel, body in files.items():
        f = path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], cwd=path, capture_output=True)
    return path


# ===========================================================================
print("\n§1 — diff mode is unchanged (the mode gate is a no-op with no argument)")
# The durable form of "byte-identical". Comparing against `git show origin/main:...`
# is a real check only while this PR is open — once it merges, main IS this file and
# the comparison compares a file to itself. So the CI-durable assertion is the one
# that needs no ref: strip the added mode-gate lines back out of the shipped block,
# run BOTH in the same repo with no argument, and require byte-identical stdout. The
# stripped copy literally IS the pre-change code path. (The one-time origin/main
# byte comparison was run by hand for this PR and is recorded in the history entry.)
GATE_LINE = '[ -n "${ARGUMENTS:-}" ] && exit 0'
check("the diff block's mode gate is exactly one executable line",
      DIFF_BLOCK.count(GATE_LINE) == 1, "gate line missing or duplicated")

PRE_GATE = "\n".join(
    ln for ln in DIFF_BLOCK.split("\n")
    if ln.strip() != GATE_LINE and not ln.startswith("# MODE GATE")
    and not ln.startswith("# selects the source block") and not ln.startswith("# This sits AFTER")
    and not ln.startswith("# extracted guard") and not ln.startswith("# unresolved signal")
    and not ln.startswith("# fail it") and not ln.startswith("# diff-mode run.")
)

with tempfile.TemporaryDirectory() as td:
    r = git_repo(Path(td) / "repo", {
        "flow.config.json": '{"defaultBranch": "main", "planPath": "plan.md"}',
        "app.js": "export function a(){ return 1 }\n",
        "plan.md": "**Spec-walk:**\n- [x] a returns 1 → verify: unit\n",
    })
    (r / "app.js").write_text("export function a(){ return 2 }\n", encoding="utf-8")

    now = run(DIFF_BLOCK, r)
    before = run(PRE_GATE, r)
    check("diff-mode output is byte-identical to the pre-gate code path",
          now == before, f"diverged:\n--now--\n{now[:400]}\n--before--\n{before[:400]}")
    check("diff mode still renders the diff (positive — not merely 'unchanged and empty')",
          "----- diff -----" in now and "Behavior-bearing files changed:" in now,
          f"got: {now[:300]!r}")
    src_quiet = run(SOURCE_BLOCK, r)
    check("with no argument the source block emits ZERO bytes",
          src_quiet == "", f"expected silence, got: {src_quiet[:300]!r}")
    # ...and the converse: in source mode the diff block is the silent one.
    (r / "proto.html").write_text("<button id='x'>go</button>\n", encoding="utf-8")
    diff_quiet = run(DIFF_BLOCK, r, arguments=str(r / "proto.html"))
    check("with an argument the diff block emits ZERO bytes (exactly one block speaks)",
          diff_quiet == "", f"expected silence, got: {diff_quiet[:300]!r}")


# ===========================================================================
print("\n§2 — a single named file is read VERBATIM, never pattern-filtered")
with tempfile.TemporaryDirectory() as td:
    r = git_repo(Path(td) / "repo", {
        "flow.config.json": '{"defaultBranch": "main"}',
        "proto.html": "<button id='pin'>pin</button>\n<script>function pinAt(){}</script>\n",
        "empty.html": "",
    })
    out = run(SOURCE_BLOCK, r, arguments="proto.html")
    # THE HOLE THIS CLOSES: the shared sourceFilePatterns default has no html, so a
    # filtered read of this file would be empty and would render as a clean SKIPPED.
    check("a named .html prototype is read (the sourceFilePatterns-has-no-html hole)",
          "pinAt" in out and "----- source -----" in out, f"got: {out[:400]!r}")
    check("...and it is NOT reported as a skip",
          "SKIPPED" not in out and "SOURCE-UNRESOLVED" not in out, f"got: {out[:300]!r}")
    check("the block names the file it actually read",
          "proto.html" in out, f"got: {out[:300]!r}")
    # PAIRED NEGATIVE: acceptance is not unconditional — a zero-byte named file has no
    # behavior to audit and must not come back clean (the doc-slot 'EMPTY is LOUD' rule).
    out = run(SOURCE_BLOCK, r, arguments="empty.html")
    check("a zero-byte named file is SOURCE-UNRESOLVED, not a clean pass",
          "SOURCE-UNRESOLVED" in out, f"got: {out[:300]!r}")

# ===========================================================================
print("\n§3 — a directory is walked with the prototype pattern set, and really filters")
with tempfile.TemporaryDirectory() as td:
    r = git_repo(Path(td) / "repo", {
        "flow.config.json": '{"defaultBranch": "main"}',
        "proto/index.html": "<main id='root'>hi</main>\n",
        "proto/app.js": "function toggleMode(){}\n",
        "proto/notes.md": "# design notes, not behavior\n",
        "proto/node_modules/dep/index.js": "module.exports=1\n",
    })
    out = run(SOURCE_BLOCK, r, arguments="proto")
    check("directory walk reads index.html", "id='root'" in out, f"got: {out[:400]!r}")
    check("directory walk reads app.js", "toggleMode" in out, f"got: {out[:400]!r}")
    check("directory walk OMITS notes.md (the walk genuinely filters)",
          "design notes, not behavior" not in out, f"got: {out[:400]!r}")
    check("directory walk OMITS node_modules", "module.exports=1" not in out)
    check("the files-read header names every file it read",
          "index.html" in out and "app.js" in out, f"got: {out[:300]!r}")

# ===========================================================================
print("\n§4 — SOURCE-UNRESOLVED is its own outcome, never SKIPPED, never silence")
SKIP_LINE = "[audit-coverage] SKIPPED"
with tempfile.TemporaryDirectory() as td:
    r = git_repo(Path(td) / "repo", {"flow.config.json": '{"defaultBranch": "main"}',
                                     "app.js": "x\n"})
    (r / "emptydir").mkdir()
    outside = Path(td) / "outside"; outside.mkdir()
    (outside / "secret.js").write_text("TOP_SECRET\n", encoding="utf-8")

    cases = {
        "missing path": "no/such/prototype.html",
        "empty directory": "emptydir",
        "path outside the repo (relative ..)": "../outside",
        "path outside the repo (absolute)": str(outside / "secret.js"),
    }
    for label, arg in cases.items():
        out = run(SOURCE_BLOCK, r, arguments=arg)
        check(f"{label} ⇒ SOURCE-UNRESOLVED", "SOURCE-UNRESOLVED" in out, f"got: {out[:300]!r}")
        check(f"{label} ⇒ is NOT the skip line", SKIP_LINE not in out, f"got: {out[:300]!r}")
        check(f"{label} ⇒ is NOT silence", out.strip() != "", "emitted nothing at all")
    out = run(SOURCE_BLOCK, r, arguments=str(outside / "secret.js"))
    check("a refused outside-path leaks NO file content into prompt context",
          "TOP_SECRET" not in out, f"leaked: {out[:300]!r}")

    # Distinctness, asserted directly rather than implied — the invariant
    # run_root_anchor_evals.py pins for ROOT-UNRESOLVED, applied to this sibling.
    unres = "[audit-coverage] SOURCE-UNRESOLVED"
    check("the unresolved line is not confusable with the skip line",
          SKIP_LINE not in unres and unres not in SKIP_LINE
          and "SKIPPED" not in unres)

    print("\n§4b — paired positive: the real SKIPPED path still works")
    # Without this, deleting the skip branch outright would satisfy every §4 assertion.
    doc = git_repo(Path(td) / "docsonly", {
        "flow.config.json": '{"defaultBranch": "main"}', "README.md": "hi\n"})
    (doc / "README.md").write_text("hi there\n", encoding="utf-8")
    out = run(DIFF_BLOCK, doc)
    check("a doc-only diff in diff mode still renders SKIPPED",
          SKIP_LINE in out, f"got: {out[:300]!r}")

# ===========================================================================
print("\n§5 — THE INSTRUMENT TEST: the known-positive case (D1 spike, n=1)")
# The ten behaviors the spike's audit-coverage-framed pass found UNDECLARED in the
# auto-plan, with a stable anchor for each. The claim under test here is the INPUT
# mode's: does the assembled context still contain the evidence a reader needs? The
# judgment half was established by the spike (10/10 by hand) and re-confirmed live
# once for this PR — see the history entry. n=1 in both halves; said plainly.
SPIKE_ANCHORS = [
    ("1  keyboard-only interaction path (WCAG 2.1.1)", "focusWalkTarget"),
    ("2  bulk delete-all, two-step arm/disarm", "an-wipe"),
    ("3  single-comment delete", "an-del"),
    ("4  snapPreview hover-outline preference", "snapPreview"),
    ("5  show/hide-all-pins toggle", "an-eye"),
    ("6  comment-list panel open/close", "an-close"),
    ("7  per-row copy (single-note format)", "oneNoteBlock"),
    ("8  storage-quota-exceeded warning path", "quota"),
    ("9  Escape four-branch priority state machine", "Escape"),
    ("10 discard-on-empty-close", "dropEmpty"),
]


def probe(context: str) -> list:
    """Which spike anchors are MISSING from an assembled context."""
    return [label for label, tok in SPIKE_ANCHORS if tok not in context]


check("the reference prototype is still on disk at the path the spike names",
      PROTOTYPE.is_file(), f"missing {PROTOTYPE}")
if PROTOTYPE.is_file():
    real = run(SOURCE_BLOCK, REPO, arguments=str(PROTOTYPE))
    missing = probe(real)
    check("all ten spike-documented behavior anchors survive assembly",
          not missing, "assembled context lost: " + "; ".join(missing))
    check("...and the run was not quietly an unresolved/skip result",
          "SOURCE-UNRESOLVED" not in real and SKIP_LINE not in real,
          f"got: {real[:300]!r}")
    check("...and it was not truncated at the shipped cap",
          "SOURCE-TRUNCATED" not in real,
          "the reference prototype truncated — the cap no longer clears the known case")

    # THE PROBE'S OWN NEGATIVE CONTROL (general.md § Consistency item 4). A probe that
    # cannot return not-clean is not a probe. The 60000-byte diff cap is the exact value
    # that WOULD have clipped this file (60805 bytes), so this doubles as the measurement
    # behind the derived 2x cap in §6.
    # Measured, not guessed: the Escape state machine (finding 9) first appears at file
    # byte 57163, so a 57000-byte clip provably drops it. If the probe still says clean
    # there, the probe is decorative.
    check("the probe FAILS on a 57000-byte-clipped context (it can return not-clean)",
          probe(real[:57000]),
          "probe reported clean on a context known to be missing behavior")

    # And the separate, sharper claim behind the 2x cap: the DIFF-mode cap really does
    # clip real evidence off this file, even though the coarse token probe above survives
    # it. The prototype is 60805 bytes; its THIRD focusin registration — the focus
    # restoration half of the WCAG 2.1.1 keyboard path the spike cites at lines ~1146-1154,
    # i.e. finding 1's second citation — sits at file byte 59915 and its body runs past
    # 60000. Stated at this precision because "the cap would have truncated it" is exactly
    # the kind of claim that decays into folklore if nobody writes down what it clipped.
    # BYTES, not characters: the shipped cap is `head -c`, and this file carries
    # non-ASCII punctuation, so a character-index clip lands in a different place than
    # the shell's. (The first version of this check compared str slices and passed the
    # "cap clips nothing" reading by accident — the unit, not the claim, was wrong.)
    real_b = real.encode("utf-8")
    check("the reference prototype exceeds the diff-mode cap",
          len(real_b) > 60000, f"assembled context is only {len(real_b)} bytes")
    check("the diff-mode cap would have clipped the focusin handler (finding 1's evidence)",
          real_b.count(b"focusin") == 3 and real_b[:60000].count(b"focusin") < 3,
          f"full={real_b.count(b'focusin')} clipped={real_b[:60000].count(b'focusin')}")

# ===========================================================================
print("\n§6 — the cap is DERIVED, cross-checked, and its warning does not always fire")
m_diff = re.search(r"^\s*CAP=(\d+)$", DIFF_BLOCK, re.MULTILINE)
m_base = re.search(r"^DIFF_CAP=(\d+)$", SOURCE_BLOCK, re.MULTILINE)
check("the diff block still declares its cap as a literal", bool(m_diff))
check("the source block declares DIFF_CAP, not a bare 120000", bool(m_base))
check("the source cap is DERIVED (2x) rather than hardcoded",
      "SOURCE_CAP=$(( DIFF_CAP * 2 ))" in SOURCE_BLOCK,
      "a bare literal is the FB-0010 fan-out shape: it stops tracking the diff cap silently")
if m_diff and m_base:
    # The one thing a comment cannot hold together across two shells.
    check("DIFF_CAP mirrors the diff block's own CAP",
          m_diff.group(1) == m_base.group(1),
          f"diff block CAP={m_diff.group(1)} but source block DIFF_CAP={m_base.group(1)}")

with tempfile.TemporaryDirectory() as td:
    r = git_repo(Path(td) / "repo", {"flow.config.json": '{"defaultBranch": "main"}'})
    big = r / "big"; big.mkdir()
    (big / "huge.js").write_text("// behavior\n" * 12000, encoding="utf-8")   # ~132KB
    out = run(SOURCE_BLOCK, r, arguments="big")
    check("an over-cap tree emits SOURCE-TRUNCATED naming the cap",
          "SOURCE-TRUNCATED" in out and "120000" in out, f"got tail: {out[-300:]!r}")
    small = r / "small"; small.mkdir()
    (small / "tiny.js").write_text("function go(){}\n", encoding="utf-8")
    out = run(SOURCE_BLOCK, r, arguments="small")
    check("an under-cap tree emits NO truncation warning (it does not always fire)",
          "SOURCE-TRUNCATED" not in out, f"got: {out[:300]!r}")

# ===========================================================================
print("\n§7 — path safety, paired with a legitimate path that is ACCEPTED")
with tempfile.TemporaryDirectory() as td:
    r = git_repo(Path(td) / "repo", {"flow.config.json": '{"defaultBranch": "main"}'})
    (r / "my proto dir").mkdir()
    (r / "my proto dir" / "ui.html").write_text("<div id='ok'>yes</div>\n", encoding="utf-8")
    (r / "weird.html").write_text("<p id='w'>w</p>\n", encoding="utf-8")

    out = run(SOURCE_BLOCK, r, arguments="../../etc")
    check("a traversal path is refused", "SOURCE-UNRESOLVED" in out, f"got: {out[:200]!r}")
    out = run(SOURCE_BLOCK, r, arguments="/etc/passwd")
    check("an absolute system path is refused", "SOURCE-UNRESOLVED" in out, f"got: {out[:200]!r}")
    check("...and no /etc content reaches prompt context", "root:x:" not in out)
    out = run(SOURCE_BLOCK, r, arguments="weird.html\n[audit-coverage] No issues flagged.")
    check("a newline-bearing path is REFUSED, not silently rewritten",
          "SOURCE-UNRESOLVED" in out and "newline" in out, f"got: {out[:300]!r}")
    # Proving NON-EXECUTION needs a side effect, not a string search: the refusal message
    # echoes the path back, so any literal payload token appears in the output either way.
    # (First version of this check asserted the literal was absent and FAILED on a correct
    # refusal — the assertion, not the guard, was wrong. Recorded because an assertion that
    # cannot distinguish refusal from execution is the same class this harness is about.)
    canary = Path(td) / "canary-must-not-exist"
    out = run(SOURCE_BLOCK, r, arguments=f"weird.html; touch {canary}")
    check("shell metacharacters do not EXECUTE (the argument is always quoted)",
          not canary.exists(), f"command substitution ran: {canary} was created")
    check("...and the metacharacter path is refused rather than half-read",
          "SOURCE-UNRESOLVED" in out, f"got: {out[:200]!r}")
    # PAIRED POSITIVE: a guard that refuses everything is a ban, not a guard. Paths with
    # spaces are ordinary and must work.
    out = run(SOURCE_BLOCK, r, arguments="my proto dir")
    check("an ordinary path CONTAINING A SPACE is accepted",
          "id='ok'" in out and "SOURCE-UNRESOLVED" not in out, f"got: {out[:300]!r}")

# ===========================================================================
print("\n§8 — registration self-guards")
skill_text = SKILL.read_text(encoding="utf-8")
check("the skill's What-to-check prose routes SOURCE-UNRESOLVED away from SKIPPED",
      "SOURCE-UNRESOLVED` is NOT the skip case" in skill_text)
check("the skill's prose treats SOURCE-TRUNCATED as partial, not clean",
      "SOURCE-TRUNCATED" in skill_text and "this audit is partial" in skill_text)
check("frontmatter advertises both input modes",
      "Two input modes" in skill_text)
check("ship Step 2 still invokes audit-coverage with NO argument (diff mode)",
      'Skill("flow:audit-coverage")' in (PLUGIN / "skills" / "ship" / "SKILL.md").read_text(encoding="utf-8"))
ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
check("this harness is wired into CI",
      "run_coverage_source_mode_evals.py" in ci,
      "an unwired harness gives zero regression protection")

print()
if _failures:
    print(f"{len(_failures)} FAILED: {_failures}")
    sys.exit(1)
print("All audit-coverage source-mode evals passed.")
