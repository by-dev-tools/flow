#!/usr/bin/env python3
"""Eval harness for the worker->orchestrator message-label convention (FB-0132).

Pins the prose contract `[w:<short-name>] <STATUS>` -- the opener every worker puts
on a message back to the orchestrator seat -- at EVERY site that states the ping
contract, plus the `/flow:orchestrate` status-only digest path that the same work
added.

Run:  python3 plugins/flow/evals/run_ping_label_evals.py

WHY THE SITE LIST IS DERIVED *AND* PINNED -- it takes both
----------------------------------------------------------
Four files state this one contract, which is the FB-0010 fan-out class: a value in N
files held together by author memory. A hardcoded list of four paths would be the bug
rather than the defense -- a fifth site added later would state the contract without
the label and nothing would notice.

So `contract_sites()` GREPS for the contract's own trigger phrase ("on a blocking
question" -- the middle of the three triggers the brief instructs a worker to report
on) across the three surfaces that DEFINE the contract, and every file it finds must
carry the convention. `dev-docs/` is excluded on purpose: plan, history and feedback
entries quote the contract as a narrative record of a decision, and a record of what
was decided is not a statement of the live rule. Adding a contract surface under
`plugins/flow/` or `research/` is what must fail, and does.

Measured at the COMPOSED layer, not just in a predicate (general.md § Consistency item 4,
third corollary): a throwaway `research/__probe-fifth-site.md` stating only the trigger
phrase was picked up as a fifth site and failed 6 of the 7 per-site checks by name; it goes
back to green on removal. The grep is therefore known to be able to *find* a new site, which
is the half of this design that a mutation of existing text cannot demonstrate.

**But a derived sweep alone is only half a check, and the missing half was MEASURED on this
harness before it shipped.** A grep-derived list protects against a site being ADDED without
the convention. It cannot protect against a site DROPPING OUT, because a file that stops
matching the trigger phrase stops being a site -- and its seven per-site checks leave with it.
Reworded `plugins/flow/docs/workflow.md`'s trigger to "when blocked", deleted the convention
paragraph from it outright, and added one conforming fifth site under `research/`: the harness
printed `passed: 0 failing check(s)` while the shipped consumer doc carried none of the
contract. A `len(sites) >= 4` floor does not catch it either -- the fifth site satisfies the
count -- and that floor is itself the hardcoded number this design claims to avoid.

That is general.md § Consistency item 3 exactly: the sweep passed both when the contract was
honored *and* when a site quietly stopped stating it. So the list is **both** halves, unioned:

  * `KNOWN_SITES` -- the sites that state the contract today, pinned explicitly. Every one must
    still be found by the sweep. A dropout therefore fails as a REMOVAL, loudly, naming the
    path; retiring a site is a deliberate edit to this tuple, not something a reword can do.
  * `contract_sites()` -- the derived sweep, which catches ADDITIONS the pin cannot know about.

Neither half is redundant and neither is sufficient. If you retire a contract site on purpose,
delete it from `KNOWN_SITES` in the same commit, which is the edit that makes the intent legible.

INSTRUMENT VALIDATION (general.md § Consistency item 4)
------------------------------------------------------
Every assertion here is a substring/shape check over shipped prose, so the whole
harness could silently degrade to "clean" -- a typo in a canonical string would make
it unfalsifiable, not failing. Arm 4 therefore runs the same predicates against MUTATED
copies of the real text (template removed, a status renamed, a fifth status added, a trigger
unmapped, a trigger mapped twice, the mapping reworded, uniqueness dropped, the firewall rule
dropped, the PR link unlinked, a doc-slot write added) and FAILS if any mutation is still
accepted. It runs on EVERY invocation rather than behind a flag, because CI passes no flags
and a validation step you have to opt into is one that does not run.

DELETION CRITERION
-----------------
Delete this harness when the label convention stops being prose -- i.e. when the dispatch
backend wraps worker messages and the opener is produced mechanically rather than by a worker
following an instruction. At that point the contract is enforced where it happens and pinning
four prose copies is maintaining a shadow of a real mechanism. Also delete if the convention
itself is retired: a harness pinning a withdrawn rule is worse than no harness, because it
makes the rule look live.

WHAT IT COVERS
  sites-derived    -- the sweep is non-vacuous and finds at least every pinned site.
  sites-pinned     -- every KNOWN_SITES path still states the contract (the DROPOUT half;
                      measured bypass without it -- see above).
Every row below is labelled with the check id it actually PRINTS, so a FAIL line can be
grepped straight back to the row that explains it. (The first draft used a second, prettier
naming -- `wall 1`, `store 1` -- which is the FB-0010 fan-out class in a single file.)

  template          -- every site carries the opener's template verbatim.
  mapping           -- every site carries the canonical mapping line VERBATIM; this is what
                       "stated identically at every site" means operationally, and it is also
                       the pin that catches a renamed status.
  status-set-exact  -- the published status set is EXACTLY the four, PARSED OUT OF THE FILE
                       (not out of the MAPPING constant -- the first draft read the constant,
                       which made this check tautological). Adding a fifth fails here.
  no-extra-status   -- paired negative: no `<trigger> -> `STATUS`` pair maps to an unpublished
                       status, and the one token the plan considered and rejected (`STALLED`)
                       appears nowhere. Word-boundary-anchored on the LEFT, because
                       "INSTALLED" ends in "STALLED" and a naive substring check fires on four
                       innocent sentences in this repo.
  triggers          -- all three ping triggers (completion / blocking question / stall) are
                       mapped, each to exactly one status, parsed from the file.
  unique            -- every site states that short-names must be unique across live workers.
  firewall          -- every site states the loopback-in-a-code-span delivery failure.
  orch-skips-5-and-6 -- the status path names steps 5 AND 6 as skipped, with a reason each.
  orch-reuses-2-4   -- it names the derivation it reuses -- the positive paired with the
                       "adds no second derivation" claim.
  orch-stores-nothing -- it states "write nothing" AND carries a deletion criterion.
  orch-pr-hyperlinked -- the digest template hyperlinks PR numbers (field manual § 3).
  orch-writes-no-doc-slot -- no doc-slot write in the status path, asserted by shape: no
                       Write-tool instruction and no shell redirect into a doc slot.
  orch-two-vocabularies-not-unified -- BOTH state sets are named (the closed four-value message
                       set and the six-value digest set), with the reason they differ and an
                       explicit do-not-unify rule pinned in both directions. User direction:
                       keep the derived values, and make the docs say why "so nobody unifies
                       them later" -- so the REASON is pinned, not only the tokens.
  orch-derived-states-marked -- the digest's State column names which values are reported and
                       which derived. Asserts
                       the rule AND its OBSERVANCE in the rendered template (every derived cell
                       carries the dagger, and the footnote exists) -- the prose-only version of
                       this check let the template contradict the rule eleven lines below it.
  orch-gate-vs-silent-both-halves -- both halves of field manual § 8's detector plus the
                       explicit no-default-to-GATE guard. Keyed on the guard's own clause, not
                       on the bare phrase "could not classify", which occurs twice in the
                       section and made the conjunct satisfiable without the guard.
  orch-edge-states-stated -- zero live workers (distinguishing "nothing in flight" from "could
                       not derive"), the nothing-needed case, the dash-for-absent convention,
                       and the opener-less ping.
  orch-needs-you-leads -- the action line precedes the inventory table.
  orch-sanitizes-repo-derived-refs -- the three classification commands single-quote their
                       interpolations and use `grep -F --`, and the section states the
                       reduce-to-[A-Za-z0-9._/-] rule. Pinned because a review MEASURED that
                       stripping the quotes was accepted by every other predicate here -- the
                       one claim with a security consequence was the one with no pin.
  orch-0-section-present -- the status section exists at all; a gate, since an absent section
                       makes every orch check above vacuous.

WHAT IT DELIBERATELY DOES NOT COVER -- read this before treating green as coverage
  * **A worker's actual message.** Nothing wraps worker output, so this harness pins the
    four CONTRACT DOCS and nothing observes whether a worker honored the opener. Green here
    means "the contract is stated identically everywhere it is stated", never "the convention
    is followed".
  * **The RENDERED brief.** `/flow:spawn`'s Contract block is transcribed by a model into
    `.flow/brief-<item>.md`; this pins the skill file, not the brief that reaches a worker.
    A paraphrase at write time breaks the convention and leaves this harness green. Tracked
    in the roadmap -- the fix is a shipped partial the brief is built from.
  * **The firewall drop itself.** A message the channel ate is unobservable from the sending
    end, so `firewall` pins the RULE's presence, not the delivery.
  Stated here rather than left to the deletion criterion to imply, because a reader checking
  what green means looks at the coverage list, not at the retirement condition.
"""

