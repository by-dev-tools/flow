#!/usr/bin/env python3
"""Assert every (PR#, version) pairing in dev-docs matches what that PR actually shipped.

Why this exists: #158's PR title said "v1.46.0, FB-0113/FB-0114" when it was opened, then
`plugin.json` shipped as v1.48.0 by the time it merged (two other PRs landed first and claimed
v1.46.0/v1.47.0). The title never got corrected, and FIVE dev-docs sites (plus TWO in a
handoffs doc) copied the stale v1.46.0 from the title rather than reading the manifest — this
script's own first run found NINE, plus a second, independent instance on #84 (v1.22.0 in its
title, shipped v1.24.0, one doc site copied it). Same class each time: **the PR title is not the
version.** A title is written when the PR opens and goes stale on every rebase; `plugin.json` at
the merge commit is the fact.

Ground truth is derived from git history, not hand-maintained: for every commit that touched
`plugins/flow/.claude-plugin/plugin.json`, read that commit's PR number (out of its `(#NNN)`
subject suffix -- GitHub's squash-merge convention) and the version the file actually held at
that commit. That map is the one place "what version did PR #NNN ship under" is answered
authoritatively.

Two assertions, per `.claude/rules/general.md` item 3 (a negative alone is satisfiable by
deleting the thing it protects):

  1. POSITIVE -- dev-docs actually contains version claims paired with PR numbers (at least
     MIN_PAIRINGS). A run that finds zero pairings is not "clean," it is broken -- the scanner
     stopped seeing the shape it exists to check, and a green exit must not look identical to
     that failure the way it would if this were the only assertion.
  2. NEGATIVE -- no PR-paired version claim in dev-docs contradicts the ground truth map.

Deliberately NOT asserted: that every version mention in dev-docs is paired with a PR number (most
aren't, and shouldn't be -- "v1.49.0 added X" with no PR number is a description, not a claim this
script can verify against anything). Only PR-paired claims are checkable, so only those are
checked.

Needs full git history (a shallow clone breaks the ground-truth walk silently -- see the
depth-1 guard below, which fails loud rather than reporting a false-clean "0 mismatches").

Stdlib only (repo rule). Exit 0 = clean, 1 = mismatches found, 2 = the check itself broke.
"""

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_JSON = "plugins/flow/.claude-plugin/plugin.json"

# Scope is deliberately narrower than "every dev-doc": only the LIVING surfaces where a stale
# version claim actively misleads a reader today.
#   - roadmap.md is reconciled continuously (Now/Next/Later) -- always current by design.
#   - handoffs/*.md carry a Status banner meant to be checked before treating the doc as active.
#   - plan.md's "## Current Focus" section (everything before the first "## PR --" heading) is
#     the living part; everything after is a shipped/historical PR record kept AS THE RECORD
#     (CLAUDE.md: dev-docs/history/ and the retained plan.md PR blocks are point-in-time,
#     "not maintained" by design) -- editing those retroactively would rewrite history the repo
#     deliberately preserves, and the historical narrative legitimately re-tells an old, since-
#     corrected version claim as part of explaining how the claim drifted (see plan.md:716's own
#     "one known stale survivor, deliberately not edited" note -- that pattern is intentional,
#     not a bug this check should flag).
SCAN_FILES = ["dev-docs/roadmap.md"]
SCAN_DIRS = ["dev-docs/handoffs"]
PLAN_MD = "dev-docs/plan.md"
PLAN_MD_LIVING_HEADING_RE = re.compile(r"^## PR ", re.MULTILINE)

VERSION_OPEN_RE = re.compile(r"v(\d+\.\d+\.\d+)\**\s*\(")

