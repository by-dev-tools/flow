# `/flow:audit-coverage` gains a source-tree input mode

**Date:** 2026-09-20 · **Version:** v1.47.0 · **Branch:** `conductor/d1-a-audit-coverage-source-input-mode`
**Gates:** plan approved at the plan gate; all three plan-gate open calls resolved by the orchestrator under
§4.8 (low-stakes, reversible, high-confidence, low-taste — rule 7), none escalated.

## What

`/flow:audit-coverage` can now be handed a **source tree** instead of a diff:

    /flow:audit-coverage                      # unchanged — the workspace diff (the /flow:ship Step 2 path)
    /flow:audit-coverage <path>               # new — an approved prototype's source (file or directory)

One skill, **one** evidence block that dispatches internally on `$ARGUMENTS` — the same shape `/flow:audit-plan`,
`/flow:critique-plan` and `/flow:review-brief` already use for their optional path argument.

## Why

`dev-docs/research/2026-09-16-d1-auto-plan-quality-spike.md` — D1's §9.3 spike. An auto-written Spec-walk plan
scored **0/13 vacuous** (clean on criterion *quality*, confirmed testable by a live headless-Chrome dry-read)
while **under-declaring 10 real behaviors against 13–14 declared**, including an entire keyboard-only
interaction path on a prototype whose own code cites WCAG 2.1.1.

The mechanism is the part worth keeping: the pre-execution reviewers read the **plan** and the **brief**, and
*nothing reads the approved prototype's code*. `plan-critic` caught the keyboard gap only because that
particular brief happened to mention keyboard — luck, not design. What caught 10 of 12 gaps was a
coverage-style pass over the prototype's **source**.

## The design decision: an input mode, not a fourth reviewer

`audit-coverage`'s **input** is diff-shaped (`SKILL.md:90` builds its file list from `git diff`). Its
**judgment** is not: *"for each user-perceptible behavior change, check whether any declared criterion would
cause someone to test it"* (`:130`), scoped at `:129` to *"declared-vs-built completeness only, not criterion
quality."* That axis is what found the gaps, and it is already written, already tuned, already eval-backed.

So the judgment is reused **verbatim** and only the input path is new. The rejected alternative was a fourth
pre-execution reviewer with its own prompt: new judgment surface to maintain, drifting against the one that
already works, to re-derive a result the spike had already reproduced by hand using this reviewer's own framing.

**Tradeoff accepted:** one skill now carries two input modes, which is more conditional shell in a file that is
already dense. The alternative — a separate `/flow:audit-prototype` skill — would have duplicated the judgment
prose into a second file, and `.claude/rules/general.md` § Consistency item 2 is precisely about contract
values that live in N files and drift. Conditional shell in one file beats identical prose in two.

**Shape corrected at `/simplify`, and the correction is the more interesting half.** The approved plan proposed
a *second* `!` block gated by one prepended line. The altitude lens — which built and ran the alternative before
proposing it — showed that was one level too shallow: every other `$ARGUMENTS` dual-mode skill here dispatches
inside one block, and the second block was what generated all the surrounding machinery (a third copy of the
FB-0074 anchor; an `EXPECTED_GUARDS` 2 → 3 edit to a *shared* harness contract for a *local* reason; a restated
`DIFF_CAP` in a shell that cannot share a variable, plus a cross-check eval to hold the copies together; a prose
invariant the LLM had to honor; and an empty heading rendered into every diff-mode prompt). Merging them is
strictly subtractive and re-verified byte-identical. `SOURCE_CAP=$(( CAP * 2 ))` is now a genuinely shared
variable rather than a policed duplicate — and `run_root_anchor_evals.py` drops out of this PR's diff entirely,
which is the better version of a contract edit: the one you no longer need. The forced-mirror precedent
(`verify-build/lib/file_patterns.py` keeping a checked jq mirror) does **not** apply, because that duplication
is forced by a language boundary and this one was created by the block split.

## Three things the implementation had to get right

1. **The default `sourceFilePatterns` contains no `.html`.** Measured at plan time. The shared default the diff
   block uses (`SKILL.md:87`) matches `ts|js|py|go|...` — so naively reusing it on the reference prototype
   (`annotation-layer.html`) filters the file list to empty and renders a clean `[audit-coverage] SKIPPED`.
   **The feature would have reported "no undeclared changes" over a prototype it never opened** — the exact
   failure it exists to prevent, reproduced inside itself. Resolution: a **single named file is read verbatim,
   never pattern-filtered** (a human who names one file has already made the selection; re-deciding it by
   extension list re-opens the hole); a **directory** is walked with a prototype-oriented pattern set
   (html/css first — a prototype is a rendered artifact, not a service), deliberately *not* `sourceFilePatterns`.