from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
PLUGIN = HERE.parent
REPO = PLUGIN.parent.parent

# ---------------------------------------------------------------- the contract text
# These five strings are the convention. They are written ONCE, here, and asserted
# verbatim at every site -- which is what makes "stated identically" checkable rather
# than a thing a reader has to eyeball across four files.
TEMPLATE = "`[w:<short-name>] <STATUS>`"
MAPPING = (
    "completion → `DONE` · blocking question → `BLOCKED` · stall → `BLOCKED` "
    "(same next action; the body carries the distinction) · parked at a plan gate → `GATE` "
    "· no action needed → `FYI`"
)
UNIQUE = ("Short-names must be unique across live workers — two workers on one label defeats "
          "the convention.")
FIREWALL = ("Report a localhost or loopback health check in **plain text, never inside a code "
            "span** — the message channel's firewall silently drops a message carrying a "
            "loopback URL in backticks, and the identical text without them delivers.")

STATUSES = {"GATE", "DONE", "BLOCKED", "FYI"}
TRIGGERS = ("completion", "blocking question", "stall")

# The trigger phrase that identifies a file as STATING the ping contract.
CONTRACT_PHRASE = "on a blocking question"
# Surfaces that DEFINE the contract. dev-docs/ is excluded -- see the module docstring.
#
# The exclusion is drawn as a DIRECTORY but the rule it stands for is a ROLE ("a statement of
# the live rule", not "a record of a decision"), and the two do not coincide perfectly: the
# research plan below is a design doc carrying dogfood checkmarks, i.e. partly a record. It is
# included anyway, and deliberately, because it declares itself canonical -- its own header
# reads "where any older doc disagrees with this one, this one wins" -- which makes it a live
# rule regardless of its genre. Judge a new surface by that test, not by which directory it
# landed in.
CONTRACT_ROOTS = (
    PLUGIN / "skills",
    PLUGIN / "docs",
    REPO / "research",
)