# Negative lookbehind excludes "health-tracker#116" -- a DIFFERENT repo's issue/PR number that
# happens to collide numerically with one of this repo's own. Measured: roadmap.md cites
# health-tracker#116 by name, and without the lookbehind it silently misread as this repo's #116.
PR_RE = re.compile(r"(?<![\w-])#(\d{1,6})\b")
MAX_SPAN_LEN = 1500  # chars; measured real spans in this corpus run ~700 at the high end
MAX_MATCHES_PER_FILE = 500  # sanity cap against an O(spans * prs) blowup; see find_pairings
# How close to a span's own opening paren a PR number must sit to count as THAT version's
# headline claim, vs. an incidental cross-reference somewhere in a long descriptive paragraph.
# Measured false positive: roadmap.md's v1.49.0 entry is a multi-hundred-char paragraph that
# mentions "#159's recorded 0-of-5" and "on #158: 4 of 63" deep in its own prose, describing
# OTHER PRs' history -- neither claims #159/#158 shipped as v1.49.0, but both sit inside
# v1.49.0's parenthetical span. Every real claim in this corpus opens as "vX.Y.Z (shipped #NNN"
# or "vX.Y.Z (#NNN", i.e. within a few words of "(" -- so only the FIRST PR number within a
# span, and only if it is this close to the open paren, is treated as that span's claim.
HEADLINE_PROXIMITY = 20

# Supplementary shape: "(v1.22.0, #84)" -- a paren that OPENS before the version rather than
# right after it (the `_version_spans` model only catches "vX.Y.Z(..."). Rare in this corpus
# (one confirmed instance) but it is exactly the shape one of the two real bugs this check was
# built from takes, so it gets its own explicit pattern rather than being folded into the more
# general span engine and risking the same false-positive class that engine was hardened
# against.
PAREN_COMMA_RE = re.compile(r"\(v(\d+\.\d+\.\d+),\s*#(\d+)\)")
MIN_PAIRINGS = 5  # this corpus always has at least this many; a drop to 0 is the failure mode


