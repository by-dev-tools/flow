# `/flow:audit-coverage` enumerates before it judges — recall 65% → 82%, and three instruments that lied

**Date:** 2026-09-26 · **Version:** v1.49.0 · **Branch:** `conductor/audit-coverage-recall-two-stage-union` · **Feedback:** FB-0115

## The problem, and why its shape decided the fix

Ben: *"those gaps are huge; not really acceptable for an autonomous system that we're trusting."*

The coverage reviewer's **precision is unblemished** — across every measured run it has never once
reported a gap that was not real. Its **recall** was 0–100%. That asymmetry is the whole design
constraint, and it is the *opposite* of the published practitioner problem: G-Research's code-review
tool had false positives and used a second pass to filter. Copying that would have added machinery to
solve a problem we do not have. **The lever was widening stage one.**

**The mechanism, read off the shipped prompt rather than guessed.** `SKILL.md:130` fused three jobs
into one invisible step: *enumerate* the behaviours, *match* them against criteria, *suppress* weak
findings. The suppression half is heavily tuned — `auditor.md`'s "default to covered **even loosely**",
"do not invent findings to appear thorough", "a reviewer prompted to find gaps will usually report
some". Those rules are exactly *why* precision is perfect, and applied to **enumeration** they are pure
recall loss. And because the enumeration was never written down, **a run that enumerated 6 of 11
behaviours emitted a clean result indistinguishable from a thorough one** — `general.md` § Consistency
item 4, a measurement that can only return "clean", living inside a shipped gate.

So the fix is a **split**, which is subtractive: Stage 1 enumerates with the suppression rules
explicitly scoped *off* (there, the only error is omission); Stage 2 matches with the existing judgment
**verbatim**. Nothing was added to the matching half. No new reviewer, agent, skill, or config slot.

## Measured, on cases with committed ground truth

| case | mode | before (mean) | after (mean) | before (union) | after (union) |
|---|---|---|---|---|---|
| spike — 10 documented gaps | **source** | **65%** (n=4) | **82%** (n=5) | 80% | **100%** |
| pr158b — 5 gaps | **diff** | 60% (n=3) | **60%** (n=3) | 60% | 60% |

**Source mode: the distributions do not overlap.** Every after-run (80·80·80·90·80) beats every
before-run (60·60·70·70). **Precision held at zero false positives across all 15 runs.**

**Diff mode: the change did not move recall. 3-of-5 before, 3-of-5 after, the same two missed both
times.** Stated first and without softening, because the two results are different claims and must not
be read as one: **the source-mode numbers are the recall result; the diff-mode result is diagnostic.**
Nothing here should be read as a recall gain in diff mode.

The before-condition **reproduces #158's recorded 2-of-5** (runs returned 2, 3, 3), which is the validity
check on the reconstruction — it is measuring the real thing. **n=3, said plainly**; a second valid
diff-mode case was deliberately not built (see § "The criteria can belong to a different PR" for why they
are rare, and the cost is real).

What *did* change is where the failure lives. The two residual misses are **enumerated and then
dismissed**: the after-runs' inventories list both `present` behaviours and the `COVERAGE MAP` marks them
`covered`. So the enumerator found them and the **matcher's "default to covered" call** dropped them.
Before this change a miss and a thorough pass were indistinguishable from outside — that was the whole
diagnosis of `SKILL.md:130`, and it is why `0-of-5`, `2-of-5` and a clean run read the same for months.
**The next lever for whoever picks this up is the matcher, not the enumerator** — specifically the
"even loosely" clause in `auditor.md`'s disprove self-check, which is what is doing the dropping.

**82% is a floor, not a point estimate.** Two runs flagged a real gap the spike's own list of 10 never
carried (reopening a comment from a pin or panel row), and it was **not** added to the key — fitting a
key to the outputs it scores measures nothing. So both denominators under-credit equally, the spike's
"10" was itself an undercount, and the true recall in both conditions is higher than reported.

Every run is committed under `tools/coverage-recall/runs/`, unmodified, so the numbers are re-derivable
rather than trusted (`recall.py report tools/coverage-recall/runs`). The §9.3 spike's precedent.

**One run is excluded and recorded.** A sixth source-mode attempt returned only *"I need to read the
rest of the file."* — it truncated its Read of a 77 KB prompt and produced no verdict. 1 of 13 attempts,
which is a real operational property of running a reviewer over a large evidence block, not a result.

## The deterministic half, and the tier that matters