# The DROPOUT half of the site list (see the module docstring). Pinned paths, relative to the
# repo root. Retiring a contract site means deleting its line here in the same commit.
KNOWN_SITES = (
    "plugins/flow/skills/spawn/SKILL.md",            # the brief -- the operative copy
    "plugins/flow/docs/workflow.md",                 # the shipped consumer doc
    "research/2026-08-23-flow-cloud-workflow-plan.md",   # canonical design, §4.8 rule 6
    "research/orchestrator-field-manual.md",         # operational residue, S3
)

ORCH = PLUGIN / "skills" / "orchestrate" / "SKILL.md"

# The blind spots, as data rather than prose, so the docstring and the clean-pass footer cannot
# disagree. Printed on every green run -- see main().
DOES_NOT_COVER = (
    "a worker honored the opener (nothing wraps worker messages; this pins the contract docs)",
    "the RENDERED brief carries it (this pins the skill file, not .flow/brief-<item>.md)",
    "a message was delivered (a message the channel ate is unobservable from the sending end)",
)

fails = 0


def check(cid, ok, detail=""):
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f"  — {detail}" if detail else ""))
    return ok


def contract_sites() -> list[Path]:
    """Every file on a contract-defining surface that STATES the ping contract."""
    out = []
    for root in CONTRACT_ROOTS:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.md")):
            try:
                if CONTRACT_PHRASE in p.read_text(encoding="utf-8"):
                    out.append(p)
            except OSError:
                continue
    return out


# ------------------------------------------------------------------- the predicates
# Each takes raw text and returns (ok, detail). They are the ONLY place a rule is
# expressed, so the selftest arm (4) can run the identical predicate over mutated text.

def p_template(t):
    """The opener's template, verbatim.

    Deliberately does NOT also check that each status token appears: every one of them is a
    substring of MAPPING, so that half could never fail independently of `p_mapping` -- it only
    doubled the FAIL lines for one typo and forced every status-touching mutation below to name
    two keys (which the first draft got wrong). The statuses stay pinned twice over: verbatim by
    `p_mapping`, and parsed-from-the-text by `p_status_set_exact`.
    """
    return TEMPLATE in t, f"missing {TEMPLATE}"


def p_mapping(t):
    """The canonical mapping, compared WHITESPACE-NORMALIZED.

    Not a raw substring test: `MAPPING` is a single-line literal, so a raw test would force
    every site to carry it as one physical line -- and two of the four sites wrap at ~97
    characters, so the pin would have dictated a hard-wrap violation in prose it does not own.
    Normalizing both sides pins the SENTENCE rather than its line breaks, which is the thing
    "stated identically" actually means.
    """
    return _norm(MAPPING) in _norm(t), "canonical mapping line absent or reworded"


# `<trigger> -> `STATUS`` pairs, parsed out of THE FILE -- never out of the MAPPING
# constant above. Reading the constant is what the first draft of this harness did, and
# it made both predicates below tautological: they asserted a property of a literal
# sitting three lines away and would have stayed green over any edit to the shipped
# text. Measured on every site: exactly five pairs, four distinct statuses, so parsing
# the whole normalized file (rather than trying to delimit the clause) is unambiguous.
# BOUNDED repetition, not `[a-z ]*`. The unbounded form is O(n^2) in the length of a
# contiguous lowercase-and-space run, and `mapped_pairs` runs it over a whole file collapsed
# to ONE line. Measured on a pure `[a-z ]` blob: 5KB 118ms / 20KB 1.77s / 80KB 28.1s unbounded,
# against 1ms / 4ms / 16ms bounded. That is reachable in CI -- `ci.yml` runs on `pull_request`,
# and any `.md` under the contract roots containing the trigger phrase becomes a site, so a
# fork PR could burn the runner toward its ceiling on an obviously-failing branch. Five words
# is the cap because the longest real left-hand side is five ("parked at a plan gate");
# verified to parse the IDENTICAL pairs on all four sites before and after.
PAIR = re.compile(r"([a-z]+(?: [a-z]+){0,4}) \u2192 `([A-Z]{2,})`")


