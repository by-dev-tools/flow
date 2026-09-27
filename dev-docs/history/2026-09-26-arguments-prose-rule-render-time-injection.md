# `$ARGUMENTS` leaves the shell block — the prose rule

**Date:** 2026-09-26 · **Version:** v1.50.0 · **Branch:** `conductor/arguments-idiom-render-time-injection-fix` · **Feedback:** FB-0116, FB-0117

## What

A render-time command-execution sink in every flow skill that takes a path argument, closed by one house idiom applied at four sites, plus a second placeholder family nobody had noticed.

`$ARGUMENTS` is substituted **textually into the whole skill body before anything parses it**, and is not shell-escaped. A `` !` `` span containing it therefore runs attacker-chosen commands at render time, with no interactive permission prompt. Sites on `main`: `audit-plan:13` (×2), `critique-plan:43/57/58`, `audit-coverage:168`, all `!`-spans; `review-brief:69` (×2) in a fenced block.

- **`plugins/flow/lib/arg_placeholders.py`** — the predicate, with the host's own regexes transcribed from the shipped bundle, plus a faithful `cde()`/`xS()` emulation. One definition, several readers.
- **Tier 1 (the agent Reads it)** — `audit-plan`, `critique-plan`. The `!`-block runs argument-less; the placeholder appears once, in prose, under `## Argument`; the reviewer uses its own `Read`.
- **Tier 2 (Write-then-path)** — `review-brief`, `audit-coverage`. The model writes the raw value with `Write`; the block reads a **fixed literal** path. New `extract_session.py --plan-file-from PATH`, which **refuses** a multi-line value rather than taking line 1.
- **FB-0117, a separate live bug** — `$0`–`$9` are the same mechanism, so `/flow:ship <any argument>` was corrupting ship's own FB-0107 provenance block (`awk 'index($0,H)'`, `$0` → first argument token). Fixed at `ship`, `doctor`, `contribute`, `verify-build`.
- **`run_arg_safety_evals.py`**, CI-wired — 30 checks.

## Why

The direction was not in question; FB-0108 had already reached it for a different sink, and `/flow:land` + `/flow:post-merge` already carried their arguments in prose without interpolating anything. What needed establishing was the *mechanism*, once, before it fanned out six ways.

**Why not a delimiter, a heredoc, or better quoting.** Substitution precedes parsing, so lines 2..n of a multi-line payload always land at column 0 in some shell context. v1.41.0 shipped a quoted-delimiter heredoc and it was defeated by a payload whose second line equalled the delimiter — and the newline guard then printed a correct-looking refusal *after* the command had run, so the run read clean. Every text boundary can appear in the text (FB-0108 rule 2).

**Why two tiers rather than one.** The obvious single answer — "the agent writes the value somewhere and the block reads it" — is impossible for three of the four sites. `audit-plan`, `critique-plan` and `audit-coverage` are `context: fork` with `agent: auditor`/`plan-critic`, whose grant is `tools: Read, Grep`: no `Write`, no `Bash`, and the block renders *before* any agent acts, so nothing can write a file for it to read. Tier 1 exists because of a tool grant, not a preference.

## Tradeoffs

- **`critique-plan`'s deterministic pinning lint degrades in plan-file mode.** `plan-critic` cannot run Python, so under Tier 1 the lint can only read the session-extracted plan. Rather than silently linting the wrong document, the block now **prints its own scope** and the prose routes a named plan file to the file's existing "treat pinning as UNCHECKED, not clean" line. The alternative — restructuring `critique-plan` to main-thread + `Agent` — is a change to a reviewer's execution model inside a security PR, i.e. fanning out an untested pattern to fix an untested one. Routed to the roadmap with the tool-grant reason stated.
- **`audit-coverage`'s coverage of its own argument is not uniform, and the skill says so.** Its directory walk needs `find`/`grep` that the auditor does not have, so the fix takes the value from a fixed scratch file (Tier 2, which `/flow:ship` can populate) and the prose carries a Tier-1 fallback for direct invocation — with a required `WEAKENED · FILTERS-ADVISORY` line, because a reader must be able to tell a mechanically-filtered read from a hand-filtered one. Named as a residual in the skill, with the real fix (derive the path from config; `.flow/prototypes/<branch-slug>/` is already canonical) routed to the roadmap.
- **A ~10-line change at the capture point, not a 170-line excision.** Excising `audit-coverage`'s source mode would have demolished `run_coverage_source_mode_evals.py` and a feature merged four days earlier. Replacing only the capture closes the hole completely and leaves every guard, filter, cap and test intact.
- **`--plan-file` is kept, deliberately.** FB-0108 removed `--finding` because that flag carried free *text*, so every argv spelling was unsafe. This flag carries a *path*, which is what a correct caller has; the hazard was never the parameter but the shell interpolation in front of it. Closing it at the parameter would mutilate a correctly-used interface and leave the real hazard untouched. It is closed where it lives — in the skill body, by the lint.

## What went wrong on the way, because it is the useful part

Five instruments of mine reported a wrong answer, and each was caught by a different discipline. They are listed because the disciplines are the transferable part:

