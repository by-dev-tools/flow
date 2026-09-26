#!/usr/bin/env python3
"""Eval harness for /flow:audit-coverage's deterministic change inventory (FB-0115).

WHAT THIS PINS, and why it is the half that must be deterministic. Across four live runs
with known ground truth the coverage reviewer found 10-of-10, 5-of-10, 0-of-5 and 2-of-5
of the gaps present -- at precision 4/4, never once a false positive. Recall is the whole
problem, and the mechanism is that the shipped prompt fuses *enumerate* + *match* +
*suppress* into one invisible step: a run that enumerated 6 of 11 behaviours emits a clean
result indistinguishable from a thorough one. `change-inventory.py` removes the
enumeration from judgment entirely -- git says which hunks exist, and which of them the
plan PREDATES.

THE INSTRUMENT WAS VALIDATED BEFORE IT WAS BELIEVED (`general.md` Consistency item 4), and
that validation found a real defect rather than confirming a hope: replayed on #158's real
commit graph, the first version rendered `prototype-gate.py` (a NEW file on that branch) as
ONE +987-line `pre-plan` row -- a one-entry checklist for the PR whose five missed
behaviours all live in that file, tiered wrong. §5 below is that replay, kept as a
permanent known-positive, and it asserts the fix at the granularity the defect needed: all
five ground-truth behaviours named BY FUNCTION in the rows.

Sections:
  §1  tiering: POST-PLAN fires when it should, and -- paired -- does NOT when it should not
  §2  PLAN-PREDATES-BRANCH is its own tier, stronger than POST-PLAN, never silence
  §3  INVENTORY-UNAVAILABLE on every failure path, and it is NEVER the SKIPPED line
  §4  the cap warns, and does not always fire
  §5  THE KNOWN POSITIVE: #158's real graph, plus its real negative control
  §6  registration self-guards (the skill calls it; the file list is not re-filtered)

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_coverage_inventory_evals.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from eval_utils import commit, git_repo          # noqa: E402  the shared hoist target

HERE = Path(__file__).parent
PLUGIN = HERE.parent
REPO = PLUGIN.parent.parent
ENGINE = PLUGIN / "skills" / "audit-coverage" / "lib" / "change-inventory.py"
SKILL = PLUGIN / "skills" / "audit-coverage" / "SKILL.md"

SKIP_LINE = "[audit-coverage] SKIPPED"
UNAVAIL = "[audit-coverage] WEAKENED · INVENTORY-UNAVAILABLE"

_failures: list[str] = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


def inv(cwd, files, base="main", plan="plan.md", extra=None):
    """Run the SHIPPED engine, never a restatement of it."""
    cmd = [sys.executable, str(ENGINE), "--base", base, "--plan", plan] + (extra or [])
    p = subprocess.run(cmd, cwd=str(cwd), input="\n".join(files) + "\n",
                       capture_output=True, text=True, timeout=120)
    return p.stdout + p.stderr


def tier_of(out, needle):
    """The tier on the first row mentioning `needle`, or None.

    Reads the LEADING tier column (`  H1  POST-PLAN  path:12 (+4)`). It used to read the
    trailing field; the tier moved to the front because trailing put a 30-column-ragged edge
    on the one field the prose tells the reader to scan for."""
    for line in out.splitlines():
        if line.startswith("  H") and needle in line:
            parts = line.split(None, 2)          # ["H1", "<TIER>", "<rest>"]
            return parts[1] if len(parts) > 1 else None
    return None


def row_tiers(out):
    """Every tier appearing on an actual ROW.

    Required because the output now carries a legend line that NAMES all five tiers, so a
    whole-output `"POST-PLAN" in out` is true on every run and four assertions here silently
    became unfailable the moment the legend shipped. Reading rows is both the fix and the
    stricter check — it was always what those assertions meant.
    """
    return [line.split(None, 2)[1] for line in out.splitlines()
            if line.startswith("  H") and len(line.split(None, 2)) > 1]


# ===========================================================================
print("\n§1 — POST-PLAN fires when it should, and does NOT when it should not")
# The paired shape general.md item 3 requires: a tier that always fires is not a tier, and
# an assertion that only checks "POST-PLAN is absent" would pass if the tier were deleted.
with tempfile.TemporaryDirectory() as td:
    # Source, THEN plan, THEN more source -- the real /simplify + staff-review shape.
    #
    # TWO FILES, deliberately. The first version of this fixture put both changes in one
    # file and asserted the pre-plan one stayed `pre-plan`. It did not, and the ENGINE was
    # right: contiguous additions COALESCE into a single `@@ -2,0 +3,8 @@` hunk, so there
    # was no separable pre-plan hunk to tier -- the one hunk genuinely contained post-plan
    # lines, and calling it POST-PLAN is both correct and the conservative direction for
    # recall. Separating the files is what makes the discrimination testable at all; the
    # coalescing behaviour is now pinned in its own check below so nobody re-derives this.
    r = git_repo(Path(td) / "seq", {
        "declared.py": "def d():\n    return 1\n",
        "app.py": "def a():\n    return 1\n",
        "plan.md": "**Spec-walk:**\n- [x] a returns 1 → verify: unit\n",
    })
    subprocess.run(["git", "branch", "-q", "base-mark"], cwd=r, capture_output=True)
    commit(r, {"declared.py": "def d():\n    return 2\n"}, "src: behaviour later declared")
    commit(r, {"plan.md": "**Spec-walk:**\n- [x] a returns 1 → verify: unit\n"
                          "- [x] d() returns 2 → verify: unit\n"}, "plan: declare it")
    commit(r, {"app.py": "def a():\n    return 1\n\n\ndef added_by_simplify():\n"
                         "    return 3\n"}, "simplify: new behaviour")

    out = inv(r, ["app.py", "declared.py"], base="base-mark")
    check("the hunk added after the plan's last edit is POST-PLAN",
          tier_of(out, "app.py") == "POST-PLAN", out)
    check("the POST-PLAN summary line names the plan commit it compared against",
          "[audit-coverage] POST-PLAN —" in out and "AFTER the plan was last edited" in out, out)
    check("the file the plan was edited to cover is NOT POST-PLAN (paired negative)",
          tier_of(out, "declared.py") in ("pre-plan", "SAME-COMMIT"),
          "a tier that always fires is not a tier — declared.py came back "
          f"{tier_of(out, 'declared.py')!r}: " + out)

with tempfile.TemporaryDirectory() as td:
    # Pin the coalescing behaviour that corrected the fixture above, so the next reader does
    # not re-run the same experiment: a pre-plan addition CONTIGUOUS with a post-plan one is
    # one hunk, and it is tiered POST-PLAN. Conservative on purpose -- the tier exists to
    # raise recall, and under-marking is the failure that costs a missed behaviour.
    r = git_repo(Path(td) / "coalesce", {
        "app.py": "def a():\n    return 1\n",
        "plan.md": "**Spec-walk:**\n- [x] a → verify: unit\n",
    })
    subprocess.run(["git", "branch", "-q", "base-mark"], cwd=r, capture_output=True)
    commit(r, {"app.py": "def a():\n    return 1\n\n\ndef declared():\n    return 2\n"}, "src")
    commit(r, {"plan.md": "**Spec-walk:**\n- [x] a\n- [x] declared\n"}, "plan")
    commit(r, {"app.py": "def a():\n    return 1\n\n\ndef declared():\n    return 2\n"
                         "\n\ndef later():\n    return 3\n"}, "post-plan, contiguous")
    out = inv(r, ["app.py"], base="base-mark")
    check("a pre-plan hunk contiguous with a post-plan one is marked POST-PLAN, not pre-plan",
          "pre-plan" not in row_tiers(out) and "POST-PLAN" in row_tiers(out),
          "under-marking a coalesced hunk would hide post-plan behaviour: " + out)

with tempfile.TemporaryDirectory() as td:
    # The mirror: plan edited LAST. Nothing may be POST-PLAN.
    r = git_repo(Path(td) / "planlast", {
        "app.py": "def a():\n    return 1\n",
        "plan.md": "**Spec-walk:**\n- [x] a → verify: unit\n",
    })
    subprocess.run(["git", "branch", "-q", "base-mark"], cwd=r, capture_output=True)
    commit(r, {"app.py": "def a():\n    return 9\n"}, "src")
    commit(r, {"plan.md": "**Spec-walk:**\n- [x] a returns 9 → verify: unit\n"}, "plan last")
    out = inv(r, ["app.py"], base="base-mark")
    check("a branch whose LAST commit is the plan yields zero POST-PLAN rows",
          "POST-PLAN" not in row_tiers(out), out)
    check("...and still renders a real inventory (not silence)",
          "change inventory (deterministic)" in out and "  H1 " in out, out)

with tempfile.TemporaryDirectory() as td:
    # An uncommitted source edit is post-plan by construction and gets its own louder tier.
    r = git_repo(Path(td) / "dirty", {
        "app.py": "def a():\n    return 1\n",
        "plan.md": "**Spec-walk:**\n- [x] a → verify: unit\n",
    })
    subprocess.run(["git", "branch", "-q", "base-mark"], cwd=r, capture_output=True)
    (r / "app.py").write_text("def a():\n    return 1\n\n\ndef uncommitted():\n    pass\n",
                              encoding="utf-8")
    out = inv(r, ["app.py"], base="base-mark")
    check("a working-tree-only change is tiered UNCOMMITTED",
          "UNCOMMITTED" in row_tiers(out), out)

with tempfile.TemporaryDirectory() as td:
    # THE KNOWN LIMITATION, PINNED AS KNOWN — not left to read like a working tier.
    # `plan_last` is the last commit touching the plan FILE, so when a single commit carries
    # BOTH the plan and the code (which is /flow:ship's normal shape — Step 5 rewrites
    # planPath in the ship commit) every hunk lands SAME-COMMIT, and the sharp POST-PLAN
    # signal is lost exactly where the measured miss class lives. Two independent /simplify
    # lenses found this on one run. It is honest (the tier reports it cannot tell) but it is
    # a real ceiling, and an eval that merely stayed green here would let the next reader
    # believe the tier fires on this repo's own ships. The deeper fix — tier off the active
    # Spec-walk BLOCK's line range via `git log -L` — is on the roadmap, and when it lands
    # THIS check must fail and be rewritten, which is the point of writing it down.
    r = git_repo(Path(td) / "together", {
        "app.py": "def a():\n    return 1\n",
        "plan.md": "**Spec-walk:**\n- [x] a → verify: unit\n",
    })
    subprocess.run(["git", "branch", "-q", "base-mark"], cwd=r, capture_output=True)
    # One commit carrying plan + code, the ship-time shape.
    commit(r, {"app.py": "def a():\n    return 1\n\n\ndef added():\n    return 2\n",
               "plan.md": "**Spec-walk:**\n- [x] a → verify: unit\n- [x] noted\n"}, "ship: plan+code")
    out = inv(r, ["app.py"], base="base-mark")
    check("KNOWN CEILING: plan+code in ONE commit degrades to SAME-COMMIT, not POST-PLAN",
          tier_of(out, "app.py") == "SAME-COMMIT",
          "if this now says POST-PLAN the block-scoped fix landed — rewrite this check and "
          "the roadmap entry rather than deleting it: " + out)
    check("...and the summary does NOT claim POST-PLAN over it (no self-contradiction)",
          "[audit-coverage] POST-PLAN —" not in out,
          "a headline that disagrees with its own rows is worse than no headline: " + out)

# ===========================================================================
print("\n§2 — PLAN-PREDATES-BRANCH is its own tier, and it is the STRONGER signal")
with tempfile.TemporaryDirectory() as td:
    r = git_repo(Path(td) / "untouched", {
        "app.py": "def a():\n    return 1\n",
        "plan.md": "**Spec-walk:**\n- [x] a → verify: unit\n",
    })
    subprocess.run(["git", "branch", "-q", "base-mark"], cwd=r, capture_output=True)
    commit(r, {"app.py": "def a():\n    return 1\n\n\ndef b():\n    return 2\n"}, "src only")
    out = inv(r, ["app.py"], base="base-mark")
    check("a plan never touched on this branch reports PLAN-PREDATES-BRANCH",
          "PLAN-PREDATES-BRANCH" in row_tiers(out), out)
    check("...and says the whole diff is undeclared, not that the tier is unknown",
          "NO declared criterion was written against" in out, out)
    check("...and does NOT also claim POST-PLAN (one tier, not two)",
          "[audit-coverage] POST-PLAN —" not in out, out)

# ===========================================================================
print("\n§3 — INVENTORY-UNAVAILABLE on every failure path, and never the SKIPPED line")
# The FB-0074 shape applied to a new outcome: "I could not build the checklist" and "there
# was nothing to check" have opposite consequences, so they must not share a line. Each
# case asserts the POSITIVE (the unavailable line is present) AND the NEGATIVE (SKIPPED is
# absent) -- the pairing general.md item 3 requires, because a check that only forbids
# SKIPPED passes in a world where the whole engine was deleted.
with tempfile.TemporaryDirectory() as td:
    r = git_repo(Path(td) / "u", {"app.py": "x = 1\n", "plan.md": "**Spec-walk:**\n- [x] x\n"})
    cases = [
        ("an unresolvable base ref", dict(files=["app.py"], base="no/such/ref")),
        ("an empty file list", dict(files=[], base="main")),
    ]
    for label, kw in cases:
        out = inv(r, **kw)
        check(f"{label} reports INVENTORY-UNAVAILABLE", UNAVAIL in out, out)
        check(f"...and {label} is never the SKIPPED line", SKIP_LINE not in out, out)
        check(f"...and {label} says a clean result below is WEAKER, not equal",
              "WEAKER" in out and "NOT a skip" in out, out)
        check(f"...and {label} carries the WEAKENED token the skill prose matches on",
              "WEAKENED · " in out,
              "the prose rule keys on the token; a weakening without it is invisible: " + out)

    # Not a git repo at all -- the engine must not traceback into the evidence block.
    with tempfile.TemporaryDirectory() as td2:
        out = inv(Path(td2), ["app.py"], base="main")
        check("a non-repo cwd reports INVENTORY-UNAVAILABLE rather than crashing",
              UNAVAIL in out and "Traceback" not in out, out)
        check("...and a non-repo cwd is never the SKIPPED line", SKIP_LINE not in out, out)

with tempfile.TemporaryDirectory() as td:
    # NON-UTF-8 CONTENT MUST NOT CRASH THE ENGINE. Strict decoding raised UnicodeDecodeError
    # outside `Unavailable`, so a latin-1 funcname produced a traceback on stderr and NO
    # [audit-coverage] line at all -- the direct contradiction of this module's "every failure
    # path prints INVENTORY-UNAVAILABLE and exits 0" contract, and worse than a weakening
    # because Stage 1 then has no checklist AND no notice that it has none.
    r = git_repo(Path(td) / "latin1", {"plan.md": "**Spec-walk:**\n- [x] x\n"})
    (r / "a.py").write_bytes(b"x = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=r, capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "b"],
                   cwd=r, capture_output=True)
    subprocess.run(["git", "branch", "-q", "base-mark"], cwd=r, capture_output=True)
    (r / "a.py").write_bytes(b"def \xe9legant():\n    return 1\n\n\nx = 2\n")
    subprocess.run(["git", "add", "-A"], cwd=r, capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "l"],
                   cwd=r, capture_output=True)
    out = inv(r, ["a.py"], base="base-mark")
    check("non-UTF-8 content does not crash the engine (contract: never print nothing)",
          "Traceback" not in out and "[audit-coverage] change inventory" in out, out)
    check("...and it still produces a real row rather than degrading to unavailable",
          row_tiers(out) != [], out)

# ===========================================================================
print("\n§4 — the cap warns, and does not always fire")
with tempfile.TemporaryDirectory() as td:
    body = "".join("v%d = %d\n" % (i, i) for i in range(40))
    r = git_repo(Path(td) / "cap", {"app.py": body, "plan.md": "**Spec-walk:**\n- [x] x\n"})
    subprocess.run(["git", "branch", "-q", "base-mark"], cwd=r, capture_output=True)
    # Change every other line -> many separate hunks under -U0.
    lines = body.splitlines()
    for i in range(0, len(lines), 2):
        lines[i] = "v%d = %d" % (i, i + 1000)
    commit(r, {"app.py": "\n".join(lines) + "\n"}, "many hunks")
    out_small = inv(r, ["app.py"], base="base-mark", extra=["--max-rows", "3"])
    check("over the cap emits INVENTORY-TRUNCATED",
          "WEAKENED · INVENTORY-TRUNCATED" in out_small, out_small)
    check("...and the HEADER says PARTIAL, so the qualifier precedes the rows it qualifies",
          "PARTIAL — the cap was reached" in out_small.splitlines()[0],
          "a clipped inventory opened with a complete-sounding total and its correction sat "
          "below every row it qualified: " + out_small.splitlines()[0])
    check("...and says the checklist is PARTIAL",
          "PARTIAL" in out_small, out_small)
    out_big = inv(r, ["app.py"], base="base-mark", extra=["--max-rows", "500"])
    check("under the cap does NOT emit INVENTORY-TRUNCATED (the warning is not decorative)",
          "INVENTORY-TRUNCATED" not in out_big, out_big)
    check("...and an un-clipped header does NOT claim PARTIAL",
          "PARTIAL" not in out_big.splitlines()[0], out_big.splitlines()[0])
    # THE PAIRED NEGATIVE for the whole token scheme. The engine's ordinary output -- header,
    # tier legend, POST-PLAN summary -- are all `[audit-coverage]` control lines above the
    # delimiter, and the first version of the prose rule captured them, which would have
    # demanded "this audit is weaker" on every healthy run. If a success line ever gains the
    # token, the marker stops distinguishing healthy from degraded.
    check("a HEALTHY run emits no WEAKENED token at all (the marker means something)",
          "WEAKENED" not in out_big,
          "an informational line is carrying the weakening token: " + out_big)

# ===========================================================================
print("\n§5 — THE KNOWN POSITIVE: #158's real commit graph, and its real negative control")
# `general.md` item 4. This does not validate on a synthetic case where the answer was
# authored alongside the assertion -- it replays the actual branch whose ship run found
# 2 of 5, at the actual SHA coverage ran at, and requires the deterministic inventory to
# name all five ground-truth behaviours BY FUNCTION. The five are quoted from #158's own
# draft manifest, not restated: an unrecognised gate literal is refused (cmd_gate_execute);
# the approval digest emits both committed lines (render_digest); `contract` emits one
# parseable verdict with no prototype (_contract); `present` always returns an openable
# path and reports the hash of what it presented (cmd_present).
GROUND_TRUTH_158 = {
    "gate literal refused": "def cmd_gate_execute",
    "approval digest lines": "def render_digest",
    "contract verdict with no prototype": "def _contract",
    "present returns an openable path + reports its hash": "def cmd_present",
}
SHIP_SHA = "c91b8c2"      # after /flow:staff-review, before the criteria were back-filled
BASE_SHA = "5a2aaf3"      # origin/main at the time (#159)
TARGET = "plugins/flow/skills/prototype/lib/prototype-gate.py"

have_graph = subprocess.run(["git", "cat-file", "-e", SHIP_SHA + "^{commit}"],
                            cwd=str(REPO), capture_output=True).returncode == 0
if not have_graph:
    # A shallow clone genuinely cannot run this. Say which, loudly -- a silently skipped
    # known-positive is how an unvalidated instrument ships looking green.
    print("  SKIP  #158's graph is not in this clone (%s unreachable); §5 did NOT run. "
          "This is not a pass." % SHIP_SHA)
else:
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "wt158"
        subprocess.run(["git", "worktree", "add", "-f", "--detach", str(wt), SHIP_SHA],
                       cwd=str(REPO), capture_output=True)
        try:
            out = inv(wt, [TARGET], base=BASE_SHA, plan="dev-docs/plan.md")
            missing = [label for label, fn in GROUND_TRUTH_158.items() if fn not in out]
            check("all four #158 ground-truth call sites are named in the inventory rows",
                  not missing, "inventory never named: " + "; ".join(missing))
            check("...and every one of them is tiered POST-PLAN",
                  all(tier_of(out, fn) == "POST-PLAN" for fn in GROUND_TRUTH_158.values()),
                  out)
            check("...and the NEW-FILE whole-file row is labelled as the file, not a hunk",
                  any(line.startswith("  H") and "NEW-FILE" in line
                      for line in out.splitlines())
                  and "NEW-FILE: the row is the whole file, not one hunk" in out,
                  "the row needs the marker AND the legend needs to define it: " + out)
            check("...and the whole-file row is excluded from the POST-PLAN tally",
                  "whole-file row spanning the same region" in out
                  and "(11 hunks + 1 whole-file)" in out,
                  "a row containing all the others must not be counted alongside them, and "
                  "both denominators must be visible in the header: " + out)

            # THE PROBE'S OWN NEGATIVE CONTROL, on real data rather than a fixture: at the
            # branch TIP the last commit touching the plan is newer than the source commits,
            # so the identical call must report nothing POST-PLAN. If it fires there too,
            # §5's positive means nothing.
            tip = Path(td) / "wttip"
            subprocess.run(["git", "worktree", "add", "-f", "--detach", str(tip),
                            "origin/conductor/track-b-d1-phase-2-prototype-gate"],
                           cwd=str(REPO), capture_output=True)
            if tip.is_dir():
                out_tip = inv(tip, [TARGET], base=BASE_SHA, plan="dev-docs/plan.md")
                check("at #158's TIP (plan edited last) the same call reports no POST-PLAN",
                      "[audit-coverage] POST-PLAN —" not in out_tip, out_tip)
                subprocess.run(["git", "worktree", "remove", "--force", str(tip)],
                               cwd=str(REPO), capture_output=True)
            else:
                print("  SKIP  #158's tip is not in this clone; the real negative control "
                      "did NOT run. This is not a pass.")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(wt)],
                           cwd=str(REPO), capture_output=True)

# ===========================================================================
print("\n§6 — registration: the skill calls it, with the block's OWN file list")
skill = SKILL.read_text(encoding="utf-8")
check("the evidence block invokes change-inventory.py",
      "change-inventory.py" in skill, "the engine ships but nothing calls it")
check("...via CLAUDE_PLUGIN_ROOT, like the sibling extract-criteria.py call",
      'CLAUDE_PLUGIN_ROOT}/skills/audit-coverage/lib/change-inventory.py' in skill,
      "the call must resolve through the plugin root, not a bare relative path")
# THE fan-out guard. The inventory must annotate the SAME hunks the diff shows. If it grew
# its own source-file filter, the two could disagree and Stage 1 would be told to account
# for rows that are not in its evidence (or worse, not told about rows that are).
#
# STRICT FORM ONLY. The first version carried an `or` fallback that accepted a SKILL.md
# merely mentioning "$FILES" somewhere and change-inventory.py somewhere, with no piping
# relationship between them — i.e. it would have passed in exactly the refactor this check
# exists to catch. It was also dead, since the strict arm matches today; a dead lenient
# fallback is a check that degrades silently the moment it starts mattering.
check("the inventory is fed $FILES through a pipe, so there is exactly one source-file filter",
      'printf \'%s\\n\' "$FILES" | python3 "${CLAUDE_PLUGIN_ROOT}/skills/audit-coverage/lib/change-inventory.py"' in skill,
      "the piping relationship is what guarantees one filter; a co-mention does not")
check("the engine really contains no second source-file filter (paired positive)",
      "sourceFilePatterns" not in ENGINE.read_text(encoding="utf-8")
      and "--files-from" in ENGINE.read_text(encoding="utf-8"),
      "a filter inside the engine would silently diverge from the block's")

# ===========================================================================
print()
if _failures:
    print(f"{len(_failures)} check(s) FAILED:")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)
print("All audit-coverage inventory evals passed.")
