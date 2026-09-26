"""The four artifact-backed recall cases, with keyed ground truth (FB-0115).

DEV TOOLING, NOT SHIPPED (CLAUDE.md § 3). No /flow:* skill invokes this.

Every case's ground truth is quoted from a committed artifact, never invented for the
measurement -- that is what makes this measurable rather than arguable:

  spike    `dev-docs/research/2026-09-16-d1-auto-plan-quality-spike.md`'s table of 10,
           against the committed prototype + auto-plan. Two of the four live runs used
           this exact input (10-of-10 hand-run, then 5-of-10), so it is the one case with
           a recorded instrument-variance measurement already attached.
  pr159    the five criteria commit `0b69457` declared, which its own ship-time coverage
           run returned "No issues flagged" over. **NOT A RECALL CASE, and measuring it is
           how that was discovered.** Reconstructed faithfully (clone with `origin/main`
           rewritten to `f278aec`), the run's file list is `marketplace.json`, `ci.yml` and
           `plugin.json` -- a version bump. All five gaps were added in
           `skills/audit-coverage/SKILL.md`, 212 insertions, which the behaviour diff
           EXCLUDES as `.md` (the `|\.md$` clause is byte-identical in the installed 1.29.0
           that produced the run and in the f278aec-era tree). The reviewer was never shown
           the code, so no prompt change can move this number. Kept as a STRUCTURAL case:
           `structural_blindness` asserts the blindness deterministically instead of
           scoring it as judgment.
  pr158    the five named verbatim in #158's draft manifest, which its ship-time run
           found 2 of.

AND THE SERIES MEASURES TWO DIFFERENT THINGS. An earlier telling counted #159's single event twice
("5 of 6 review-added behaviours were undeclared" -> reported as both `0-of-5` and
`0-of-6`). Corrected at the plan gate before it reached shipped prose. Then measuring pr159
showed its `0-of-5` is a FILE-FILTER result, not a judgment one (see pr159 below). So:

  judgment recall   10-of-10 (hand-run, source) - 5-of-10 (source, same input)
                    - 2-of-5 (#158, diff). Three runs, worst case 40%.
  structural miss   0-of-5 (#159, diff) -- the file the gaps live in never reached the
                    reviewer. Not recall. Reported separately, never averaged in.
  degenerate        80% / 100% (pr158, diff) -- the HIGHEST scores in the corpus, and they
                    measure nothing: the criteria describe a different PR, so every behaviour
                    is trivially undeclared. `report` labels this case rather than printing it
                    in the recall column, because the best number in the table being the
                    meaningless one is exactly how a reader gets misled.

Precision 4/4 across every run that produced findings. A test set that quietly inherits
either a double-counted datapoint or a mis-attributed one is a test set nobody can check,
so both corrections are recorded here rather than in a commit message.

`anchors` are the SCORING KEY and they are deliberately mechanical -- a symbol, an element
id, a literal string from the artifact. A gap counts as found iff a FLAGGED finding cites
one of its anchors. The model suggests; the key defines.
"""

