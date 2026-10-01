# 2026-09-30 — `/flow:audit-coverage` can read behaviour-bearing prose (CV1, v1.55.0)

**SHA:** (this PR) · **Version:** 1.55.0 · **Feedback:** FB-0126, FB-0127 · **Roadmap:** CV1 closed; three § Next items opened

## What

`/flow:audit-coverage` never showed the reviewer a `.md` file. On a plugin whose deployed surface
*is* prose, that made the completeness gate blind to most of what this repo changes. Three parts:

- **A — say it.** With the slot unset, a run prints `[audit-coverage] WEAKENED · DOC-BLIND` naming
  every changed doc-shaped file it did *not* read, and says which predicate matched them (the
  consumer's declaration, or a built-in suggestion). New control-line vocabulary, registered
  wherever the existing tokens are enumerated and pinned by `run_coverage_vocab_evals.py`, which
  derives the token list **from the emitters** rather than restating it.
- **B — see it.** New `behaviorBearingDocPatterns` config slot (schema 36 → 37 slots), **empty by
  default**. When set, matching paths are unioned back into the behaviour diff *after* the source
  filter, minus test/fixture paths. Invalid and valid-but-vacuous slot values are both flagged
  (`DOC-SLOT-INVALID`), because a slot that compiles and matches nothing reads fewer files while
  looking healthy.
- **C — fit it.** `head -c` over a concatenation made files late in `sort -u` order **entirely
  invisible** once the 60 KB cap bound. Replaced with max-min fair-share allocation
  (`lib/evidence-budget.py`), which names every cut file. On #158's 15-file shape: 13 files at full
  size, 2 cut, **0 invisible**, total exactly 60,000 bytes.

## Why

The exclusion everyone pointed at was not the cause. **A `.md` path does not match
`sourceFilePatterns` at all**, so `EXCL`'s `|\.md$` clause was belt-and-braces and deleting it would
have changed nothing. That makes this an **inclusion** change, not an exclusion edit — which is why
the fix is a union after the filter rather than a narrower filter, and why widening `EXCL` (the
roadmap's original sketch) would have been a no-op with a convincing rationale. See FB-0126.

`sourceFilePatterns`/`EXCL` are a published contract every consumer inherits, so the slot defaults
empty: no consumer's result changes until they opt in. The DOC-BLIND line exists so that opting out
is a *choice* rather than an invisible default — FB-0121's rule applied to file selection.

## Measured

`tools/coverage-recall/` with `--selftest` passing first, #159's reconstruction (5 keyed gaps):

| arm | `.md` reaches reviewer | score |
|---|---|---|
| slot unset | no — `DOC-BLIND` fires, naming both files | no verdict produced; structurally 0-of-5 |
| slot set, instrument's own edit in the diff | yes | **0-of-5, fp=1** — the one finding was the harness's setup |
| slot set, that edit hidden | yes | **2-of-5 (40%), fp=0** |
| slot set + criteria untruncated | yes | **1-of-5 (20%), fp=0** — a *disjoint* gap |
| union of the two clean runs | — | **3-of-5 (60%), fp=0** |

Paired prose negative, same file and render path, one variable: a wording-only change to a
`skills/*/SKILL.md` returns `No issues flagged.`; one added rule in the same file is flagged with
its exit code and token named. The negative held even under an adverse `PLAN-PREDATES-BRANCH` tier.

Per-file cap behaviour on the 176 KB case, as asked: `ship/SKILL.md` is **177,768 B** against
`SOURCE_CAP` **120,000 B** — 1.5× the whole budget in one file. Source mode is untouched here and
that number is a § Next item deferred to D1 Phase 3, because fair-share has nothing to share when
one file exceeds the budget alone.

## Tradeoffs

- **A slot, not a wider default.** Rejected widening `EXCL` for everyone: on a repo where `.md` is
  documentation, that makes every docs PR read as a behaviour change and drowns the signal — the
  failure the exclusion was added to prevent. Cost: consumers who never set the slot keep the blind
  spot, which is why A ships with B rather than after it.
- **One knob, not two.** The slot decides what is *read*; it does not also decide whether the
  warning fires. Unset still warns, off a built-in suggestion, so the warning cannot be silenced by
  never configuring anything.
- **Fair-share, not a bigger cap.** Raising the cap postpones the problem and hides it; making
  truncation *even* and *named* means the reviewer can tell a fully-read file from a partly-read one.
- **Reported rather than tuned: recall moved, but not far.** 2-of-5 and 1-of-5 are weak. They are
  reported as judgment recall rather than improved by prompt-tuning in this PR, because the task was
  to make the file visible and conflating the two is how #159's file-filter result got recorded as a
  judgment result for two releases.

## Found while measuring, and fixed here

- **A pin that asserted a literal instead of a decision.** `cases.py`'s `structural_blindness`
  asserted `|\.md$'` still appeared in `EXCL` and promised to "fail loudly if the exclusion is ever
  fixed". It did not: the fix unioned matches back in *after* that filter, so the literal survived
  while the property it stood for was lifted. Replaced with a replay of the shipped block's own
  extracted regexes asserting the **selection outcome** in both slot states, paired, and
  mutation-validated three ways. Corollary added to `.claude/rules/general.md` item 4.
- **A disclosed confound is still a confound (FB-0127).** The recall harness injected the slot as an
  uncommitted `flow.config.json` edit and disclosed it on stderr, reasoning that one disclosed hunk
  "cannot affect the question being measured". It did: that hunk was the *only* finding the first
  slot-set run produced. Hidden with `git update-index --skip-worktree` — the block reads the config
  from the working tree but builds its file list from `git diff` — and asserted, not assumed.
- **An eval of mine that checked a filename instead of content.** Part C's "every file still
  contributes" matched the *path* in the output, which the file list prints whatever the allocator
  does. Swapping in a greedy first-fit allocator — the exact regression the section exists to catch —
  left it green. Now each fixture file opens with a unique marker and the check asserts the marker
  arrived; the mutation fails it 3-of-6.
- **The stale-slot-count scanner could not see a hyphen.** `README.md:89` read "A **24-slot**
  `flow.config.json`" against a 37-slot schema while every `N slots` sweep reported clean, because
  `\d+\s+slots?` cannot match `-`. Third separator escape for the same guard (after FB-0079's wrap
  and FB-0102's interposed word). Fixed in the first separator only — the looser form matched
  `FB-0058 boolean-slot` and `Step 4 config-slot`, two measured false positives — and pinned with a
  hyphenated positive plus that negative.
- **A shipped claim this measurement falsified.** The skill's "Running this more than once" section
  justified a single pass at ship Step 2 with "a gain measured at zero", from three diff-mode runs
  that found identical gaps, and explicitly asked for a second diff-mode case. This is that case and
  it went the other way (+30pp). The dead premise is out of the frontmatter, the prose and the table;
  the single-pass decision stands, now on cost grounds, and the open question is routed to § Next.

## Deliberately not fixed here

- **Criterion truncation.** `walk_extract.py`'s `CHECKBOX_RE` matches one physical line; a wrapped
  `- [ ]` bullet's continuation lines reach no consumer and raise no warning. Measured at #159's
  ship-time HEAD: **12 of 12 criteria wrapped, 1,143 of 5,819 characters reaching the reviewer — 80%
  dropped**. Different surface, and a second consumer (`/flow:verify-build` Step 3 feeds these
  strings to bundled `/verify`). Filed as a silent-skip on its own merits — the untruncated arm did
  *not* raise recall, so truncation is explicitly **not** offered as the explanation for any number
  above.
- **Source mode**, for the `SOURCE_CAP` reason above.

## What review found, and what it cost

`/simplify` (4 lenses) then `/flow:staff-review` (4 lenses) after the rigor gate reported
`rigor: missing`. Eight lenses produced three findings I would call serious, and **two of them were
mine, introduced by this PR's own cleanups** — which is the part worth recording.

**1. A partial-coverage blind spot that A could not report (`/simplify`, altitude lens).** With the
slot set, `DOC-BLIND` was computed against the *effective* pattern, so every file the slot matched
was in `$FILES` by construction and `$DROPPED` could only ever be empty. A slot covering `skills/`
but forgetting `agents/` — the realistic hand-written case — produced **no warning of any kind**
over a changed, unread `agents/*.md`. Invisible to dogfooding, because flow's own slot value is
byte-identical to `DOC_BUILTIN`, so both paths agree in this repo forever. Now computed against
`DOC_BUILTIN|BBDP`; a doc-shaped path either reached the reviewer or is named. That subsumed the
~10-line vacuity block, which is deleted.

**2. The batched `git diff` inherited the user's renderer (`/flow:staff-review`, staff-engineer).**
The 24→2-spawn optimisation keys hunks off git's per-file header, and that header's shape is
user-configurable. Measured: with `diff.noprefix=true` — an ordinary setting — no path matched,
every blob came back empty, the under-cap fast path printed nothing, and the block emitted
`----- diff -----` followed by **silence with zero weakening tokens**. A healthy-looking gate over
no evidence. The per-file loop it replaced was prefix-agnostic, so *the regression arrived with the
optimisation*. Fixed by pinning the renderer (`--no-ext-diff --no-color --src-prefix=a/
--dst-prefix=b/ --no-pager`), hardening the keying (exact match first, suffix only for renames,
per-file fallback for paths containing whitespace or `" b/"`), and adding an `EVIDENCE-EMPTY` floor
so zero bytes can never render as a clean small diff. Pinned by three hostile-config eval cases.

**3. A false completeness claim in consumer docs (`/flow:staff-review`, UX lens).** `workflow.md`
said DOC-BLIND names "every changed doc-shaped file it did not read". It names only files matching
flow's built-in guess. Measured: a changed `prompts/system.md` — this slot's *own second documented
example* — with the slot unset produces zero warnings. A false completeness claim about the
mechanism whose purpose is preventing false completeness claims, against this repo's own "Honest
limitations" bar. Corrected to state the guess's scope and that silence elsewhere is not coverage.

**Also mine, also found by review:** the slot-count scanner's comparison still read the count with
`claim.split()[0]` after the matcher learned the hyphenated form, so every `37-slot` compared as a
string against `37` and was flagged stale *whatever the number* — and my own fixture passed straight
through it, because a broken comparison flags hyphenated forms either way. Only a correct-count
fixture distinguishes the two. The same sweep never read `README.md` at all, which is why
`24-slot` sat on the front page against a 37-slot schema while the check stayed green.

**A near-miss with a permanent guard.** Hoisting `TESTDIRS`, a comment I wrote contained a literal
bang-backtick *inside a bang-span*. The host's span regex is `[^` + `]+`, so one backtick ends the
span early and silently demotes the rest of an executable gate to prose. `arg_placeholders.py`
documented this and nothing enforced it. Now checked across every shipped skill, paired with a
non-vacuity floor. Caught only because the evals assert files ARE read.

**Deferred, all in `roadmap.md` § Next with their measurements** — most importantly the one two
lenses found independently: Stage 1 and `auditor.md` both still instruct the reviewer that
**doc changes are not behaviours**, so B feeds it a `SKILL.md` diff and the prompt hands it a rule
for discarding it. That is the leading candidate explanation for the recall figures below, it
predicts their *shape* (perfect precision, disjoint misses), and it is not fixed here: it is a
reviewer-prompt change needing its own re-measurement.