def fail(msg, code=2):
    print(f"[version-provenance] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def run_git(args):
    try:
        return subprocess.run(
            ["git"] + args, cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout
    except subprocess.CalledProcessError as e:
        fail(f"git {' '.join(args)} failed: {e.stderr.strip()}")
    except FileNotFoundError:
        fail("git not found on PATH")


def assert_full_history():
    """A shallow clone (actions/checkout's default) truncates the log this script walks, which
    would silently shrink the ground-truth map and make real mismatches invisible -- a shallow
    clone must fail LOUD, never report a smaller-but-clean result."""
    out = run_git(["rev-parse", "--is-shallow-repository"])
    if out.strip() == "true":
        fail(
            "this is a shallow git clone (fetch-depth: 1) -- the ground-truth walk over "
            f"{PLUGIN_JSON}'s history would be truncated and mismatches would go undetected. "
            "Fix: set fetch-depth: 0 on this job's actions/checkout step."
        )


def build_ground_truth():
    """PR number -> version it actually shipped, from every commit that touched plugin.json."""
    log = run_git(["log", "--format=%H|%s", "--", PLUGIN_JSON])
    ground_truth = {}
    for line in log.splitlines():
        if "|" not in line:
            continue
        sha, subject = line.split("|", 1)
        pr_match = re.search(r"\(#(\d+)\)\s*$", subject.strip())
        if not pr_match:
            continue
        pr = int(pr_match.group(1))
        try:
            content = run_git(["show", f"{sha}:{PLUGIN_JSON}"])
        except SystemExit:
            continue
        ver_match = re.search(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"', content)
        if not ver_match:
            continue
        ver = ver_match.group(1)
        # A PR number should map to exactly one shipped version. If the log ever shows two
        # different versions for the same PR (a genuine history rewrite), that is exactly the
        # "structural ambiguity" this check cannot resolve on its own -- surface it loudly
        # rather than silently keeping the first-seen or last-seen value.
        if pr in ground_truth and ground_truth[pr] != ver:
            fail(
                f"PR #{pr} maps to two different shipped versions in git history "
                f"({ground_truth[pr]} and {ver}) -- the manifest history is ambiguous for this "
                "PR. This needs a human to resolve, not a mechanical fix."
            )
        ground_truth[pr] = ver
    if not ground_truth:
        fail(f"found zero PR-tagged commits touching {PLUGIN_JSON} -- ground truth is empty.")
    return ground_truth


def _version_spans(text):
    """Every `vX.Y.Z(` (markdown emphasis tolerated) opens a span running to ITS OWN matching
    close-paren, found by depth-counting from that specific `(` -- nested parens inside the
    description (common: "...(a toolchain-shaped reason **and** a host probe...)...") are
    handled by the depth counter, not skipped over. Returns (open_idx, close_idx, version).

    This is the one shape robust to this repo's dominant authoring convention --
    "vX.Y.Z (shipped #NNN -- <description>)" -- without being fooled by dense list lines where
    an unrelated PR number sits right next to a NEIGHBORING item's version. A PR number is only
    ever attributed to the version whose own parenthetical textually contains it; a bare
    distance/nearest heuristic (tried first) mispaired constantly on exactly that shape.

    Free-form prose is NOT guaranteed paren-balanced (a stray "(" in a code span or a lone
    smiley is enough), so an unterminated span is discarded rather than allowed to run to EOF --
    measured on this corpus: one real unbalanced "(" turned a ~700-char span into a 147,927-char
    one that silently swallowed six unrelated PR numbers into the wrong version's pairing. A
    bounded MAX_SPAN_LEN turns that into "this version's claim is unpaired" (safe, under-checks)
    instead of "every PR number for the next 148KB belongs to this version" (unsafe)."""
    spans = []
    for m in VERSION_OPEN_RE.finditer(text):
        open_idx = m.end() - 1  # index of the "(" itself
        depth = 1
        i = open_idx + 1
        n = len(text)
        limit = min(n, open_idx + 1 + MAX_SPAN_LEN)
        while i < limit and depth > 0:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
            i += 1
        if depth != 0:
            continue  # unterminated within the cap -- discard, don't guess a boundary
        spans.append((open_idx, i, m.group(1)))
    return spans


def find_pairings(text, path, line_offset=0):
    """Yield (path, line_no, pr, claimed_version) for each span's HEADLINE PR number only --
    the first `#NNN` inside a version's own parenthetical span, and only when it sits within
    HEADLINE_PROXIMITY chars of the opening paren. Deliberately does NOT try to pair a PR that
    appears outside every version span (e.g. "#152 (FB-0108, v1.42.0 ...)" -- PR-number-first
    phrasing), and deliberately ignores every OTHER PR number mentioned deeper inside a long
    span's own descriptive prose (a paragraph about what v1.49.0 shipped routinely cites other
    PRs' history in passing -- "#159's recorded 0-of-5" -- without claiming they shipped as
    v1.49.0). Under-detecting either way is far safer than the false positives a wider match
    produced on this corpus's dense narrative paragraphs."""
    spans = _version_spans(text)
    # NOTE: deliberately no early-return on empty spans -- PAREN_COMMA_RE below finds pairings
    # independent of the span engine (a fixture/doc with only the "(vX.Y.Z, #NNN)" shape and no
    # "vX.Y.Z(" shape would otherwise silently yield zero pairings; caught by the selftest).
    # line_offset lets a caller (plan.md's living-prefix slice) report line numbers relative
    # to the ORIGINAL file rather than the slice.
    line_starts = [0]
    for line in text.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    def line_of(pos):
        # line_starts[i] is the start offset of line i+1 (1-indexed); bisect would be cleaner
        # but this corpus is small enough that a linear scan costs nothing measurable.
        lo = 1 + line_offset
        for i in range(len(line_starts) - 1):
            if line_starts[i] <= pos < line_starts[i + 1]:
                return lo + i
        return lo + len(line_starts) - 1

    pr_matches = [(m.start(), int(m.group(1))) for m in PR_RE.finditer(text)]

    # SECURITY (found by /flow:security-review on this PR): the loop below is
    # O(len(spans) * len(pr_matches)) with no bound on either count beyond MAX_SPAN_LEN (which
    # only caps a single span's WIDTH, not how many spans/PR references a file can contain). CI
    # runs on `pull_request`, so a crafted doc added by any PR (e.g. tens of thousands of
    # repeated "v1.0.0(#1)"-shaped tokens under dev-docs/handoffs/, which this script scans in
    # full) could otherwise hang the job. Fail loud on an implausibly large count rather than
    # silently grinding -- consistent with this script's fail-loud posture everywhere else, and
    # cheaper than a bisect-based rewrite for a bound this corpus will never approach honestly.
    if len(spans) > MAX_MATCHES_PER_FILE or len(pr_matches) > MAX_MATCHES_PER_FILE:
        fail(
            f"{path} has {len(spans)} version span(s) and {len(pr_matches)} PR reference(s) -- "
            f"over the {MAX_MATCHES_PER_FILE} sanity cap. Either this file grew far beyond a "
            "normal dev-doc (check it by hand) or something is generating repeated tokens; "
            "refusing to run the pairing scan rather than risk an unbounded CI hang."
        )

    pairings = []
    for open_idx, close_idx, version in spans:
        # First PR number inside this span, closest to the open paren -- that is the span's
        # headline claim. Every other PR mentioned deeper in the same span's prose is an
        # incidental cross-reference, not a new claim (see the function docstring).
        inside = [(pos, pr) for pos, pr in pr_matches if open_idx < pos < close_idx]
        if not inside:
            continue
        pos, pr = min(inside, key=lambda t: t[0])
        if pos - open_idx <= HEADLINE_PROXIMITY:
            pairings.append((path, line_of(pos), pr, version))

    for m in PAREN_COMMA_RE.finditer(text):
        pairings.append((path, line_of(m.start()), int(m.group(2)), m.group(1)))

    return pairings


def collect_files():
    """Returns (rel_path, text) pairs -- plan.md is pre-sliced to its living prefix here so the
    rest of the pipeline never has to know about the split."""
    out = []
    for rel in SCAN_FILES:
        p = os.path.join(REPO_ROOT, rel)
        if os.path.isfile(p):
            try:
                out.append((rel, open(p, encoding="utf-8").read()))
            except OSError as e:
                fail(f"cannot read {rel}: {e}")
    for rel in SCAN_DIRS:
        d = os.path.join(REPO_ROOT, rel)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.endswith(".md"):
                p = os.path.join(d, name)
                try:
                    out.append((os.path.join(rel, name), open(p, encoding="utf-8").read()))
                except OSError as e:
                    fail(f"cannot read {rel}/{name}: {e}")
    plan_path = os.path.join(REPO_ROOT, PLAN_MD)
    if os.path.isfile(plan_path):
        try:
            plan_text = open(plan_path, encoding="utf-8").read()
        except OSError as e:
            fail(f"cannot read {PLAN_MD}: {e}")
        m = PLAN_MD_LIVING_HEADING_RE.search(plan_text)
        living = plan_text[: m.start()] if m else plan_text
        out.append((f"{PLAN_MD} (Current Focus)", living))
    return out


def selftest():
    """Per `.claude/rules/general.md` item 4: a measurement that can only return "clean" is not
    a measurement. Runs `find_pairings` (the mechanical half this whole check rests on) against
    synthetic fixtures shaped like this repo's real corpus, asserting it catches a KNOWN
    mismatch and does NOT false-positive on the two shapes that produced every false positive
    while this checker was being built. Exit 0 = the engine can both pass and fail as designed;
    non-zero = the engine itself is broken (never trust a check that has never been seen to
    fail)."""
    cases = [
        (
            "version-first, dense list line (the historical false-positive source)",
            "Recently shipped: **v1.48.0 (#158 -- D1 Phase 2), v1.47.0 (#159 -- source-tree "
            "mode), v1.45.0 (#157 -- orchestrator suite).**",
            {158: "1.48.0", 159: "1.47.0", 157: "1.45.0"},
        ),
        (
            "PR-first, comma-paren (the #84 shape)",
            "commenting-as-mode shipped (v1.24.0, #84).",
            {84: "1.24.0"},
        ),
        (
            "incidental cross-reference inside a long span must NOT pair",
            "**v1.49.0 (shipped #160 -- fixes a bug first reported against #159's own recall "
            "numbers, unrelated to what #159 itself shipped as).**",
            {160: "1.49.0"},  # note: 159 must NOT appear as a pairing at all
        ),
        (
            "unbalanced paren must not create a runaway span",
            "v1.21.1 (audit-skips can't silently no-op on a broken handoff: `skip-audit-checks.py` "
            "now exits non-zero on a present-but-malformed handoff (stderr diagnostic, clean "
            "stdout) instead of `return 0` + `{\"error\": \"x (unterminated\", #83).",
            {},  # the unterminated inner code-span must not swallow #83 into v1.21.1
        ),
        (
            "external repo#NNN must not be misread as this repo's PR",
            "ported from health-tracker#116 with its loud-failure property. v1.29.0 (#116 -- "
            "binary asset re-export).",
            {116: "1.29.0"},
        ),
    ]
    failed = False
    for name, text, expected in cases:
        got = {pr: version for _, _, pr, version in find_pairings(text, "<selftest>")}
        if got != expected:
            failed = True
            print(f"[version-provenance] SELFTEST FAIL — {name}", file=sys.stderr)
            print(f"    expected: {expected}", file=sys.stderr)
            print(f"    got:      {got}", file=sys.stderr)
    if failed:
        print("[version-provenance] SELFTEST FAILED -- the pairing engine itself is broken; "
              "do not trust its output on the real corpus until this is fixed.", file=sys.stderr)
        return 1
    print(f"[version-provenance] SELFTEST PASS -- {len(cases)} fixtures, engine catches real "
          "mismatches and does not false-positive on the three shapes that fooled earlier "
          "drafts of this checker.")
    return 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())

    assert_full_history()
    ground_truth = build_ground_truth()

    all_pairings = []
    for rel, text in collect_files():
        all_pairings.extend(find_pairings(text, rel))

    if len(all_pairings) < MIN_PAIRINGS:
        fail(
            f"only found {len(all_pairings)} PR+version pairings across dev-docs "
            f"(expected >= {MIN_PAIRINGS}). Either the scanned files shrank a lot, or this "
            "script's own pairing regex broke -- both are failures, not a clean pass.",
            code=1,
        )

    mismatches = []
    for rel, lineno, pr, claimed in all_pairings:
        actual = ground_truth.get(pr)
        if actual is not None and actual != claimed:
            mismatches.append((rel, lineno, pr, claimed, actual))

    if mismatches:
        print(
            f"[version-provenance] FAIL — {len(mismatches)} of {len(all_pairings)} "
            f"PR+version pairing(s) contradict what that PR actually shipped:",
            file=sys.stderr,
        )
        for rel, lineno, pr, claimed, actual in mismatches:
            print(
                f"  {rel}:{lineno}: claims #{pr} shipped v{claimed}, "
                f"but plugin.json at that PR's merge commit says v{actual}",
                file=sys.stderr,
            )
        print(
            "  Fix: read the version from plugins/flow/.claude-plugin/plugin.json at the PR's "
            "merge commit, never from the PR title (titles go stale on rebase). "
            "Do NOT edit this check to pass — the mismatch is real.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"[version-provenance] PASS — {len(all_pairings)} PR+version pairing(s) checked, "
        f"0 contradict the manifest history."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
