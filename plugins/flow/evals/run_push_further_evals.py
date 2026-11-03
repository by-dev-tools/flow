#!/usr/bin/env python3
"""Regression eval: the push-further lens can never hold up a PR (FB-0141).

The contract, in Ben's words: "i dont want a regular feature to get held up in
staff review because it doesn't have fidgetability - not every single thing in
an app can have that." Before this harness the guarantee held only by
construction (the lens has no BLOCKER bucket) and was written down nowhere, so
an edit giving the lens a blocking verdict would have passed silently.

What is pinned, each with its own mutation in --selftest:

  buckets-exact   The labels in the lens's output-format line, AND the bucket
                  headings in its bucket list (the part a model actually reads
                  when choosing), are each EXACTLY the three non-blocking buckets. Allow-list polarity, on purpose:
                  a new label fails whatever it is called, so "must-fix" is
                  caught as surely as "BLOCKER" (general.md item 4, FB-0136's
                  polarity lesson, a blacklist would default to the dangerous
                  answer).
  triage-never-blocks
                  In /flow:staff-review's triage, no bucket name appears on the
                  BLOCKER line. Paired with:
  triage-routes-every-bucket
                  every bucket appears on some non-BLOCKER triage line, so
                  deleting the buckets from triage cannot turn the negative
                  green (general.md item 3).
  brief-never-blocks
                  /flow:review-brief's non-blocking class names push-further.
  absence-rule    The lens states that a missing quality the surface doesn't
                  call for is not a finding, and that it never blocks. This one
                  is prompt text by nature: the sentence IS the mechanism a
                  model reads, so presence of the rule is the decision.
  session-pointer The future-exploration bucket names the deep-dives session for
                  interaction-feel questions (exact name, with a closing
                  boundary) and its install line, and no other bucket mentions
                  deep-dives at all: it is a routing hint, not a fourth bucket.
  lens-b-buckets-exact, lens-b-absence-rule
                  The same two contracts for lens-experience's Lens B, which
                  runs push-further at the brief/plan gate with its own labels.

Every run also runs the selftest: each check must go red under its own
mutation, or the harness fails. Offline, stdlib only. Run:
    python3 plugins/flow/evals/run_push_further_evals.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOW = HERE.parent
LENS = FLOW / "agents" / "lens-push-further.md"
STAFF = FLOW / "skills" / "staff-review" / "SKILL.md"
BRIEF = FLOW / "skills" / "review-brief" / "SKILL.md"
EXPERIENCE = FLOW / "agents" / "lens-experience.md"

BUCKETS = {"inline-cheap", "roadmap-concrete", "future-exploration"}
LENS_B_BUCKETS = {"artifact-revision", "prototype-target", "future-exploration"}
FORMAT_LINE = re.compile(r"^\[push-further / [^\]]+\]$", re.M)
ABSENCE_RULE = "doesn't call for is not a finding"
SESSION_CMD = "/deep-dives:puckett-uncommon-care"
SESSION_INSTALL = "/plugin install deep-dives@flow"
TRIAGE_LINE = re.compile(r"^- \*\*(?P<head>[^\n]*?)\*\*(?P<rest>[^\n]*)$", re.M)


def triage_block(staff: str) -> str:
    m = re.search(r"^## 4\. Triage\n(.*?)^## ", staff, re.M | re.S)
    return m.group(1) if m else ""


def section(text: str, heading: str, stop: str = r"#{2,3} ") -> str:
    """Body under the first heading starting with `heading`, up to the next `stop` heading."""
    m = re.search(rf"^{re.escape(heading)}[^\n]*\n(.*?)(?=^{stop}|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def labels_exact(text: str, bucket_heading: str, want: set[str]) -> tuple[bool, str]:
    """Both the ONE output-format line and the bucket list equal `want` (allow-list polarity)."""
    fmt = FORMAT_LINE.findall(text)
    labels = set(re.findall(r"push-further / ([\w-]+)", fmt[0])) if len(fmt) == 1 else set()
    listed = set(re.findall(r"^- \*\*([\w-]+)\*\*", section(text, bucket_heading), re.M))
    return (labels == want and listed == want,
            f"format lines={len(fmt)}, format labels={sorted(labels)}, "
            f"bucket list={sorted(listed)}, want {sorted(want)}")


def evaluate(lens: str, staff: str, brief: str, experience: str) -> dict[str, tuple[bool, str]]:
    """Every check by name -> (passed, detail). Pure, so the selftest can mutate inputs."""
    r: dict[str, tuple[bool, str]] = {}
    r["buckets-exact"] = labels_exact(lens, "## Findings buckets", BUCKETS)

    lines = [(m["head"], m["head"] + m["rest"]) for m in TRIAGE_LINE.finditer(triage_block(staff))]
    blocker = [full for head, full in lines if "BLOCKER" in head]
    others = [full for head, full in lines if "BLOCKER" not in head]
    on_blocker = sorted(b for b in BUCKETS if any(b in line for line in blocker))
    r["triage-never-blocks"] = (bool(blocker) and not on_blocker,
                                f"BLOCKER lines found={len(blocker)}, buckets on it={on_blocker}")
    unrouted = sorted(b for b in BUCKETS if not any(b in line for line in others))
    r["triage-routes-every-bucket"] = (not unrouted,
                                       f"buckets missing from non-blocking triage: {unrouted}")

    nb = [line for line in brief.splitlines() if "captured, non-blocking" in line]
    r["brief-never-blocks"] = (any("push-further" in line and "never blocks" in line for line in nb),
                               f"non-blocking lines naming push-further: {len(nb)}")

    r["absence-rule"] = ("You never block" in lens and ABSENCE_RULE in lens,
                         "lens must state it never blocks and that an uncalled-for "
                         "missing quality is not a finding")

    bullets = re.findall(r"^- \*\*([\w-]+)\*\*(.*)$", section(lens, "## Findings buckets"), re.M)
    fx = " ".join(v for k, v in bullets if k == "future-exploration")
    # Exact name: a closing boundary, so "/deep-dives:puckett-uncommon-care-v2" does not count.
    named = re.search(re.escape(SESSION_CMD) + r"(?![\w-])", fx) is not None
    # Leak marker is the plugin name, not the command: any spelling of the pointer counts.
    elsewhere = sorted({k for k, v in bullets if k != "future-exploration" and "deep-dives" in v})
    r["session-pointer"] = (named and SESSION_INSTALL in fx and not elsewhere,
                            f"future-exploration names session={named}, "
                            f"install={SESSION_INSTALL in fx}; also in other buckets: {elsewhere}")

    lens_b = section(experience, "## Lens B", stop="## ")
    r["lens-b-buckets-exact"] = labels_exact(lens_b, "### Buckets", LENS_B_BUCKETS)
    r["lens-b-absence-rule"] = ("**never blocks**" in lens_b and ABSENCE_RULE in lens_b,
                                "lens-experience Lens B must state it never blocks and that an "
                                "uncalled-for missing quality is not a finding")
    return r


def selftest(lens: str, staff: str, brief: str, experience: str) -> list[str]:
    """Each mutation must turn ITS check red (FB-0136: one mutation per assertion, and a
    check asserting two things gets a mutation for each)."""
    fmt = FORMAT_LINE.search(lens).group(0)
    fmt_b = FORMAT_LINE.search(section(experience, "## Lens B", stop="## ")).group(0)
    blocker_line = next(line for line in triage_block(staff).splitlines()
                        if line.startswith("- **BLOCKER**"))
    # A new bucket that shares no token with BLOCKER: proves the allow-list, not a blacklist.
    new_bucket = "- **must-fix** — holds the PR until addressed.\n"
    L, S, B, E = lens, staff, brief, experience
    mutations = [
        ("buckets-exact", "new label in the format line",
         (L.replace(fmt, fmt[:-1] + " | push-further / must-fix]"), S, B, E)),
        ("buckets-exact", "new bucket in the bucket list only",
         (L.replace("- **inline-cheap**", new_bucket + "- **inline-cheap**", 1), S, B, E)),
        ("triage-never-blocks", "a bucket on the BLOCKER line",
         (L, S.replace(blocker_line, blocker_line + " Includes push-further future-exploration."), B, E)),
        ("triage-routes-every-bucket", "a bucket dropped from triage",
         (L, S.replace("**future-exploration**", "**open-question**"), B, E)),
        ("brief-never-blocks", "review-brief may block",
         (L, S, B.replace("never blocks", "may block"), E)),
        ("absence-rule", "never-block sentence removed",
         (L.replace("You never block", "You rarely block"), S, B, E)),
        ("absence-rule", "not-a-finding sentence removed",
         (L.replace(ABSENCE_RULE, "lacks is a finding"), S, B, E)),
        ("session-pointer", "session command misspelled",
         (L.replace(SESSION_CMD, "/deep-dives:uncommon-care"), S, B, E)),
        ("session-pointer", "install line removed",
         (L.replace(SESSION_INSTALL, "the plugin's install"), S, B, E)),
        ("session-pointer", "session name suffixed",
         (L.replace(SESSION_CMD, SESSION_CMD + "-v2"), S, B, E)),
        # Shares no text with SESSION_CMD: the leak check must not depend on one spelling.
        ("session-pointer", "a differently-worded pointer leaks into another bucket",
         (L.replace("- **inline-cheap** —", "- **inline-cheap** — or try the deep-dives session —", 1), S, B, E)),
        ("session-pointer", "a duplicate bucket bullet carries the pointer",
         (L.replace("- **inline-cheap** —", "- **inline-cheap** — see deep-dives —\n- **inline-cheap** —", 1), S, B, E)),
        ("lens-b-buckets-exact", "new label in Lens B's format line",
         (L, S, B, E.replace(fmt_b, fmt_b[:-1] + " | push-further / gate]"))),
        ("lens-b-buckets-exact", "new bucket in Lens B's bucket list only",
         (L, S, B, E.replace("- **artifact-revision**", new_bucket + "- **artifact-revision**", 1))),
        ("lens-b-absence-rule", "Lens B never-block sentence removed",
         (L, S, B, E.replace("**never blocks**", "**rarely blocks**"))),
        ("lens-b-absence-rule", "Lens B rule moved out of Lens B",
         (L, S, B, E.replace("Like `lens-push-further`, this lens **never blocks**", "Like the other lens, it does what it does")
                    + "\n## Elsewhere\nThis lens **never blocks**; a quality it " + ABSENCE_RULE + ".\n")),
    ]
    return [f"{name} ({why})" for name, why, args in mutations if evaluate(*args)[name][0]]


def main() -> int:
    paths = (LENS, STAFF, BRIEF, EXPERIENCE)
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        print(f"[push-further] FAIL — missing: {missing}")
        return 1
    texts = [p.read_text(encoding="utf-8") for p in paths]
    results = evaluate(*texts)
    failed = {k: d for k, (ok, d) in results.items() if not ok}
    for k, d in failed.items():
        print(f"  - {k}: {d}")
    # Only meaningful over a green tree: mutating an already-failing input proves nothing.
    dead = [] if failed else selftest(*texts)
    for k in dead:
        print(f"  - selftest: {k} stayed green under its own mutation (a check that cannot fail)")
    if failed or dead:
        print(f"[push-further] FAIL — {len(failed)} of {len(results)} checks failed, "
              f"{len(dead)} dead under mutation")
        return 1
    print(f"[push-further] PASS — {len(results)} checks; every mutation caught")
    return 0


if __name__ == "__main__":
    sys.exit(main())
