> **Status: PLAN — AWAITING BEN'S APPROVAL AT THE PLAN GATE (2026-09-13).** Not executed, no PR authorized.
> Critiqued by `flow:plan-critic` (4 findings: 2 BLOCKER, 1 REDIRECT, 1 FOLLOW-UP) and audited by
> `flow:auditor` (3 findings). All 7 applied; the diffs they forced are marked inline. Both were
> spawned directly over the FB corpus rather than via `/flow:critique-plan`, because the installed
> plugin is 1.29.0 and cannot resolve the directory-valued `referenceGlob` — it would have run
> document-blind (FB-0107).

# PLAN — Session-efficiency program (Anthropic session-value guidance)

**Status:** PLAN ONLY. Not executed. Plan gate is Ben's.
**Mode:** program (multiple sequenced PRs), not a single PR.
**Base:** `origin/main` @ a156228, v1.41.0.
**Version/FB:** deliberately UNCLAIMED — this plan authorizes no single PR, and claiming a
number for a program that ships in four parts is how collisions happen. Each PR claims at
execution time, re-swept against `origin/main` AND open branches (T5).

## Restated request

Evaluate flow's process against Anthropic's "maximizing the value of your Claude Code
sessions" guidance, then plan how to adhere to it. The problem: the shared five-hour
rate window is the program's binding constraint (canonical §1 req 6, which IS a recorded
measurement), and we hit it — a `/flow:security-review` subagent died on HTTP 429 mid-ship on
2026-09-13.

**Provenance of that second claim, flagged by the audit pass and corrected here: it is
OBSERVED-IN-SESSION AND UNRECORDED, not measured-and-retrievable.** No repo artifact records
it; a repo-wide grep for the date returns nothing. It is the motivating evidence for the whole
program, and this plan closes two alternatives on a chain that starts from it, so a future
reader must not inherit it as measured. **If it matters to the decision, the honest fix is to
write the FB entry at execution time and cite it here** — not to keep re-asserting it. The
standing §1 req 6 constraint does not depend on it and stands on its own.

## Measurements (taken 2026-09-13; these ground every claim below)

| Surface | chars | ~tokens | prose | shell |
|---|---|---|---|---|
| `ship/SKILL.md` | 150,465 | ~40,700 | **65%** | 29% |
| `verify-build` | 57,839 | ~15,600 | 80% | 20% |
| `doctor` | 52,778 | ~14,300 | 30% | **67%** |
| `ship-spike` | 52,588 | ~14,200 | 68% | 32% |
| always-loaded (`CLAUDE.md` + 3 rules) | 29,128 | ~7,900 | — | — |

**Counting rule, stated because an audit caught that it was not** (and stating it moved two
numbers): **shell = content inside ` ```sh ` / ` ```bash ` fences, fence lines excluded.
Untagged fences and ` ```markdown ` fences count as PROSE.** An earlier revision counted any
fenced content as shell, which inflated `ship` from 29% → 34%: it carries three ` ```markdown `
PR-body templates and five untagged output samples. Without this rule, Spec-walk criterion 2's
±2% band could go red on a definitional mismatch with nothing wrong in the tool — and Phase 1
is the PR whose whole job is making these numbers reproducible.

Two findings that **refute** the orchestrator's first-pass proposal and are the reason this
plan is not what was described to Ben in chat:

1. **"Move the war-stories out of ship" is low-yield.** Only 58 prose lines (~8% of ship's
   prose, ~4% of the file) cite FB numbers / dogfood history. The bulk of ship's 65% prose is
   *instruction*, not rationale. A rationale-extraction pass would reclaim single-digit
   percentages while risking the anti-drift property the repo depends on.
2. **There is no single lever; the profile inverts per skill.** ship is prose-dominated;
   doctor is 69% shell. A one-size remedy would under-serve one and over-serve the other.
   ~29% of ship's *shell* is `#` comments — rationale hiding inside code blocks, which is the
   one place extraction is both safe and meaningful.

## Scope — in

