#!/usr/bin/env python3
"""Eval harness for pr-coherence.py — the deterministic body↔draft coherence +
read-back engine behind FB-0067 (stale NOT-READY manifest on a ready PR).

Pins the coherence invariant the acceptance criteria name:

  manifest-present-on-ready-PR  ⇒ FAIL   (the recurring bug)
  manifest-absent-on-ready-PR   ⇒ PASS
  manifest-present-on-draft     ⇒ PASS

plus marker/heading detection parity (either token trips it), and the read-back
subcommand (expect present, forbid absent, draft-state match, coherence backstop).

Explicit body strings + --is-draft flags — no git/gh dependency. Stdlib only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "ship" / "lib" / "pr-coherence.py"

MARKER = "<!-- flow:not-ready-manifest -->"
HEADING = "🚫 NOT READY TO MERGE"

READY_WITH_MANIFEST = f"""## {HEADING} — unresolved blockers
{MARKER}
- [security] leaked token — needs: secret rotation
<!-- /flow:not-ready-manifest -->

## Summary
- does a thing
"""

READY_CLEAN = """## Summary
- does a thing

## Test plan
- [x] it works
"""

DRAFT_WITH_MANIFEST = READY_WITH_MANIFEST  # same body, but the PR IS a draft
HEADING_ONLY_READY = f"## {HEADING} — unresolved blockers\n\n## Summary\n- x\n"
MARKER_ONLY_READY = f"{MARKER}\n\n## Summary\n- x\n"

# --- FB-0074: Test-plan provenance fixtures -------------------------------------
PROVENANCE = "<!-- flow:test-plan-rendered -->"

# The attack: hand-authored block, hand-ticked boxes, no renderer stamp.
FORGED_TEST_PLAN = """## Summary
- does a thing

## Test plan
- [x] Criterion 1 verified
- [x] Criterion 2 verified
"""

STAMPED_TEST_PLAN = f"""## Summary
- does a thing

## Test plan

- [x] Criterion 1 verified

{PROVENANCE}
<!-- Test plan rendered from the /flow:verify-build findings buffer; checkbox state = machine verdict, not self-report. Do not hand-edit criterion checkboxes. -->
"""

# A docs PR that explains the Test-plan format: the only "## Test plan" is inside a fence.
DOCS_FENCED_EXAMPLE = """## Summary
Documents what the renderer emits.

```markdown
## Test plan
- [x] example criterion
```

Nothing else.
"""

# A hand-authored Test plan whose only stamp sits inside a fenced example.
FENCED_STAMP_LAUNDER = f"""## Test plan
- [x] Criterion 1 verified

Reference — the renderer emits:

```markdown
{PROVENANCE}
```
"""

# The honest no-gate-ran path is ALSO stamped — the marker attests provenance, not passage.
STAMPED_FALLBACK_TEST_PLAN = f"""## Test plan

> ⚠️ **No behavioral gate ran** (verify-build skipped: platform library).

- [ ] <how to verify — fill in per the change>

{PROVENANCE}
<!-- verify-build produced no current buffer; Test plan is manual. checkbox stays unchecked until a human verifies. -->
"""

_failures: list[str] = []


def run(subcmd, body, extra_args):
    """Run pr-coherence.py <subcmd> with body written to a temp file. Returns exit code + stdout."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(body)
        path = f.name
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), subcmd, "--body-file", path, *extra_args],
            capture_output=True, text=True,
        )
        return proc.returncode, proc.stdout + proc.stderr
    finally:
        Path(path).unlink(missing_ok=True)


def expect(name, got_rc, want_rc, out):
    if got_rc == want_rc:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}: exit {got_rc}, wanted {want_rc}\n        output: {out.strip()}")
        _failures.append(name)