1. **`${0}` inside awk.** The brace fix is right for shell and a **syntax error** in awk, so my "fix" broke ship's provenance function while reading as correct. Caught by asserting the extracted function's *output* is identical bare vs. under a 3-token argument — behaviour, not text. `$(0)` is the awk-safe spelling.
2. **My own comments were injection sites.** The comments I wrote warning about `$0`–`$9` contained bare `$0`, `$9` and `$1`. Documentation about the hazard, written as the hazard. Caught by the lint I had just added.
3. **The lint itself had a gap that certified a live hole.** I wrote the matcher's escape rule
   as a naive `(?<!\\)` lookbehind. The host's actual escape arm is `(?<!\\)\\\$`, which consumes
   `\$` only when that backslash is not itself preceded by one — so **two** backslashes leave the
   placeholder LIVE, and my lookbehind silently passed every run of 2+. `\\$ARGUMENTS` inside a
   `` !` `` block would have been reported clean over a working injection site. A lint with a gap
   is worse than no lint, because it certifies. Found by tabulating the host's three substitution
   arms against the matcher in both directions — miss *and* over-match — rather than by spot
   checks; now pinned as `test_host_agreement`, 15 rows.
4. **And the test I wrote for that gap asserted on a proxy.** It compared "did the rendered text
   change", which cannot distinguish a substituted value from a *consumed `\$` escape*, and which
   reports no change for `$9`/`$10` unless the argument happens to have a token at that index. It
   failed against correct code three times. The honest oracle is whether the payload token reaches
   the output — FB-0004, in the harness built to enforce FB-0004.
5. **A collision check that returned COLLISION for all 115 branches**, including this one, which touches no such file — it diffed stale branches against an advanced `main` instead of merge-base. `.claude/rules/general.md` § Consistency item 4, in my own instrument, caught only because a known-negative came back positive.

**The residual pin flipped as designed.** #159 shipped its delimiter-collision check in its true *vulnerable* state (`check(…, canary.exists())`) with instructions naming whoever closed it. It went red on this fix; the polarity is flipped and the payload is **kept**, so a future author reintroducing any delimiter scheme meets the payload that already refuted it.

**The brief's own exclusion list was refuted by measurement.** It classified `review-brief:69` as not-exposed because it is fenced — an inferred mechanism, never measured. The host's replace is over the whole body, so the value does arrive; the fence changes only who executes it. Included. That is FB-0116 rule 3, and the fourth time in this program an inferred mechanism lost to a measured one.

## Third review round — `/flow:staff-review`, and why it was worth re-running

The first ship attempt could not run staff-review: all three lens spawns died on an account
session limit, so it was routed as a `[rigor]` draft-manifest entry rather than waived. Re-running
it five hours later found **four more BLOCKERs**, two of which the *earlier* rounds had created:

1. **A measured live lint bypass.** The fence classifier had been widened to accept *indented*
   fences; it was still blind to **blockquoted** ones (`> ```sh`), and `ship/SKILL.md` carries two
   of those wrapping real shell the skill tells the model to run. A live placeholder planted inside
   that block classified `prose` — the lint reported CLEAN over a live site, which is exactly the
   failure its own comment claims to prevent. The lesson is item 4 again, one level up: fixing one
   *cause* of parity inversion is not closing the *class*. Now a five-row table (column-0,
   indented, blockquoted, tilde, blockquote+indent), each validated on a known positive, paired
   with a positive that genuine prose still reads as prose.
2. **`/flow:review-brief <path>` silently ignored its argument on any branch containing `/`** —
   i.e. every branch in this repo. The stamping fix slugified the branch in the block, while the
   prose told the model to write an *unslugified* name; `[ -s ]` was then false and the run fell
   back to session mode, reviewing the wrong document with nothing printed. The fix is that nobody
   composes the name any more: `arg_placeholders.py --arg-path <skill>` prints it, the block echoes
   the path it will read, and an eval asserts the Python printer and the shipped shell derivation
   agree byte-for-byte on four branch shapes — including one with a `/` and one non-ASCII, where
   `tr -c` (byte-based) and a codepoint regex had genuinely disagreed.
3. **A contradiction with no stated precedence.** `audit-coverage`'s path 2 said "if you see a
   `SKIPPED` line despite being given a path, read the path yourself"; a later rule said a `SKIPPED`
   diff means "output exactly that line as your entire response." Source mode's main use is a
   pre-execution run where an empty diff is *expected*, so a compliant agent could emit "nothing to
   audit" for a run that named a path — the collision the file spends three bullets forbidding.
4. **The canonical doc misspelled its own subject at five sites** (`\ARGUMENTS`, no `$`) and, worse,
   its rule sentence advised the **two-backslash** escape — which this PR had already measured to be
   *live*, because the host's escape arm fails its own lookbehind at 2+. The section teaching the
   safe spelling named an unsafe one.

Also from that round: a rebase artifact had resurrected a superseded plan block that said "this
branch" about a *different* branch; the Spec-walk credited `run_review_brief_evals.py` with pinning
Tier 2 when it invokes `--plan-file` directly and never touches that channel; and the host
transcription carried no provenance, in a repo that ships `plugin-provenance.py` on the premise
that an unstamped version claim is worthless.

**Three of my test oracles were wrong rather than the code**, across the three rounds — "did the
text change" instead of "did the payload leak", `${0}` in awk, and an assertion string that did not
match the shipped refusal. Each was caught by running the thing rather than reading it.

## Verification

- `run_arg_safety_evals.py` (new, CI-wired) **validates its instrument on a known positive first**: it renders the historical unfixed `audit-plan:13` and asserts the filesystem canary **is** created (4 of 7 payloads execute), with a negative control proving the payloads are inert when no placeholder is present — then **aborts** rather than continuing if that does not fire, because every later "no canary" would be unfalsifiable. The ancestor of this harness certified this exact RCE as safe by modelling `env` instead of substitution.
- Canary is a **filesystem artifact**, never a string search: a refusal message echoes the payload back, so string matching cannot distinguish "refused" from "executed, then printed a refusal" — which is precisely how v1.41.0 read clean (FB-0004).
- Every negative is **paired with a positive** that the skill still accepts and still acts on its argument, so deleting the feature turns the harness red.
- **38/38 eval harnesses green**, plus `dev-docs/check-index.py` and both tools suites.