# Ten behaviors the spike found undeclared. Anchors are kept byte-identical to
# `run_coverage_source_mode_evals.py`'s SPIKE_ANCHORS and asserted equal to them by
# `selftest`, so the two copies cannot drift (general.md item 2 fan-out).
SPIKE_GAPS = [
    ("kb", "keyboard-only interaction path (WCAG 2.1.1)",
     ["focusWalkTarget", "walkStep", "walkDepth", "Shift+Arrow", "keyboard-only"]),
    ("wipe", "bulk delete-all, two-step arm/disarm",
     ["an-wipe", "delete-all", "delete all", "disarm()"]),
    ("del", "single-comment delete",
     ["an-del", "single-comment delete", "single comment delete", "per-row"]),
    ("snap", "snapPreview hover-outline preference",
     ["snapPreview", "snap preview", "hover-outline", "hover outline"]),
    ("eye", "show/hide-all-pins toggle",
     ["an-eye", "show/hide", "hide all pins", "hide-all-pins", "hide pins", "hide-pins"]),
    ("panel", "comment-list panel open/close",
     ["an-close", "panel open", "list panel", "panel itself", "closes the panel"]),
    ("rowcopy", "per-row copy (single-note format)",
     ["oneNoteBlock", "an-copy1", "per-row copy", "row copy", "single-note"]),
    ("quota", "storage-quota-exceeded warning path",
     ["saveWarned", "QuotaExceeded", "storage limit", "blocking local storage",
      "storage blocked", "blocked storage", "could not be saved"]),
    ("esc", "Escape four-branch priority state machine",
     ["Esc key", "setCommenting(false)", "escape branch", "escape cascade",
      "escape hierarchy", "escape ladder", "escape steps", "escape layering",
      "esc is layered", "escape is a layered"]),
    ("empty", "discard-on-empty-close",
     ["dropEmpty", "discard-on-empty", "empty comment", "blank comment",
      "empty note", "never persisted"]),
]

PR159_GAPS = [
    ("symlink", "a named path that is a symlink is refused, target never read",
     ["symbolic link", "-L ", "is a symlink", "symlink refusal"]),
    ("delim", "only control lines above the ----- source ----- delimiter are authoritative",
     ["----- source -----", "column 0", "above the delimiter", "forged control",
      "control line", "control-line"]),
    ("relpath", "exclusions are matched against the repo-relative path",
     ["repo-relative", "relative path", "SEXCL", "ROOTP"]),
    ("index", "the index line reads `files selected (N)`, one path per line, never 'read'",
     ["files selected", "index line", "one path per line"]),
    ("readline", "source-mode output opens with a `Read: <files>` line",
     ["Read:", "Read line", "read line", "opens with"]),
]

PR158_GAPS = [
    ("gatelit", "an unrecognised gate literal is refused rather than passed through",
     ["cmd_gate_execute", "gate-execute", "gate literal", "unrecognised gate",
      "unrecognized gate", "prototype-first"]),
    ("digest", "the approval digest emits both committed lines, folds newlines, truncates visibly",
     ["render_digest", "digest_line", "Prototype approved:", "both lines", "two lines",
      "TWO-line", "two-line"]),
    ("contract", "`contract` emits one parseable verdict when no prototype exists",
     ["_contract", "feasibility_required", "parseable verdict", "no prototype.html",
      "nothing to approve", "nothing to check", "absent-artifact", "absent artifact"]),
    ("openable", "`present` always returns an openable path",
     ["cmd_present", ".presented.html", "open_this", "openable path"]),
    ("hash", "`present` reports the hash of what it presented",
     ["source_sha256", "hash of what", "reports the hash", "presented hash"]),
]