**Phase 1 — make the measurement continuous and correct (one small PR).**
`tools/harness_audit/harness_audit.py:157` miscounts the 85 KB `workflow.md` as always-loaded
(a live bug in merged #136). Fix it, and extend the tool to emit the prose/shell/comment split
above per skill.

**This fix already has an owner — roadmap AB Step 1b — so Phase 1 must say what it consumes
rather than claim it twice.** Phase 1 **absorbs and closes** the `roadmap.md:391`
always-loaded-miscount bullet, and updates AB.1b in the same PR to say so. It explicitly does
**NOT** take AB.1b's two sibling fixes to the same file — the gitignored per-clone `.last-audit`
(`roadmap.md:387`) and `audit_due()` coupling "checked" with "consumed" (`roadmap.md:388`) —
which stay open under AB.1b and are named here so a future reader does not find them silently
absorbed. AB.1b's queued "extend the audit to ship-pipeline gates/steps" (`roadmap.md:379`) is
also untouched. Rationale: every later phase is justified by these
numbers, and right now they come from an orchestrator running `wc -c` by hand. A program
whose evidence is not reproducible is not measurable at the end.

**Phase 2 — orchestrator operating discipline (docs only, free).**
Codify in `research/orchestrator-field-manual.md` + canonical §4.8: **the orchestrator seat
dispatches, it does not implement.** Evidence: this seat ran >24h in ONE session doing
orchestration + succession + doc authoring + a full implementation PR with two lens spawns,
loading ~52K tokens of skill prose (ship + staff-review + security-review) into the most
expensive context in the fleet. That is the article's anti-pattern #16, self-inflicted.
Also codify: set model/effort at dispatch and never mid-session (#9/#17 — mid-session switches
break the prompt cache).

**Phase 3 — extract shell from the shell-dominated skills (one PR, `doctor` first).**
`doctor` is 67% `sh`-fenced. Move it to `lib/*.sh` invoked by name, **and rewrite the two eval
call sites that extract those fences by heading** (`run_design_language_scaffold_evals.py:154`,
`run_merge_status_evals.py:310`) to assert against the extracted scripts instead. Those two are
in scope; the PR is not shippable without them. This is better
engineering independent of tokens — shell in a `.md` is unlintable, untestable, and re-parsed
by an LLM on every invocation. `doctor` first because it is the highest shell ratio and the
lowest blast radius (it is a diagnostic, not a gate).

*(Phase 4 — moving where ship's tokens land — is deliberately NOT in scope. It lives under
Open call 1 as an undecided question. It was previously listed here, which authorized it by
placement while Open call 1 recommended deferring it: an executor reading Scope-in would have
seen four approved phases, one reading Open call 1 would have seen three.)*

## Scope — out, named

- **Rationale-extraction from ship prose.** Measured at ~4% of the file. Not worth the
  anti-drift risk. Explicitly rejected, not deferred.
- **Touching `ship/SKILL.md`'s content in Phases 1–3.** It is gate machinery and it has an
  in-flight PR (FB-0108, +272 lines). Any edit collides.
- **Re-pointing `flow.config.json` slots, or any consumer-visible contract change.**
- **Model routing (the user's area (c)) — DEFERRED to roadmap M, and this is an explicit
  narrowing decision, not an omission.** Recommendation: keep it out. **Confidence: HIGH.**
  Justification: verifying that a subagent's `model:` frontmatter actually routes is a
  *measurement* PR, and `roadmap.md:366` records that `shadow_sampler.py`'s real-invocation
  path has no CLI entry point at all — so it is a build, not a check. `roadmap.md:368` further
  states that routing any subagent off Opus "remains a separate, future, data-gated decision."
  Bundling that into a weight-reduction program would put an unbuilt measurement harness on the
  critical path of three small PRs. Phase 2's "set model/effort at dispatch, never mid-session"
  does NOT discharge this — that is the article's prompt-cache hygiene item (#9/#17), a
  different concern from whether routing works at all.
- **`/compact`, `/clear`, `@`-notation, `/context` discipline.** These are the article's
  cheapest wins (#1, #2, #3, #10) but they are *Ben's* session habits, not repo changes.
  Named here so they are not silently dropped; they belong in a one-page operator note, not
  in a PR.

## Spec-walk

- [ ] `harness_audit.py` no longer counts `workflow.md` as always-loaded, **paired with the
      positive assertion that the always-loaded set still resolves `CLAUDE.md` and the
      `.claude/rules/*.md` glob.** Both halves, one check. → verify: RED against the current
      line 157 for the negative; RED against an emptied `static_paths` for the positive.
      *Without the pairing this is `general.md` rule 3 exactly — "excludes `workflow.md`"
      passes in two opposite worlds: the entry was removed (the fix), or the list was emptied
      (the deletion). Criterion 5 below was already paired correctly; this is copying it.*
- [ ] `harness_audit` emits per-skill prose/shell/comment char splits matching the table
      above within ±2%. → verify: run it against `ship` and `doctor` and diff against the
      hand-measured values recorded here.
- [ ] The field manual and canonical §4.8 both state the dispatch-not-implement rule, and
      name this session as the worked counter-example. → verify: grep both files.
- [ ] `doctor`'s fenced shell drops below 20% of its chars, with behaviour unchanged.
      → verify: `run_*_evals.py` for doctor green before and after; harness_audit delta.
- [ ] No skill's total char count INCREASED. → verify: harness_audit before/after table.
      Paired positive: at least one skill's count decreased by >30%, so the check cannot be
      satisfied by changing nothing.

## Assumptions

- **A1 — the article's guidance transfers to a multi-session fleet. MEDIUM.** It is written
  for a single developer in one session. Our topology already implements its core thesis
  (#16) at the fleet level — each worker is its own workspace. *If it flips:* Phases 1 and 3
  stand on their own engineering merits; Phase 2 is the one that depends on it.
- **A2 — extracting shell to `lib/*.sh` reduces tokens in practice. MEDIUM, and it is the
  assumption most likely to be wrong.** The skill must still *describe* what each script
  does, so some prose returns. Net saving is unmeasured. *Mitigation:* Phase 1 lands first
  precisely so Phase 3 can be measured rather than asserted.
- **A3 — no consumer depends on reading shell inline from a SKILL.md. ~~HIGH~~ → REFUTED, and
  Phase 3 is re-scoped because of it.** The audit pass disproved this and the disproof is
  verified: `plugins/flow/evals/run_design_language_scaffold_evals.py:154` and
  `run_merge_status_evals.py:310` both call `eval_utils.fenced_block(doctor_skill_text, "Check
  2.N —")` — they locate a fenced block **by heading** and then assert on its **literal source
  text** (`'P="core-docs/' not in block`, `'P="dev-docs/' in block`). Extracting that shell to
  `lib/*.sh` deletes the fence they index into.

  Note *why* the original HIGH was unearned: the coupling runs through a helper named
  `fenced_block`, not through any string naming shell, so the `git grep` that justified HIGH
  could not have surfaced it. A confidence verdict is only as good as the search that backs it.
  **Consequence:** Phase 3 is a coordinated skill **+ eval** refactor, not a single-file
  extraction, and `doctor`'s "lowest blast radius" ranking loses one of its two supports (the
  other — that `doctor` is not in `sensitivePaths` and nothing in the ship pipeline invokes it
  — was independently verified and stands).

## Deletion criteria (FB-0088)

- Phase 1's split-reporting is deleted when a first-party harness reports it.
- Phase 2's rule is deleted when `/flow:orchestrate` enforces dispatch mechanically.
- **Phases 1–3 are complete when `doctor`'s shell ratio is below 20% of its chars and the
  per-skill split report is reproducible from the tool rather than by hand.** That is a target
  these phases can actually reach.
  *An earlier revision set the bar at "no skill above ~20K tokens." Measured, every surface
  except `ship` is already under it — so that was a statement about `ship` alone, the one file
  Phases 1–3 exclude and Open call 1 recommends deferring. The program would have been
  unable to reach its own completion criterion by construction.*
- **The program's wider question closes** when a measured run shows whether skill weight is or
  is not the binding constraint. "It is not" is a real possible outcome and is not a failure —
  it would retire Open call 1 without building anything.

## Open calls for the human

**1. THE BIG ONE — does ship's pipeline move into a subagent?** The article's #13/#15 say run
noisy jobs in subagents so the intermediate work does not persist. `/flow:ship` is the one
place flow does NOT use the pattern it uses well everywhere else: the four lenses, the
auditors and the critics all fork and return summaries, while ship's ~40K tokens land in the
worker's main session and are carried through every later turn.
- **Recommended: NOT YET.** Confidence: MEDIUM-HIGH that it is the biggest lever; MEDIUM-LOW
  that it is safe today. Ship writes commits, drives the PR, and hands off to the human gate
  at Step 8; and flow has been bitten twice by fork boundaries already (FB-0074 root
  resolution, FB-0082 `/tmp` transport). Moving gate machinery across a fork boundary
  re-enters that hazard class for a token saving we have not yet measured.
- **The cheaper 80%:** Phases 1–3 first, then re-measure.

### Phase 4 — the decision gate, and what makes it answerable

**Ben, 2026-09-14: "don't move it yet, but prepare things to move in that direction. Does the
plan have a path to it?" The honest answer was NO — the plan had a deferral with a vague
re-measure trigger, not a path. This section is the fix.**

The decision is not currently *deferred*; it is **unanswerable**, because three things are
unknown. Name them and the decision becomes a calculation rather than a judgement call.

**Precondition A — the pure/impure inventory. This is the missing piece.**
Ship's steps divide into those that CAN cross a fork boundary and those that cannot:

| | examples | can it fork? |
|---|---|---|
| **Pure** — read, judge, report | the four reviewers, `audit-skips`, `audit-coverage`, manifest classification/triage, the doc-currency *checks* | yes — and four of these already do |
| **Impure** — side effects the parent owns | `git commit`, `gh pr create`, body/draft writes, the Step 8 human hand-off | no |

Nobody has inventoried which steps are which, or how many of ship's ~40,700 tokens sit on
each side. **If the pure fraction is ~70%, moving is a large win; if it is ~20%, the hazard is
not worth it.** That single number decides Phase 4, and producing it is a read of one file —
Phase 1's tooling can emit it per-section once it already walks the fences.

**Precondition B — is the fork boundary actually safe now?**
Flow has been bitten twice here: FB-0074 (a forked skill could not resolve the repo root and
validated every unverifiable skip as LEGITIMATE) and FB-0082 (a fork could not see the `/tmp`
handoff the parent wrote, silently disabling the skip gate from v1.13.0). Both have fixes —
repo-local `.flow/`, the `flow_stamp` refusal — and **ship already forks four reviewers
successfully today, which is the working precedent.** What is NOT established is whether
ship's own *orchestration* can fork, which is a different question because it writes. Needs an
audit of the remaining gaps, not a guess.

**Precondition C — a measured baseline.** Phase 1 delivers this. Without it the payoff is
unfalsifiable.

**And the part that answers "prepare things to move in that direction":**

> **Phase 3 IS the rehearsal.** Extracting `doctor`'s 67% `sh` to `lib/*.sh` is the low-stakes
> version of exactly the move ship would need — a skill delegating its mechanics to invoked
> scripts rather than carrying them inline. It forces us to solve the eval-coupling problem
> (two suites index `doctor`'s fences by heading) which is the *same* coupling ship would hit,
> on a diagnostic where a mistake costs a re-run instead of a bad merge gate.

So Phase 3 is not merely a parallel efficiency win; it is the de-risking step. That reframing
is why the phases are ordered as they are, and it should survive into execution: **if Phase 3
turns out to be hard, that is the strongest available evidence that Phase 4 should not be
attempted** — and learning it on `doctor` is the cheap way to learn it.

**Phase 4 is authorized only when A, B and C are all in hand, and is re-presented at the plan
gate with the pure-fraction number attached.** Not before.

**2. Do Phases 1–3 ship as three PRs or one?** Recommended: three. Confidence: HIGH. They have
different blast radii (a dev-tool bugfix, a docs change, and a refactor of a shipped skill)
and bundling them would put a `doctor` refactor behind a docs review.

**3. Who executes?** Recommended: a fresh worker per phase, NOT this orchestrator seat.
Confidence: HIGH — that is Phase 2's own rule, and declining to apply it to the plan that
proposes it would be the FB-0077 shape (a rule satisfiable by its author's exemption).