def _norm(s):
    """Collapse all whitespace runs to one space.

    Every prose pin below runs through this, so a site is free to wrap a pinned sentence at
    its own file's width. One definition, because a second copy would be the fan-out class.
    """
    return re.sub(r"\s+", " ", s)


# Memoized: three predicates ask the same site's text for the same pairs, and one site is
# 127 KB collapsed to a single line, where PAIR's `[a-z ]*` backtracks hard. Measured 18 calls
# per run, 11 of them on text already seen -- 220ms -> 87ms, same verdict. The decorator rather
# than hoisting the call into test_per_site deliberately: predicates must keep taking RAW TEXT
# so the selftest can run the identical predicate over a mutated copy.
@functools.lru_cache(maxsize=None)
def mapped_pairs(t):
    return PAIR.findall(_norm(t))


def p_status_set_exact(t):
    """The published set is exactly the four -- parsed from the text, not assumed."""
    pairs = mapped_pairs(t)
    if not pairs:
        return False, "no `<trigger> -> `STATUS`` pair found to parse a status set out of"
    found = {s for _, s in pairs}
    return found == STATUSES, f"text publishes {sorted(found)}, expected {sorted(STATUSES)}"


def p_no_extra_status(t):
    """Paired negative, two ways.

    (a) no pair maps a trigger to an unpublished status; (b) the one status the plan
    considered and rejected appears nowhere. (b) is word-boundary-anchored on the LEFT
    because `INSTALLED` ends in `STALLED` -- four innocent sentences in this repo say
    "INSTALLED" and a naive substring check fires on all of them.
    """
    # KNOWN CONSEQUENCE, deliberate: because the scan is over the whole file, a contract site
    # cannot *document* the rejected token either -- writing "a fifth status such as `STALLED`
    # was considered and rejected" into one of the four sites fails this check. That is the
    # intended trade (the four sites state the contract; the reasoning lives in the plan, the
    # history entry and FB-0132), but it is recorded here so the next editor reads the FAIL as
    # the rule working rather than as a contract breach.
    stray_pairs = sorted({s for _, s in mapped_pairs(t)} - STATUSES)
    rejected = sorted({m.group(0) for m in re.finditer(r"(?<![A-Z])STALLED\b", t)})
    bad = stray_pairs + rejected
    return not bad, f"unpublished status token(s): {bad}"


def p_triggers(t):
    """Each of the three ping triggers maps to exactly one status, in the text."""
    pairs = mapped_pairs(t)
    detail = []
    for trig in TRIGGERS:
        # `endswith`, not `==`: at one site the mapping is mid-sentence, so the first
        # pair's left side legitimately carries the leading prose with it.
        hits = {s for lhs, s in pairs if lhs == trig or lhs.endswith(" " + trig)}
        if len(hits) != 1:
            detail.append(f"{trig!r}->{sorted(hits) or 'unmapped'}")
    return not detail, f"trigger(s) not mapped to exactly one status: {detail}"


def p_unique(t):
    # Normalized for the same reason as p_mapping: pin the sentence, not its line breaks.
    return _norm(UNIQUE) in _norm(t), "short-name uniqueness rule absent"


def p_firewall(t):
    return _norm(FIREWALL) in _norm(t), "loopback-in-a-code-span delivery rule absent"


SITE_PREDICATES = {
    "template": p_template,
    "mapping": p_mapping,
    "status-set-exact": p_status_set_exact,
    "no-extra-status": p_no_extra_status,
    "triggers": p_triggers,
    "unique": p_unique,
    "firewall": p_firewall,
}


def status_section(t: str) -> str:
    """The `## 8. status` section of orchestrate/SKILL.md, to end of file or next `## `."""
    # No `(?!#)` guard: `^## ` already requires a space in column 2, so `### ` cannot match it.
    m = re.search(r"^## 8\. `status`.*?$(.*?)(?=^## |\Z)", t, re.M | re.S)
    return m.group(1) if m else ""


def p_orch_skips(sec):
    ok = ("Step 5" in sec and "Step 6" in sec
          and "Skip steps 5 and 6" in sec
          and "points live workers at" in sec
          and "boot setup" in sec)
    return ok, "steps 5/6 not both named as skipped with a reason each"


def p_orch_reuse(sec):
    names_steps = ("steps 2, 3 and 4" in sec or "steps 2-4" in sec or "steps 2–4" in sec)
    ok = names_steps and "no second derivation" in sec
    return ok, "does not name the derivation it reuses"


def p_orch_nostore(sec):
    ok = "Write nothing" in sec and "Deletion criterion" in sec
    return ok, "missing 'write nothing' or a deletion criterion"


def p_orch_prlink(sec):
    ok = bool(re.search(r"\[#\d+\]\(https://[^)]*/pull/\d+\)", sec))
    return ok, "digest template carries no markdown PR link"


def _template_block(sec):
    """The first fenced ```markdown block in the status section -- the digest template.

    This is the artifact a model COPIES, so several predicates below assert against it rather
    than against the prose that describes it.
    """
    m = re.search(r"```markdown\n([\s\S]*?)```", sec)
    return m.group(1) if m else ""