`skills/audit-coverage/lib/change-inventory.py` emits one row per hunk of the already-filtered behaviour
diff — fed `$FILES` on stdin so there is exactly **one** source-file filter in the skill and no fan-out.
Stage 1 must account for every row; anything it cannot classify lands under `UNACCOUNTED` instead of
disappearing. Rows are tiered by their relation to the plan, and the load-bearing tier is **`POST-PLAN`**:
the hunk landed in a commit *after* the plan was last edited, so no declared criterion **can** cover it.
This is not a heuristic or a prior — it is a `git` fact, and it targets the shape of most measured misses
(behaviour added during `/simplify` and staff-review arrives after the Spec-walk was written).

**Validated on the known positive before it was believed, and the validation found a real defect.**
Replayed on #158's actual commit graph the computation selects exactly `c91b8c2` (staff-review, where the
missed behaviours came from) and correctly **excludes** `2798889` (`/simplify`, whose behaviours *were*
declared in `a25bdbf`). Paired negative, on real data: at #158's tip the plan is the last commit and the
identical call reports nothing `POST-PLAN`. The defect the replay found: the first version rendered
`prototype-gate.py` — a **new** file, so one `+987` cumulative hunk — as a single `pre-plan` row. A
one-entry checklist for the PR whose five missed behaviours all live in that file, tiered wrong. Rows now
come from **two** diffs (cumulative *and* post-plan) merged with the stronger tier winning, which gives
that region 11 precise hunks instead of one.

A second defect came from rendering the real block instead of reasoning about it: an **untracked** new
file is invisible to every `git diff`, so the inventory reported "0 hunks" over a brand-new source file —
the exact failure it exists to prevent, reproduced inside itself. Untracked files now get a whole-file
row, detected by `ls-files --error-unmatch`'s **exit code** rather than a grep of its output.

## Three instruments that reported green while broken

All three were caught the same way — by looking at what the instrument actually produced — and all three
are the same class this repo already documents. Listed because the pattern is the finding.

1. **The harness audited its own setup.** To point the evidence block at a case's historical base, the
   first build edited `flow.config.json` in the worktree. That edit is an uncommitted `.json` change the
   behaviour diff **matches**, so the rendered inventory listed five hunks of the setup and none of the
   PR. It could not have worked anyway: the block resolves the base from `origin/HEAD` **before** the
   config. Now a `--shared` clone with `origin/main` rewritten, plus a **scoped positive assertion** about
   which files may differ (not a blanket skip).
2. **The scorer reported a perfect number while measuring vocabulary.** `pr158b` before scored **5/5**
   against a recorded 2-of-5, because the key carried the bare words `present`, `contract`, `sha` —
   ordinary English in a finding about anything in that file. Its selftest passed because every synthetic
   fixture spelled the anchors out verbatim, so the fixtures could not distinguish a working matcher from
   a word-frequency detector. Fixed by a rule stated and enforced mechanically — **an anchor must be
   symbol-like or a multi-word phrase** — applied blind, with the checker's own negative control. Keys are
   derived from committed artefacts, never from the outputs they score.
3. **A stage-1 metric that did not measure enumeration.** Built to attribute a miss to enumerator vs
   matcher, it scored the inventory against the same code-symbol key — and code symbols appear in a
   finding's `Hunk:` line, not in a one-line prose behaviour description. It reported 50% where a reader
   counts far more, and passed its selftest for the same reason as (2). **Removed rather than repaired**,
   because the repair was to add prose anchors *after* reading the outputs, i.e. tune the instrument to
   its own result. The enumerator/matcher split is reported as a stated, reader-checkable observation.