2. **`SOURCE-UNRESOLVED` is its own outcome, never `SKIPPED`** (FB-0074's distinction, applied to a new sibling).
   Missing path, path outside the repo, newline-bearing path, empty walk, zero readable bytes — all route as
   "I never looked", never as "I found nothing to audit". If you named a path, an empty result is evidence the
   *input* is wrong, not that the work is covered. Asserted non-confusable with the skip line directly, the way
   `run_root_anchor_evals.py` pins it for `ROOT-UNRESOLVED`, and **paired** with §4b's positive: the real
   `SKIPPED` path still works, so deleting the skip branch cannot satisfy the suite.
3. **The cap is derived, not hardcoded.** The reference prototype is **60,805 bytes** against a **60,000-byte**
   diff cap. `SOURCE_CAP=$(( CAP * 2 ))` — one literal, one shell, genuinely shared. A bare `120000` is the
   FB-0010 fan-out shape, silently stopping to mean "twice the diff cap" the day that value moves. (The
   two-block draft could not share the variable and held two literals together with a cross-check assertion;
   the merge removed the fan-out instead of policing it, and §6 now asserts the duplication has not returned.)

## Evidence

**Diff mode is unchanged — measured two ways.** One-time comparison against `origin/main`: the diff block and
the criteria block each produce **byte-identical** output (355 bytes) in a temp repo rendering a real non-empty
diff, so the equality is not the vacuous "both empty" kind. The durable CI form needs no git ref (an
`origin/main` comparison stops meaning anything once this merges): §1 strips the mode-gate lines back out of the
shipped block and requires byte-identical stdout from both copies — the stripped copy literally *is* the
pre-change code path. `ship/SKILL.md` and `ship-spike/SKILL.md` are untouched.

**The instrument test (`.claude/rules/general.md` § Consistency item 4).** A measurement that can only return
"clean" is not a measurement, so §5 runs the real source block against the real `annotation-layer.html` and
asserts all **ten** spike-documented behavior anchors survive assembly — then validates that probe against a
context clipped at a measured 57,000 bytes, where finding 9 provably drops out and the probe **must** fail.

**Item 4 earned its place within days of landing (#157).** Writing the harness first surfaced three real defects
that a "does it run and return clean?" test would have passed:
- a **zero-byte named file** rendered the full source-mode header over nothing and read as a clean pass;
- the probe's **own negative control passed**, because every anchor token appears early in the file — a probe
  that could not return not-clean;
- the metacharacter assertion **failed on a correct refusal**, because it searched for a literal that the
  refusal message echoes back — an assertion that could not distinguish refusal from execution. Replaced with a
  filesystem side-effect canary.

**On the 2x cap, at the precision it was actually measured.** The coarse token probe *survives* a 60,000-byte
clip, so "the diff cap would have truncated the reference case" needed a sharper instrument than the probe: the
prototype's **third** `focusin` registration — the focus-restoration half of the WCAG 2.1.1 path the spike cites
at lines ~1146–1154 — sits at file byte 59,915 with its body running past 60,000, and is provably absent from a
60,000-byte clip. Asserted in **bytes**, not characters: the first version compared Python `str` slices against
a shell `head -c` cap on a file carrying non-ASCII punctuation, and passed by accident. The unit was wrong, not
the claim — and an assertion that is right about its claim and wrong about its unit **passes for the wrong
reason**, which is this PR's whole subject one level further down. A green check earned by a unit mismatch is
indistinguishable from one earned by the contract holding, which is the same indistinguishability that makes
`SKIPPED` and `SOURCE-UNRESOLVED` different lines.

**Live joint test (one authorized `flow:auditor` spawn) — the path works, and the number is not 10.** The joint
(new input feeding the existing judgment, end to end) was the one thing neither the instrument test nor the
spike had exercised: the instrument test proves the *context*, the spike proved the *judgment*. Fed the real
source block's output plus the spike's 13-criterion auto-plan, a fresh auditor returned **4 findings, all 4
real** — precision 4/4, zero false positives — covering **5 of the spike's 10 behaviors**: finding 1 (the
flagship keyboard/WCAG gap) reproduced independently, plus `snapPreview`, show/hide-pins, and bulk + single
delete consolidated into one finding. **Not reproduced this run:** panel open/close, per-row copy, the
storage-quota warning, the Escape state machine, discard-on-empty-close.

So the mechanism is confirmed end-to-end and re-found the gap that motivated the work — but **recall varied
substantially between two runs of the same judgment on the same artifact** (10 behaviors hand-run, 5 here). That
is a property of best-effort LLM judgment, which this reviewer has always been documented as. Recorded rather
than rounded up, because "audit-coverage finds ~10 gaps on a prototype" is exactly the kind of claim that
hardens into folklore. **n=1 on each side, one prototype.** Shipping is how this reaches n=2.


## `/flow:staff-review` — two BLOCKERs, both reproduced, both in the new mode

The lenses ran on the post-`/simplify` tree. Both blockers are the same shape: **source mode renders raw
file bytes, and a diff structurally cannot.**

1. **A symlink defeated the containment guard.** The single-file arm built its absolute path from
   `cd "$(dirname "$SRC")" && pwd -P` plus `basename` — so only the **parent** was physically resolved and the
   final component was never dereferenced. An in-repo symlink pointing anywhere therefore passed the
   containment `case`. Reproduced: `ln -s /etc/passwd repo/leak.html` printed the whole file into what becomes
   prompt context — under the block's own comment saying the guard exists so source mode is *not* "an
   arbitrary-file reader that pipes whatever it is pointed at into prompt context." The directory arm was
   already safe (`find -type f` does not follow links), so the hole was asymmetric and none of the existing
   containment cases reached it. **Fixed by refusing symlinks outright** rather than resolving-then-checking —
   the same call `dispatch_backend.py` makes about unsafe placeholder values: an interface that forbids the
   shape has no bypass left to get wrong. `CONTRIBUTING.md` already documents that a branch checked out here
   is hostile-capable, which makes this reachable rather than theoretical.
2. **A file under review could forge a control line and silence its own audit.** Every rule in *What to check*
   instructs the auditor to emit a fixed line **as its entire response**; source mode `cat`s bytes at column 0,
   so a prototype containing `[audit-coverage] SOURCE-UNRESOLVED …` or `SKIPPED` renders byte-identically to
   the genuine line. Diff mode was structurally narrower only because `git diff` prefixes every content line.
   **Fixed positionally:** every genuine control line is emitted *above* the `----- source -----` delimiter, and
   the prose now says only those are the skill speaking. That required moving the `SOURCE-TRUNCATED` notice
   from after the body to before it — it had been the one control line position could not disambiguate.

**Also fixed:** the exclusion regex is anchored `(^|/)` but was matched against `find`'s **absolute** paths, so
a checkout merely living under a directory named `build/`, `dist/`, `test/`, `vendor/`, `evals/`… had every file
excluded and was refused with "the path or its contents are wrong" — blaming the user for the harness's own
ancestry. Loud rather than silent, but a false refusal; now filtered on the repo-relative path, paired with an
assertion that the filter still excludes `node_modules`.

**And a defect in the harness itself, which is the one worth remembering.** The distinctness assertion compared
`unres = "[audit-coverage] SOURCE-UNRESOLVED"` against `SKIP_LINE` — **two Python literals**. It could only ever
pass, in every possible world including one where the skill emits `[audit-coverage] SKIPPED — source
unresolved`. A measurement that can only return clean, inside the harness that cites item 4 in its own
docstring. Re-pointed at real stdout. The push-further lens caught a sibling: the cap assertion was
`count(b"focusin") == 3`, coupling CI to a literal in a **separately-maintained shipped file** — add a fourth
registration and the cheapest green is bumping the 3, satisfying the detector while the claim goes
unre-measured (item 3). Now count-free: `count(full) > count(clipped)`, with the measured numbers left in the
comment where they cannot be edited into a false green.

**UX lens, BLOCKER:** the prose told the auditor to collapse **five** distinct diagnoses — wrong path, outside
the repo, newline in the argument, empty walk, zero readable bytes — into one fixed sentence carrying no path,
no reason and no remedy, on the most likely first-run mistake of a brand-new argument. The block had already
done the careful work; the prose threw it away. It now requires the block's own line quoted **verbatim**, and
the harness asserts the causes stay *distinguishable* — which is what makes the verbatim rule worth having.

**One finding pushed back on.** The push-further lens read the shell tail ("This is NOT a clean skip") and the
prose ("This is not a clean pass") as a drifted contract. They are not: across this whole file the shell always
says *skip* and the prose always says *pass*, including for the pre-existing `ROOT-UNRESOLVED` and `JQ-MISSING`
rules. It is a consistent convention, not drift. The overstatement was in my own comment claiming the tail was
"a contract with the What-to-check prose"; the comment was corrected rather than the code.

**Design-engineer + push-further, applied:** the index line says `files selected (N)` one path per line rather
than `files read:` space-joined — "read" would contradict `SOURCE-TRUNCATED` in the same artifact, and
space-joining rendered a prototype under `design mocks/` as two apparent entries. And source mode must now open
its output with a `Read: <files>` line: *"I found nothing in these three files"* is falsifiable at a glance by
the one reader who knows what is in their own prototype; *"I found nothing"* is not.

**Deferred to the roadmap, not fixed here:** the remaining forgery surface (`SOURCE-TRUNCATED` needs a nonce or
a byte-count assertion for full immunity), source mode's inability to name its own plan (criteria stay pinned to
`planPath`, so a queued second prototype would be audited against stale criteria — a real hazard for Track B's
`.flow/prototypes/<slug>/` shape), `SKIPPED`-on-empty-criteria arguably being wrong in source mode, and a
`designLanguagePath` that has no conventions for "the prompt as a rendered artifact" despite that being flow's
highest-traffic rendered surface. The staff lens also proposed a pointer comment inside `annotation-layer.html`
naming its eval dependents — **declined here specifically**: that file is under `verify-build/**`, which is
`sensitivePaths`, and touching it would change this PR's stakes classification for a comment.