def p_orch_sanitizes_refs(sec):
    """The injection fix is pinned, not just present.

    Measured during review: removing the single quotes from all three classification commands
    AND deleting the reduce-to-[A-Za-z0-9._/-] instruction were BOTH accepted by every other
    predicate here. It was the one claim in this section with a security consequence and the
    only one with no pin -- which is the inverse of how the pins should be distributed.
    """
    fence = re.search(r"```sh\n([\s\S]*?)```", sec)
    cmds = fence.group(1) if fence else ""
    quoted = cmds.count("'<") >= 2 and "'origin/<branch>'" in cmds
    ok = (quoted
          and "grep -F --" in cmds
          and "[A-Za-z0-9._/-]" in sec
          and "REPOSITORY-DERIVED" in sec)
    return ok, ("the classification commands do not sanitize+quote repository-derived refs "
                f"(quoted={quoted} grep-F={'grep -F --' in cmds} "
                f"reduction-stated={'[A-Za-z0-9._/-]' in sec})")


def p_orch_two_vocabularies(sec):
    """Both state sets are named explicitly, with the reason they differ and a do-not-unify rule.

    User direction, 2026-10-04: keep the derived `WORKING`/`SILENT` values, and make the docs
    name BOTH sets and say WHY they differ "so nobody 'unifies' them later." That instruction is
    about a future editor, so the thing to pin is the REASON and the prohibition -- not just the
    tokens. A section that listed the values without the argument would satisfy a token grep and
    still invite the collapse.

    Pinned in both directions, because the regression has two forms: adding a derived value to
    the closed MESSAGE contract, and deleting a derived value from the DIGEST.
    """
    named_both = "THE MESSAGE SET" in sec and "THE DIGEST SET" in sec
    closure = "exactly four, closed, never a fifth" in sec
    reason = ("different sets by construction" in sec
              and "not a duplication to be deduplicated" in sec)
    both_directions = ("adding a derived value to the MESSAGE contract is wrong" in sec
                       and "removing a derived value from" in sec)
    why_silent = "no turn in which to ping" in sec and "idle" in sec
    ok = named_both and closure and reason and both_directions and why_silent
    return ok, ("the two state vocabularies are not both named with the reason they differ "
                f"(named={named_both} closure={closure} reason={reason} "
                f"both-directions={both_directions} why-SILENT-matters={why_silent})")


def p_orch_derived_marked(sec):
    """The digest's State column is a SUPERSET of the message vocabulary, and says which is which.

    Added after a review found the digest reusing the four message statuses for a column that
    also has to describe workers who have said nothing -- so there was no value for "working
    normally" and `FYI` silently meant both "fine" and "possibly dead". The fix introduces
    derived values, which is only safe if the digest states that they are derived and marks
    them; otherwise the human cannot tell a worker's claim from the agent's inference.
    """
    stated = ("THE MESSAGE SET" in sec and "THE DIGEST SET" in sec
              and "WORKING" in sec and "SILENT" in sec
              and "Reported" in sec and "Derived" in sec
              and "Mark every derived cell" in sec)
    # The OBSERVANCE half, not just the statement. The first version of this predicate greped
    # only the prose above, and three review lenses independently measured the consequence: the
    # rendered template carried `WORKING` with NO marker and no footnote, contradicting the rule
    # eleven lines below it -- and this check stayed green. A model composing a digest copies the
    # TEMPLATE, so the template is the spec; asserting the rule's presence while its own example
    # breaks it is general.md § Consistency item 3 (the prohibition is satisfiable by the thing
    # it protects being wrong).
    tmpl = _template_block(sec)
    rows = [r for r in tmpl.splitlines() if r.startswith("| ") and "|" in r[2:]]
    derived_cells_marked = all(
        "\u2020" in r for r in rows
        if re.search(r"\|\s*(WORKING|SILENT)\u2020?\s*\|", r))
    has_footnote = "\u2020 derived" in tmpl
    saw_a_derived_row = any(re.search(r"\|\s*(WORKING|SILENT)\u2020?\s*\|", r) for r in rows)
    ok = stated and saw_a_derived_row and derived_cells_marked and has_footnote
    return ok, ("digest does not distinguish reported from derived State values "
                f"(stated={stated} template-has-a-derived-row={saw_a_derived_row} "
                f"every-derived-cell-marked={derived_cells_marked} footnote={has_footnote})")


def p_orch_gate_vs_silent(sec):
    """Both halves of field manual §8's detector, not just the reassuring one.

    Carrying only the GATE shape makes a dead worker render as a parked one -- the exact
    conflation §8 records as costing three chases in one program.
    """
    # NOT keyed on the bare phrase "could not classify": that literal ALSO appears in the
    # shell-safety paragraph, so the conjunct was satisfied twice over and deleting this entire
    # bullet measured green. Keyed on the no-default sentence's own distinguishing clause.
    ok = ("no branch on the remote at all" in sec
          and "could not classify" in sec
          and "defaulting to it is how the asymmetry bites" in sec)
    return ok, ("the gated-vs-silent test is missing a half: needs the trouble shape "
                "AND the explicit no-default-to-GATE guard")