CASES = {
    # THE ONE VALID DIFF-MODE RECALL CASE, and building it was forced by a gap in the first
    # measurement round: `spike` is SOURCE mode, which renders no change inventory at all, so
    # the spike numbers measure the two-stage prose SPLIT ALONE and say nothing about the
    # inventory or the POST-PLAN tiers. `pr158` as originally set up could not fill that gap
    # (its first Spec-walk block belongs to another PR -- see below). This case fixes exactly
    # that, and nothing else, by using #158's OWN plan section as the whole plan doc:
    #
    #   plan   = the `## PR — D1 Phase 2 …` section of `dev-docs/plan.md` at c91b8c2, which
    #            carries #158's own 73-checkbox Spec-walk and -- verified -- NONE of the five
    #            ground-truth criteria, because those were back-filled later at the gate.
    #   diff   = 5a2aaf3..c91b8c2, i.e. what #158's ship-time coverage run actually faced.
    #   truth  = the same five PR158_GAPS, all in `prototype-gate.py`, all `.py`, all visible.
    #
    # So this is the faithful reconstruction of what #158's run SHOULD have compared against,
    # and the only case in the set where the inventory is rendered and the criteria are real.
    "pr158b": {
        "mode": "diff",
        "worktree_ref": "c91b8c2",
        "plan": "dev-docs/plan.md",
        # Keep only this section, so the FIRST Spec-walk block is #158's own.
        "plan_first_section": "## PR — D1 Phase 2: the prototype phase, human gate 1,",
        "argument": None,
        "base": "5a2aaf3",
        "gaps": PR158_GAPS,
        "recorded": "2-of-5 at ship (#158) — reconstructed with #158's OWN criteria",
    },
    "spike": {
        "mode": "source",
        # The spike's own committed artifacts, unmodified -- the point of committing them.
        "worktree_ref": None,                 # runs in the repo as-is
        "plan": "dev-docs/research/2026-09-16-d1-auto-plan-quality-spike/auto-plan.md",
        "argument": "plugins/flow/skills/verify-build/lib/annotation-layer.html",
        "base": None,
        "gaps": SPIKE_GAPS,
        "recorded": "10-of-10 hand-run (#153); 5-of-10 on re-run (#159)",
    },
    "pr159": {
        "mode": "diff",
        "worktree_ref": "bd29167",            # ship-time HEAD, before 0b69457 declared the five
        "plan": "dev-docs/plan.md",
        "argument": None,
        "base": "f278aec",                    # origin/main when #159 branched
        "gaps": PR159_GAPS,
        "recorded": "0-of-5 at ship (#159) — STRUCTURAL, not recall",
        # Asserted by `selftest`: the reviewer's own file list must NOT contain the file the
        # five gaps live in. A positive assertion of the blindness, so that if the exclusion
        # is ever fixed this case fails loudly and is re-classified, rather than silently
        # becoming a recall case whose recorded number is 0 for a reason nobody remembers.
        "structural_blindness": {
            "gaps_live_in": "plugins/flow/skills/audit-coverage/SKILL.md",
            "excluded_by": r"\.md$",
        },
    },
    "pr158": {
        "mode": "diff",
        "worktree_ref": "c91b8c2",            # after /flow:staff-review, before the back-fill
        "plan": "dev-docs/plan.md",
        "argument": None,
        "base": "5a2aaf3",
        "gaps": PR158_GAPS,
        "recorded": "2-of-5 at ship (#158) — DEGENERATE as a before/after case; see below",
        # MEASURED AND REPORTED, NOT SCORED. At this commit the plan doc's FIRST
        # `**Spec-walk:**` block -- the only one `extract-criteria.py` reads -- is a DIFFERENT
        # PR's (17 criteria, every one about `/flow:audit-coverage` source mode; the extractor
        # warns that 65 blocks exist). So every behaviour in the diff is genuinely undeclared
        # and recall scores HIGH for the worst possible reason: **80% before (4.0/5) and 100%
        # after (5.0/5)** across three runs each, with 3 and 7 unmatched findings respectively
        # -- the tell that the reviewer is correctly flagging a diff nothing describes.
        #
        # THOSE NUMBERS WERE WRONG IN THIS COMMENT UNTIL THE EVIDENCE WAS COMMITTED. It read
        # "5/5 in BOTH conditions", measured before the scoring key was tightened to reject
        # bare common words; under the admissible key the before condition is 4/5. Nobody
        # could have caught that while the six raw outputs lived only in a sandbox -- which is
        # the argument for committing them, made by the act of committing them. Kept in the file
        # because the finding is worth more than the datapoint: a coverage gate whose criteria
        # silently belong to another PR returns a verdict about nothing, and the loud warning
        # it prints is routed nowhere. v1.49.0 makes the skill surface that warning; the
        # deeper fix (a per-PR boundary marker for the walk parsers) is already on the roadmap.
        "degenerate": "the first Spec-walk block at this commit belongs to a different PR",
    },
}
