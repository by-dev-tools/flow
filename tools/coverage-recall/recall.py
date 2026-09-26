#!/usr/bin/env python3
"""Measure /flow:audit-coverage's RECALL against cases with known ground truth (FB-0115).

DEV TOOLING, NOT SHIPPED (CLAUDE.md § 3). No /flow:* skill invokes this. It cannot run in
CI -- scoring needs a real reviewer output, and producing one needs a model call -- which is
exactly why it lives here and not in `plugins/flow/evals/`.

  render <case> [--before]   assemble the EXACT prompt a forked `flow:auditor` receives:
                             the SKILL.md body with every !` span executed against the
                             case's worktree and substituted. `--before` renders from
                             origin/main's SKILL.md instead of the working tree, so the
                             two conditions differ only in the artifact under test.
  score <case> <output>      deterministic recall/precision against the keyed ground truth.
  selftest                   prove the scorer CAN FAIL before any number is believed.
  report <dir>               aggregate every <case>.<cond>.<run>.txt in a directory.

WHY `selftest` GATES EVERYTHING (`.claude/rules/general.md` Consistency item 4). Four
instruments in the last two PRs reported green while broken. A recall scorer is trivially
gameable in one specific way that matters here: the change under test ADDS a `BEHAVIOR
INVENTORY` section that NAMES behaviors without flagging them. A scorer that greps the whole
output would score the after-condition near-perfect for merely enumerating, which is the one
result that must not be obtainable for free. So `score` reads **only the flagged region** --
from the first `ISSUE`/`AUDIT SUMMARY` onward -- and `selftest` asserts exactly that with a
rich inventory sitting above a `No issues flagged.`

Stdlib only.
"""

from __future__ import annotations

import argparse
import os
import re
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
from cases import CASES                       # noqa: E402

SKILL_REL = "plugins/flow/skills/audit-coverage/SKILL.md"
ARG_TOKEN = "$" + "ARGUMENTS"
BLOCK_RE = re.compile(r"^!`\n(.*?)^`$", re.MULTILINE | re.DOTALL)
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# The flagged region starts at the first of these. Everything above it -- including the new
# BEHAVIOR INVENTORY and COVERAGE MAP -- is enumeration, not a finding, and must not score.
# One fragment, composed twice — the two regexes must agree about what an ISSUE header looks
# like, or `score` finds findings it cannot split.
_ISSUE_HEAD = r"ISSUE(?:\s+\d+)?\s+·"
FLAG_START_RE = re.compile(r"^(%s|AUDIT SUMMARY)" % _ISSUE_HEAD, re.MULTILINE)
CLEAN_RE = re.compile(r"^No issues flagged\.", re.MULTILINE)
# A control line means the reviewer deliberately refused to audit (skip / unresolved), which is
# a real outcome. Its ABSENCE, together with no findings and no clean verdict, means the run
# produced nothing at all — and that must not be averaged in as 0/N. See NO-VERDICT below.
CONTROL_RE = re.compile(r"^\[audit-coverage\] (SKIPPED|[A-Z-]*UNRESOLVED|JQ-MISSING)",
                        re.MULTILINE)
ISSUE_SPLIT_RE = re.compile(r"^%s" % _ISSUE_HEAD, re.MULTILINE)


# --------------------------------------------------------------------- rendering

def skill_text(before: bool) -> str:
    if not before:
        return (REPO / SKILL_REL).read_text(encoding="utf-8")
    out = subprocess.run(["git", "show", f"origin/main:{SKILL_REL}"], cwd=REPO,
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("cannot read origin/main's SKILL.md: " + out.stderr.strip())
    return out.stdout


def render(case_name: str, before: bool, workdir: Path) -> str:
    case = CASES[case_name]
    text = skill_text(before)
    body = FRONTMATTER_RE.sub("", text)
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO / "plugins" / "flow")
    env.pop("CLAUDE_PROJECT_DIR", None)

    def run_block(m):
        block = m.group(1)
        rendered = block.replace(ARG_TOKEN, case["argument"] or "")
        p = subprocess.run(["sh", "-c", rendered], cwd=str(workdir), env=env,
                           capture_output=True, text=True, timeout=300)
        return p.stdout + p.stderr

    return BLOCK_RE.sub(run_block, body)