def p_orch_edge_states(sec):
    # The absent-value conjunct was NAMED in this detail string and asserted nowhere -- measured:
    # deleting the dash-convention bullet was accepted. A failure message that names a rule the
    # predicate does not check is worse than silence; it tells the next reader it is covered.
    ok = ("Zero live workers" in sec
          and "I could not derive the fleet" in sec
          and "Nothing needs you" in sec
          and "An absent value in any cell" in sec
          and "A ping with no opener" in sec)
    return ok, ("digest edge states unspecified (zero live / nothing needed / absent value / "
                "opener-less ping)")


def p_orch_needs_you_first(sec):
    """`Needs you` must precede the table -- step 7 rule 4 applied to this surface."""
    i_needs, i_table = sec.find("**Needs you:**"), sec.find("| Worker | State")
    ok = 0 <= i_needs < i_table
    return ok, "the action line does not come before the inventory table"


def p_orch_no_write(sec):
    """Shape check: the section must not instruct a write to a doc slot."""
    bad = [pat for pat in (r"Write tool", r">\s*\$?\{?(?:planPath|roadmapPath)",
                           r">>?\s*dev-docs/", r"tee\s+dev-docs/")
           if re.search(pat, sec)]
    return not bad, f"status path appears to write: {bad}"


ORCH_PREDICATES = {
    "skips-5-and-6": p_orch_skips,
    "reuses-2-4": p_orch_reuse,
    "stores-nothing": p_orch_nostore,
    "pr-hyperlinked": p_orch_prlink,
    "writes-no-doc-slot": p_orch_no_write,
    "derived-states-marked": p_orch_derived_marked,
    "gate-vs-silent-both-halves": p_orch_gate_vs_silent,
    "edge-states-stated": p_orch_edge_states,
    "needs-you-leads": p_orch_needs_you_first,
    "sanitizes-repo-derived-refs": p_orch_sanitizes_refs,
    "two-vocabularies-not-unified": p_orch_two_vocabularies,
}


# ------------------------------------------------------------------------ the arms
def test_sites() -> list[Path]:
    print("\n1. SITES -- a derived sweep UNIONED with a pinned set (both halves, see docstring)")
    sites = contract_sites()
    rel = [str(p.relative_to(REPO)) for p in sites]
    for r in rel:
        print(f"      site: {r}{'' if r in KNOWN_SITES else '   (not pinned -- a NEW site)'}")

    # The ADDITIONS half. Non-vacuity is asserted against the pin rather than a literal count:
    # `>= 4` would be the hardcoded number this design exists to avoid, and it passes when one
    # site drops out and another appears.
    check("sites-derived-nonvacuous", len(sites) >= len(KNOWN_SITES),
          f"grep for {CONTRACT_PHRASE!r} across "
          f"{[str(r.relative_to(REPO)) for r in CONTRACT_ROOTS]} found {len(sites)} site(s): "
          f"{rel} -- fewer than the {len(KNOWN_SITES)} pinned, so the sweep is under-reading "
          "and every per-site check below is weaker than it looks.")

    # The DROPOUT half, and the one that was measured missing. A pinned site that the sweep no
    # longer finds has stopped stating the contract -- which the derived list reports as
    # "nothing to check" rather than as a failure.
    for known in KNOWN_SITES:
        found = known in rel
        on_disk = (REPO / known).is_file()
        check(f"sites-pinned:{known}", found,
              ("file is MISSING from disk" if not on_disk else
               f"file exists but no longer contains {CONTRACT_PHRASE!r}, so it dropped out of "
               "the sweep and its per-site checks did NOT run. Either restore the contract "
               "statement, or retire the site by deleting it from KNOWN_SITES -- do not let a "
               "reword silently remove a contract surface."))

    # Union: the pinned sites are checked even when the sweep missed them, so a dropout fails
    # its per-site predicates too rather than only this one line.
    for known in KNOWN_SITES:
        pk = REPO / known
        if pk.is_file() and pk not in sites:
            sites.append(pk)
    return sites


def test_per_site(sites: list[Path]) -> None:
    print("\n2. PER SITE -- the convention, stated identically")
    for p in sites:
        rel = str(p.relative_to(REPO))
        t = p.read_text(encoding="utf-8")
        for name, pred in SITE_PREDICATES.items():
            ok, detail = pred(t)
            check(f"{name}:{rel}", ok, detail)