The span-integrity eval also caught backticks inside a `` !` `` span (FB-0010 — one inner backtick
truncates it), which is the existing machinery doing its job on a new author.

## The criteria can belong to a different PR — a laundered PASS, measured

The second-most important thing in this change, and it is not a recall finding at all.

`extract-criteria.py` reads only the **first** `**Spec-walk:**` block in the plan doc. A plan doc that
retains shipped PRs' blocks can therefore put **another PR's criteria** on top — and at #158's ship-time
commit that is exactly what had happened: 17 criteria, every one about `/flow:audit-coverage` source
mode, none describing the diff under review. Against criteria that describe different work, **every**
behaviour is trivially "undeclared".

That is the laundered-PASS hazard biting the coverage gate specifically, and it is measured rather than
imagined: the first `pr158` case scored **5/5 in both conditions** and was measuring the setup, not the
change. A gate can also launder the other way — a verdict about nothing reads exactly like a verdict
about something. `extract-criteria.py` prints a loud warning (*"65 blocks found, only the first read"*)
and **nothing routes on it**, which is the FB-0010 silent-skip shape with the warning already written.

**Minimal fix shipped here:** one bullet, the same shape as the `INVENTORY-UNAVAILABLE` weakening — if
the criteria block carries that warning, the reviewer says so in its output, and says that if these
criteria do not describe this diff then the declared set is the wrong one and every finding must be
re-read in that light. It never silently treats another PR's criteria as this PR's. The real fix is the
per-PR boundary marker for the walk parsers, already on the roadmap; `plan-discipline`'s active-block
placement rule is what prevents it today.

## One more finding routed, not fixed here

**`.md` is invisible to this gate, and it is the dominant cause of the worst number in the series.**
Reconstructing #159's ship-time run faithfully, the reviewer's file list was `marketplace.json`,
`ci.yml`, `plugin.json` — a version bump. All five of that PR's undeclared behaviours were added in
`skills/audit-coverage/SKILL.md`, **212 insertions**, excluded by `EXCL`'s `|\.md$`. So its recorded
`0-of-5` was **never a judgment failure** — the reviewer was never shown the code, and no prompt change
can move that number. The exclusion is byte-identical in the installed 1.29.0 that produced the run and
in the f278aec-era tree. On #158: **63 files changed, 4 reached the reviewer.** Out of scope
deliberately — it is a published contract every consumer inherits, it collides with the 60 KB cap in a
way needing its own design, and mixing it in would have made both halves unmeasurable. Roadmap, loudly.

## The record corrected twice

The recall series was reported as five runs — `10 · 5 · 0-of-5 · 0-of-6 · 2-of-5`. The `0-of-6` is the
**same event** as the `0-of-5`, described two ways and counted twice; it was minutes from shipping as
"Across five live runs" into two files. And the surviving `0-of-5` is a **file-filter** result, not a
judgment one. The honest series: **10-of-10 · 5-of-10 · 2-of-5** judgment, plus one structural miss where
the reviewer never received the file. Both corrections came from re-deriving provenance instead of
trusting a summary, which is the only reason they were caught before merge.

## The stated drop-rule named the wrong metric

The rule this PR was executed under was *"if a change does not move recall on the real cases, drop it"* —
and it is a good rule, which is why it was followed rather than argued with until there was data. Applied
literally it deletes the change inventory: diff mode moved 0.

It was too narrow, and the reason is the same error class as everything else this entry records, one
level up. **The inventory's value is observability, and the headline metric cannot see observability.**
Recall did not move because the inventory did its job and the bottleneck relocated downstream — the
enumerator found both missed behaviours and the matcher dismissed them. A rule that counts only the
headline number would have deleted a validated instrument for succeeding at something the number does not
measure. Recorded because *measuring the wrong thing and acting confidently on it* is precisely what the
rest of this PR is about, and the rule-setter is not exempt.

The kept-on-merit test, for the record: the inventory is **deterministic** (it cannot regress recall),
**validated against a known positive** (it names all five of #158's ground-truth call sites by function),
and **demonstrably used** — two after-runs cite `POST-PLAN` in their own reasoning. It was **not** kept on
"n=3 is weak evidence"; that argument would admit anything.

## Tradeoffs

- **Two stages inside one forked context, not two invocations.** The skill is `context: fork` with
  `agent: auditor`, so the reviewer cannot spawn a second pass. Two labelled stages in one prompt cannot
  fully shed the system prompt's global suppression — it is scoped by instruction, a soft constraint. It
  measured as enough in source mode; a genuine second invocation would cost a second run of the whole
  evidence block and was not needed to move the number.
- **Union across runs was measured, not shipped.** Precision licenses it (unioning can only add true
  positives), and union does rise — 80% → 100% at matched n. But that needs N invocations per gate, and
  single-run mean already moved. Recorded as the available lever if recall needs more later.
- **`eval_utils.py` gained the repo builders rather than a sixth copy being written.** The five existing
  copies are untouched (scope), but the hoist target is now populated, so the deferred cleanup is a
  deletion instead of a rewrite. `commit()` is new because the `POST-PLAN` tier is computed from commit
  **order**, and a builder that makes only one commit cannot exercise it at all.
- **The spike's "10" is an undercount, and the key was left alone.** Two runs flagged a real gap the
  spike never listed (reopening a comment from a pin or panel row). Adding it would have fitted the key
  to the outputs it scores, so both conditions stay equally under-credited and the adjudication is
  recorded instead.
