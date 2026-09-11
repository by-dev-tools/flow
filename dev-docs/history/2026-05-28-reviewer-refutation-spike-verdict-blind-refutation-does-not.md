### Reviewer-refutation spike — verdict (blind refutation does not cut the FP tax on this diff; re-test as the feature evolves)
**Date:** 2026-05-28
**Branch:** `claude/dazzling-goodall-1ea214`
**Commit:** [SHA at commit time]

**What was done:**
Ran the reviewer-refutation spike (drafted in `plan.md`, plan-critic-APPROVED) as a dynamic workflow: 3 reviewer stances (staff-engineer, security/red-team, shell-robustness) fanned over `template/base/bootstrap.sh`, producing 15 raw findings; each finding was then verified two ways in parallel — **Method A** = the finder re-checks its own finding (today's PR J self-disproof), **Method B** = a fresh **blind** agent that never sees the finder's reasoning or the other findings. Cost: 33 agents / ~983k tokens / ~4 min for one 259-line file.

**Result:**
- Self-disproof (A) kept 10/15 (refuted 5). Blind refutation (B) kept **15/15 (refuted 0)** — a rubber stamp. The hypothesis (blind refutation cuts the false-positive tax) **inverted**.
- Root cause: the false positives in this diff are **significance** misjudgments, not **verification** errors. The claimed mechanism is almost always real (the code does do X); what makes it a false positive is the judgment that X doesn't matter under Flow's documented trust model (e.g. the symlink/FLOW_DIR "attacks" require an attacker already inside the adopter's own repo/shell). A blind agent confirms the mechanism and stamps "real"; it lacks the stance + project context to ask "but does this matter?" Blindness removes deference bias but also removes the judgment that catches the dominant FP class.
- Self-disproof outperformed but was **internally inconsistent**: it refuted the dangling-symlink write-through yet kept the structurally identical symlink-append; it refuted the slot-count finding in one framing yet kept the same false claim in another. Right answers, unreliable process.
- Adjudication (grounded): of the 5 disagreements, self-disproof was correct on 4 (the two symlink/FLOW_DIR significance calls and the slot-count false positive — verified: schema has 16 properties at b1c8e01 / 17 at HEAD, so "slots" ≠ example-key-count). One was a compound finding (real dead-code claim bundled with a false stray-space claim) neither method handled cleanly.

**Verdict:** **Do not encode blind refutation into the reviewer prompts.** PR J's self-disproof stays — it does real work. But the experiment's real payoff is diagnostic: the FP bottleneck is significance judgment, and both methods apply it inconsistently. The promising (untested) direction is **informed-independent refutation** — a fresh agent *with* stance + project context (not blind) + a uniform significance/exploitability rubric. **Not a write-off:** this is one data point on one problem type (a clean, already-reviewed shell script). Dynamic workflows are in research preview and will evolve; re-test across other problem types — especially UI projects, genuinely-buggy pre-review diffs, and migration-scale diffs — before drawing a general conclusion. Tracked in `roadmap.md` § Exploration.

**Why:**
The 2026-05-28 dynamic-workflows release made adversarial refutation a native runtime primitive; the spike measured whether the *pattern* is worth porting into Flow's shippable reviewer prompts (plugins can't bundle workflows, so the runtime itself isn't shippable — see `dev-docs/research/dynamic-workflows-2026-05.md` §5.3).

**Design decisions:**
- Controlled comparison (same finder pass, vary only the verification step) rather than two end-to-end runs — isolates the blindness variable instead of confounding it with finder variance.
- Reviewed a real, self-contained code diff (`bootstrap.sh`) rather than a docs diff — docs-only diffs early-exit the reviewers and produce no signal.

**Tradeoffs discussed:**
- Blind vs informed refutation: blindness kills deference bias (the original goal) but also kills significance judgment. The experiment showed significance is the dominant axis here, so blindness was the wrong knob — independence + context is the right combination. Recorded as the next variant to test, not adopted now.
- One diff is directional, not statistically robust; the named limitation (undersamples "kills real findings" because the file was already reviewed clean) is why the roadmap entry requires re-test on buggy + UI diffs before any general conclusion.

**Lessons learned:**
- A single dynamic-workflow review fan-out cost ~983k tokens on a 259-line file — concrete confirmation that workflows are a *selective tier*, not a per-PR default (matches the research doc's trigger-model finding).
- The spike paid for itself regardless of the methodology verdict: it found a real BLOCKER-class crash + two NITs in flow's own `bootstrap.sh` (fixed in the entry below), triangulated by all three stances.