def test_docstring_covers_every_check() -> None:
    """Every predicate this file RUNS must have a row in WHAT IT COVERS.

    The docstring claims, in its own words, that "every row below is labelled with the check id
    it actually PRINTS, so a FAIL line can be grepped straight back to the row that explains
    it." That claim had already gone false once: four ORCH predicates were added and the block
    was not, so a third of the orch ids printed with nothing explaining them -- the FB-0010
    fan-out class inside a single file, in the file whose docstring names that class.

    Asserting it mechanically is the only version of this that stays true, because the
    alternative is remembering. Keyed on the predicate REGISTRIES, so adding a predicate without
    documenting it fails here rather than drifting.
    """
    print("\n5. DOCSTRING -- every check that prints has a row explaining it")
    doc = __doc__ or ""
    for name in sorted(SITE_PREDICATES):
        check(f"documented:{name}", f"  {name}" in doc or f"\n  {name} " in doc,
              f"predicate {name!r} runs but WHAT IT COVERS has no row for it")
    for name in sorted(ORCH_PREDICATES):
        check(f"documented:orch-{name}", f"orch-{name}" in doc,
              f"predicate orch-{name!r} runs but WHAT IT COVERS has no row for it")
    check("documented:orch-0-section-present", "orch-0-section-present" in doc,
          "the section-present gate prints but is undocumented")


def test_orchestrate() -> None:
    print("\n3. ORCHESTRATE -- the status-only digest path")
    t = ORCH.read_text(encoding="utf-8")
    sec = status_section(t)
    if not check("orch-0-section-present", bool(sec.strip()),
                 "no '## 8. `status`' section found -- every check below is vacuous"):
        return
    for name, pred in ORCH_PREDICATES.items():
        ok, detail = pred(sec)
        check(f"orch-{name}", ok, detail)


# --------------------------------------------------------------------- SELFTEST
MUTATIONS = {
    # (label, mutate-fn, the predicate keys that MUST reject the mutation)
    "label-template-removed": (lambda t: t.replace(TEMPLATE, "`<worker>/<state>`"),
                               ["template"]),
    # Keyed on `mapping` ALONE now that p_template no longer re-checks the status tokens --
    # the verbatim mapping line is what a renamed status actually breaks.
    "a-status-deleted": (lambda t: t.replace("`FYI`", "`INFO`"), ["mapping"]),
    # BOTH detectors named on purpose: the stray PAIR trips status-set-exact, and the one
    # token the plan considered and rejected trips the word-boundary scan. They are not the
    # same assertion, and a mutation only one of them caught would be a coverage hole.
    "fifth-status-added": (
        lambda t: t.replace(MAPPING, MAPPING + " · stalled → `STALLED`"),
        ["status-set-exact", "no-extra-status"]),
    # The rewording leaves every pair intact, so the IDENTITY check is its only honest
    # detector -- listing status-set-exact/triggers here was the first draft's error and
    # the selftest caught it.
    "mapping-reworded": (
        lambda t: t.replace("(same next action; the body carries the distinction)", "(see above)"),
        ["mapping"]),
    "a-trigger-unmapped": (
        lambda t: t.replace("\u00b7 stall \u2192 `BLOCKED` ", ""),
        ["mapping", "triggers"]),
    "trigger-mapped-twice": (
        lambda t: t.replace("\u00b7 stall \u2192 `BLOCKED` ",
                            "\u00b7 stall \u2192 `BLOCKED` \u00b7 stall \u2192 `GATE` "),
        ["mapping", "triggers"]),
    "uniqueness-dropped": (lambda t: t.replace(UNIQUE, ""), ["unique"]),
    "firewall-dropped": (lambda t: t.replace(FIREWALL, ""), ["firewall"]),
}