def prepare(case_name: str, td: Path):
    """Set up the directory the blocks run in. Returns (dir, cleanup-callable).

    A DIFF CASE GETS A CLONE WITH `origin/main` REWRITTEN TO THE CASE'S BASE, and that is
    not fussiness -- it is the difference between measuring the PR and measuring nothing.
    Two defects the first version had, both found by reading the render instead of trusting
    it (`general.md` item 4 applied to my own instrument):

      1. It pointed `defaultBranch` at the base by EDITING `flow.config.json` in the
         worktree. That edit is itself an uncommitted change to a `.json` file, which the
         evidence block's own filter MATCHES -- so the rendered inventory listed five hunks
         of `flow.config.json` and nothing else. The harness was auditing its own setup.
      2. The edit could not have worked anyway: the block resolves the base from
         `git symbolic-ref refs/remotes/origin/HEAD` FIRST and only falls back to the
         config, so in a worktree of this repo the base is always today's `origin/main` --
         which, for #159, already CONTAINS #159. The diff would have been near-empty and
         a clean result would have looked like a recall failure.

    A `--shared` clone costs almost nothing (no object copy) and lets `origin/main` be set
    to the real historical base, so the first tier of the block's own 3-tier resolution
    returns the right answer with no config edit at all.

    The SOURCE case is different and keeps its config edit: its evidence is a named source
    tree, the diff plays no part, and the criteria genuinely live in a non-default plan path
    (the spike's committed `auto-plan.md`). A dirty config cannot reach its evidence block.
    """
    case = CASES[case_name]
    ref, base = case["worktree_ref"], case["base"]

    if ref is None:
        # Source mode, in this checkout. Override planPath, restore it afterwards.
        cfg = REPO / "flow.config.json"
        # Refuse rather than overwrite a dirty tracked file. The `finally` in main() restores it
        # on exceptions and on SIGINT, but a SIGKILL -- or an editor holding unsaved edits --
        # loses whatever was there. A measurement tool has no business risking the config of the
        # repo it is measuring.
        # Read the EXIT CODE, not just stdout: a failed `git status` leaves stdout empty and
        # the old form then proceeded to overwrite the config. general.md item 4's corollary --
        # prefer the tool's own exit code over a read of its output -- in the dev tool that
        # cites item 4 elsewhere.
        _st = subprocess.run(["git", "status", "--porcelain", "--", "flow.config.json"],
                             cwd=REPO, capture_output=True, text=True)
        if _st.returncode != 0:
            raise SystemExit("could not determine whether flow.config.json is dirty (git status "
                             "exited %d: %s) — refusing to overwrite it blind."
                             % (_st.returncode, _st.stderr.strip()))
        dirty = _st.stdout.strip()
        if dirty:
            raise SystemExit("flow.config.json has uncommitted changes (%s) and this case needs "
                             "to override planPath in it. Commit or stash it first — refusing to "
                             "overwrite a dirty tracked file." % dirty)
        original = cfg.read_text(encoding="utf-8")
        data = json.loads(original)
        data["planPath"] = case["plan"]
        cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        def undo():
            cfg.write_text(original, encoding="utf-8")
        return REPO, undo

    clone = td / ("clone-" + case_name)
    def git(*a, cwd=clone):
        return subprocess.run(["git", *a], cwd=str(cwd), capture_output=True, text=True)

    r = subprocess.run(["git", "clone", "--shared", "--quiet", "--no-checkout",
                        str(REPO), str(clone)], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("clone failed: " + r.stderr.strip())
    # Rewrite the remote-tracking ref the block's FIRST resolution tier reads.
    git("update-ref", "refs/remotes/origin/main", base)
    git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    co = git("checkout", "--detach", ref)
    if co.returncode != 0:
        raise SystemExit(f"checkout {ref} failed: {co.stderr.strip()}")
    # Assert the setup took, rather than assuming it: a silently wrong base is the failure
    # this whole docstring is about, and it renders as a confident, empty-ish diff.
    got = git("rev-parse", "origin/main").stdout.strip()
    want = git("rev-parse", base).stdout.strip()
    if got != want or not got:
        raise SystemExit(f"origin/main rewrite did not take: {got!r} != {want!r}")
    section = case.get("plan_first_section")
    if section:
        # Keep only the case's own section of the plan doc, so the FIRST `**Spec-walk:**`
        # block -- the only one extract-criteria.py reads -- is the one that describes this
        # diff. Left UNCOMMITTED on purpose: `.md` is excluded from the behaviour diff, so a
        # dirty plan doc cannot enter the evidence, and committing it would instead make the
        # plan the newest commit and empty the POST-PLAN window -- destroying the one property
        # this case exists to measure.
        planp = clone / case["plan"]
        text = planp.read_text(encoding="utf-8")
        idx = text.index(section)
        nxt = text.find("\n## ", idx + len(section))
        planp.write_text(text[idx:nxt if nxt != -1 else len(text)], encoding="utf-8")

    # Assert the setup cannot enter the evidence. NOT "assert clean" -- a `.md` edit is
    # deliberate above and is provably invisible to the behaviour diff -- but every OTHER
    # dirty path is exactly the bug the first version of this harness shipped (it audited its
    # own flow.config.json edit and reported five hunks of the setup). So the check is scoped,
    # and it is a positive assertion about WHICH files may differ, not a blanket skip.
    dirty = [l[3:] for l in git("status", "--porcelain").stdout.splitlines() if l.strip()]
    stray = [f for f in dirty if not f.endswith(".md")]
    if stray:
        raise SystemExit("the prepared clone is dirty in a file the behaviour diff CAN see, "
                         "so the harness would audit its own setup: " + ", ".join(stray))
    return clone, (lambda: None)


# ----------------------------------------------------------------------- scoring

# THE ANCHOR ADMISSIBILITY RULE, and it exists because the first key violated it badly.
#
# `pr158b`'s original anchors included the bare words `present`, `contract` and `sha`. Those
# are ordinary English in a finding about ANY behaviour in that file, so a run that flagged
# two gaps scored 5/5 -- against a recorded 2-of-5 for the same input. The scorer was
# measuring vocabulary, not recall, and it reported a PERFECT number while doing so. Its
# selftest passed because every synthetic fixture cited the primary anchor verbatim, so the
# fixtures could not distinguish a working matcher from a word-frequency detector.
#
# The rule below is stated mechanically and was applied BEFORE re-reading any score, so it is
# a rule rather than a tuning: an anchor must be **symbol-like** (contains `_`, `-`, `(`, `.`,
# a digit, or an interior capital) or a **phrase of two or more words**. A bare single word is
# inadmissible no matter how apt it feels. Anchors are derived from the committed artefacts --
# the symbol that implements the behaviour, or the manifest's own wording -- never from a
# reviewer output, because a key fitted to the outputs it scores measures nothing.
# Symbol-like: punctuation a code identifier or literal carries, an interior capital
# (camelCase), or an ALL-CAPS token of 4+ characters (a shell/Python constant).
_SYMBOLY = re.compile(r"[_\-().0-9+/:]|[a-z][A-Z]|\b[A-Z]{4,}\b")


def anchor_ok(a: str) -> bool:
    return len(a.split()) >= 2 or bool(_SYMBOLY.search(a))


def assert_key_admissible():
    bad = []
    for name, case in CASES.items():
        for gid, _label, anchors in case["gaps"]:
            for a in anchors:
                if not anchor_ok(a):
                    bad.append(f"{name}/{gid}: {a!r}")
    return bad


def flagged_region(output: str) -> str:
    """Only the part of the output that PUBLISHES findings.

    This is the scorer's whole integrity. The after-condition's output names behaviors in a
    BEHAVIOR INVENTORY without flagging them; a whole-output grep would credit that as
    recall and the measurement would be a tautology.
    """
    m = FLAG_START_RE.search(output)
    return output[m.start():] if m else ""


# ---------------------------------------------------------------------------------------
# A STAGE-1 ("did it ENUMERATE the behaviour, even if it then suppressed it") METRIC WAS
# BUILT HERE AND REMOVED. Recorded rather than deleted silently, because the reason is the
# same rule this whole file is built around.
#
# The idea was sound: once the enumeration is visible, a miss can be attributed to the
# ENUMERATOR (absent from the inventory) or the MATCHER (present, then marked covered), and
# before the split every miss looked identical. The implementation was not. It scored the
# inventory region against the same `anchors` key -- and that key is deliberately made of
# CODE SYMBOLS (`focusWalkTarget`, `an-wipe`, `oneNoteBlock`), which appear in a finding's
# `Hunk:` line but not in a one-line behaviour description written in prose. So it measured
# anchor-vocabulary overlap, not enumeration, and reported 50% where a human reading the same
# inventories counts far more.
#
# It PASSED its own selftest, because the fixture I wrote to validate it spelled the anchors
# out verbatim -- a measurement validated only on input built from the key cannot distinguish
# a working scorer from a symbol-matcher. `general.md` item 4, committed by the harness whose
# entire purpose is to enforce it, one layer down.
#
# The fix would have been to add prose anchors to the key AFTER reading the outputs, i.e. to
# tune the instrument to the result it was measuring. So the metric is gone and the
# enumerator/matcher split is reported as a stated, reader-checkable OBSERVATION instead of a
# number: in the after-runs the inventory contains lines for the panel-row reopen and the
# empty-note discard while the COVERAGE MAP marks both `covered`, so those two residual misses
# are the matcher's "default to covered" doing its job, not the enumerator failing to look.
# ---------------------------------------------------------------------------------------


def score(case_name: str, output: str):
    """Recall for one run.

    THREE OUTCOMES, NOT TWO. `flagged_region()` returns "" both for a genuinely clean audit and
    for a run that never produced one, and the earlier version reported 0/N for both — so a
    truncated-read failure would be averaged in as a real miss. That is this PR's own doctrine
    ("I found nothing" and "I didn't look" must not read alike) one layer down, on the
    instrument, and it was enforced only by a prose note in runs/README.md: drop such a file
    into runs/ next month and the mean quietly absorbs a 0. `no_verdict` makes it a state the
    aggregate excludes and counts separately.
    """
    case = CASES[case_name]
    region = flagged_region(output)
    low = region.lower()
    found, missed = [], []
    for gid, label, anchors in case["gaps"]:
        if any(a.lower() in low for a in anchors):
            found.append((gid, label))
        else:
            missed.append((gid, label))

    issues = ISSUE_SPLIT_RE.split(region)[1:]
    all_anchors = [a.lower() for _g, _l, anchors in case["gaps"] for a in anchors]
    unmatched = [i for i in issues if not any(a in i.lower() for a in all_anchors)]
    return {
        "case": case_name,
        "n": len(case["gaps"]),
        "no_verdict": not region and not CLEAN_RE.search(output)
                      and not CONTROL_RE.search(output),
        "found": found,
        "missed": missed,
        "recall": len(found) / len(case["gaps"]) if case["gaps"] else 0.0,
        "issues": len(issues),
        "clean": bool(CLEAN_RE.search(output)) and not issues,
        # NOT auto-scored as false positives: an unmatched finding may be a real gap the key
        # does not carry (that happened in the spike). Reported for hand adjudication, which
        # is the honest treatment when the key is not known to be exhaustive.
        "fp_candidates": len(unmatched),
    }


def fmt(s) -> str:
    if s["no_verdict"]:
        return ("%-7s NO-VERDICT — the run produced no audit (no findings, no clean verdict, "
                "no control line). NOT scored as 0/%d." % (s["case"], s["n"]))
    return ("%-7s %2d/%-2d recall=%3.0f%%  issues=%-2d  fp?=%-2d  missed: %s"
            % (s["case"], len(s["found"]), s["n"], 100 * s["recall"], s["issues"],
               s["fp_candidates"], ", ".join(g for g, _l in s["missed"]) or "—"))


# ---------------------------------------------------------------------- selftest

def selftest() -> int:
    fails = []

    def ck(name, cond, detail=""):
        print(("  PASS  " if cond else "  FAIL  ") + name + (("" if cond else " — " + detail)))
        if not cond:
            fails.append(name)

    gaps = CASES["pr158"]["gaps"]
    n = len(gaps)

    # 1. Perfect output -> N/N. Without this the harness could be scoring nothing at all.
    def issue_blocks(subset):
        """The two fixtures below are the same builder over different slices. Stated once, so
        an output-format change cannot land in one and silently stop matching the other."""
        return "AUDIT SUMMARY\n%d issues flagged\n\n" % len(subset) + "\n".join(
            "ISSUE %d · Undeclared change\nClaim:\n> %s\n" % (i + 1, a[0])
            for i, (_g, _l, a) in enumerate(subset))

    perfect = issue_blocks(gaps)
    s = score("pr158", perfect)
    ck("an output citing every anchor scores N/N", len(s["found"]) == n, str(s))

    # 2. Clean output -> 0/N.
    s = score("pr158", "No issues flagged.\nNote: passive audit only checks stated evidence.")
    ck("'No issues flagged.' scores 0/N", len(s["found"]) == 0 and s["clean"], str(s))

    # 3. THE ONE THAT MATTERS: a rich enumeration above a clean verdict must score 0/N.
    #    This is the specific way the after-condition could win for free.
    enumerated = ("BEHAVIOR INVENTORY\n"
                  + "\n".join("B%d  %s  [H%d]" % (i + 1, a[0], i + 1)
                              for i, (_g, _l, a) in enumerate(gaps))
                  + "\nNOT BEHAVIOR\n(none)\nUNACCOUNTED\n(none)\n"
                    "COVERAGE MAP  " + " · ".join("B%d covered" % (i + 1) for i in range(n))
                  + "\n\nNo issues flagged.\n")
    s = score("pr158", enumerated)
    ck("naming every behavior WITHOUT flagging it scores 0/N (not a tautology)",
       len(s["found"]) == 0, "the scorer is crediting enumeration as recall: " + str(s))

    # 3b. NO-VERDICT is distinguished from clean, using the REAL text of the run this project
    #     actually discarded — not a synthetic stand-in, because the whole point is that the
    #     discard rule stops being prose. Paired with the positive (check 2 already asserts the
    #     clean fixture scores `clean`), so it cannot pass by classifying everything NO-VERDICT.
    nv = score("pr158", "I need to read the rest of the file.")
    ck("a run that produced no audit is NO-VERDICT, not 0/N",
       nv["no_verdict"] and not nv["clean"], str(nv))
    ck("...and a genuinely clean audit is NOT NO-VERDICT (paired positive)",
       not score("pr158", "No issues flagged.\nNote: passive audit only.")["no_verdict"],
       "classifying a clean verdict as no-verdict would hide real clean runs")
    ck("...and a deliberate SKIPPED control line is NOT NO-VERDICT either",
       not score("pr158", "[audit-coverage] SKIPPED — no behavior-bearing source files.")["no_verdict"],
       "a refusal to audit is a real outcome the reviewer chose, not an absent one")

    # 4. Subset -> exactly that subset.
    two = gaps[:2]
    partial = issue_blocks(two)
    s = score("pr158", partial)
    ck("a two-gap output scores exactly those two",
       {g for g, _ in s["found"]} == {g for g, _l, _a in two}, str(s))

    # 5. Unrelated findings -> 0 found, and counted as FP candidates rather than silence.
    s = score("pr158", "ISSUE 1 · Undeclared change\nClaim:\n> the CSS grid gap changed\n")
    ck("an unrelated finding scores 0 found and 1 fp-candidate",
       len(s["found"]) == 0 and s["fp_candidates"] == 1, str(s))

    # 6. MUTATION: deleting an anchor set must move the score. A scorer that returns the same
    #    number after the key changes is not reading the key.
    saved = CASES["pr158"]["gaps"]
    try:
        CASES["pr158"]["gaps"] = saved[:-1]
        s_mut = score("pr158", perfect)
        ck("dropping one gap from the key changes the denominator",
           s_mut["n"] == n - 1, str(s_mut))
    finally:
        CASES["pr158"]["gaps"] = saved

    # 7. The spike key must agree with the shipped eval's SPIKE_ANCHORS about WHICH TEN
    #    BEHAVIOURS exist. Two hand-maintained copies of the same ground truth is the FB-0010
    #    fan-out class, so they get a positive assertion tying them together.
    #
    #    Compared on LABELS, not anchors, and the distinction is substantive rather than a
    #    workaround: the shipped list's tokens are matched against ASSEMBLED SOURCE (does the
    #    evidence block still carry the code?), while this key's are matched against a
    #    REVIEWER'S FINDING (did it cite this behaviour?). `quota` is a fine source-side token
    #    and an inadmissible finding-side one. Forcing the two vocabularies to be identical
    #    would push an inadmissible anchor into one file or a useless one into the other; what
    #    must not drift is the SET OF BEHAVIOURS, and that is what this asserts.
    ev = (REPO / "plugins/flow/evals/run_coverage_source_mode_evals.py").read_text(encoding="utf-8")
    shipped = [re.sub(r"^\d+\s+", "", lbl) for lbl in
               re.findall(r'\("(\d+\s+[^"]+)",\s*"[^"]+"\)', ev)]
    mine = [l for _g, l, _a in CASES["spike"]["gaps"]]
    ck("the spike key describes the same ten behaviours as the shipped SPIKE_ANCHORS",
       shipped == mine, f"shipped={shipped}\n         mine={mine}")

    # 8. THE ANCHOR KEY IS ADMISSIBLE, and the checker can reject. Without the negative half
    #    this is the deletable-prohibition shape: a rule that only forbids passes in a world
    #    where the rule was removed (general.md item 3).
    # `mode` and `worktree_ref is None` both encode source-vs-diff. Keeping `mode` (it
    # documents the case for a reader) is only safe if something forces the two to agree.
    ck("every case's declared mode agrees with whether it uses a worktree ref",
       all((c["mode"] == "source") == (c["worktree_ref"] is None) for c in CASES.values()),
       "a case's declared mode contradicts its setup: " + ", ".join(
           n for n, c in CASES.items() if (c["mode"] == "source") != (c["worktree_ref"] is None)))

    bad = assert_key_admissible()
    ck("every anchor in every case is symbol-like or a multi-word phrase",
       not bad, "inadmissible anchors match incidentally and inflate recall: " + "; ".join(bad))
    ck("...and the admissibility checker REJECTS a bare common word",
       not anchor_ok("present") and not anchor_ok("contract") and anchor_ok("cmd_present")
       and anchor_ok("parseable verdict"),
       "the checker accepts anything, so it is not a checker")

    # 9. THE BLOCK-SHAPE CONTRACT IS PINNED, like the other two forced duplications.
    #    `BLOCK_RE` and the textual-substitution model in `render()` are copies of
    #    `run_coverage_source_mode_evals.py`'s (the import is rejected — that harness runs
    #    checks at module level). This PR pinned its other two forced duplications (the spike
    #    key ↔ SPIKE_ANCHORS, check 7; the .md exclusion, check 10) and left this one
    #    unpinned — the FB-0010 fan-out class, inside the PR about it.
    #
    #    What the gap would cost: if the evidence block ever grows a second span or an inline
    #    `!`cmd`` form, `render()` returns the block text UNEXECUTED as prose, the render still
    #    succeeds, `score` still prints a number, and that number goes into a PR body. The
    #    sibling harness asserts the same count for the same reason.
    n_blocks = len(BLOCK_RE.findall(skill_text(False)))
    ck("the skill still has exactly the two dynamic blocks this renderer assumes",
       n_blocks == 2,
       f"found {n_blocks} — render() would emit an unexecuted block as prose and still "
       "produce a scoreable number")

    # 10. THE STRUCTURAL CASE'S OWN ASSERTION, paired positive+negative. #159's `0-of-5` is
    #    not a recall result -- the file its five gaps live in never reached the reviewer,
    #    because the behaviour diff excludes `.md`. Asserting the blindness POSITIVELY (the
    #    exclusion clause is present in the shipped block AND the gaps' file matches it)
    #    means that if the exclusion is ever fixed, this fails loudly and the case is
    #    re-classified -- instead of silently becoming a recall case whose recorded 0 nobody
    #    can explain. A bare "pr159 is not scored" comment would have rotted in a week.
    sb = CASES["pr159"].get("structural_blindness") or {}
    if sb:
        block = (REPO / SKILL_REL).read_text(encoding="utf-8")
        # Strict form only: the exclusion must appear as an alternation branch inside EXCL,
        # not merely somewhere in the file. The earlier `or <loose>` disjunct could never
        # change the result (the strict operand CONTAINS the loose one), so it read as a
        # fallback while enforcing nothing.
        ck("the shipped block still carries the exclusion that blinded #159",
           "|" + sb["excluded_by"] + "'" in block,
           "the .md exclusion is gone or moved — re-classify pr159 as a recall case and re-measure")
        ck("...and #159's five gaps really do live in a file that exclusion matches",
           sb["gaps_live_in"].endswith(".md"),
           "the structural claim no longer matches the case")

    print()
    if fails:
        print("SELFTEST FAILED (%d). No recall number from this harness means anything "
              "until these pass." % len(fails))
        return 1
    print("Selftest passed — the scorer can fail, and fails for the right reasons.")
    return 0


# --------------------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render"); r.add_argument("case", choices=sorted(CASES))
    r.add_argument("--before", action="store_true"); r.add_argument("-o", "--out", required=True)
    s = sub.add_parser("score"); s.add_argument("case", choices=sorted(CASES))
    s.add_argument("output")
    sub.add_parser("selftest")
    rep = sub.add_parser("report"); rep.add_argument("dir")
    a = ap.parse_args(argv)

    if a.cmd == "selftest":
        return selftest()

    # EVERY scoring path is gated on the selftest. An instrument that can be used without
    # being validated will be, eventually, by someone in a hurry -- and the number it prints
    # will be quoted in a PR body forever.
    if a.cmd in ("score", "report"):
        print("— validating the instrument before reporting (general.md item 4) —")
        if selftest() != 0:
            return 1
        print()

    if a.cmd == "render":
        with tempfile.TemporaryDirectory() as td:
            target, undo = prepare(a.case, Path(td))
            try:
                text = render(a.case, a.before, target)
            finally:
                undo()
        Path(a.out).write_text(text, encoding="utf-8")
        cond = "before" if a.before else "after"
        print(f"rendered {a.case} [{cond}] → {a.out}  ({len(text)} chars)")
        for line in text.splitlines():
            if line.startswith("[audit-coverage]"):
                print("  " + line[:160])
        return 0

    if a.cmd == "score":
        print(fmt(score(a.case, Path(a.output).read_text(encoding="utf-8"))))
        return 0

    if a.cmd == "report":
        rows = {}
        for f in sorted(Path(a.dir).glob("*.txt")):
            parts = f.stem.split(".")
            if len(parts) < 3 or parts[0] not in CASES:
                continue
            case, cond = parts[0], parts[1]
            rows.setdefault((case, cond), []).append(score(case, f.read_text(encoding="utf-8")))
        for (case, cond), all_runs in sorted(rows.items()):
            # Excluded from the mean, counted in the open: a run with no verdict is not a miss.
            nv = [r for r in all_runs if r["no_verdict"]]
            runs = [r for r in all_runs if not r["no_verdict"]]
            if not runs:
                print("%-7s %-6s ALL %d run(s) produced NO VERDICT — nothing scoreable."
                      % (case, cond, len(nv)))
                continue
            union = set()
            for run in runs:
                union |= {g for g, _l in run["found"]}
            n = runs[0]["n"]
            mean = sum(len(x["found"]) for x in runs) / len(runs)
            fps = sum(x["fp_candidates"] for x in runs)
            print("%-7s %-6s n=%d runs=%d  flagged mean=%.1f/%d (%3.0f%%)  "
                  "union=%d/%d (%3.0f%%)  fp?=%d%s"
                  % (case, cond, n, len(runs), mean, n, 100 * mean / n,
                     len(union), n, 100 * len(union) / n, fps,
                     ("  no-verdict=%d (excluded)" % len(nv)) if nv else ""))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