def main() -> int:
    print("pr-coherence evals (FB-0067)")

    # --- coherence: the three acceptance cases ---------------------------------
    rc, out = run("coherence", READY_WITH_MANIFEST, ["--is-draft", "false"])
    expect("manifest-present-on-ready-PR ⇒ FAIL", rc, 1, out)

    rc, out = run("coherence", READY_CLEAN, ["--is-draft", "false"])
    expect("manifest-absent-on-ready-PR ⇒ PASS", rc, 0, out)

    rc, out = run("coherence", DRAFT_WITH_MANIFEST, ["--is-draft", "true"])
    expect("manifest-present-on-draft ⇒ PASS", rc, 0, out)

    rc, out = run("coherence", READY_CLEAN, ["--is-draft", "true"])
    expect("manifest-absent-on-draft ⇒ PASS", rc, 0, out)

    # --- marker/heading detection parity (either token is enough) --------------
    rc, out = run("coherence", HEADING_ONLY_READY, ["--is-draft", "false"])
    expect("heading-only-on-ready ⇒ FAIL (marker stripped, heading remains)", rc, 1, out)

    rc, out = run("coherence", MARKER_ONLY_READY, ["--is-draft", "false"])
    expect("marker-only-on-ready ⇒ FAIL (heading stripped, marker remains)", rc, 1, out)

    # --- readback: the post-write verification path ----------------------------
    rc, out = run("readback", READY_CLEAN, [
        "--is-draft", "false", "--expect", "## Summary", "--forbid", HEADING, "--want-draft", "false"])
    expect("readback: expect present + forbid absent + coherent ⇒ PASS", rc, 0, out)

    rc, out = run("readback", READY_CLEAN, [
        "--is-draft", "false", "--expect", "## Nonexistent Section"])
    expect("readback: expected substring missing ⇒ FAIL", rc, 1, out)

    rc, out = run("readback", READY_WITH_MANIFEST, [
        "--is-draft", "false", "--forbid", HEADING])
    expect("readback: forbidden substring present ⇒ FAIL", rc, 1, out)

    rc, out = run("readback", READY_CLEAN, [
        "--is-draft", "false", "--want-draft", "true"])
    expect("readback: draft-state mismatch ⇒ FAIL", rc, 1, out)

    # The load-bearing backstop: readback FAILS on an incoherent state even when the
    # caller forgot to --forbid the manifest — this is what catches the silent write.
    rc, out = run("readback", READY_WITH_MANIFEST, ["--is-draft", "false"])
    expect("readback: incoherent (ready+manifest) with no explicit forbid ⇒ FAIL", rc, 1, out)

    # --- test-plan provenance (FB-0074) ----------------------------------------
    # The forgery this closes: an agent hand-writes "## Test plan" and hand-ticks the
    # boxes, so a self-assertion reads exactly like a machine verdict.
    rc, out = run("test-plan-provenance", FORGED_TEST_PLAN, [])
    expect("provenance: hand-authored Test plan ⇒ FAIL", rc, 1, out)

    # Hand-written "stamped" fixtures are deliberately NOT used for the PASS cases any
    # more — they carry the marker but no content digest, which is exactly the
    # pre-v1.22.0 shape that must now fail. The PASS cases below run the REAL renderer.
    rc, out = run("test-plan-provenance", STAMPED_TEST_PLAN, [])
    expect("provenance: marker without a content digest ⇒ FAIL (pre-v1.22.0 render)", rc, 1, out)

    # The stamp attests PROVENANCE, not passage — the honest "no gate ran" fallback
    # carries it too (verified end-to-end below), so an honest-but-unverified PR is
    # never punished for being honest.
    rc, out = run("test-plan-provenance", STAMPED_FALLBACK_TEST_PLAN, [])
    expect("provenance: fallback marker without digest ⇒ FAIL (pre-v1.22.0 render)", rc, 1, out)

    # No Test plan at all is a different defect (Step 7 always writes one); this
    # check must stay silent rather than manufacture a second failure for it.
    rc, out = run("test-plan-provenance", "## Summary\n- x\n", [])
    expect("provenance: no Test plan section ⇒ N/A, exit 0", rc, 0, out)

    # Heading detection must not be defeated by case or trailing text.
    rc, out = run("test-plan-provenance", "## test plan (manual)\n- [x] faked\n", [])
    expect("provenance: lowercase/suffixed heading still detected ⇒ FAIL", rc, 1, out)

    # Self-found false POSITIVE: a PR body that DOCUMENTS the Test-plan format carries a
    # fenced example with a literal "## Test plan" and no stamp. Counting that as a real
    # section fails the check — and ship Step 7b exits 1 on failure, so it would hard-block
    # a legitimate ship with no escape hatch. Only unfenced text is real body structure.
    rc, out = run("test-plan-provenance", DOCS_FENCED_EXAMPLE, [])
    expect("provenance: '## Test plan' inside a fenced example ⇒ N/A, not FAIL", rc, 0, out)

    # The mirror: a stamp quoted inside a fence must NOT launder a hand-authored plan.
    rc, out = run("test-plan-provenance", FENCED_STAMP_LAUNDER, [])
    expect("provenance: stamp only inside a fence does NOT satisfy the check ⇒ FAIL", rc, 1, out)

    # END-TO-END parity (FB-0010 fan-out defense). The marker AND the digest algorithm
    # are declared in two files; a source-text match would pass on a re-quoted literal
    # and never exercise the renderer. So run the REAL renderer and feed its REAL output
    # to the checker — the only test that proves the two agree.
    renderer = HERE.parent / "skills" / "ship" / "lib" / "render-test-plan.py"
    example = HERE.parent / "skills" / "verify-build" / "lib" / "findings-example.json"
    meta = json.loads(example.read_text(encoding="utf-8")).get("metadata", {})
    proc = subprocess.run(
        [sys.executable, str(renderer), str(example),
         "--branch", meta.get("branch", ""), "--head-sha", meta.get("head_sha_short", "")],
        capture_output=True, text=True,
    )
    rendered = proc.stdout
    rc, out = run("test-plan-provenance", rendered, [])
    expect("provenance: REAL renderer output verifies end-to-end", rc, 0, out)

    # The realistic forgery the marker alone could not catch: let ship render the block,
    # then flip a box and leave the comment intact. The content digest is what closes it.
    flipped = re.sub(r"^- \[[ ~]\] ", "- [x] ", rendered, count=1, flags=re.M)
    expect("provenance: rendered block was actually mutated by the test",
           0 if flipped != rendered else 1, 0, "fixture did not flip a box — test is vacuous")
    rc, out = run("test-plan-provenance", flipped, [])
    expect("provenance: tick-flip on a genuinely-rendered block ⇒ FAIL", rc, 1, out)

    # ...but prose around the block is the human's to edit and must NOT false-fail —
    # Step 7b exits 1, so a brittle digest would hard-block a legitimate ship.
    prosed = rendered.replace("## Test plan", "## Test plan\n\n_Reviewer: see criterion 2._", 1)
    rc, out = run("test-plan-provenance", prosed + "\n\nExtra human notes.\n", [])
    expect("provenance: prose edits around the block still PASS", rc, 0, out)

    # The fallback path is the one flow's OWN repo takes (platform: library). Ship Step 7
    # instructs the agent to fill in its `<how to verify>` line — that documented happy
    # path must not fail its own gate, while hand-ticking its box must.
    fb = subprocess.run(
        [sys.executable, str(renderer), str(HERE / "no-such-buffer.json"),
         "--branch", "main", "--head-sha", "abc1234"],
        capture_output=True, text=True,
    ).stdout
    rc, out = run("test-plan-provenance", fb, [])
    expect("provenance: manual fallback verifies", rc, 0, out)
    rc, out = run("test-plan-provenance",
                  fb.replace("<how to verify — fill in per the change>", "Run the suite"), [])
    expect("provenance: filling the fallback's <how to verify> line still PASSES", rc, 0, out)
    rc, out = run("test-plan-provenance", fb.replace("- [ ] <how to verify", "- [x] <how to verify"), [])
    expect("provenance: hand-ticking the fallback box ⇒ FAIL", rc, 1, out)

    # SCOPE: the renderer digests only its own block, so the verifier must too. A PR body
    # routinely carries unrelated checkboxes (a reviewer checklist, a TODO) and is followed
    # by `## Flow run`. Digesting the whole body would fold those in and hard-fail a
    # perfectly good ship — a false accusation, since Step 7b exits 1.
    ship_shaped = (
        "## Summary\n- does a thing\n- [ ] reviewer: check the migration\n\n"
        + rendered
        + "\n\n## Flow run\n\n| Step | Status |\n|---|---|\n| Clarify | ✓ |\n"
    )
    rc, out = run("test-plan-provenance", ship_shaped, [])
    expect("provenance: unrelated checkboxes elsewhere in the body do NOT fail it", rc, 0, out)

    # ...but the scoping must not become an escape hatch: flipping a box INSIDE the
    # section still fails even when the body has other checkboxes around it.
    rc, out = run("test-plan-provenance",
                  ship_shaped.replace(rendered, flipped), [])
    expect("provenance: tick-flip inside the section still FAILS in a full body", rc, 1, out)

    # --- red-team bypasses (both were EXPLOITABLE; both verified against the pre-fix code)
    # 1. A 4-space-indented ``` is an INDENTED CODE BLOCK in CommonMark, not a fence.
    #    Treating it as a fence swallowed the rest of the body, so the section vanished
    #    and the check returned N/A + exit 0 — while GitHub rendered the forged, fully
    #    ticked Test plan normally.
    rc, out = run("test-plan-provenance",
                  "    ```\n\n## Test plan\n- [x] totally verified\n- [x] also verified\n", [])
    expect("bypass: 4-space-indented fence hiding a forged plan ⇒ FAIL", rc, 1, out)

    # 2. An unclosed fence hides everything after it from the parser, so every question
    #    answers "not present". Fail closed rather than report a clean N/A.
    rc, out = run("test-plan-provenance", "```\n## Test plan\n- [x] forged\n", [])
    expect("bypass: unclosed fence ⇒ FAIL (fail closed, not N/A)", rc, 1, out)

    # 3. Verifying only the FIRST section is a bypass: keep the honest stamped block and
    #    append a second all-ticked one; the gate validates the section nobody reads.
    rc, out = run("test-plan-provenance",
                  fb + "\n\n## Test plan\n- [x] everything verified\n", [])
    expect("bypass: a SECOND '## Test plan' section ⇒ FAIL", rc, 1, out)

    # ship always writes a Test plan, so at Step 7b its absence is a failed write, not
    # "nothing to verify". Standalone use keeps the lenient N/A.
    rc, out = run("test-plan-provenance", DOCS_FENCED_EXAMPLE, ["--require-section"])
    expect("provenance: --require-section turns a missing section into FAIL", rc, 1, out)

    # A stamp with no digest (a pre-v1.22.0 render, or a stripped digest line) attests
    # nothing about checkbox state — it must not pass.
    no_digest = "\n".join(
        ln for ln in rendered.splitlines() if not ln.startswith("<!-- flow:test-plan-digest ")
    )
    rc, out = run("test-plan-provenance", no_digest, [])
    expect("provenance: stamp present but digest line stripped ⇒ FAIL", rc, 1, out)

    # --- usage: missing body file exits 2, never a false PASS ------------------
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "coherence", "--body-file", "/no/such/file.md", "--is-draft", "false"],
        capture_output=True, text=True)
    expect("missing body file ⇒ exit 2 (never a false PASS)", proc.returncode, 2, proc.stdout + proc.stderr)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "test-plan-provenance", "--body-file", "/no/such/file.md"],
        capture_output=True, text=True)
    expect("provenance: missing body file ⇒ exit 2", proc.returncode, 2, proc.stdout + proc.stderr)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All pr-coherence evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