## `/flow:security-review` — a live RCE in the new mode, and the eval that certified it safe

**The finding.** `$ARGUMENTS` is **textually substituted** into a `` !` `` block before the shell parses it,
and is **not** shell-escaped. Claude Code says so itself, in the Gemini-command-import guard inside the shipped
binary: Gemini escapes its placeholder inside a shell span, *"Claude Code's `$ARGUMENTS` substitution doesn't,
so importing would let typed arguments inject shell commands."* I verified the string in the binary and
reproduced the execution before acting on either.

So `SRC="$ARGUMENTS"` — the obvious, house-idiomatic form, the one three sibling skills use — is a
**render-time command-execution sink with no Bash-tool permission prompt**, bypassing the harness's entire
command-approval gate. Quoting is not a defence: `$( )` expands inside double quotes. Measured on this block
before the fix: an argument of `README.md"; echo "PWNED:$(id -un)"; :"` executed **twice** (once per
substitution site) and the block then rendered normally, so the output looked entirely clean to a reader.

**Every guard this PR had already added was downstream of it.** Containment, the symlink refusal, the newline
refusal, `SOURCE-UNRESOLVED` — all operate on `$SRC`, i.e. after the shell has already run the payload. They
were path guards on an already-won shell.

**The mitigation — and it is a mitigation, not a fix.** A quoted-delimiter heredoc capture makes the
substituted text literal to the shell, which neutralises every *single-line* payload class: quote-break,
command substitution, appended subshell, semicolon chain. All measured inert with a filesystem canary.

**But the re-review defeated it, and the correction matters more than the fix.** A payload containing a line
equal to the delimiter escapes the capture and executes — verified with a canary against this exact block. The
first version of this entry called the delimiter "long and unguessable"; that claim was worthless, because the
delimiter is a published literal in a world-readable shipped file. It costs an attacker one extra payload line.
And the newline refusal then fires *after* execution, printing a correct-looking `SOURCE-UNRESOLVED` — so the
run reads clean, which is the exact "looked entirely clean to a reader" failure this entry describes for the
original bug, reproduced by its own fix one commit later.

**No static delimiter can close this.** Substitution happens before the shell parses, so lines 2..n of a
multi-line payload always land at column 0 in some shell context. The real fix is for the argument to leave the
`!` block entirely — a house-idiom decision across four skills, escalated rather than taken at ship time
(security-sensitive, competing options of comparable merit, and it sets the idiom: all three FB-0011 triggers).
It is pinned as a **KNOWN RESIDUAL in the eval, asserted in its true vulnerable state**, so the suite cannot
print "all passed" over a live hole and a future fix makes the pin go red on purpose.

Other residual named in the block:
- **the placeholder must appear exactly once in the block, inside the heredoc.** A second occurrence *in a
  comment* is a live injection site, because a multi-line payload leaves lines 2..n as executable code. I
  introduced exactly that while writing the fix — three of the four occurrences were in the explanatory comment
  — and it is now an asserted invariant rather than a thing I must remember.

Also handled: an unsubstituted placeholder (direct shell run, older host) previously would have yielded the
literal token as a path; it now degrades to no-argument.

## The part worth keeping: the harness certified the RCE as safe

`run()` passed the argument as `env["ARGUMENTS"]`. Under that model the shell always sees one quoted word, so
this assertion —

```python
check("shell metacharacters do not EXECUTE (the argument is always quoted)", not canary.exists(), ...)
```

— **could only ever pass, in every possible world, including the one where the shipped block had a live RCE.**
It did. A measurement that can only return clean, inside the harness whose own docstring cites
`.claude/rules/general.md` § Consistency item 4. And `dev-docs/plan.md`'s criterion *"`$ARGUMENTS` cannot escape
the repo root or inject a verdict line"* was checked off on the strength of it.

`run()` now renders the block the way the preprocessor does — textual substitution — so every assertion in the
file is measured under the real model, and six injection payloads are asserted non-executing via a filesystem
canary **paired with a positive that the canary itself fires**. Fixing the code without fixing the instrument
would have reproduced the certification.

**This is the third distinct instance of the same defect class in one PR**, which is the honest reason to think
the rule is load-bearing rather than decorative: the probe that could not return not-clean, the distinctness
check comparing two Python literals, and now the injection test that could not observe injection. In all three
the *code* was fine or fixable; the *instrument* was the thing reporting green.

**Systemic half, routed not fixed:** `/flow:audit-plan` (2 sites) and `/flow:critique-plan` (4 sites) have the
same sink, reproduced. `/flow:review-brief` does **not** — its placeholder sits in a documentation code fence,
not an executed span, correcting the security review's claim. Fixing two more shipped skills is a house-idiom
decision across files outside this diff, so it is a `[security] decision-required` manifest entry plus a roadmap
entry carrying the measured fix idiom — with the instrument half stated explicitly, because that is the half
that gets forgotten.

## Provenance (FB-0107)

Measured in this workspace before any verification was believed: **installed plugin 1.29.0** (`gitCommitSha
cf783ac`) against a working tree at **1.45.0** — sixteen releases stale. So `Skill("flow:audit-coverage")` in
this session resolves 1.29.0's `SKILL.md` and **structurally cannot exercise the mode this PR adds**. Every
verification above ran the extracted shell block under the **Bash tool** (working tree), never via the skill.
If a later reviewer proposes "just dogfood it through `/flow:ship`" as evidence for this change, that is not
evidence — it is the previous release reviewing itself. Substitute evidence, labelled, per #150.

## Scope held

No D1 Phase 3. No auto-plan writing. No wiring into a Step 6 that does not exist. No change to `/flow:ship`
Step 2 or `/flow:ship-spike`. No fourth reviewer and no new judgment prose — the `What to check` section gained
only mode-scoping for the new not-clean outcomes; `:129`/`:130` are untouched. No edit to
`dev-docs/handoffs/d1-prototype-first-gate.md`, including its known §0/§8-vs-§9.3 self-contradiction about
whether the spike gates Phase 2 or Phase 3. §9.3 itself is **not** resolved — this closes the *mechanism* gap
the spike identified; the Phase-3 design decision (spike option (a) vs (b)) remains the orchestrator's.

## Files

- `plugins/flow/skills/audit-coverage/SKILL.md` — the source block, the one-line diff-mode gate, mode-scoped prose
- `plugins/flow/evals/run_coverage_source_mode_evals.py` — new, 81 checks, CI-wired
- `plugins/flow/evals/fixtures/coverage_source_mode_undeclared_context{,.expected}.{md,txt}` + `ground_truth.yaml`
  — offline-validated fixture pair, the same tier as the three diff-mode coverage fixtures (it pins the
  assembled-context shape and the output schema; it does **not** demonstrate live LLM behavior)
- `plugins/flow/docs/workflow.md`, `README.md`, `skills/workflow-help/SKILL.md` — two-input-mode wording
- `plugin.json` / `marketplace.json` → 1.47.0; `changelog/v1.47.0.md`