ORCH_MUTATIONS = {
    "skip-rationale-dropped": (lambda s: s.replace("Skip steps 5 and 6", "Also run 5 and 6"),
                               ["skips-5-and-6"]),
    "reuse-claim-dropped": (lambda s: s.replace("no second derivation", "fresh derivation"),
                            ["reuses-2-4"]),
    "store-rule-dropped": (lambda s: s.replace("Write nothing", "Write the table"),
                           ["stores-nothing"]),
    "pr-link-unlinked": (lambda s: re.sub(r"\[#(\d+)\]\(https://[^)]*/pull/\d+\)", r"#\1", s),
                         ["pr-hyperlinked"]),
    "writes-a-doc-slot": (lambda s: s + "\nWrite the digest with the Write tool to dev-docs/.\n",
                          ["writes-no-doc-slot"]),
    "derived-marker-dropped": (lambda s: s.replace("Mark every derived cell", "Cells are cells"),
                               ["derived-states-marked"]),
    "silent-half-dropped": (lambda s: s.replace("no branch on the remote at all", "it is quiet"),
                            ["gate-vs-silent-both-halves"]),
    "edge-states-dropped": (lambda s: s.replace("Zero live workers", "Some workers"),
                            ["edge-states-stated"]),
    # Moves the action line BELOW the table, which is the ordering the review corrected.
    "quotes-stripped": (
        lambda s: s.replace("'<branch>'", "<branch>").replace("'origin/<branch>'", "origin/<branch>")
                   .replace("'<slug>'", "<slug>"),
        ["sanitizes-repo-derived-refs"]),
    "reduction-instruction-dropped": (
        lambda s: s.replace("[A-Za-z0-9._/-]", "whatever you like"),
        ["sanitizes-repo-derived-refs"]),
    # The regression has two directions and each must be caught. Deleting a derived value from
    # the digest is the one a well-meaning "cleanup" produces.
    "message-set-opened": (
        lambda s: s.replace("exactly four, closed, never a fifth", "four or so"),
        ["two-vocabularies-not-unified"]),
    "unify-rationale-dropped": (
        lambda s: s.replace("not a duplication to be deduplicated", "much the same thing"),
        ["two-vocabularies-not-unified"]),
    "do-not-unify-rule-dropped": (
        lambda s: s.replace("adding a derived value to the MESSAGE contract is wrong",
                            "the sets may be aligned"),
        ["two-vocabularies-not-unified"]),
    "why-silent-matters-dropped": (
        lambda s: s.replace("no turn in which to ping", "less to say"),
        ["two-vocabularies-not-unified"]),
    "derived-marker-stripped-from-template": (
        lambda s: s.replace("WORKING\u2020", "WORKING"),
        ["derived-states-marked"]),
    "footnote-dropped": (
        lambda s: s.replace("\u2020 derived by me", "x derived by me"),
        ["derived-states-marked"]),
    "no-default-guard-dropped": (
        lambda s: s.replace("defaulting to it is how the asymmetry bites", "it is usually right"),
        ["gate-vs-silent-both-halves"]),
    "dash-convention-dropped": (
        lambda s: s.replace("An absent value in any cell", "Some value in a cell"),
        ["edge-states-stated"]),
    "needs-you-demoted": (
        lambda s: s.replace("**Needs you:**", "**NEEDS-YOU-MOVED:**", 1) + "\n**Needs you:** x\n",
        ["needs-you-leads"]),
}


def test_selftest(sites: list[Path]) -> None:
    print("\n4. SELFTEST -- every predicate must REJECT a mutated copy of the real text")
    # `sites` is PASSED IN, not re-derived: a second call to contract_sites() would be a
    # second independent derivation of the one list this module argues must have a single
    # source, and it re-read every markdown file to produce the same answer.
    if not check("selftest-0-have-a-site", bool(sites), "nothing to mutate"):
        return
    # Mutate the richest site: the one carrying every canonical string.
    base = base_rel = None
    for p in sites:
        t = p.read_text(encoding="utf-8")
        if all(pred(t)[0] for pred in SITE_PREDICATES.values()):
            base, base_rel = t, str(p.relative_to(REPO))
            break
    if not check("selftest-0-clean-baseline", base is not None,
                 "no site currently satisfies every predicate, so a mutation run cannot "
                 "distinguish 'the mutation was caught' from 'it was already failing'"):
        return
    print(f"      baseline: {base_rel}")
    for label, (mutate, must_reject) in sorted(MUTATIONS.items()):
        mutated = mutate(base)
        check(f"selftest-mutation-changed-text:{label}", mutated != base,
              "the mutation was a no-op -- it proves nothing about the predicate")
        for key in must_reject:
            ok, _ = SITE_PREDICATES[key](mutated)
            check(f"selftest:{label}->{key}-rejects", not ok,
                  f"predicate {key!r} ACCEPTED mutation {label!r} -- it cannot fail, so its "
                  "green result above is not evidence")

    sec = status_section(ORCH.read_text(encoding="utf-8"))
    # Same guard the site arm gets above, and for the same reason: with an empty section every
    # ORCH predicate returns False, so every `not ok` rejection below would pass VACUOUSLY --
    # "the mutation was caught" and "there was nothing to mutate" would render identically.
    if not check("selftest-0-orch-baseline", bool(sec.strip()),
                 "no status section to mutate, so the rejections below would prove nothing"):
        return
    for label, (mutate, must_reject) in sorted(ORCH_MUTATIONS.items()):
        mutated = mutate(sec)
        check(f"selftest-mutation-changed-text:{label}", mutated != sec, "no-op mutation")
        for key in must_reject:
            ok, _ = ORCH_PREDICATES[key](mutated)
            check(f"selftest:{label}->{key}-rejects", not ok,
                  f"predicate {key!r} ACCEPTED mutation {label!r}")


def main() -> int:
    sites = test_sites()
    test_per_site(sites)
    test_orchestrate()
    # The selftest runs ALWAYS, never behind a flag. A validation step you have to remember
    # to pass a flag for is a validation step that does not run in CI -- and CI passes no
    # flags. Hence no `--selftest` option: it would have been a flag whose only effect was
    # to say it had no effect.
    test_docstring_covers_every_check()
    test_selftest(sites)
    print(f"\n{'passed' if fails == 0 else 'FAILED'}: {fails} failing check(s)")
    if fails == 0:
        # The docstring's blind-spot list reaches only a reader who opens this file; green
        # reaches everyone, in a CI log. One definition, both readers.
        print("green means: the convention is stated identically at every contract site.")
        for line in DOES_NOT_COVER:
            print(f"  it does NOT mean: {line}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
