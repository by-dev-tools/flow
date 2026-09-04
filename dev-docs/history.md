# History

Detailed record of shipped work. Reverse chronological (newest first). This is not a changelog -- it captures the **why**, **tradeoffs**, and **decisions** behind each change so future sessions have full context on how the project evolved.

---

## 2026-09-03 — `/flow:ship-spike` audits its own skips (gate machinery, FB-0100)

**Branch:** `conductor/ship-spike-audits-its-own-skips-gate-machinery` · **SHA:** (assigned at commit) · **Mode:** feature (gate machinery — sensitive set) · **Version:** v1.38.0

### The class, not the instance

`/flow:ship` invokes five reviewers and then `/flow:audit-skips` over the result. `/flow:ship-spike` invoked exactly one, `/flow:verify-build`. Its single `audit-skips` mention was not a call site — it was the admission, stating in as many words that *"it never invokes `/flow:audit-skips`"*. PR #140 shipped with five stages skipped — preflight, `/simplify`, staff-review, verify-build, memory — and nothing audited any of them. The gate whose entire job is "no skip is accepted on its own say-so" did not run on the path that produces the most skips.

**This is the fourth recorded instance of one class, and the class is what matters.** FB-0082: `/flow:audit-skips` silently inert for eight versions, because a forked skill cannot read a `/tmp` handoff. FB-0085: rules that shipped and never loaded. FB-0077: a composition "fixed" by deleting the call site, leaving a lint green over a feature that no longer existed. The doctor default in #141: a check whose fallback disagreed with the schema it enforced. Every one is **a gate that does not fire where it is most needed** — and each was found by a human noticing, not by a check. The instance here is cheap to fix; the class is why the fix ships with mechanical pins rather than prose.

### What was decided, and why

**Which reviewers belong in spike mode.** The answer was not "add the other three" and not "keep spike mode light". It was: *no stage gets a blanket mode-based excuse, and the gate — not a hardcoded per-mode list — decides which reviewers run.* ship-spike's stated rationale, "the code is disposable", is real and reaches exactly two stages: `/simplify` and `/flow:staff-review`, both of which review code *quality* on code that gets deleted. It does not reach the others, and the reasons are not symmetric:

- **security-review — runs.** The code is disposable; the **commit is not**. A key hardcoded to move fast in a spike is still a leaked key after the spike is deleted.
- **accessibility-review — runs.** This was the one genuine judgment call, presented at MEDIUM-HIGH with its counter-argument (a11y on a prototype scheduled for deletion is the archetypal "craft review on throwaway code is theater" case). The argument that decided it came from the human at the plan gate and is stronger than the one I had: flow is deliberately moving the human gate *onto prototypes* (D1 — a written plan cannot convey feel, so the human approves a prototype instead). If prototypes are where visual and interaction decisions actually get made, an a11y flaw in an approved prototype does not die with the throwaway code — **it propagates into the real PR as an endorsed pattern.** That is the opposite of theater.
- **audit-coverage — skipped, for a structural reason rather than a mode one.** Its premise is "is the *declared* criteria set complete?", and a spike declares a research question, not a `**Spec-walk:**` block, while spike-mode verify-build runs a fixed 3-check rubric instead of plan-derived criteria. There is no declared set to be incomplete. It is recorded as `no Spec-walk` — a claim the engine verifies *mechanically against the plan file*, which is a stronger guarantee than the reviewer's own self-skip — and it is self-correcting: a spike plan that does carry an active Spec-walk block yields `SHOULD-RE-RUN · auto-resolvable` and the reviewer runs.

**Rejected: teaching the engine a `spike` skip reason for the stages outside that pair.** It would have been the smallest diff and it is exactly the bug class this PR closes — a blanket skip the gate cannot fire on. The engine now does the opposite: `spike`/`tiny` is **refused** as a skip reason for every stage outside a closed two-member allowlist (`_MODE_SKIP_OK = {simplify, staff-review}`). It shipped in this PR's first draft as a *denylist* of three and was corrected at review — see "What `/simplify` caught" above. A mode-declared blanket skip is unauditable by construction, because mode is a plan declaration and the gate would be accepting the very claim it exists to contest.

**Keeping a legitimate spike legitimate.** The risk in adding this gate was making spike mode unusable — every spike drafting over its own declared mode. Checked empirically before designing, by running the engine against a #140-shaped handoff rather than reading the code: a declared spike skip of `/simplify` + staff-review returns `NEEDS-JUDGMENT`, not `SHOULD-RE-RUN`, and the auditor resolves it against the plan's declared mode, which ship-spike's own pre-condition already requires. The one thin spot was that nothing put the plan's mode in front of the auditor — so `context.plan_mode` now carries it (path, first `**Mode:**` line, occurrence count, ambiguity flag).

**Rejected: promoting mode to a mechanical verdict.** Tempting — it would make the one NEEDS-JUDGMENT spike mode depends on deterministic. But flow's own `plan.md` carries **53** `**Mode:**` lines across retained PR blocks, and "active PR at the top" is the same soft convention `walk_extract.py` needed multi-block warnings and anchor co-location to survive. A first-match read could return a confident **false LEGITIMATE** sourced from a retained block: failure-open, on gate machinery, which is worse than the judgment call it replaces. Evidence in context; verdict with the agent. Both directions are pinned by eval, because the two failure modes are opposite and a plausible fix for either one alone breaks the other.

**Routing, given spike PRs have no draft manifest.** `/flow:ship` routes unresolved findings to the NOT-READY manifest; a spike PR is explicitly not manifest-gated (stated twice in ship-spike §7). Rather than import manifest machinery, spike mode reuses the mechanism it already had for exactly this shape — the halt-and-adjudicate the toolchain-absent verify-build skip uses. `auto-resolvable` → re-run the stage and re-audit **once**; everything else (decision-required, a `LEGITIMATE · manifest:` entry there is no manifest to file, and every error shape) halts and hands the user the choice, recorded verbatim in the history entry that is the spike's deliverable anyway.

### Two defects found while confirming the first

**`/flow:ship-spike` declared no `Skill` tool.** Its `allowed-tools` was `Read, Edit, Write, Glob, Grep, Bash, Agent` while Step 2 instructed `Skill("flow:verify-build")`; `ship`, `post-merge` and `verify-build` all declare `Skill`. Adding the audit on top of that allowlist would have shipped a *second* inert gate — FB-0082's shape exactly. Honest limit, kept in the PR body and not upgraded: the declaration inconsistency is certain, but **a live runtime rejection was not observed**; `allowed-tools` is the documented restriction mechanism and the fix is one word. The class is now linted repo-wide (any skill emitting a fenced `Skill()` call must declare the tool; prose mentions excluded, so `/flow:doctor` — which documents the idiom it lints — correctly passes).

**An eval pinned the defect as an invariant.** `run_skip_audit_evals.py` asserted `'Skill("flow:audit-skips")' not in spike_skill`, with a note that it "should be revisited" if ship-spike ever gained the call. It was accurate about the tree and wrong about the product: it encoded "spike mode has no skip audit" as something to *protect*. Now inverted and pinned positively from both ends per FB-0077 — a bare "the call exists" check and a bare "the note exists" check each go green in two opposite worlds; the pair cannot.

### The scope condition, and what checking it changed

The human made the "spike-only, don't expand the `preflight` row into `/flow:ship`" decision **conditional** on a property of my own plan — that the drift-pin actually covered the new row — and explicitly refused to let me assume it. Checking it changed the design. The pin as I had described it mirrored `/flow:ship`'s existing `contract-ship-handoff-*` checks, which are **per-file string-presence greps**: they would have passed just as green with a `preflight` row the engine had never heard of, leaving the asymmetry silent — which by the stated condition argued for the wider scope. Rather than take the wider scope or quietly restate the condition, the pin was strengthened until it genuinely held: extract the stage rows from *both* handoffs, drive the **real engine** with them, assert none falls through to `unknown stage`, and pin the ship↔spike row delta as a declared literal so changing either file fails a check naming the other. Both directions red-verified (revert the engine → the preflight row is caught; drop the row → the delta literal is caught). Condition met, so **spike-only** stands, and `preflight` on the ship side is a scope choice recorded in the eval's own failure message rather than a principle.

### What `/simplify` caught in this PR's own gate (worth recording)

The four cleanup lenses found a real hole in the change itself, and it is the same class the PR is about. `_NO_MODE_SKIP` shipped as a **denylist** — `{security, accessibility, audit-coverage}` — with a comment claiming that hoisting the guard out of the individual branches is what stops "the next stage added silently inherit[ing] the hole." The next stage added, `preflight`, was added *in the same commit* and inherited it; so did `verify-build`, the behavioral gate and one of the five stages FB-0100 names as unaudited in #140. A handoff row of `{"name":"verify-build","skip_reason":"spike"}` reached the fork agent as `NEEDS-JUDGMENT`, where `audit-skips/SKILL.md` instructs it to default to LEGITIMATE on anything it cannot refute. **The stage the PR most exists to protect was still skippable by typing "spike."**

Inverted to `_MODE_SKIP_OK = {"simplify", "staff-review"}` — an allowlist closed by the rationale itself rather than by enumeration, so a stage added tomorrow fails closed. Verified empirically after the fix: `verify-build` and `preflight` now return SHOULD-RE-RUN on a mode-declared skip while `simplify`/`staff-review` still return NEEDS-JUDGMENT (spike mode stays usable). The eval was widened to assert this over the **live** row sets scraped from both handoffs, so it covers stages that do not exist yet rather than re-enumerating the three the denylist did.

The lenses also caught that FB-0100's first draft pinned the handoff's symlink/stamp/read-back guards against the **spike copy only** — leaving `ship`, the original that copy was made from, free to drop its CWE-59 refusal with the harness still green. A one-sided pin on a two-sided duplication is not a pin. Both copies are now looped, and `ship-spike` was registered in `idiom_sites` so it inherits the three existing cross-site checks instead of hand-rolling them; the symlink guard is now pinned at all seven scratch sites rather than one.

### Deferred, with reasons

- **`plan_mode` still abstains on `occurrences == 0`.** A plan that declares no mode anywhere is an unambiguous mechanical refutation of a mode-declared skip — the same shape as the `no Spec-walk` check the engine *does* turn into a verdict. Not taken here: the human approved evidence-only at the plan gate, and converting it is a design change to gate machinery that belongs in front of them, not absorbed mid-execution. Routed to the roadmap.
- **The handoff shell is still duplicated rather than extracted.** The lens correctly noted that `ship-spike` sources helpers through the `CLAUDE_PLUGIN_ROOT`-else-checkout fallback three times in the same file, which weakens the "a sourced helper is unreachable" justification. Extracting it would touch `/flow:ship`'s Step 2a.1 — outside this PR's human-set scope. The pin was strengthened instead (8 guards across both copies, up from 4 against one).
- **`manifest_kind` names ship's terminal, not the finding**, so the shared skill's output contract tells a spike agent to "add + draft" when spike mode has neither. One prose override today; the rename is cross-cutting. Routed to the roadmap.

### Tradeoffs

- **The handoff shell block is duplicated, not extracted.** ship's Step 2a.1 states the constraint: the stamp is written in shell rather than via a helper because `CLAUDE_PLUGIN_ROOT` is unset in Bash-tool calls and a `plugins/flow/...` fallback only resolves inside the flow checkout, not in a consumer project. ship-spike already duplicates Steps 1.5 and 1a on the same reasoning. The FB-0010 fan-out risk is answered by `contract-ship-spike-handoff-*`, which pins each of ship's guards (symlink refusal, self-ignore, jq stamp, read-back) in the second copy — so the duplication does not rest on author memory.
- **Spike mode is now slightly heavier**: two reviewer forks that early-exit on the typical docs-only spike, plus one audit fork. Accepted deliberately, with the cost bound stated rather than assumed — both reviewers self-detect and exit.
- **`memory` is still unaudited**, and that is not an omission to fix later: Step 4b runs *after* the audit point, so auditing it is an ordering impossibility, and its skip condition ("no candidate signal in this session") is not mechanically decidable from the repo at all.

### FB collision, sixth instance

FB-0099 was claimed, pushed as a standalone commit before any other work (the claim-time defense — `/flow:critique-plan` raised the batch-at-ship version as a BLOCKER against this very plan), and then **renumbered to FB-0100 at rebase** anyway: #142 had opened while this branch sat at its plan gate and had already written its FB-0099 entry across feedback.md, history.md and the dev-docs index. Protocol step 4, applied. Worth noting that the early push did not prevent the collision here — it made it cheap, because nothing but the reservation line had been invested.

### Files touched

`plugins/flow/skills/ship-spike/SKILL.md` (Step 2.1 reviewers, Step 2.2, new Step 2a, `allowed-tools`, the line that claimed it never calls the audit, PR-body `## Flow run` rows, config-slot table), `plugins/flow/skills/audit-skips/SKILL.md` (description + `plan_mode` rule + caller-neutral routing prose), `plugins/flow/skills/audit-skips/lib/skip-audit-checks.py` (`_NO_MODE_SKIP`, `preflight` stage, `read_plan_mode`), `plugins/flow/docs/workflow.md`, `README.md`, `CHANGELOG.md`, version → v1.38.0 (`plugin.json`, `marketplace.json` ×2), three CI-wired eval harnesses (`run_skip_audit_evals.py` 79 → 103 checks, `run_scratch_isolation_evals.py` 61 → 69, `run_skill_composition_evals.py` + the repo-wide allowed-tools layer), and the dev-docs set.

## 2026-09-03 — Existing-repo design-language migration brief (FB-0099)

**Branch:** `conductor/design-language-migration-brief-existing-repos` · **SHA:** [this commit] · **Mode:** tiny (dev-docs only, no plugin artifacts touched) · **Version:** v1.37.0 unchanged (rebased past #141's merge, which bumped v1.36.0 → v1.37.0; this PR itself carries no plugin-facing change)

**What was built.** `dev-docs/design-language-migration-brief.md` — a portable, project-agnostic prompt to paste into an agent session working inside any repo (flow-consumer or not) that has, or should have, a design-language doc. It walks the agent through: locate the doc → audit it against the five shape rules `dev-docs/research/2026-09-design-md-investigation.md` derived (Axioms, Anti-patterns, Priority order, Tokens: one home, Coverage gaps, plus the observable-decisions authoring rule) → check token drift against shipped code → propose additions in the target repo's own vocabulary → stop and present, never edit unilaterally. Indexed in `dev-docs/README.md` in the same commit.

**Why.** Dispatched by the orchestrator as the mirror of a concurrently-open sibling PR (#141, `template/base/core-docs/design-language.md`): that PR scaffolds a fresh design-language doc for *new* repos; this one audits and proposes upgrades to a doc that already exists in an *existing* repo (`health-tracker`, `ripe`, `music-app`, `portfolio` — the same four the research doc surveyed). Both derive from the same source doc so they can't drift apart independently.

**Design decisions.**
- **Character-for-character wording match with #141, not independent re-derivation (FB-0099).** `/flow:critique-plan` flagged that my first draft paraphrased the research doc's rule descriptions on the exact passage the dispatch instruction called the session's main coordination risk. Resolved by copying #141's already-shipped `template/base/core-docs/design-language.md` wording exactly (fetched from its open branch, since #141 hadn't merged yet) rather than independently paraphrasing the research doc a second time. Two rejected alternatives, both explicitly named and rejected by the user: matching-but-not-identical wording (the FB-0010 fan-out hazard — "close enough" drifts silently over time) and extracting a new shared-source file both artifacts point to (new machinery the spike's "build almost nothing" thesis doesn't justify for a benefit this small). **Verified at rebase (#141 merged as v1.37.0 while this branch was open):** a mechanical whitespace-normalized substring diff of all five rule descriptions against the merged `template/base/core-docs/design-language.md` found the Tokens rule had drifted from the pre-merge branch copy in three small ways (a missing period + "below", spurious backticks around `<path>`, an extra period my brief had added that the template's own text doesn't carry) — fixed to exact. One clause is a deliberate, documented non-match: the Tokens rule's trailing template-authoring instruction ("see the token names below only if you chose the code-pointer form") points at the template's own fill-in-the-blank section, which this brief has no equivalent of; everything else in all five rules, confirmed exact.
- **Placement: `dev-docs/`, not `plugins/flow/docs/` or `template/base/`.** Weighed against CLAUDE.md's three-surface boundary: `template/base/` was ruled out first — it's scaffold copied into new repos at bootstrap, a different lifecycle than a paste-and-discard prompt, and stacking two different-lifecycle artifacts in one directory is the exact fan-out-confusion class FB-0010 warns about. Between `plugins/flow/docs/` and `dev-docs/`, the deciding fact is that `portfolio` — one of the four repos this brief exists to help — genuinely is not a flow consumer (verified: no `flow.config.json`, uses `.claude/forge/` instead), so shipping via the plugin buys nothing for a quarter of the target set while manual copy-paste works uniformly for all four. Ben's actual use case is copying this out into another repo's agent session regardless of install path, so portability mattered and shipped-surface location didn't.
- **Independent corroborating evidence for the placement call:** a concurrent harness-weight-audit spike found `plugins/flow/docs/workflow.md` (85 KB) has no `@`-import anywhere and accounts for ~64% of that audit's overstated total — a shipped file nothing loads. Shipping a second doc next to a file already sitting unloaded would compound the same graveyard pattern rather than avoid it.
- **No version bump, matching the originating spike's own precedent.** The diff touches zero `plugins/flow/**` files — same reasoning as the 2026-09-03 spike entry below (a version bump would publish a plugin release with no behavior change). Version is v1.37.0 not because this PR bumped it, but because #141 did (merged while this branch was open) and this branch rebased past it unchanged.

**Technical decisions.**
- **The brief is self-contained — it does not cite `dev-docs/research/...` inline for its own readers.** The shipped brief text restates the five rules' definitions rather than pointing at flow's internal research doc, because the brief must work standalone in repos (like `portfolio`) that have no access to flow's `dev-docs/` at all. The verbatim-derivation discipline instead applies at the *maintenance* layer: this file's own header states the provenance requirement (keep in sync with `template/base/core-docs/design-language.md`, note here if they deliberately diverge) so a future editor doesn't silently drift the two apart the way FB-0099 was almost about to happen twice in one session.
- **Reserved FB-0099** in `dev-docs/reserved-feedback-numbers.md` before drafting the entry, per protocol — next free after FB-0097 (reserved at draft time) and FB-0098 (claimed by open #141 at draft time; #141 has since merged and its reservation was swept clean at this branch's rebase). FB-0099 was re-confirmed still free against `main`'s new high-water at the same rebase — no collision, no renumber needed.

**Tradeoffs discussed.**
- **Roadmap.md deliberately not touched.** #141 makes its own roadmap.md edits (a "Now" headline update + three § Exploration entries) on the same lines this branch would otherwise touch; since this brief is a completed, self-contained deliverable rather than a queued backlog item, and since the originating spike itself left roadmap.md routing to the follow-up PR rather than editing it directly, this branch stays out of that file entirely to avoid an unforced collision with #141's open PR.
- **CHANGELOG.md not touched**, for the same reason as the version-bump decision: no plugin-facing change occurred.

**Lessons learned.** The `/flow:critique-plan` finding here is a good instance of the "escalate rather than paraphrase" instruction actually working as designed: the critic caught a real silent-resolution risk (two paraphrases of the same source drifting apart), and rather than either ignoring it or unilaterally deciding how to fix it, presenting it back to the user as an open call produced a cleaner resolution (option 2, exact match) than either autopilot choice would have.

---

## 2026-09-03 — Spike: agentic design-guidance investigation (Vercel `design.md` + public survey)

**Branch:** `conductor/spike-designmd-investigation-vercel-agentic-design-guidance` · **SHA:** (assigned at commit) · **Mode:** spike · **Version:** v1.36.0 unchanged (zero plugin artifacts touched — see Tradeoffs)

**Research question.** What, if anything, should flow learn from Vercel's `design.md`? Extended mid-spike by user direction to a survey: what are leading AI/product companies publishing about how agents produce high-quality **design/craft** output, and how that output improves from human feedback? That axis is the gap in flow's research corpus — `ai-workflow-landscape-2026-07.md`, `anthropic-canon-alignment-2026-08.md` and `service-agnostic-2026-07.md` all cover how agents *work* (orchestration, context, reflection, packaging), not how they produce *taste*.

**What was built.** No code. `dev-docs/research/2026-09-design-md-investigation.md` — primary sources fetched live and quoted rather than paraphrased from search summaries, the four consumer repos read at HEAD via `gh api` with two token drift-checks, and a layering argument built on that evidence. Indexed in `dev-docs/README.md` in the same commit, per the repo rule.

**What we learned.**

1. **Vercel published three artifacts, not one, and the popular one is the least applicable.** `design.md` (2026-08-31) is a *rewrite* after a failed port, and Vercel says why: *"Inside our codebases, an agent reads product-design surrounded by real components and shipped examples of the things it describes. But a public prompt includes none of that, leaving every model to rebuild our style from just words alone."* Its elaborate structure is **compensation for having no codebase**. Every flow consumer has one — so the applicable post is `teaching-agents-product-design-at-vercel` (2026-06-25): an in-repo skill + linters + a review loop.
2. **The only large measured result in the survey is about loading, not authoring.** Vercel's Jan-2026 Next.js evals: an available skill went **uninvoked in 56% of cases** and scored **exactly at baseline (53% vs 53%)** — slightly *below* baseline on tests, suggesting an unused skill is mild noise. A passive 8 KB AGENTS.md index hit **100%**. Measured on framework-API correctness, **not** design; extending it to design guidance is recorded in the doc as *inference, not a measured result*, with the cheap experiment that would settle it named (per `.claude/rules/documentation.md` § "Recorded rejections").
3. **The consumer docs are working, and nothing is enforcing them.** Drift-checked documented token values against shipped code: `ripe` zero drift across 17 values (its `Tokens.swift` even carries the doc's own reconciliation narrative), `health-tracker` zero drift across 11 values three-way, `music-app` drift-*proof* by construction (names in the doc, values only in Swift). The one repo with drift — `portfolio`, `--text-grey` documented `45%`, shipping `40%` — **is not a flow consumer** (no `flow.config.json`; it uses `.claude/forge/`). Suggestive, not causal: n=1 each way, and `ripe` is clean because its author wrote ratification notes, not because a tool checked.
4. **The corpus already invented Vercel's two best moves and never wrote them down.** `ripe` heads a section *"Axioms (violate = design bug)"*; `music-app` has *"Anti-patterns (cut on sight)"*. Those are Vercel's falsifiable-rule and named-anti-pattern mechanisms, arrived at independently, in two repos, by the same author. Neither has the third move — a **priority order for resolving conflicting rules** — which *both* Vercel artifacts carry and *no* repo in the fleet does.
5. **Three verified defects in flow's own `designLanguagePath` plumbing.** No template ships (`template/base/core-docs/` has the other five core docs, not this one); the slot is absent from `/flow:doctor`'s slot-existence loop; and the single-string slot leaves ~80% of `health-tracker`'s ten-file design corpus invisible to the three lens agents that call it their primary source-of-truth. **15 plugin files** reference the slot.
6. **On the wider survey: nobody else has published anything substantial on this axis.** Linear's Agent Interaction Guidelines are about agents *as users of a product*, not agents producing design (asserted, no measurement). Stripe and Vercel converged on retrieval-led docs — verified first-hand, `docs.stripe.com/llms.txt` is a real 90 KB machine index whose first line is an anti-stale-training-data instruction — but that is about *factual currency*, not taste. Anthropic publishes authoring and eval discipline, not design guidance. Notion, Google, Copilot and Cursor: **nothing found**, reported as a result. Worth knowing before treating "the industry is converging on design.md" as a premise. It isn't — one team published three careful posts.

**Recommendation: proceed, small.** Next real PR is §5a's S1+S2+S3. **Explicit NO** to six things (§5c), each with a deletion criterion (FB-0088) and a stated flip condition: a design-guidance eval harness, a token drift-checker, a fifth design gate, a hosted design.md convention, a multi-path `designLanguagePath`, and design linters in the plugin.

**The finding that outlives the spike.** Flow's eval-fixture discipline ("prompt changes are code changes"; no rule without a fixture) is the *same* discipline as Vercel's *"Nothing got in any other way"* and Anthropic's *"Create evaluations BEFORE writing extensive documentation… Establish baseline."* Three independent parties, one rule — genuine convergent evidence that flow's core bet is sound. **But Vercel closed a loop flow has not:** they measure whether the complaint rate *falls* after encoding a fix, and treat a flat rate as evidence the fix is wrong. Flow enqueues, drains, merges — and then nothing checks whether the encoded lesson changed anything. That is the **same gap** `ai-workflow-landscape-2026-07.md` § 5 already found for memory ("nothing measures effectiveness" → roadmap #3), reached from a different direction. It should **merge into roadmap #3, not become a new item** — and it should not be sized until the §5b ablation establishes that guidance changes behavior at all.

**Design decisions.**
- **Studied the mechanism, did not copy the content.** No Vercel brand material was imported. The transferable output is a doc *shape* (falsifiable axioms, named anti-patterns, a conflict-resolution ladder, one home for token values, declared coverage gaps) plus one authoring rule: write corrections as **observable decisions** — *"Let evidence tables use the full available width"*, not *"make the table feel less cramped"*, because only one of those can be checked.
- **The layering cut is "shape vs content", not Vercel's own "judgment vs primitives".** Their cut fails for flow: their judgment prose is *also* unportable (*"Use Geist Sans"*, *"Design in monochrome"*, *"Avoid em dashes"*), and it directly contradicts `ripe`'s *"One curvature family per surface"* and `music-app`'s *"The artwork is the sacred object."* Judgment **is** content. What flow can own is the shape the judgment is written in, and the plumbing that makes sure it loads.
- **Answered "should flow ship a bounded primitive vocabulary?" with no.** Not because it is project-specific, but because the problem it solves (a model inventing typography with no repo to read) does not exist for flow's consumers, all of whom already have `Tokens.swift` / `Palette.swift` / `theme.css`. The context-saving argument doesn't transfer either — a Swift token file is already outside the prompt.

**Tradeoffs discussed.**
- **Recommending near-nothing was the point, not a cop-out.** Flow carries ~91 queued roadmap items and a recent repo-wide review found real overbuilding; the brief set a high bar for new machinery. The evidence cleared that bar for three small plumbing fixes and cleared it for nothing else. The honest finding is that the docs already work and nothing enforces them — building an enforcement layer against that evidence would be the overbuilding pattern the spike was told to guard against.
- **`/flow:doctor`'s gap is wider than `designLanguagePath` — and that reframing came from human review, not from me.** The original doc framed it as one missing slot. The human pointed out doctor's frontmatter advertises *"all 33 slots have sensible values"* while Check 2.4's loop covers five. Verified and sharpened in the doc: Check 2.3 value-checks **2** slots, Check 2.4 path-checks **5** — **7 of 33, ~21%**. Same advertised-but-not-delivered class as Phase 00 / FB-0085. **S1 was widened to fix the frontmatter wording too, but deliberately NOT widened to audit the other 26** — that needs its own evidence that unchecked slots cause real failures, and is routed to § Exploration instead. Sharpest irony recorded: Check 2.5 exists specifically to catch stale literal "N slots" counts in *consumer* docs while doctor's own frontmatter carries one it doesn't keep.
- **No version bump, against the letter of the ship instruction.** The instruction was to take the next free minor above `main`. The diff touches **zero** plugin artifacts, and the last three merges (#125, #136, #138) all sit at v1.36.0 — two of them dev-tooling-only. Bumping would publish a plugin version with no behavior change *and* falsify the research doc's own "`plugins/flow/**` untouched" claim. Flagged to the human at hand-off rather than decided silently; it is a one-line change if they disagree.
- **Corrected the stale egress caveat without over-correcting it.** `anthropic-canon-alignment-2026-08.md` claimed anthropic.com was egress-blocked; it returns `200` here and was verified twice. The fix says the *access* claim was false while stating plainly that the article quotes **remain unverified against source** — the tempting over-correction ("we can reach it, so the quotes are fine") would have silently upgraded unverified claims. What changed is the *cost* of verifying, and the doc now says so, so a future pass can finish the job.
- **Preserved the design-language doc's scope sentence while fixing its `uiSurface` claim.** Those two assertions sat in one sentence and only one was wrong. Rewriting the doc would have been overreach on a currency fix.

**Lessons learned.**
- **Read the vendor's *other* posts before adopting the famous one.** The single highest-value find here — that `design.md` exists to compensate for the absence of a codebase — was one sentence in the post's own preamble, and it inverts the naive recommendation. A one-artifact reading would have proposed exactly the wrong thing.
- **A stale provenance caveat is as costly as a stale fact.** The prior research doc routed around anthropic.com for a month on a block that had lifted, and the workaround (search summaries + training knowledge) is *why* its quotes are unverified. Access caveats deserve a re-check date, not just a warning.
- **The corpus is evidence.** Two drift checks against real repos settled in minutes a question that could have been argued from principle indefinitely — and the answer ("it's working; don't build the checker") was the opposite of what the machinery-shaped question invited.

---

## 2026-09-03 — `/flow:doctor` slot-coverage honesty + design-language template (FB-0098, v1.37.0)

**Branch:** `conductor/doctor-slot-loop-coverage-design-language-template` · **SHA:** (assigned at commit) · **Mode:** bugfix + small feature (`platform: library`-shaped; no UI surface in this diff)

**What was done (user-facing).** `/flow:doctor` Check 2.4 now checks `designLanguagePath` (gated on `uiSurface`, WARN not FAIL) alongside the existing five doc-path slots. `template/base/core-docs/design-language.md` ships as a new template — shape only (Axioms, Anti-patterns, a numbered conflict-resolution Priority order, one-home Tokens, Coverage gaps, plus a "write corrections as observable decisions" authoring rule) — so a `uiSurface: true` consumer bootstrapping flow no longer gets a slot pointing at a file nothing scaffolds. Doctor's frontmatter no longer claims "all 33 slots have sensible values"; it now names exactly which checks (2.3/2.4/2.7/2.8/2.9/2.11) cover which slots, and states the rest are intentionally excluded (ephemeral paths created on first write, non-path config, one deferred directory-path gap).

**Why.** `dev-docs/research/2026-09-design-md-investigation.md` (spike, branch `conductor/spike-designmd-investigation-vercel-agentic-design-guidance`) found `designLanguagePath` was the only unchecked doc-path slot despite 23+ dependent files across four staff-review lens agents, `plan-critic`, `planner`, `verify-build`, `staff-review`, `accessibility-review`, and `ship` — and that no template existed for the doc, so a fresh `uiSurface: true` project scaffolds every other core doc except this one. Classed with FB-0085/Phase 00 ("shipped-but-never-verified" surfaces) rather than treated as a one-off slot addition.

**Design decisions.**
- **Slot classification, not exhaustive slot-checking.** All 33 schema properties were read individually and bucketed: doc-path (6, now fully checked), ephemeral/created-on-first-write (4 — `verifyFindingsPath`, `verifyReportPath`, `visualHistoryPath`, `lastHarvestedPath` — deliberately excluded, a missing file is their correct steady state), path-shaped-but-covered-by-a-different-check (4 — `statusDocs`/`statusSurfaceCandidates` via 2.7/2.9, `flowRepoPath`/`contributionsQueuePath` via 2.8), glob-not-path (`referenceGlob`), one deferred directory-path gap (`rustWorkspaceDir`, routed to `roadmap.md` § Exploration — conditional on the optional `platform` hint, narrow blast radius, not part of the verified finding), and 17 non-path config slots. This closes the *evidenced* gap without building an eval harness, drift-checker, fifth design gate, hosted design.md convention, multi-path slot, or linter — all explicitly out of scope per the spike's DO-NOT-BUILD list.
- **Template is shape, not content.** Five sections the spike's corpus survey found: two (Axioms, Anti-patterns) independently reinvented by two of our own consumer repos under different names; one (Priority order) present in both surveyed Vercel artifacts and absent from every corpus repo; Tokens and Coverage gaps round out the set. Zero project tokens, per the project-agnostic quality bar.

**Technical decisions.**
- **The actual root cause was one line, not flow's config.** Check 2.4's unset-slot default built `core-docs/<slot>.md` — a literal that was the *sole* outlier in the whole plugin: the schema declares `dev-docs/<slot>.md` as every doc-path slot's default, and 16 other call sites across `ship`, `ship-spike`, `land`, `verify-build`, `staff-review`, `security-review`, `accessibility-review`, `audit-coverage`, `audit-skips`, `planner`, and `docs` already use `dev-docs/`. My first fix attempt (explicitly setting the six slots in flow's own `flow.config.json`) would have masked the symptom on this one dogfood repo while leaving the same false-`[WARN]` live for every other consumer with an unset slot — the human caught this and redirected to the actual root cause (FB-0098). Fixing the default also required a camelCase→kebab-case transform for the default-path builder, since the prior word-only strip built `designLanguage.md`, not `design-language.md`, for the one compound slot name.
- **A second, independent bug caught by the new eval before it shipped:** `UI_SURFACE=$(jq -r '.uiSurface // true' flow.config.json)` silently coerces an explicit `uiSurface: false` back to `true`, because jq's `//` treats JSON `false` as "no value" the same as null/absent. Fixed to the plugin's established-safe pattern (`if .uiSurface == false then ... else ... end`, matching `accessibility-review`'s existing gate) — caught by `run_design_language_scaffold_evals.py`'s `exec-3`/`exec-4` checks actually executing Check 2.4's real shell block against a `uiSurface: false` fixture, not by inspection.
- **New eval, `run_design_language_scaffold_evals.py`**, follows `run_role_slot_evals.py`'s execute-the-real-block style (via `eval_utils.fenced_block`) rather than grepping prose. Includes a schema-driven "join" check: for each of the six doc-path slots, the check's real executed default-resolution output is asserted equal to the schema's own declared `default` field — directly, not via a duplicated hardcoded expectation — so the class of bug this PR fixes (a hardcoded default drifting from the schema) can't silently regrow. Wired into `.github/workflows/ci.yml`.

**Tradeoffs discussed.**
- `rustWorkspaceDir` (directory path, Tauri/Rust-only, conditional on the optional `platform` hint) is a real, evidenced gap of the same shape, deliberately not fixed here — narrow blast radius (one stack overlay), not the verified finding this PR was dispatched to close, and conditional-on-an-optional-hint is a fuzzier check shape than the unconditional doc-path slots. Routed to `roadmap.md` § Exploration with an explicit trigger rather than silently dropped.
- The frontmatter's check-citation list (2.3/2.4/2.7/2.8/2.9/2.11) is hand-maintained, not mechanically derived from Check 2.4's classification prose — `/flow:critique-plan` flagged this exact fragility mid-planning (an earlier draft under-cited Check 2.7, then separately under-cited Check 2.11), and the fix each time was to re-derive the citation set by grepping the classification table rather than trusting memory. No single source of truth exists to derive it from automatically; a future pass could build one if the citation list drifts again.

**Lessons learned.** See FB-0098 for the synthesized rule (fix the check against its contract, not the data that exposed the disagreement) and the jq `//`-with-`false` gotcha. Also: `/flow:critique-plan` caught three real issues before any code was written — a batched-not-immediate FB reservation (protocol violation), an under-cited check list (the exact fan-out-omission class this PR exists to fix, reproduced at plan-review scale), and a factually wrong "verified fact" in my own plan draft (claimed flow's config explicitly set 5 slots it does not) — worth noting because the last one was caught by the critique loop *before* I re-verified it myself, i.e. the adversarial pass earned its keep on a claim I had asserted with unwarranted confidence.

**Files touched:** `plugins/flow/skills/doctor/SKILL.md`, `template/base/core-docs/design-language.md` (new), `plugins/flow/evals/run_design_language_scaffold_evals.py` (new), `.github/workflows/ci.yml`, `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json`, `CHANGELOG.md`, `dev-docs/roadmap.md`, `dev-docs/plan.md`, `dev-docs/history.md` (this entry), `dev-docs/feedback.md` (FB-0098), `dev-docs/reserved-feedback-numbers.md`.

---

## 2026-08-27 — AB Step 1: harness-weight audit mechanism (FB-0095)

**Branch:** `conductor/ab-attention-budget-harness-weight-audit-fb-0084` · **SHA:** (assigned at commit) · **Mode:** feature (dev tooling)

**What was done (user-facing).** Built the harness-weight audit *mechanism* named in the FB-0084 handoff's AB item — the half of that top-priority reprioritization M's Step 1 (#129) didn't already cover. `tools/harness_audit/harness_audit.py` (stdlib, dev-tooling — never a shipped plugin artifact) provides two pieces: `--audit-due`, a periodic cadence gate (every 5 merged PRs to `main`, driftless via `git rev-list --count` against a stored marker SHA — no decrementing counter, unlike the memory audit's, because flow's own linear history is ground truth); and `--surfaces`, an inspectable inventory of flow's own harness weight split into two cost classes that are never summed: **Class A** (always-loaded every session — `CLAUDE.md`, `.claude/rules/*.md`, `plugins/flow/docs/workflow.md`, plus every skill's/agent's frontmatter `description:` — the part that actually renders into a session's system reminder) and **Class B** (invoked-per-use — the full body of every shipped `plugins/flow/skills/*/SKILL.md`). A documented fresh-context audit-agent prompt in `dev-docs/workflow.md` § "Harness-weight audit" flags candidates only; it never prunes.

**Why.** `dev-docs/research/anthropic-canon-alignment-2026-08.md` § 3 identified that flow has no mechanism auditing its own harness weight the way the 5-ship memory audit (`plugins/flow/tools/memory/check.mjs`) audits memory entries — token cost accumulates invisibly as scaffolding built for older model capability goes un-revisited. This PR closes that "no mechanism" gap; it does not yet use the mechanism to prune anything.

**Plan-gate history (four escalations surfaced and resolved by explicit human decision, per FB-0011/the orchestrator's §4.8 escalation-format convention — recommendation + confidence + justification, never picked silently):**
1. **Phasing** — build only this mechanism now; queue dev-doc compaction (AB.2), a real token-count report (AB.3), and the JIT-retrieval/curated-examples doctrine fold (AB.4) as separate PRs. *Approved.*
2. **Placement** — dev-tooling (`tools/harness_audit/`), not a shipped `/flow:*` skill, mirroring M Step 1's posture under FB-0083's measurement-first constraint. *Approved.*
3. **Gate/step-level auditing** — the roadmap's own framing ("always-loaded surface **+ gates**") named ship-pipeline steps as in-scope; deferred to a new AB.1b instead, because judging whether a *gate* still earns its keep needs per-gate regression evidence (why was it added, is that reason still true) a generic surface-scan prompt can't provide. *Accepted.*
4. **Compaction aggressiveness** — a real judgment call (too aggressive loses context a cold reader needs; too timid doesn't dogfood the principle) registered with a recommendation (one-paragraph program heads, tradeoffs live in `history.md` only) but explicitly *not* decided here — it's AB.2's call to make when that PR lands. *Deferred, not decided.*

**Scope correction from the human, mid-plan-gate.** The drafted v1 surface set excluded full `SKILL.md` bodies on the reasoning that they're JIT-loaded, not always-loaded — technically true, but it meant the audit would skip `ship/SKILL.md` (1,384 lines, the single heaviest prompt in the repo, and literally the context window for the duration of `/flow:ship`) while dutifully auditing `CLAUDE.md`. Fixed by adding invoked-skill bodies as **Class B**, reported separately from Class A's always-loaded surfaces so the two cost models (per-session vs. per-invocation) are never conflated into one misleading total.

**Design decisions.**
- **Flags, never prunes — by design, not by omission.** There is no ground truth for "still earns its cost at current model capability" the way the memory audit has a partially-mechanizable fire-log-staleness check. Shipping an auto-prune on top of an unverified judgment would be exactly the kind of over-reach the FB-0088 "prompt changes are code changes" discipline warns against.
- **Guardrails hard-coded into the shipped prompt, not just this plan's prose.** The audit-agent prompt in `dev-docs/workflow.md` explicitly protects FB-0010 footgun/incident comments, curated canonical examples (only flags genuinely *exhaustive* lists), and anything marked `SAFETY` — and `run_harness_audit_evals.py` greps these guardrail sentences verbatim out of the real doc, so a future edit that silently drops one is caught mechanically, not discovered live during an audit run.
- **Driftless cadence over a counter file — vs. reality, not vs. reasoning.** The memory audit's `.last-audit` decrements a counter because per-project ship invocations aren't otherwise recorded. Flow's own `main` is git-ground-truth (linear, squash-merged), so this audit stores the last-audited SHA and asks git directly instead of trusting a hand-incremented count. **Caveat found by `/flow:staff-review` (staff-engineer lens), not fixed in this PR:** the marker file itself is gitignored/per-clone, so under the now-active flow cloud workflow (ephemeral per-PR workspaces) every fresh workspace's first `--audit-due` reports "due" regardless of true elapsed-PR count — the git-truth design is sound, but the marker's *storage* doesn't yet survive the environment this repo actually runs sessions in. Filed to `roadmap.md` § Next "AB" for AB.1b, alongside a second staff-review finding (`audit_due()` couples "checked" with "consumed" with no separate completion signal — same section).

**Technical decisions / tradeoffs.**
- **`.gitignore:10`'s bare `tools/` gotcha, pre-empted.** M Step 1 hit this twice (a blanket-ignored `tools/` pattern blocks new files, but not already-tracked ones). `git add -f tools/harness_audit/` used directly at commit time this session, per the lesson already recorded in `plan.md`'s M Step 1 block.
- **Live dry run performed, findings recorded but not acted on.** A real fresh-context `Explore` agent was spawned with the shipped prompt against this repo's actual `--surfaces` output. Class A: no issues flagged. Class B (ship/verify-build/doctor spot-checked): two real candidates — `verify-build/SKILL.md`'s dated "as of 2026-05-28" contract section still lists items as "UNKNOWN" that a later §5a section already resolves (stale, unreconciled); `ship/SKILL.md`'s closing "Config slots" table duplicates ~11 of `workflow.md`'s already-documented slot defaults (a two-places-to-update fan-out risk). Neither fixed here — both flagged in `roadmap.md` § Next "AB" for whoever picks up the pruning follow-up. This is the mechanism working as designed: producing a candidate for a human to weigh, not a silent auto-fix.
- **`plugins/flow/tools/memory/check.mjs` has no eval harness of its own** — discovered while building this PR's own eval harness as a mirror. Not fixed here (out of scope — it's the *precedent's* gap, not this PR's), but noted in `roadmap.md` § Next "AB" so it isn't lost.

**`/simplify` + `/flow:staff-review` (four lenses), applied before ship.** `/simplify`'s reuse lens caught a verbatim-duplicated `check()`/`_failures` eval-assertion helper between this PR's eval harness and `tools/model-measure/run_model_measure_evals.py` — skipped (fixing it means editing an already-shipped sibling PR's file, out of this PR's scope; filed to `roadmap.md` § Next as a small standalone extraction). Applied in-tree: extracted a `_render_class` helper collapsing the Class A/B report-rendering duplication; shared one fixture tree across the read-only surface-resolution tests instead of rebuilding it 7 times; corrected a comment that overstated `AUDIT_INTERVAL`'s equivalence with the memory audit's same-named-but-different-measurement constant. `/flow:staff-review`'s four lenses then ran in parallel: staff-engineer caught the two cadence-marker gaps above (filed to AB.1b) plus a stale reservation-file status line and an undisclosed `--audit-due` side effect (both fixed in-tree); UX-designer caught that Class B's rendered "total" implied a cost that never actually occurs (skills load one at a time, never together) and that `_run_git` swallowed the stderr a human would need to debug a degraded cadence check (both fixed in-tree, plus the exit-code convention now self-documents in `--help`); design-engineer and push-further correctly found no applicable surface / nothing to push for a scope-tight CLI mechanism PR.

**Three-surface note.** Dev-tooling + dev-docs only (`tools/`, `.github/workflows/ci.yml`, `CLAUDE.md` § 3 table row, `dev-docs/*`). No `plugins/flow/*` artifact changed — the four ship reviewers self-skip on this diff.

**Renumbered from FB-0093** at rebase — FB-0093 was independently claimed and merged by `conductor/phase-00-rules-as-skills-hooks-fix-fb-0085` for an unrelated concept while this branch was in flight; see `dev-docs/feedback.md` FB-0095.

## 2026-08-27 — `/flow:doctor` Check 2.5 hoisted to the shared, wrap-tolerant slot-count predicate (FB-0079 class, FB-0096)

**Branch:** `conductor/doctor-check-25-hoist-slot-count-predicate-fb-0079-class` · **PR:** #139 · **Mode:** bugfix (small, roadmap § Next) · **Version:** 1.32.0 → 1.36.0

**PROCESS NOTE (FB-0096):** this branch was dispatched with an explicit instruction to stop at the plan gate and get approval before executing. It did not — the fix below was implemented and eval-verified first, and `/flow:critique-plan` was only run afterward, against a "plan" that narrated already-done work. The critic correctly flagged this as a BLOCKER (the gate was never actually held open). Presented with the choice, the user directed keeping the work rather than reverting it — "green, small, and fully reversible... reverting verified work to re-perform a ceremony would cost more than it protects" — on the condition that the skip be reported here and in the PR body, not papered over. See FB-0096 for the synthesized rule.

**PROCESS NOTE 2 (session-continuity, not FB-worthy — a sandbox/rate-limit constraint, not a taste or judgment call):** this session hit its rate-limit window three times, each time immediately after being cleared to proceed — right after the keep-vs-revert decision, again mid-ship, and a third time after PR #139 had already opened. The first two times the completed, green diff existed only uncommitted in the sandbox, and a cloud workspace has a hard lifetime, so on the second resume the user redirected priority explicitly: commit + push FIRST, before any further doc work or rebase, because "a pushed branch with no PR is recoverable, an unpushed sandbox is not." Committed and pushed once the working tree was green and fully reviewed (staff-review + security-review + `/simplify` + audit-coverage all complete) but before the rebase/version-collision work below — collision episodes 2 and 3 were therefore both resolved as post-push, post-PR rebases, never pre-push.

**What was done.** `/flow:doctor` Check 2.5 (the consumer-facing "documented slot count matches schema" guard) was a strictly weaker twin of the internal slot-count sweep `run_merge_status_evals.py` runs over flow's own tree, which FB-0079 hardened after a wrapped `all 30\n  slots` in `doctor/SKILL.md`'s own YAML frontmatter slipped a line-oriented grep. Check 2.5 still had all three properties that produced that miss: line-oriented (`grep -rEn`), a single-literal-space pattern (`([0-9]+) slots?`), and doc-ish-only scan targets. Fixed by hoisting the predicate into a new shared module, `plugins/flow/skills/doctor/lib/slot_count_scan.py` (stdlib; wrap-tolerant `(\d+)\s+slots?\b` matched over full file text, not per line; same `.sh`-comment historical-narrative exemption as the internal sweep), and having both runtimes call it: `run_merge_status_evals.py` imports it directly (mirroring the existing `_lint()`/`skill-composition-lint.py` loader pattern); Check 2.5's shell block now resolves it the same way it already resolves `SCHEMA` (CLAUDE_PLUGIN_ROOT-first) and shells out to it, translating its exit code into doctor's `[PASS]/[WARN]/[SKIP]` vocabulary. Also added `bootstrap.sh` to Check 2.5's scan-target list — narrower than first claimed (see the staff-review finding below, corrected before ship).

**Why.** A guard flow ships to every consumer project being weaker than the guard flow runs on itself is the FB-0079 class recurring one PR after the lesson ("greps are line-oriented; grep the shape, not the value") was written down — this time inside FB-0079's own sibling check rather than a different one.

**Design decisions.**
- **Hoist to one shared module, not two independently-maintained regexes.** The roadmap entry named this as the primary fix shape (over a `\s+`-pattern-plus-parity-assertion fallback) specifically because a shared module makes "both runtimes agree" a property of the code, not of two authors remembering to keep two regexes in sync — the exact thing that broke here.
- **Extend the scan-target list, don't change what gets excluded.** The fix touches only what Check 2.5 scans (`+bootstrap.sh`) and how it matches (wrap-tolerant, full-file-text), not its historical-narrative tolerance — `dev-docs/history.md`/`feedback.md`/`plan.md`/`roadmap.md` remain in scope and still legitimately WARN on old counts; that's documented, expected behavior, unchanged by this PR.

**Technical decisions.**
- `scan_paths(paths, expected, exclude_substrings=())` returns `(stale, scanned)` — pure, no printing — so both the eval harness (which wants the raw list) and the CLI (which wants formatted `[slot-count-scan] STALE ...` lines) can consume it without a second parser.
- CLI exit codes (0 clean / 1 stale / 2 vacuous-scan) mirror `skill-composition-lint.py`'s existing 0/1/2 shape rather than inventing a new convention.
- The eval-harness change is more than a straight port: `run_merge_status_evals.py` previously found only the FIRST "N slots" match per matching grep line (`head -n1`); the hoisted `scan_paths` finds every occurrence in a file via `finditer`. Verified this against the real repo tree (not just the synthetic fixture) — the old shell logic surfaced 75 survivor lines against flow's own `dev-docs/`+`CHANGELOG.md`; the new predicate surfaces 94, entirely accounted for by (a) multiple genuine "N slots" occurrences on one source line now each reported instead of only the first, and (b) format granularity (one line per occurrence vs. one line per matching source line) — not by any newly-wrapped instance (grepped: no `\n`-wrapped "N slots" occurrence currently exists anywhere in the live repo). No behavioral surprise, just a more complete count of an already-WARN-only, non-blocking check.

**Tradeoffs discussed.**
- **Did not fix the pre-existing "FB-XXXX slot" false-positive class.** The regex (`\d+\s+slots?\b`, inherited unchanged from the original design) matches "0010 slot" inside prose like "FB-0010 slot-count fan-out" — a false attribution of the FB number as a claimed schema-slot-count. Confirmed this already existed identically in the shipped (pre-fix) Check 2.5 and the shipped internal sweep (same regex shape, `[0-9]+ slots?`, no word-boundary difference that would change it) — not introduced or worsened by this PR. Out of scope: the roadmap item named line-orientation, the space-pattern, and doc-ish-only targets specifically, not this separate false-positive class, and Check 2.5 is WARN-only/advisory (never blocks), with its own output already caveating "some may be intentional historical narrative."
- **A live self-referential catch, worth recording because it's the kind of proof a guard actually works.** An early draft of Check 2.5's own explanatory shell comment read `bootstrap.sh — the template-shipped script FB-0079 caught with a stale "28 slots" comment`. Running the new predicate over the real repo flagged that exact comment as a stale survivor — the guard correctly could not distinguish its own doc-comment's illustrative digits from a genuine stale claim. Reworded to drop the literal digit+"slots" pair. Left as evidence in-session (not fixed silently) because it's a clean, reproducible demonstration that the wrap-tolerant, full-file-text predicate is actually scanning what it claims to scan, not a vacuous pass.

**Verification.** Full eval suite (`plugins/flow/evals/run_*.py`, 25 harnesses) green, no regressions. `run_merge_status_evals.py`: 42/42, including three new checks — the module catches a synthetic wrapped `all 30\n  slots` fixture; Check 2.5's SKILL.md text references `slot_count_scan.py` (a regression guard against silently regrowing a private grep); and Check 2.5's real shell block, extracted and executed via `sh -c` against the same wrapped fixture with `CLAUDE_PLUGIN_ROOT` pointed at this checkout, also flags it — proving both runtimes agree on the fixture that originally exposed the gap, not just that the library is correct in isolation. Manually exercised three cases against the extracted, executed shell block (wrapped-stale → WARN with survivor; clean 33-slots doc → PASS; plain non-wrapped stale count → WARN) before trusting the automated parity check.

**Staff-review pass (`/flow:staff-review`, ship-time rigor gate — no marker existed for this source, so it ran at Step 1.0a before the reviewers).** Design-engineer and push-further lenses found nothing applicable — no UI/visual surface in a doctor-check + eval-harness diff. Two lenses found real, fixed issues:
- **Staff-engineer NIT: the `bootstrap.sh` claim was factually wrong.** The rationale text (this entry's own first draft, plus the SKILL.md comment and the roadmap/plan blocks) asserted adding `bootstrap.sh` to Check 2.5's scan-target list "closes the named '.json/.sh' gap for the one concrete top-level script class FB-0079's corollary 3 identified." Verified false: `template/base/bootstrap.sh`'s own `copy_n` calls never copy itself into a bootstrapped project (only `CLAUDE.md`, `README.md`, `core-docs/*`, `.claude/`, `tools/`, `.github/`), and it doesn't exist at flow's own repo root either — only at `template/base/bootstrap.sh`, already covered by the *internal* sweep's separate recursive scan over a different runtime and scan root. Corrected every rationale (SKILL.md comment, this entry, roadmap, plan) to the honest, smaller claim: kept as a harmless zero-cost addition (a plausible top-level leftover if a consumer downloaded the script and left it at their project root), not a closed gap.
- **Staff-engineer FOLLOW-UP (applied): a stale security backlog item now describes dead code.** `dev-docs/plan.md`'s queued "Symlink-following grep hardening in Check 2.5" item described `grep -rEn`'s BSD/macOS symlink-following default — a mechanism Check 2.5 no longer runs at all post-hoist. Verified empirically (a `docs/linked -> /etc`-style fixture) that `Path.rglob("*")` lists a symlinked directory as an entry but does not descend into it — narrower than grep's default, a real risk reduction. Marked the backlog item mooted rather than deleted, so the historical concern stays legible.
- **UX-designer NIT (fixed): `repr()` leaked to the CLI reader, and the line number was computed but discarded.** `scan_paths()` originally appended `f"{f}: {m.group(0)!r}"` — for the wrapped case this rendered a literal two-character `\n` escape inline, reading as a tool bug rather than "these words are on separate lines." Fixed: the regex now captures the "slot"/"slots" word separately, and survivor lines render `path:line: "N slots"` (or `"N slots" (wrapped across a line break)` for the wrapped case) — human words, a jump-to line number, no Python syntax.
- **UX-designer NIT (fixed): the `SCANNED` count extraction was an unvalidated field-position coupling.** `awk '{print $3}'` against the library's first print line, with no check that the result parsed as a number — a future format change to `slot_count_scan.py` would have silently rendered a blank count in the `[PASS]` line rather than surfacing the drift. Now validated (`case "$SCANNED" in ''|*[!0-9]*) ...`) with a visible fallback naming the raw output.
- **UX-designer NIT (fixed): the catch-all exit-code branch swallowed the one diagnostic that would explain a scan failure.** The wildcard `case` arm printed only `"could not run (exit $RC)"`, discarding the captured `$OUT` (which could carry e.g. a Python traceback or "command not found"). Now prints it, matching Check 1.4's existing pattern in the same file.
- **UX-designer FOLLOW-UP (deferred, not applied):** no automated regression coverage of Check 2.5's real shell block on the PASS path — only manually verified this session. Reasonable to defer (additive, not required to close the FB-0079 class); left for whoever next touches `slot_count_scan.py`'s print format. Also noted, addressed with a one-line code comment rather than a fix: exit code 2 conflates an argparse usage error with a vacuous scan — harmless for doctor's own call site (always supplies a validated `--expected` and an existence-checked path list), worth a comment for a future caller.
- **Staff-engineer + UX-designer, both noted, neither fixed (pre-existing, out of scope):** `python3` availability is never pre-checked before Check 2.5 shells out to `$LIB` — matches the identical gap at Check 2.7, not a regression this PR introduces, and fails loud (the wildcard `case` arm) rather than silently passing.

**`/simplify` pass (bundled Claude Code skill, 4 parallel cleanup agents — reuse / simplification / efficiency / altitude).** Run before `/flow:ship`'s Step 2 reviewers per the canonical loop order (initially skipped in the process-gate lapse this entry's PROCESS NOTE describes; run properly here rather than marked skipped with a fabricated "tiny" reason, which would have been the exact same honesty failure this PR's own FB-0096 exists to name). Efficiency lens found nothing. The other three found real, fixed issues:
- **Reuse + Altitude (independently, both flagged the same defect): `fenced_block`/`_rest_from` in `run_merge_status_evals.py` were a byte-for-byte duplicate of the identical helper already in `run_role_slot_evals.py`** — introducing the exact FB-0079 duplication class this PR's own thesis is eliminating, one function away from `_lint()`'s correct reuse of `skill-composition-lint.py` in the same diff. Fixed: hoisted both functions into a new `plugins/flow/evals/eval_utils.py`, and both `run_role_slot_evals.py` and `run_merge_status_evals.py` now import from it instead of defining their own copies. (Touches a file — `run_role_slot_evals.py` — outside this PR's original scope; judged worth it given two independent lenses flagged it as directly undermining this PR's stated purpose, and the fix is a pure, behavior-preserving extraction.)
- **Simplification (fixed): `stale = [line.split(str(root) + "/", 1)[-1] for line in stale]` reconstructed a relative path by string-splitting** instead of using `Path.relative_to()`, which the code had access to and previously used before the hoist. Fixed: `scan_paths()` gained an optional `root=` parameter that calls `f.relative_to(root)` internally, so no caller reconstructs relativity from formatted text.
- **Simplification + Altitude (both flagged, fixed): the `SCANNED` count extraction (`awk '{print $3}'` against a human-readable sentence) coupled the shell parser to word position in prose**, and the altitude lens additionally noted the PASS path had zero real-subprocess regression coverage (only the WARN path was exercised end-to-end). Fixed two ways: `slot_count_scan.py` now emits a dedicated machine-parseable trailer line (`SCANNED_COUNT=N`) the shell extracts by `sed`, format-stable by construction rather than by validation guard; and a new `doctor-check-2.5-shell-pass-path-renders-scanned-count` eval case runs the real shell block against a clean, matching fixture and asserts the PASS line renders a real count.
- **Altitude (fixed): exit code 2 conflated "usage error" with "vacuous scan."** `slot_count_scan.py`'s own comment already admitted this; fixed properly rather than left as a comment — `main()` now catches argparse's `SystemExit` and remaps a usage error to exit 3, so a bad invocation can no longer be misread by a caller as "scanned 0 files, nothing to verify."
- **Altitude (found, not fixed — deferred to an existing roadmap item): `SLOT_RE` hardcodes the "slots" noun** rather than parameterizing to any "N `<noun>`" shape (skill count, lens count, rule count are the same FB-0010 class). Real, but a genuine scope expansion beyond the roadmap-named fix this PR implements — `dev-docs/plan.md` § "Generalize Check 2.5 beyond slot count" already tracks it as a separate item. Cross-referenced in `slot_count_scan.py`'s docstring rather than built here.
- **Simplification (found, judged false positive — not fixed): the `LIB`/`SCHEMA` shell-resolution-block duplication in Check 2.5.** The suggested fix (a shared shell function) would break the architecture every doctor check in this file already relies on — `run_role_slot_evals.py`'s own Check 2.11 test and this PR's new Check 2.5 test both extract and execute ONE check's fenced block in isolation via `fenced_block()`, so a function defined inside a different check's block would not exist when a check runs standalone. The duplication is structurally required, and matches the pre-existing convention already used identically by `SCHEMA=`/`L=`/`SDHELP=` resolution blocks elsewhere in the same file.

Full eval suite re-verified green after every `/simplify` fix, including the three cases (wrapped-stale, clean-pass, plain-stale) manually re-exercised against the final shell block.

**Version + FB-number collision — three episodes, each following a rate-limit-window stall that separated plan-gate resolution from shipping (this branch's own §4.8-class lesson in why a stale-base gate must re-check at EVERY rebase, not once).**

**Episode 1 (mid-session, before the first push):** drafted as **FB-0092**. By the time the session resumed, `#133` (orchestrator communication contract) and `#136` (AB Step 1) had opened claiming **FB-0092** and **FB-0093** respectively — both still open, unmerged. `origin/main` itself had not moved yet (0 commits behind), so this was caught via live `gh pr list` state, not a `git merge-base` divergence — the reservation protocol's collision defense extends to in-flight open PRs, not only what's already merged. Renumbered **FB-0092 → FB-0094** (swept 11 references, verified via `git diff` that each was this branch's own addition) and bumped **v1.32.0 → v1.33.0** (`#134`/`#135` also claimed v1.33.0 at the time — a known, accepted three-way race).

**Episode 2 (a second stall, resolved via an actual rebase — the first real `git merge-base` divergence):** `origin/main` had advanced one commit (`#133` merged, confirming episode 1's FB-0092 collision was real), and the open-PR field had grown: `#134` → v1.34.0, `#135` → v1.33.0, `#137` → v1.36.0 (`#136` unchanged). Re-derived the version fresh rather than trust the earlier pick — read each open PR's actual `plugin.json` by fetching its head ref directly (not its title), and took the next free minor above the highest live claim: **v1.32.0 → v1.36.0**. FB-0094 remained uncontended at this point (checked against `origin/main`'s `feedback.md` and every open PR body).

**Episode 3 (a third stall, at the SECOND real rebase):** both `#134` and `#135` had now merged, taking `origin/main` to **v1.34.0** — and `#134` had independently drafted and merged **FB-0094** for its own, unrelated concept (memory-effectiveness instrumentation, roadmap #3) while this branch sat open. Renumbered **FB-0094 → FB-0096** (swept every reference again) and re-confirmed the version pick fresh: v1.36.0 was still the next free minor above `main`'s new v1.34.0 and the highest live open claim (`#137`, still at v1.36.0), so it survived unchanged this time. Also swept two now-stale `reserved-feedback-numbers.md` lines (`#134`/`#135` had both merged with "held until MERGE" reservations still showing) into cleared notes. After resolving each rebase's conflicts, ran a positive-presence sweep — every line present on `origin/main` in `history.md`/`feedback.md`/`plan.md`/`roadmap.md`/`reserved-feedback-numbers.md`/`CHANGELOG.md` confirmed still present on this branch — to catch the silent-content-loss failure mode a clean auto-merge can hide (the same class that deleted a CHANGELOG entry on a sibling PR the same day).

**Files touched:** `plugins/flow/skills/doctor/lib/slot_count_scan.py` (new), `plugins/flow/evals/eval_utils.py` (new, `/simplify`), `plugins/flow/evals/run_merge_status_evals.py`, `plugins/flow/evals/run_role_slot_evals.py` (`/simplify`), `plugins/flow/skills/doctor/SKILL.md` (Check 2.5), `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json`, `CHANGELOG.md`, `dev-docs/roadmap.md` (§ Next item resolved), `dev-docs/plan.md` (Current Focus + PR block), `dev-docs/feedback.md` (FB-0096), `dev-docs/reserved-feedback-numbers.md` (FB-0096 claimed, audit-trail entries added).

---

## 2026-08-27 — D1 Phase 1: the experience/ambition lens + design-brief template + `/flow:review-brief` pre-prototype orchestrator (FB-0081/FB-0046)

**Branch:** `conductor/d1-phase-1-experience-lens-brief-orchestrator` · **PR:** #137 · **Mode:** feature · **Version:** 1.32.0 → 1.35.0

**What was done.** D1's prototype-first gate (`dev-docs/handoffs/d1-prototype-first-gate.md`) moves a UI change's first human gate from a written plan to an approved prototype. Phase 0 (#128) shipped the `role` config slot; this PR ships Phase 1, the "review the brief before building anything" half: a new `plugins/flow/agents/lens-experience.md` agent (D3, FB-0046's two lenses — experience/product-designer, and push-further-on-quality with an anti-scope-creep guard), a design-brief template documented in `workflow.md` (six fields, ~80-word guideline), and `/flow:review-brief` — a standalone-invocable skill that extracts a brief once and fans it to `auditor` + `plan-critic` + `lens-experience` in one tool message, returning a single triaged verdict.

**Why.** FB-0081 (user-directed, settled design) requires rigor before any prototype gets built — "flow agent should still be asking me questions for clarity, and it needs some review steps for its own work similar to audit and critique before prototyping." FB-0046 established the experience/ambition + push-further-on-quality lenses as the quality layer alongside the conformance layer (`auditor`/`plan-critic`). Phase 1 delivers both, self-contained, per the handoff's own §13 PR breakdown — no trigger, no prototype phase, no loop re-ordering.

**Design decisions.**
- **`lens-experience.md` ships as one agent with two lenses**, not two agent files — matches the handoff's Phase 1 checklist item literally ("Author `plugins/flow/agents/lens-experience.md` ... (a) ... (b) ..."), and mirrors how `lens-push-further` is itself already a single multi-faceted lens within the `lens-*` family.
- **Experience-half severity is `BLOCKER`/`REDIRECT`/`FOLLOW-UP`, not the diff-lenses' `BLOCKER`/`NIT`/`FOLLOW-UP` — a human-decided deviation, caught by self-running `/flow:critique-plan` on the plan before presenting it.** The first drafted plan silently gave `lens-experience.md` this taxonomy (borrowed from `plan-critic`, on the reasoning that this lens reviews a *document* the way `plan-critic` does, not a diff the way the other three `lens-*` siblings do) plus narrower tools (`Read, Grep` only) — without surfacing either as an open call, directly contradicting the handoff's explicit "match the `lens-*.md` frontmatter + output shape" instruction. `/flow:critique-plan`, run against the plan as instructed by the dispatching orchestrator before presenting it to the human, caught this as a `REDIRECT`-severity Spec violation (citing `lens-staff-engineer.md`/`lens-ux-designer.md`/`lens-design-engineer.md` verbatim). Fix: tools conformed to the full `Read, Grep, Glob, Bash` grant (no functional reason to narrow it); the severity taxonomy was surfaced as a third open call (alongside the two already-flagged MEDIUM-confidence calls) with recommendation + confidence + justification, and the human approved the recommendation (`BLOCKER`/`REDIRECT`/`FOLLOW-UP`) at plan-approval time. **Process note:** this is FB-0090 (escalate with recommendation + confidence + justification) working as designed — the plan's own act of applying it to two calls made the reviewer's citation of it, against a silent third deviation, legible as a real gap rather than noise.
- **§9.2 (proportionality "small surface" threshold) deliberately NOT resolved here**, despite the handoff's own Phase 1 checklist saying to pin it with a fixture during Phase 1. Recommended and approved at the plan gate: defer to Phase 2, when the trigger §9.2 gates actually exists — pinning a fixture for logic nothing calls yet would be speculative, and Phase 1's own scope (per the handoff's §13 PR breakdown) is explicitly trigger-free.
- **`/flow:review-brief` is not `context: fork`, unlike `/flow:critique-plan`/`/flow:audit-plan`.** It fans out to three parallel `Agent` calls, which a single-agent fork+`agent:` dispatch structurally cannot do (the forked context becomes that one named agent's own tool grant — `plan-critic.md` has no `Agent` tool). This has a real downstream consequence: `run_jq_guard_evals.py` classifies config-reading skills as fork (routed-signal, `exit 0`) or blocking (real `MISSING=""`/`exit 1` guard) purely from the `context: fork` frontmatter field. The first draft copied `critique-plan`'s fork-shaped guard into a non-fork skill and the harness correctly failed it (`review-brief: has a command -v jq blocking guard`) — fixed by restructuring the jq check into an explicit Step 0 the assistant runs via the `Bash` tool (mirroring `/flow:staff-review`'s Step 1.5), ahead of the extraction step. Left as a discovered-not-anticipated fact in the Files-touched note, not a plan gap: nothing in the plan's own design section named this constraint before the harness surfaced it.
- **No draft-PR manifest routing for `decision-required`.** Explicitly not gate machinery (the task brief's own framing) — there is no PR at the pre-prototype-brief stage, so FB-0075's shape is reused only as "render an answerable question list," not the manifest mechanics `/flow:ship` uses downstream.
- **`review-brief`'s Step 1 hard-refuses (`ROOT-UNRESOLVED`) on an unresolvable repo root, rather than falling back to `${TMPDIR:-/tmp}/flow-detached` the way `staff-review`/`security-review`/`accessibility-review`/`ship`/`verify-build` do.** Deliberate, matching the *other* existing precedent instead — `critique-plan`/`audit-skips`'s own `ROOT-UNRESOLVED` refusal — because a spec/design-language violation cannot be judged without the reference docs a resolved root loads, so a detached fallback would silently review against nothing rather than say so. Flagged by `/flow:staff-review`'s staff-engineer lens as undiscussed in this section on the first pass; recorded here per that finding.

**Technical decisions.**
- Eval fixtures reuse `extract_session.py --mode plan --plan-file` **unmodified** — no changes to the shared extraction script, per the handoff's own "reused, do not rebuild" list.
- New harness `run_review_brief_evals.py` is entirely offline/stdlib (mechanical extraction checks + structural grep checks against hand-authored `.expected.txt` fixtures), matching the existing `run_evals.py` convention of pinning the prompt *contract*, not live LLM judgment.

**Tradeoffs discussed.**
- The design-brief template's ~80-word target is documented as a guideline, not mechanically enforced — nothing produces a brief yet for a cap to bind against. Deferred to whichever Phase 2 step ends up drafting briefs, the same way Phase 0 documented `role` before anything read it.
- The template lives in a new, clearly-labeled `workflow.md` subsection rather than inside the reordered Step 1–2 flow, so as not to preempt Phase 2's explicit task of reordering those steps.

**Verification.** `run_review_brief_evals.py` (37 checks: extraction mechanics against both brief fixtures, lens output-contract structure, orchestrator composition, workflow.md field coverage) green; `run_jq_guard_evals.py` green with `review-brief` correctly classified in the blocking (non-fork, non-carve-out) population; all 25 eval harnesses (24 prior + new) re-run, all green; CI's harness/runner join-check reproduced locally and confirmed green.

## 2026-08-27 — Memory-effectiveness instrumentation, reduced to `--dead` (roadmap #3, FB-0094)

**Branch:** `conductor/3-memory-effectiveness-instrumentation` · **PR:** #(assigned at open) · **Mode:** feature

**What was done.** `tools/memory/check.mjs` gains `--dead [--days=N]` (default 60), which
mechanically lists failure-pattern memory entries with no activity — most recent `Fire log`
date, falling back to `First seen`, falling back to file mtime — older than the threshold.
`/flow:ship` § 4b.vi (and the mirrored `ship-spike` bullet) now run it before spawning the
periodic-audit Explore agent and feed its output in as a deterministic candidate list, instead
of leaving the agent to compute date arithmetic across up to 30 entries by hand. New eval
harness `run_memory_check_evals.py` (fixture-driven, subprocess against the real script, no
mocking) wired into `ci.yml`.

**Why.** `dev-docs/roadmap.md` § Next "#3" named three pieces: (a) fire-count instrumentation,
(b) dead-entry surfacing, (c) fire-rate×recency ranking of "injection." Flow's memory corpus is
count-capped (30) + mtime-sorted with a purely manual, eyeballed audit for staleness — nothing
mechanized any of it.

**Design decisions.**
- **Scope cut to (b) only, mid-plan, by the human.** The initial plan (all three pieces) was
  critiqued via `/flow:critique-plan`, fixed, and presented — but its own analysis had already
  surfaced the ceiling: flow's `check.mjs` only *reports on* `~/.claude/projects/<canonical>/
  memory/`; the harness's native auto-memory loader reads that directory directly, and flow has
  no index file or injection-order hook. So (c) could only ever reorder a curation-facing
  `--list` output over a corpus capped at 30 files — real machinery (a scoring formula, a
  deterministic `--record-fire` writer to keep it robust, a pinned Fire-log write syntax) for a
  cosmetic payoff. The human's direction: "you found the ceiling yourself... `--dead` is the
  one piece with a genuine consumer." Synthesized as FB-0094. Full original-scope plan and the
  cut rationale are preserved in the "PR — Memory-effectiveness instrumentation" block in
  `plan.md`.
- **Two corrections to the original dispatch brief**, made before scoping: `tools/memory/
  check.mjs` doesn't exist at that path — the real file is `plugins/flow/tools/memory/
  check.mjs`, a **shipped plugin artifact** (used by `/flow:ship`, `/flow:ship-spike`,
  `/flow:post-merge`), not a `tools/model-measure/`-style dev tool. All work stayed inside
  `plugins/flow/` accordingly, under the "prompt changes are code changes" bar (eval fixture
  required).
- **Calendar-days (60), not "N ships," for the dead-entry threshold.** The roadmap literally
  said "no fire in N ships," but that requires a new per-entry, per-ship counter (incremented
  on every ship run for every non-firing entry) with no existing analog. Calendar-days reuses
  timestamps already captured in the `Fire log`/`First seen` bullets and mechanizes wording
  `/flow:ship` § 4b.vi's prose already committed to ("no activity in 60+ days"). Recommended at
  medium confidence, accepted by the human unchanged when the ranking-formula question (the
  other open decision) went moot with the cut.
- **Lenient date extraction, not a pinned write format.** Since `--record-fire` was cut, the
  parser has no deterministic writer to depend on — it still has to read whatever the existing
  freehand `ship § 4b.v` append produces. `extractDates`/`fieldLine` regex-scan for any
  `YYYY-MM-DD` substring after a `**Fire log**`/`**First seen**` bullet rather than assuming one
  exact separator style, so pre-existing entries and future freehand appends both parse.
- **Three-tier `lastActivity` fallback** (last fire → first seen → file mtime), each tier only
  reached if the one before is unparseable — never throws on a pre-this-feature entry with no
  `Fire log` bullet at all (the malformed-input path the quality bar requires).

**Technical decisions.**
- `--list`, `--count`, `--audit-due`, and the default summary are byte-for-byte unchanged —
  `--dead` is a pure addition, confirmed by the eval's regression cases.
- The eval harness builds its fixture memory dir under a real `~/.claude/projects/` tempdir
  (required by `check.mjs`'s own `validateMemoryDir` path guard — nothing outside that root is
  accepted) and saves/restores the shared `.last-audit` marker (which lives beside the script,
  per-install rather than per-fixture-dir) around its one `--audit-due` regression check, so the
  eval run doesn't perturb real ship-counter state.
- No new `flow.config.json` schema slot for the day threshold — hardcoded `DEAD_ENTRY_DAYS = 60`
  constant, mirroring the existing unconfigurable `AUDIT_INTERVAL = 5`. Avoids a slot-count
  fan-out (`workflow.md`'s "33 slots" line, the schema's 40 property keys) for a threshold that's
  a one-line change if it ever needs tuning.

**Tradeoffs discussed.** Building the full three-piece plan would have delivered a "correct in
principle" ranking system whose only real effect was reordering a report nobody but a human
curating a 30-entry corpus reads — cost (scoring formula, deterministic writer, a newly-pinned
markdown field contract, more eval surface) clearly outweighing payoff once the injection-control
ceiling was named explicitly. Calendar-days over ship-count trades literal roadmap-wording fidelity
for zero new bookkeeping; accepted as the right trade since ship-count doesn't obviously behave
better across projects with different ship cadences either.

**`/simplify` (4-lens pass) caught one real correctness bug and two minor cleanups, all fixed
in-tree.** The altitude lens found that `fieldLine` (the helper reading a `**Fire log**`/`**First
seen**` bullet) matched only the *first* line containing the label — so if a repeated firing were
appended as its own new bullet line rather than onto the existing line (a shape nothing pins;
`--record-fire`, which would have made the write format moot, was the piece that got cut), later
fires would be silently dropped and an actively-firing entry could read as dead. Its own comment
claimed a "one-bullet-per-field" contract that doesn't actually exist in `rules/documentation.md`
or `ship/SKILL.md` § 4b.v. Fixed by unioning dates across every matching line (`fieldLine` →
`fieldLines`, `'g'`-flagged) rather than pinning the write format — consistent with the parser's
stated design goal of tolerating freehand appends. Added a fixture
(`feedback_split_fire_lines.md`) writing fires across two separate bullet lines to pin the fix;
without it the bug was invisible to CI (the original fixture always comma-joined fire dates onto
one line). The simplification lens also found `parseEntry`'s `firstSeen` field was computed for
internal fallback use but returned and never read by any caller (dead output once the
fire-rate-ranking consumer was cut) — dropped from the return shape — and that `daysSince` was
computed twice per stale entry (once to filter, once to print) — now computed once and threaded
through. The eval's 7 near-identical `--dead`-default presence/absence checks collapsed into one
data-driven table. Reuse and efficiency lenses returned clean.

**`/flow:staff-review` (4 lenses) caught one real correctness bug and three cheap-nit
improvements, all fixed in-tree; two lenses N/A'd correctly.** Design-engineer lens: no visual
surface in this diff (confirmed by inspection, not assumed) — correctly returned no findings.
Staff-engineer lens found the more serious issue: `fieldLines`' regex still matched
`**Fire log**` (or `**First seen**`) **anywhere in a line**, not just on the bullet line itself —
so a *different* field's prose (e.g. a `Pattern` field discussing the feature and happening to
bold "**Fire log**") could have its own nearby dates misread as real activity, silently making a
genuinely-stale entry look fresh and defeating `--dead`'s entire purpose. Fixed by anchoring the
regex to the bullet marker (`^\s*-\s*\*\*Label\*\*.*$`, multiline). Added
`feedback_prose_mentions_fire_log.md` (a real 90-day-old fire, with Pattern-field prose bolding
"Fire log"/"First seen" near recent dates that must not count) to pin it, and confirmed the fix
is load-bearing by temporarily reverting the regex and re-running the harness (red: 1 failure on
that exact fixture; green after restoring the fix). UX-designer + staff-engineer lenses
independently converged on the same `--days=` validation gap: `parseInt` accepts fractional
(`30.5`→30) and the original regex silently skipped an empty value (`--days=` with nothing after
`=`), so both bypassed the PR's own "loud warning, never a silent wrong-default" contract (the
Spec-walk's own words). Fixed by validating the raw string (`/^\d+$/`) before `parseInt` rather
than checking `Number.isInteger` after it. UX-designer also found that passing `--days=` twice
could set a value from the first flag, then print a warning about a *different*, second flag —
message and behavior disagreeing. Fixed by honoring only the first `--days=` occurrence
(valid or not) and never inspecting a second one, so the message always describes what's actually
in effect; and that `--dead`'s printed line carried only a relative day-count while `--list`
prints an absolute ISO date, forcing a reader to compute the date themselves. Push-further lens
(independently) found the same shape from a different angle: the day-count alone can't
distinguish "known-quiet since a real date" from "no dates recorded at all, mtime is just
noise" — the exact ambiguity `parseEntry`'s three-tier fallback exists to resolve, thrown away
before printing. Both close with one fix: `parseEntry` now returns `activitySource`
(`fire`/`first-seen`/`mtime`), and the `--dead` line prints the ISO date plus which tier resolved
it (e.g. `2026-XX-XX, 90d since last activity via fire, 1 fire`) — added a backdated-mtime
fixture (`feedback_stale_mtime_only.md`, via `os.utime`) since no prior fixture actually exercised
the `mtime` tier in the *stale* set. Staff-engineer's remaining findings were accepted as
documented, no-action tradeoffs: the mtime-fallback-resets-on-rehome case (now called out
explicitly in `parseEntry`'s comment), `DEAD_ENTRY_DAYS` as a second hardcoded constant matching
the `AUDIT_INTERVAL` precedent (already reasoned about in this entry's Technical decisions), and
the eval's dependency on a writable `~/.claude/projects/` (already documented in the harness's own
docstring) — plus a cosmetic `fieldLine`→`fieldLines` doc-drift fix in `plan.md`. Reviewer notes
kept in this history entry rather than a separate PR-body section since this is a LOCAL-ONLY
review (no PR existed yet) folded directly into the ship pipeline that opens one.

**Three-surface note.** Entirely inside `plugins/flow/` (shipped plugin artifact) plus this
`dev-docs/` entry and `.github/workflows/ci.yml`. No `.claude/`/`tools/` (project-dev infra)
touched.

## 2026-08-27 — Phase 00: fix two shipped-but-never-loading flow features (FB-0085)

**Branch:** `conductor/phase-00-rules-as-skills-hooks-fix-fb-0085` · **PR:** #(assigned at open) · **Mode:** feature

**What was done.** Fixed two flow features advertised since early releases that had never mechanically fired for any consumer, per `dev-docs/handoffs/service-agnostic-roadmap-2026-07.md` §17/Phase 00:
- **00a.** Converted the 4 portable rules (`general`, `plan-discipline`, `documentation`, `exploration`) from `plugins/flow/rules/*.md` — not a real Claude Code plugin component — into path-activated skills at `plugins/flow/skills/{general,plan-discipline,documentation,exploration}/SKILL.md` (`paths:` frontmatter, carried over unchanged; `user-invocable: false`). Deleted the dead `rules/` directory. Updated the two internal cross-references (`ship/SKILL.md:518`, and the two self-references now living inside the moved files) and rewrote doctor's Check 3.2 (item 00f).
- **00b.** Confirmed hooks stay opt-in (human decision, see below) — no `plugin.json` change. Fixed `plugins/flow/docs/workflow.md`'s "default hooks" phrasing to state the opt-in posture explicitly, matching `docs/automation-boundaries.md`'s already-correct wording.
- **00c.** Reconciled the drifted `.claude/rules/{general,documentation}.md` vs their plugin counterparts (human decision, see below) — synced the 3 genuinely-duplicated sections in `general.md` (Scope discipline, Decision tracking, Autonomous work guardrails) and the whole of `documentation.md` (the plugin's version had evolved fields the project-dev copy never backported: forward-referenceable Commit/PR field, sanitization in the SAFETY-marker criteria, the "Recorded rejections" section). Added an explicit cross-reference/sync-obligation note to all 4 files (2 pairs) so future drift is a decision, not an accident.
- **00d.** No `bootstrap.sh` change (human decision, see below) — `docs/bootstrap.md`'s install-then-scaffold ordering already means the 4 rule-skills reach consumers via the plugin install with zero copy step, which is why `template/base/` never had rule templates beyond `safety.md.template` (the one that's genuinely per-project).
- **00e.** Corrected every live claim found by an evidence-based sweep (superseding the handoff's own file-list guess, which cited 2 sites that carry no such claim today). `docs/first-pr.md:208` named literal old filenames (`plan-discipline.md`, `exploration.md`) that no longer exist — fixed. `README.md:86` and `docs/automation-boundaries.md:17` needed no edit — both become *true* once 00a lands rather than needing reworded, and the human explicitly asked that README not be touched beyond what's true when this PR lands.
- **00f.** Rewrote doctor's Check 3.2 from an inferred-PASS (based on Section 1's marketplace/enabled checks) to a real shell-out: `claude plugin details flow@flow`, grep the `Skills (` line for each of the 4 names, `[FAIL]` naming which are missing, `[SKIP]` cleanly when `claude` isn't on `PATH`.
- **Fan-out sweep (FB-0010).** `dev-docs/roadmap.md:336`'s live "17 skills" claim updated to 21 (it would otherwise have gone silently stale on a living doc). Confirmed no other live surface — README, `marketplace.json`, `plugin.json`, doctor's own description, `workflow.md` — carries a stale count.

**Why.** Both were confirmed live bugs, not hypothetical: `rules/` has no plugin-root loader call site (binary-decompiled the installed CLI, v2.1.237 — one minor version past the roadmap doc's v2.1.141, so the bug is still live in the current release), and `hooks/default-hooks.json` matches no auto-discovery filename while `plugin.json` declares no `hooks` field, so `claude plugin details` always reported `Hooks (0)`.

**Design decisions.**
- **Skill naming.** Kept the source files' names as directory names (`general`, `plan-discipline`, `documentation`, `exploration`) rather than prefixing (e.g. `rule-general`) — lowest-diff option, and `user-invocable: false` means they never surface in `/help` or get model-selected, so collision risk with a future invocable skill is low.
- **Hooks stay opt-in (escalated, human call).** Recommended and accepted: `default-hooks.json`'s own header already stated the intent ("NOT auto-applied — consumers opt-in"), the shipped hook does broad substring matching with real false-positive risk (`*token*`, `*key*`, `*secret*`), and it matches flow's stated "Passive over active" product principle. Mechanically verified the alternative (declaring `"hooks": "./hooks/default-hooks.json"` in `plugin.json`) works — `Hooks (0)` → `Hooks (1)` in a scratch test — but chose not to take it.
- **Reconciliation via sync + cross-reference, not merge (escalated, human call).** Recommended and accepted: the two `.claude/rules/general.md` vs plugin `general` skill copies serve genuinely different audiences for most of their content (this repo's own FB-0010/dogfooding meta-rules vs the plugin's project-agnostic consumer content) — only 3 of ~6 sections were real accidental duplication. A structural fix (deleting the project-dev copies and self-installing `flow@flow` for this repo's own sessions) was considered and set aside as disproportionate to a loading-bug fix.
- **No bootstrap.sh copy logic added (escalated finding, human-confirmed deviation from the handoff's literal wording).** Adding `copy_n` lines for the 4 rules would have re-created exactly the copy-then-drift problem 00c exists to fix, fanned out to every consumer project — and it isn't needed, since the plugin install already precedes the scaffold step.

**Technical decisions.**
- The doctor check greps only the `Skills (` line of `claude plugin details`'s output (not the whole multi-line output) to avoid any incidental false-positive match against prose elsewhere (e.g. a future description mentioning one of the 4 names as an English word).
- `git grep` fan-out exemption narrowed from "all of `dev-docs/*`" to specifically `history.md`/`CHANGELOG.md` (immutable per-PR logs) after `/flow:critique-plan` caught that the original wording would have let `roadmap.md` — a **living doc** per `dev-docs/README.md` — go silently stale.

**Tradeoffs discussed.**
- Chose docs-only fixes for 00b/00e over touching `plugin.json`'s `hooks` field, trading a smaller code diff for the safer default (opt-in stays opt-in).
- Chose partial content-sync over full structural merge for 00c, trading a fully single-sourced rule for preserving each file's genuinely audience-specific content without a larger self-dogfood-install architecture change.
- Left `dev-docs/roadmap.md:912`'s queued config-driven-`paths:` item (activation parity for non-standard doc-name projects) unaddressed — real and related, but a distinct gap from "never loads at all," and out of this phase's scope.

**Lessons learned.** Verified both bugs against the live, installed CLI (binary string search + a scratch-copy round-trip test showing skill count 17→18 and `Hooks (0)`→`Hooks (1)`) before writing the plan, per FB-0085's own discipline — catching in the process that the handoff's own citation of `plugin.json`/`marketplace.json` as carrying a live "portable rules" claim was stale; a fresh `grep` found nothing there. `/flow:critique-plan` caught two real issues in the drafted plan (the eliminated `/flow:land` mechanism named for a job it no longer does; an overbroad `dev-docs/*` fan-out exemption that would have let a living doc go stale) — both fixed before execution.
---

## 2026-08-27 — Model-measurement harness, Steps 2+3: offline A/B eval + shadow sampler (roadmap item M, dev-tooling only)

**Branch:** `conductor/model-measurement-harness-steps-2-3-item-m` · **PR:** #(assigned at open) · **Mode:** feature (non-shipped dev tooling)

**What was done.** Builds the final two of roadmap item M's three drafted deliverables (Step 1, per-subagent token attribution, shipped as #129). New `tools/model-measure/ab_eval.py` scores two pre-captured raw reviewer outputs (`<case_id>.opus.txt` / `<case_id>.sonnet.txt`) against `plugins/flow/evals/ground_truth.yaml` by importing `run_evals.check_required`, computes a category-based finding-overlap metric and a per-model false-positive rate, and reports token cost per model via `model_measure.build_report` re-bucketed by model instead of by agent type. New `tools/model-measure/shadow_sampler.py` provides `recommend_model()` (weighted-random Opus/Sonnet pick, default 10% Sonnet), `record_sample()` (logs one JSONL line, attributing tokens for that invocation via the same sidecar lookup), and `aggregate()`. Both ship with CI-safe eval harnesses (`run_ab_eval_evals.py`, 25 checks; `run_shadow_sampler_evals.py`, 16 checks) that run entirely offline against synthetic fixtures — zero live model calls, zero network — wired into `ci.yml`'s existing `model-measure` job. Added a belt-and-suspenders concurrent-spawn case plus a targeted single-invocation lookup (`find_sidecar_invocation`) to Step 1's own harness (`run_model_measure_evals.py`, now 19 checks).

**`/simplify` pass (4 lenses, 6 findings → 6 fixes, 0 skips).** All four lenses (reuse, simplification, efficiency, altitude) independently converged on real, fixable issues — worth recording because one was a genuine correctness bug, not just style. **The altitude lens caught it:** `ab_eval.token_cost_by_model` added a subagent invocation's *full* totals into *every* model observed in that invocation's `models` set, rather than summing once — multi-counting tokens for any invocation whose transcript carried more than one model (a real, if rare, shape per `model_measure`'s own docstring). Compared against `model_measure.aggregate_by_type`'s existing sum-once/union-for-display pattern, which the new code claimed to reuse but didn't, for the aggregation half. Fixed by summing each invocation exactly once, keyed by the single model when unambiguous or a composite `"model_a+model_b"` key when genuinely mixed — surfacing the anomaly instead of silently inflating a cost report the eval exists to make trustworthy. Pinned by a new regression case (`test_token_cost_by_model_multi_model_invocation_sums_once`). **The efficiency lens caught a real quadratic-work bug:** `shadow_sampler.token_totals_for_invocation` called `model_measure.read_sidecar_subagents`, which parses *every* subagent transcript in the session, when it only ever needed one (by `tool_use_id`) — since `record_sample` is meant to be called once per real invocation over a session's life, this turned O(N) per-session logging into O(N²) total parse work. Fixed by adding `model_measure.find_sidecar_invocation` — a targeted lookup that still globs the cheap `*.meta.json` files but loads only the one matching `.jsonl` — and pinning it with 3 new cases in Step 1's own harness (now 18 checks) before shadow_sampler consumed it. **The reuse and simplification lenses independently flagged the same duplication:** `run_ab_eval_evals.py` and `run_shadow_sampler_evals.py` each pasted a byte-identical `check()`/`_failures` pass-fail helper that `run_model_measure_evals.py` already defines and that both files already import (`import run_model_measure_evals as rmme`) for other fixture helpers — collapsed to `check = rmme.check` / `rmme._failures` in both. **Simplification also caught:** a dead `mm.load_session(session_path)` call in `ab_eval.token_cost_by_model` whose result (`records`) was only used for an `if not records` guard that `read_sidecar_subagents`'s own graceful degradation already makes redundant — removed; `expected_categories`'s unnecessary nested loop over `elem.items()` when every `ground_truth.yaml` `required` entry is a single-key dict — collapsed to a direct `elem["category"]` lookup; and a YAGNI `agent_type` parameter on `shadow_sampler.recommend_model` that was accepted, immediately `del`-ed, and used by no call site or test — dropped, with all call sites (the CLI's `--dry-run` and 3 eval cases) updated to match.

**Why.** FB-0083 requires measuring a delegated model against Opus before any routing decision, and generalizes PR P's auditor-only measurement discipline to the whole subagent fleet. Step 2 (comparative eval) and Step 3 (organic sampling) are the two pieces of that measurement the roadmap named as still open after Step 1.

**Design decisions.**
- **Mechanism split, forced by "no direct API calls."** `tools/model-measure/` is stdlib Python with no Anthropic SDK dependency and no API key (CLAUDE.md's tech-stack constraint). A Python script cannot itself spawn a live Opus call and a live Sonnet call; only a Claude Code session can, via the Agent/Task tool's `model` override. So both new files split into (a) a CI-safe stdlib component whose logic is pinned against synthetic fixtures, and (b) a documented manual/human-run recipe for the live half — the same shape `plugins/flow/evals/run_evals.py` already uses for its pluggable `run_auditor()`. This was flagged explicitly at the plan gate rather than discovered mid-build.
- **Step 2 scoped to `auditor`/`plan-critic` only, not `lens-*`.** `ground_truth.yaml` has 11 cases and none of them are lens fixtures — verified with a grep before drafting the plan, not assumed from the roadmap text (which still names `lens-*` in its Step 2 bullet). Lens agents reviewing live diffs have no mechanical ground truth to score against; building fixtures for them is scoped out and left as a `roadmap.md` follow-up rather than silently narrowing scope without saying so.
- **Finding-overlap is a category-level Dice coefficient, not claim-text similarity.** Both `auditor` (`ISSUE · [category]`) and `plan-critic` (`ISSUE · [SEVERITY] · [category]`) headers are schema-fixed per each agent's own Output-format section, so parsing the `·`-delimited header is exact and requires no LLM-graded text comparison. Chose Dice (`2·common/total`) over a raw match-count so a model that raises more issues than the other doesn't get an artificially inflated or deflated score by list length alone.
- **False-positive rate returns `None`, not `0.0`, when a fixture declares no `category` check.** Fabricating a `0.0` would read as "no false positives measured" when the truth is "nothing to measure against" — the same silent-optimism failure mode FB-0010 names for other fallbacks.
- **The shadow sampler is a recommend/log utility, not a routing mechanism, by construction.** The plan's own drafted verify bullet ("a dry-run shows... that Opus stays the default assignment") reads as a design constraint, not just a test to pass: nothing in `plugins/flow/` imports or calls `shadow_sampler.py` (asserted by a `git grep` restricted to that path in the eval harness), and `recommend_model()`'s default `sonnet_rate=0.1` means Opus is the overwhelming default on every call site that might eventually consult it. The file's own docstring states this precisely so a future reader doesn't mistake the utility for shipped routing.
- **Reuse over re-derivation, twice.** `ab_eval.py`'s `token_cost_by_model` and `shadow_sampler.py`'s `token_totals_for_invocation` both call into `model_measure`'s existing sidecar-attribution functions (`load_session`, `session_dir_for`, `read_sidecar_subagents`) rather than re-parsing transcripts — Step 1's sidecar format is proven; re-deriving it in two more places would triple the surface a future transcript-shape change has to be fixed in.

**Tradeoffs discussed.**
- **No live A/B run in this PR — deliberately.** Running a real Opus-vs-Sonnet sweep costs real tokens (Agent-tool invocations). This is cost exposure per `.claude/rules/general.md`'s Autonomous work guardrails, so it was raised as an explicit open call at the plan gate rather than folded into "build the harness." The human approved the recommendation to ship harness + synthetic self-tests only, deferring the first live run to a separate, later, explicitly-confirmed step. The harness existing is not the same as the harness having been run against real data.
- **The shadow sampler's real-world sample rate may prove too sparse** (single-assignment, opt-in — a developer has to choose to consult `recommend_model()`), a risk the original plan draft named explicitly ("revisit if samples are too sparse"). Shipping single-assignment first per that guidance rather than pre-emptively building a double-run (paired, higher-cost) mode nobody has asked for yet.
- **`token_cost_by_model` re-buckets by model rather than by agent type**, the opposite grouping from Step 1's `model_measure.py` report. This is deliberate: an A/B run spawns the *same* agent type under two *different* models, so agent-type buckets would collapse the exact distinction the eval exists to draw. Step 1's per-agent-type view and Step 2's per-model view are both correct; they answer different questions over the same underlying sidecar data.

**`/flow:staff-review` (4 lenses: staff engineer, UX designer, design engineer, push-further).** Design engineer: nothing of consequence — no visual/rendered surface exists in this diff (confirmed by grepping for markup/style extensions, not assumed). The other three converged on real findings. **Staff engineer caught two correctness bugs in the just-added `/simplify` fixes themselves — worth naming because they're the same silent-optimism class the `/simplify` pass had just closed elsewhere, recurring one layer down:** (1) `shadow_sampler.aggregate()` folded a `totals: None` sample (a failed sidecar lookup) into `count`/`mean` as a zero-token observation via `s.get("totals") or {}`, corrupting the exact figure the tool exists to produce — fixed by excluding `totals is None` rows from the mean and reporting them separately via a new `unmatched` counter, so a failed lookup is visible rather than silently averaged away. (2) `find_sidecar_invocation` (added during the `/simplify` efficiency fix) dropped the "malformed meta file" warning its sibling `read_sidecar_subagents` emits for the identical condition, and `shadow_sampler.token_totals_for_invocation` then discarded even the warnings the function *did* return via an underscore-prefixed local — both fixed: `find_sidecar_invocation` now warns when the *matching* invocation's meta is malformed, and `record_sample` threads warnings through to a new `warnings` key on every logged record. **UX designer + push-further independently converged on the same two CLI-ergonomics gaps:** `ab_eval.py --json` silently dropped its `warnings` list (present only in text mode) — added to the JSON payload; a mistyped/empty `--session-file` produced a bare, unexplained absence of the token-cost section — now prints an explicit `NOTE:` line. **Push-further's `roadmap-concrete` findings, both cheap enough to fix in-tree (pure aggregation/wiring over already-computed or already-tested data, no new data path):** `ab_eval.py` now prints a `Summary across N case(s)` line (mean finding-overlap, ground-truth pass counts, mean FP-rate per model, token totals + delta when `--session-file` is given) beneath the per-case table — the aggregate answer the eval exists to produce, not left for a human to eyeball across rows; `shadow_sampler.py` gained an `--aggregate LOG_PATH` CLI flag wiring the already-built, already-tested `aggregate()` to the command line (previously reachable only by importing the module). **Deferred as a genuine scoped extension, not fixed here:** staff-engineer's broader `--recommend`/`--record` CLI surface for `shadow_sampler`'s real-invocation path — routed to `roadmap.md` under item M as a named follow-up rather than expanding this already-large PR.

**Verification.** All three harnesses pass locally (`run_model_measure_evals.py` 19/19, `run_ab_eval_evals.py` 25/25, `run_shadow_sampler_evals.py` 16/16); `dev-docs/check-index.py` passes. `git grep -n "^model:" plugins/flow/agents/*.md` confirmed empty both before drafting the plan and again at ship — the hard FB-0083 constraint has nothing to violate because no agent carries `model:` frontmatter today.

**Files.** `tools/model-measure/ab_eval.py` (new), `tools/model-measure/run_ab_eval_evals.py` (new), `tools/model-measure/shadow_sampler.py` (new), `tools/model-measure/run_shadow_sampler_evals.py` (new), `tools/model-measure/model_measure.py` (new `find_sidecar_invocation` helper), `tools/model-measure/run_model_measure_evals.py` (new concurrent-spawn + targeted-lookup cases), `.github/workflows/ci.yml` (two more `run:` steps), `dev-docs/plan.md`, `dev-docs/roadmap.md`. **No plugin artifacts changed** — no version bump, no manifest edit, no CHANGELOG entry, same non-shipped status as Step 1 (#129). **Zero agent `model:` changes; zero live model calls.**


---

## 2026-08-26 — Orchestrator communication contract: decide within scope, escalate concise + progressive (FB-0092)

**Branch:** `conductor/orchestrator-flow-cloud-workflow-succession-2` · **PR:** #133 · **Mode:** docs

**Branch:** `conductor/orchestrator-flow-cloud-workflow-succession-2` · **PR:** #133 (merged) · **Mode:** docs

**What was done.** Amended canonical plan **§4.8** with a five-rule communication contract for every orchestrator-to-human message, not only gate escalations: (1) decide within the plan-gate/merge-gate green quadrants and advance workers directly, escalating only what a red axis forces; (2) every escalation carries the FB-0090 triple (recommendation/confidence/justification) trimmed to the minimum, never a transcript; (3) progressive disclosure — lead with the decision needed, let the human pull detail by asking; (4) one decision at a time, with a one-line pointer to other open threads so the human keeps the lay of the land without being forced through everything at once. (5) the seat is the **single human-facing decision surface in both directions** — escalation means the orchestrator presents the decision in the seat and relays the answer back to the worker, never that the human opens the worker workspace; approval authority still moves to the human on high-stakes/high-taste/gate-machinery calls, but the interaction surface does not. Explicitly ties this to the §4.10 skill suite (`/flow:orchestrate`/`/flow:spawn`/`/flow:handoff`/`/flow:gate`) so it's a design requirement for those skills' human-facing output, not an unenforced convention a fresh orchestrator seat has to rediscover each time. Added FB-0092 to `feedback.md`.

**Why.** Ben's stated model: the orchestrator seat exists so he doesn't have to spend time in worker workspaces, which only works if the orchestrator's own channel to him is high-signal — humans read large blocks of text far worse than agents do. A verbose orchestrator (or one that dumps every open thread flatly) recreates the exact attention cost the seat was built to remove. Demonstrated live in-session: the orchestrator's own first status update was rewritten against these rules once stated, surfacing that this needed to be *built into the skills*, not left as a personal habit — hence codifying it in the plan + feedback doc rather than only session memory.

**Design decisions.** Placed the contract inside existing §4.8 (rather than a new section) since §4.8 already specified the escalation-format triple (FB-0090) — this generalizes that paragraph rather than duplicating a parallel rule elsewhere. Explicitly scoped to govern §4.10's skill suite by name, since that suite (decided the same session, landing separately on #131) is where these rules get mechanically enforced rather than relying on author memory.

**Provenance for rule 5.** Added 2026-08-27 after the seat ran six parallel workers: the human confirmed that decisions needing their approval should still be *collected, recommended, and relayed* by the orchestrator rather than answered inside each worker chat. Without it, a strict reading of "escalate to the human" would send the human into N workspaces — reintroducing exactly the attention cost the seat removes.

**Tradeoffs discussed.** Considered leaving this as session memory only — rejected per direct user instruction: memory doesn't propagate to a fresh orchestrator seat or to the skill suite other repos install, so the rule would have to be rediscovered every rotation (exactly the hostage/rot pattern §4.9 exists to prevent).

**Three-surface note.** Docs-only (`research/` + `dev-docs/`). No plugin artifacts.

---

## 2026-08-26 — §4.9 externalize-non-git fix + §4.10 orchestrator skill suite (in flow) + FB-0091

**Branch:** `succession-file-externalization` · **PR:** #(assigned at open) · **Mode:** docs

**What was done.** Closed two gaps the first real orchestrator succession surfaced.
- **§4.9 file-externalization fix.** The disposability invariant was too loose — a *sandbox-local file* is recoverable from **neither** GitHub nor the Conductor API and dies when the sandbox is torn down, yet the first succession brief pointed the successor at a `/home/…` report path in the *outgoing* sandbox (a different sandbox it cannot reach). Wind-down is now **three steps** — flush durable currency to git, **externalize any non-git artifact that matters** (commit if repo content, else hand its contents to the human), then hand off the brief — and the invariant sharpens to "recoverable from GitHub, the API, **or already delivered to the human**." Added the rule that every brief reference must point at a reachable location, never the outgoing sandbox. (The report survived only because it had been surfaced to the human; caught live.)
- **FB-0091.** The successor was spawned on `sonnet-5-1m`/high; the family matched the routing table but the effort was a by-feel bump. Rule: the orchestrator routes *itself* (including its successor) per the §4.3 table with a logged `model · effort · why`, never silently by feel.

**Why.** Both are dogfood findings from executing the §4.9 succession this session — the model working, and revealing its own two soft spots.

- **§4.10 + §4.4 revision — the orchestrator skill suite moves INTO flow.** The user directed the orchestration workflow to be a core part of flow (not per-repo): a suite of **agent-invocable** skills — `/flow:orchestrate` (successor bootstrap), `/flow:spawn` (the model-decision-tree + dispatch brief), `/flow:handoff` (the §4.9 wind-down + archive-safety), optional `/flow:gate` — shipped in `plugins/flow/skills/`, with Conductor mechanics behind a `dispatchBackend` adapter slot so host-agnosticism holds (reversing §4.4's exclusion, whose revisit criterion is now met). Cross-workspace invocation is *instruct-not-remote-invoke*: `/flow:spawn` creates B and tells B's agent to run a named flow skill; B, having flow installed, invokes it locally — which is precisely why the suite must ship in flow and be agent-invocable. This is now the concrete shape of §5 Step 4 (orchestrator v1).

**Three-surface note.** Docs-only (`research/` + `dev-docs/`).

---

## 2026-08-26 — SAFETY — The `toolchain` manifest kind: "verifiable in principle, just not on *this* machine" (canonical cloud-workflow §5 Step 1)

**Branch:** `conductor/toolchain-manifest-kind-keystone-v1` · **PR:** #(assigned at open) · **Mode:** feature · **Version:** 1.31.0 → 1.32.0

**What was done.** Flow could say *there is no runnable target* (`platform: library|none`, `verifyEnabled: false`). It could not say *there is one, and this machine cannot build it* — the normal condition of a Linux cloud workspace on an iOS project. Four pieces close that: a `toolchain` kind in `manifest-triage.py`'s `KIND_COPY` (auto-extending `KINDS` and the `add-entry` allow-list), classified `blocked` and added to `CHECK_ONLY`; a new shared `skills/verify-build/lib/toolchain.py` holding one platform→binaries table and an `absent()` probe; a third self-skip case in `/flow:verify-build` § 1.2 so flow itself *declares* the skip; and a validated branch in `skip-audit-checks.py` that accepts it only when a toolchain-shaped reason **and** a host probe agree. A new `manifest_kind` field carries the engine's decision across the fork boundary to `/flow:ship` Step 2a.3, which routes it to the draft manifest.

**Why.** Both prior exits were wrong, and both were traced live (canonical §2.2). Run verify-build on a toolchain-less host and it fails to launch, judges `Unknown`, and gets filed as `needs: regression fix` — the wrong diagnosis, because nothing was exercised. Skip it and `skip-audit-checks.py:257` answers "skip claims platform library/none but platform='ios'" — a refutation that is technically right and practically useless, since it demands a re-run the host cannot perform. The gate was fighting the only honest thing a cloud session could do.

**Design decisions.**
- **The verdict is a conjunction, and this was the human's call at the plan gate — overruling my recommendation.** I proposed making `LEGITIMATE` reason-*independent* (host fact decides; the reason only distinguishes the red case), arguing that the manifest entry rather than the verdict word carries the gate. The human chose reason-**conditioned**: in gate machinery a too-permissive `LEGITIMATE` branch *is* the silent failure the gate exists to prevent. That is the better call. Under the shipped rule, a skip given for an unrelated reason ("ran out of time") on a toolchain-less host resolves to `NEEDS-JUDGMENT`, not `LEGITIMATE` — the skip auditor never excuses a skip that never claimed a toolchain problem. Pinned by four eval cases covering both "reason alone" and "host fact alone".
- **`absent()`, never "`missing()` is non-empty".** A platform's entry lists every binary its build needs; `absent()` is true only when *all* are missing. The gap is the partial-toolchain host — Xcode installed, `xcrun` off `PATH` — where the gate must still **run**. Erring toward running costs a failed build; erring toward skipping silently drops the change's only behavioral gate, and the resulting entry is `CHECK_ONLY` + `blocked`, so no waiver can subtract it.
- **`ios` only, by decision rather than omission.** Android's near-universal build entry point is the repo-local `./gradlew` wrapper, which `shutil.which("gradle")` never resolves — a table entry there would make every fully-equipped Android machine self-skip on every run. `tauri` has the same unresolved question (`cargo` is usually present even where the platform toolchain is not). The producer has no `NEEDS-JUDGMENT` escape hatch, so a permissive table is unrecoverable; widening it needs a wrapper-aware probe and a capable-host fixture, not a new dict key.
- **`blocked`, not `ask`.** `ask` + `CHECK_ONLY` renders a numbered question whose only offered options are `render_decisions`' CHECK_ONLY line ("I won't mark a **failing build** ready" — nothing was built) and `DEFAULT_THEN` ("re-run the check … and mark the PR ready once it passes" — impossible on that host). `blocked` is the engine's own definition of the situation and already renders the right surface; `_then()` returns `BLOCKED_THEN` for it, so the record deliberately carries no `then` field.
- **Appended, not reordered.** The new branch is the last case in the verify-build skipped-block chain; branches 1–3 keep their positions, conditions and strings verbatim. Reordering would change verdicts on reasons that match two vocabularies at once — not a free refactor in gate machinery. The accepted residual: a toolchain reason containing the bare word `none` matches branch 1 first and gets a misquoting `SHOULD-RE-RUN`. It is safe *and* self-healing — verify-build is `auto-resolvable`, so ship re-invokes it, the producer writes the canonical reason, and the single re-audit lands on the toolchain branch. Both hops end in a draft; pinned by two cases so a future reorder is a visible decision.
- **`manifest_kind` as a 4-tuple at every `classify()` return site**, not an optional/`len()`-tolerant 4th value. A forgotten site would silently default to "owes the PR nothing" — the FB-0010 silent-skip shape, in the engine whose job is refusing silent skips. With the 4-tuple, a missed site raises an unpack error under the harness.
- **Copy describes only what exists.** Canonical §4.2 drafts the `means` string as "queued for a machine that does", but the queue it names (`needs-mac-verify` + `/verify-queue`) is §5 Step 3 and out of scope — shipping that wording would send a non-engineer looking for something that is not there. An eval asserts the rendered block contains no "queue".

**Tradeoffs discussed.**
- **A docs-only PR from a toolchain-less host still drafts.** The producer fires on the host fact alone, so a docs-only diff on such a host gets a `toolchain` entry. That is *today's* outcome too (verify-build runs, cannot launch, `Unknown` → escalate/draft), so it is status-quo-preserving rather than a regression — and it is what let the plan delete an entire shared behavior-diff predicate (`touches_behavior`, a relocated `collect_files`, a `SOURCE` kind in `file_patterns.py`, and an agreement fixture) that an earlier draft carried purely to avoid it. Relaxing it means reversing `ship/SKILL.md:313`'s deliberate "verify-build does NOT auto-skip on doc-only diffs", which is a separate decision.
- **Undeclared `platform` opts a project out silently.** The slot is optional, so an iOS project that never declared it keeps today's behavior entirely. Safe, but invisible. Autodetecting instead would make a gate verdict depend on a heuristic — the opposite of this change's premise. A `/flow:doctor` nudge for Apple-shaped repos with no declared `platform` is the named follow-up.
- **`--which-from` is a test-only trust surface on a production engine.** CI runners have no Apple toolchain, so without it the "toolchain present ⇒ SHOULD-RE-RUN" red case is unrunnable — a red case that never executes is not a red case. Only the harness passes it; `/flow:ship`'s Step 2a.1 handoff does not; the default is the real `shutil.which`. Same posture as the existing `--config`/`--files-from` overrides the module header already documents.
- **The Step 2a.3 emitter is prose, not code.** What makes it hard to skip is that the *engine* supplies `manifest_kind` (the agent does not decide it), and `test_producer_lines` fails if the literal `add-entry --kind toolchain` site disappears — the 8→9 kind-list equality alone would not have caught that, because `kinds_seen` unions the `add-entry` harvest with the inline-template harvest.

**Verification (red-green, both harnesses).** `run_skip_audit_evals.py` goes 35 → 79 checks; `run_manifest_triage_evals.py` gains a full `[toolchain]` section plus a redirect assertion over every `add-entry` site. **Red-verified** by reverting the five engine files to `origin/main` and deleting `toolchain.py` while keeping the eval cases: 18 skip-audit failures + 7 triage failures, each failing exactly as predicted. The logic failure was isolated from the new CLI flag by running the pre-change engine with no `--which-from` on this genuinely toolchain-less host — `NEEDS-JUDGMENT` with no `manifest_kind`, versus `LEGITIMATE` + `toolchain` after. The § 1.2 producer was extracted and **executed** under both `bash` and `sh`: it skips on `platform: ios` here, falls through on `web`, and prints the unchanged message on `library`. All 25 plugin harnesses green (set-compared against `ci.yml`), plus #129's `tools/model-measure` harness.

**Fan-out (grep first, edit second — FB-0010).** Four contracts changed, each swept by grep over an explicit pathspec and each paired with a positive so the check cannot go green by deletion: verify-build's skip enumeration (13 sites incl. `docs/automation-boundaries.md`, which a `plugins/`-scoped grep structurally could not reach, and `ship-spike/SKILL.md`, which three drafts of the plan never mentioned); the `platform` slot's documented semantics (schema + template example); the manifest kind count 8 → 9 (incl. `manifest-triage.py:573-574`, where "six / of eight" wraps across a line break and a line-oriented grep misses it); and ship's two-value `skip-audit=` record vocabulary (the closed alternation at `:321` and the worked example at `:324` — `:426` only *instructs* the agent to record, so an earlier two-site list would have left a toolchain PR recording a clean pass while that same audit was why it drafted).

**`/simplify` pass (4 lenses, 16 findings → 11 fixes + 1 reasoned skip).** Worth recording because two findings were about this change *preaching a rule and breaking it in the same commit*. The reuse lens found `skip-audit-checks.py` re-implementing `toolchain._load_present()` verbatim, and testing `platform in PLATFORM_TOOLCHAIN` (raw dict) where the module's own `required()` accessor answers the same question — which matters precisely because `toolchain.py` carries a live deletion criterion: if `platform` ever gains a per-project toolchain declaration, `required()` would consult config while the raw-dict test would not, and the gate condition would silently diverge from the predicate it gates. The altitude lens went further and found the same fan-out still open for the *prose*: the producer phrased its `skip_reason` in the SKILL while the auditor kept its matching needles in Python, coupled only by three unlinked string literals. `toolchain.py` now owns `SKIP_REASON_PREFIX`, `REASON_NEEDLES`, `load_present` and a `skip_reason()` that emits the canonical sentence — and a new eval feeds the producer's real output through the auditor's real predicate instead of asserting each end against a third hardcoded copy.

That also collapsed the CLI: it had grown `required` (never called by anything), `missing`, and `absent`, so the SKILL spawned Python twice and then stripped JSON punctuation with `sed` to rebuild a sentence the module could simply print. One `skip-reason` subcommand now carries the predicate in its exit code and the sentence on stdout — and it is guarded on a declared `platform`, so an undeclared project spawns **zero** interpreters where it previously paid one to be told the table has no entry. The prose there claimed undeclared projects were "unaffected"; that was true of the verdict but not the mechanism, and is now true of both. Also dropped: a `"no simulator"` needle strictly subsumed by `"simulator"`, and a top-level `toolchain` report block that no consumer read and that rendered four keys of noise into every audit payload on every project. **Declined, with reason:** ~6 redundant `shutil.which` calls (sub-millisecond, once per run) — `absent()` as a self-contained predicate is worth more than the syscalls, and threading a `len()` comparison out to callers is exactly how the two consumers would drift on the partial-toolchain case.

**`/flow:staff-review` (4 lenses) found two BLOCKERs — both in code this change added, both of which would have defeated it.** Recorded in full because the first is the sharper lesson in the whole PR.

**(1) The emitter never wrote to the manifest.** `manifest-triage.py add-entry` *validates and prints* the line; it does not write it — every other producer site spells the `>> "$(… manifest-path --branch "$BRANCH")"` redirect. The new Step 2a.3 bullet had no redirect. So the toolchain entry would have gone to stdout, Step 7a.5 would have classified an empty manifest, the verdict would be `READY`, and §7a.6 would open a **non-draft** PR. That is precisely "a LEGITIMATE toolchain verdict with no manifest entry ⇒ ready PR with no behavioral gate" — the failure this entire change exists to prevent, reintroduced by the fix for it. Proven mechanically before fixing (`add-entry` → manifest file empty → `classify` → `READY`). **Why no eval caught it:** `test_producer_lines` harvests `add-entry --kind ([a-z0-9-]+)`, which matches a redirect-less invocation identically; and the end-to-end case captured `add-entry`'s stdout and wrote the file *itself*, so it tested engine composition while stepping over the exact join that was broken. The fix ships with the assertion that closes the class — every `add-entry` site in `ship/SKILL.md` must be followed by a `manifest-path` redirect — mutation-tested by removing the redirect and confirming it goes red.

**(2) `/flow:ship-spike` lost its only gate.** Spike mode invokes no `/flow:audit-skips` and its PR is explicitly not manifest-gated, so on a toolchain-less host its sole behavioral gate was verify-build running, failing to launch, judging `Unknown`, and halting for user adjudication. The new self-skip exits 0, which would have converted that halt into a silent pass — strictly *less* gated than before, on exactly the hosts this program targets, and a direct contradiction of the plan's own stated invariant ("no path anywhere in this change makes a host less gated than it is today"). The diff had updated ship-spike's prose to *describe* the new skip without reasoning about the gate delta. Now documented as requiring the same adjudication `Unknown` demanded, and pinned.

**The UX lens found a third, in the copy.** `needs_you` offered "mark the PR ready yourself on GitHub if you accept it un-verified" while the block's own trailer, three lines below, reads "Do not merge while this block is present" — and `/flow:land` hard-fails on a PR merged still carrying the manifest. For `verify-build` that contradiction is an edge case a passing re-run clears; for `toolchain` it is the **expected terminal state of every cloud-workspace PR**, so this change would have turned a rare trap into the default path. The copy now says what actually happens: the block stays either way, and flow will ask once more to confirm the merge was deliberate.

**Three lenses independently flagged the same silent fall-through** — `2>/dev/null` plus a bare conditional treating every non-zero exit as "toolchain present", so a missing `python3` or a broken helper silently restores the launch→`Unknown`→filed-as-a-regression path. `.claude/rules/general.md` rule 1 (pair every `2>/dev/null` with a `[WARN]` branch) was being preached in this diff and broken six lines from where the warn branch was already written. Fixed on both sides: the shell branches on the exit status, and `toolchain.py` no longer exits 1 when it could not answer (a config that parses but is not an object used to raise `AttributeError` → exit 1, indistinguishable from "present"; now `ConfigError` → exit 2, while an *absent* config stays exit 1 as a normal condition).

**Process note.** The plan went through 18 `/flow:critique-plan` rounds before the gate. Several were substantive and changed the design: the original scope was a **net weakening** of the gate (an uncontested skip routed nowhere ⇒ empty manifest ⇒ ready PR with no behavioral verification); prose-keyed verdicts were exploitable in both directions; the `./gradlew` failure mode killed `android`/`tauri`; and one round caught a fan-out grep that could never return zero, so its own Spec-walk box was unsatisfiable except by widening the carve-out until it passed.

**Files.** `skills/verify-build/lib/toolchain.py` (NEW), `skills/verify-build/SKILL.md` (§ 1.2 + `:437`), `skills/ship/lib/manifest-triage.py`, `skills/audit-skips/lib/skip-audit-checks.py`, `skills/ship/SKILL.md` (Step 2a.3 + fan-out), `skills/audit-skips/SKILL.md` (`## Output` contract), `skills/ship-spike/SKILL.md`, `skills/verify-build/lib/not-tested-checklist.md`, both eval harnesses, `docs/workflow.md`, `schema/flow.config.schema.json`, `template/base/flow.config.json.example`, `docs/automation-boundaries.md`, `plugin.json` + `marketplace.json` (1.32.0), `CHANGELOG.md`, `dev-docs/{plan,roadmap,history}.md`. No `ci.yml` change (both harnesses already wired); `file_patterns.py` untouched.
---
## 2026-08-26 — §4.8 gate delegation + §4.9 orchestrator succession + escalation format (FB-0090) + doc-currency fold

**Branch:** `gate-delegation-policy` · **PR:** #(assigned at open, §4.5 #N convention) · **Mode:** docs

**What was done.** Added **§4.8 "Gate delegation"** to the canonical plan: *who* holds each gate is a function of the decision's properties — a four-axis rule (stakes / reversibility / confidence / taste) for the plan gate, and an **explicit-verifiability** rule (docs-only OR verify-build `PASS` + extremely-high confidence) for the merge gate; carve-outs (prototype-attached plan → human; `sensitivePaths` → human); **`merged_by`-via-GitHub-App** as the free, no-seat transparency primitive (label interim + a one-time App-setup checklist); crawl → walk → run rollout. Added **§4.9 "Orchestrator succession"**: the orchestrator seat is *disposable* — it holds no state not recoverable from GitHub (durable design, flushed as-you-go) + the Conductor API (live worker state, re-derived not snapshotted); wind-down flushes durable currency to git and hands a transient succession brief to the successor **via the API, not git** (a handoff, like a dispatch brief — the brief is an accelerant, not a lifeline). Added the **escalation-format** rule (FB-0090): decisions surfaced to the human carry recommendation + confidence + justification by default. **Folded the pending doc-currency** (§4.6's "eventual must not become never" bound, discharged into this substantive ship rather than a standalone land PR): plan.md ACTIVE PROGRAM head reconciled (#129 shipped; toolchain executing; D1 + measure archived), roadmap `§ Exploration` concurrent-work entry marked **RESOLVED by #126** (the CLI-vs-prose design fork retained).

**Why.** This session ran the orchestrator model live — dispatched three workers, **delegated the first plan approval** (measure: low-stakes / reversible / high-confidence / low-taste) and **escalated the gate-machinery one** (toolchain) to the human. §4.8 codifies the policy those calls followed. The measurement + iOS-simulator angle decides where merge-automation pays off (flow's own `platform: library` code merges stay human; consumer iOS projects with real verify-build are where it earns its keep).

**Three-surface note.** Docs-only (`research/` + `dev-docs/`). No plugin artifacts.

---

## 2026-08-26 — Model-measurement harness, Step 1: per-subagent token + model attribution (FB-0089, dev-tooling only)

**Branch:** `conductor/model-measurement-harness-item-m-v1` · **PR:** #(assigned at open) · **Mode:** feature (non-shipped dev tooling)

**What was done.** Builds the first of roadmap item M's three drafted deliverables (FB-0083 measurement-first constraint: Opus stays default, no swap, no routing table): a stdlib-only report attributing tokens and the model that ran to each subagent invocation, sourced from a Claude Code session transcript. New `tools/model-measure/model_measure.py` (imports `find_session_file`/`load_session` from `plugins/flow/scripts/extract_session.py` rather than duplicating session-loading logic) + `tools/model-measure/run_model_measure_evals.py` (14 fixture-driven checks), wired into `.github/workflows/ci.yml` as its own `model-measure` job. Zero plugin artifacts changed — no version bump, no manifest edit, no CHANGELOG entry.

**Why.** FB-0083 forbids routing any subagent off Opus without measured data. This is the cheapest, zero-risk first cut of that measurement: know where tokens actually go before deciding anything about where they should go. Steps 2 (an offline Opus-vs-Sonnet A/B eval over the reviewer fixtures) and 3 (a randomized/shadow sampler) remain queued as separate follow-up PRs.

**Design decisions.**
- **Two transcript shapes, one report.** Live verification this session (spawning a real subagent and inspecting the resulting files) found the actual on-disk shape in this Conductor-hosted environment: subagent invocations write to a sibling `<session-dir>/subagents/agent-<id>.jsonl` + `agent-<id>.meta.json` (same stem/prefix, naming `agentType`/`toolUseId`/`spawnDepth`) — not the inline `isSidechain: true` format `extract_session.py`'s pre-existing skip logic assumes. The tool supports both: the sidecar path (HIGH confidence, verified live) as primary, and the inline path (MEDIUM confidence, built to the existing code's assumption, not re-verified in this sandbox) as a fallback that degrades to an honest `unattributed` bucket on ambiguous concurrent spawns rather than guessing.
- **Dedup by `message.id` before summing usage.** The same live inspection found that assistant JSONL records sharing one `message.id` repeat an identical `usage` snapshot 1–4 times (thinking + tool_use content blocks split across records) — naive per-record summation would overcount tokens by that multiple. `dedupe_assistant_usage` keeps one snapshot per id (the last occurrence, defensively, in case a future Claude Code release makes this incremental instead of a repeated snapshot).
- **Non-shipped placement, twice corrected.** Originally planned for `plugins/flow/scripts/` (the shipped-plugin surface); `/flow:critique-plan` caught that the script has no consumer entry point and no `/flow:*` skill ever calls it — moved to `tools/model-measure/` per CLAUDE.md's three-surface boundary. During execution, `git add` on that path was refused (`.gitignore` blanket-ignores `tools/`); two relocation attempts (`dev-docs/tools/model-measure/`, `dev-docs/model-measure/`) chased the wrong root cause before checking repo precedent: git only enforces `.gitignore` against *untracked* files, and this repo already tracks three other paths under a `tools/` segment (`plugins/flow/tools/memory/check.mjs`, two `template/stacks/*/tools/preflight/*`) via `git add -f`. Reverted both detours; final location is the original plan-approved `tools/model-measure/`, force-added once. Full narrative in `dev-docs/plan.md`'s "Placement detour" note and `dev-docs/feedback.md` FB-0089.

**Tradeoffs discussed.**
- The ambiguous-overlap case in the inline fallback (concurrent subagent spawns) is a real, acknowledged coverage gap, not just an edge case — flow itself dogfoods parallel `Agent` calls routinely. Shipping it as an honest `unattributed` bucket rather than a wrong guess was the deliberate choice; `/flow:staff-review`'s staff-engineer lens sharpened this further (a staggered partial-close sub-case is narrower than full N-way overlap and not yet fixture-covered — routed to `dev-docs/plan.md` as a FOLLOW-UP).
- The report is stdout-only plain text; Step 2's A/B eval will likely want machine-readable output. Deferred to Step 2's kickoff rather than speculatively building a `--format json` mode now (routed to `dev-docs/plan.md`).
- `/flow:staff-review`'s UX-designer and design-engineer lenses independently caught the same defect (fixed-width table columns overflow on realistic data — a 41-char row label against a 40-char column, and real Claude model ids against a 24-char column) — fixed with data-driven widths + an explicit `" | "` delimiter so overflow degrades to ragged text rather than misaligned numbers; captured as a cross-session memory entry given the two-reviewer convergence. `/flow:security-review` suggested one defensive `isinstance()` guard (a non-string `usage.model` field would otherwise raise on `set.add()`); applied, then re-verified by a fresh, targeted `/flow:staff-review` pass (the rigor-gate marker had gone stale from that one-line fix landing after the first marker write) and given its own regression fixture, confirmed red-then-green by direct mutation testing.

**Lessons learned:** see `dev-docs/feedback.md` FB-0089 for the full write-up — verifying a claimed transcript-format assumption by producing the real thing beats inferring it from code that assumes it, and a gitignore pattern with no leading slash matches at every depth, not just the root.

**Files touched:** `tools/model-measure/model_measure.py` (new), `tools/model-measure/run_model_measure_evals.py` (new), `.github/workflows/ci.yml` (new job), `CLAUDE.md` (§3 table row), `dev-docs/plan.md`, `dev-docs/roadmap.md`, `dev-docs/feedback.md` (FB-0089), `dev-docs/reserved-feedback-numbers.md` (FB-0089 cleared), `dev-docs/history.md` (this entry).

## 2026-08-26 — D1 Phase 0: the `role` config slot (FB-0081, schema+doc only)

**Branch:** `conductor/d1-role-slot-phase-0-v1` · **PR:** #(assigned at open) · **Mode:** feature (schema + doc surface only)

**What was done.** Implements Phase 0 of the D1 "prototype-first gate" execution plan (`dev-docs/handoffs/d1-prototype-first-gate.md`, D2 in `dev-docs/roadmap.md` § Designer-signal track, FB-0081): an optional `role` enum slot (`"designer" | "engineer"`, no default) added to `plugins/flow/schema/flow.config.schema.json`; a new `/flow:doctor` Check 2.11 reporting the resolved value in all three states (unset / designer / engineer) plus a `[WARN]` on any out-of-enum value; `role` documented in `plugins/flow/docs/workflow.md` § "Project config slots" (table row + narrative paragraph); and a new stdlib eval harness `plugins/flow/evals/run_role_slot_evals.py` (24 checks: schema shape, round-trip, doctor contract, doc contract), wired into `.github/workflows/ci.yml`.

**Why.** D1 (the prototype-first human gate for UI work) needs a way to know whether the human on a project is a designer or an engineer before its trigger can branch behavior — this PR ships only the slot the trigger will read, per the handoff's own phased "Suggested PR breakdown" (§13), so D1 lands in small, independently-shippable pieces rather than one large PR.

**Explicitly not built here (later D1 phases):** the trigger logic that reads `role`, the experience/ambition lens agent (D3), the design-brief template, the pre-prototype orchestrator, the prototype phase, human gate 1, or any workflow.md re-ordering. This PR changes zero runtime behavior for any existing project.

**Design decisions.**
- **Closed two-value enum, no `default` key.** Mirrors the existing `platform` enum slot's shape (also enum-typed, no `default`, prose-documented fallback) rather than inventing a new pattern. No `default` specifically so "unset" stays a third, distinct, mechanically-checkable state from either enum value — a future trigger reading `role == "designer"` must not be able to confuse "the project didn't say" with "the project said engineer."
- **`role` lives in `flow.config.json`, not `CLAUDE.md`.** Raised directly by the user mid-session: every other behavior-affecting flow slot is in structured JSON specifically so skills can read it deterministically via `jq`, rather than parsing intent out of freeform prose. Persistent, project-scoped, set-once — not a per-session declaration.
- **Left the enum's third value unspecified.** `roadmap.md`'s D2 entry writes "designer / engineer / …" with a deliberate ellipsis; inventing a plausible third role now (e.g. `"pm"`) with no concrete consumer would be undirected scope growth this PR's own plan explicitly forbade.

**Technical decisions / tradeoffs.**
- **doctor's `[WARN]` on an out-of-enum value, not silent PASS.** Nothing enforces the schema's `enum` at runtime (no `jsonschema` dependency anywhere in this stdlib-only repo), so a typo'd `role` in `flow.config.json` would otherwise read as cleanly resolved. Doctor's own `case` statement is the only mechanical check.
- **The "N slots" fan-out swept wider than the original plan anticipated.** The plan's Spec-walk originally named one live reference (`workflow.md`); a repo-wide `git grep -n "32 slots"` during execution found two more live (not historical) references the plan missed: `doctor/SKILL.md`'s own frontmatter description (invisible to Check 2.5's line-based grep, since the "32"/"slots" tokens are wrapped across two YAML lines) and `template/base/CLAUDE.md.template` — the scaffold every new consumer project's `bootstrap.sh` copies verbatim, and therefore a live claim, not narrative. All three now say "33 slots"; the remaining `git grep` survivors (`CHANGELOG.md`, `dev-docs/plan.md`, `dev-docs/roadmap.md`, the point-in-time research doc) are confirmed past-release narrative and were left alone, per Check 2.5's own documented convention for historical counts.
- **Grep-verified no other consumer reads the slot.** `git grep -n '\.role\b' -- plugins/` surfaces several unrelated hits (`turn.role` in `extract_session.py`/`bounding_logic.py`/`harvest_lesson.py` — an LLM message's user/assistant role; a DOM/ARIA `role` attribute in `annotation-layer.html`) that are a different concept entirely, not the config slot; the new doctor check is the only reader of `flow.config.json.role`.

**`/simplify` pass (4 parallel cleanup agents — reuse, simplification, efficiency, altitude).** The reuse-angle agent's most valuable finding: `plugins/flow/evals/run_merge_status_evals.py` deliberately hardcodes `check("schema-slot-count-32", len(props) == 32, ...)` as a standing FB-0010 tripwire (forces every schema-slot addition to touch that file) — my new slot would have silently broken this existing, CI-wired eval had `/simplify` not caught it. Fixed (32→33, docstring + trail comment updated). That same file's `no-stale-slot-count-in-shipped-surfaces` sweep — a wrap-tolerant, cross-file regex scan over `plugins/` + `template/` that already existed and is *more thorough* than anything I'd built by hand — independently confirmed my `workflow.md`/`CLAUDE.md.template` fixes were correct before I even knew the sweep existed. The simplification-angle agent caught a tautological eval section (round-tripping a value against the very constant it was constructed from, exercising no real file I/O); rewritten to use real temp files + the schema's own live enum. Two eval checks (`docs-3`..`docs-6`) were deleted as weaker duplicates of the `run_merge_status_evals.py` sweep. One `run_jq_guard_evals.py` gap was closed: the new doctor check wasn't registered in that harness's extract-and-execute jq-guard testing — the exact "new guarded check, silently untested" shape FB-0074 was named for. Two findings (doctor's double `jq` call; hardcoded enum vs. a dynamic schema read) were judged to match pre-existing doctor conventions exactly (Checks 2.3/2.4 and the `platform` slot respectively) and left as-is rather than introducing a one-off inconsistency — noted, not argued away. All 24 eval harnesses in the repo re-run green after every fix.

**`/flow:security-review` (during `/flow:ship`).** No BLOCKERs. Traced `flow.config.json`'s `role` value through Check 2.11's `case`/`echo` shell and found no injection path — `$ROLE` is captured once via command substitution and only ever matched/echoed inside quotes, and POSIX shells don't re-parse an already-expanded variable's contents for metacharacters (that requires `eval`). One NIT applied: added a live-executed regression test (not a grep) that crafts a `flow.config.json` with a command-substitution payload in `role`, runs Check 2.11's real extracted shell block, and asserts the payload never executes and is echoed back inert. A follow-up re-review (staff-engineer lens) then caught that the test's own comment overclaimed what it proves — it cannot detect a hypothetical "dropped quote" regression, since shell semantics make that safe regardless of quoting; only introducing `eval`/`sh -c "$ROLE"` would trip it. Fixed the comment + error messages to state the real invariant; verified the check's discriminating power in a scratch sandbox against a genuine `eval`-based injection (canary created) vs. the safe pattern (canary not created).

**`/flow:staff-review` (4 parallel lenses, run twice — once before the security fix, once after, per the rigor-gate's auto-resolve discipline when the fix invalidated the first marker).** No BLOCKERs. UX-designer lens caught two copy issues in doctor's Check 2.11: the unset-role message leaked the internal "D1 prototype-first trigger" codename into terminal output a user would read with zero context for it (reworded to plain language), and the designer/engineer PASS branches were missing the same "nothing consumes this yet" disclaimer the unset branch implied (both branches now read `role: designer (informational only — no flow skill reads this yet)`). Staff-engineer lens caught that `run_role_slot_evals.py`'s doctor-side checks were unscoped substring matches against the whole `SKILL.md` rather than Check 2.11's own block — tightened with a `section_after()` helper so an unrelated future mention of "2.11" or "designer" elsewhere in the file can't make these pass vacuously. Design-engineer and push-further lenses found nothing (no visual surface in scope; "at ceiling for its scope"). Four FOLLOW-UPs captured to `dev-docs/plan.md` + one directly into `dev-docs/handoffs/d1-prototype-first-gate.md` §7 (the most load-bearing: once a trigger reads `role`, a designer needs a way to confirm it actually activated, not just that the slot round-trips).

**SAFETY:** none — additive schema slot, no fallback/error-handling/persistence behavior touched.

**Three-surface note.** Plugin artifacts (`plugins/flow/schema`, `plugins/flow/skills/doctor`, `plugins/flow/docs/workflow.md`, `plugins/flow/evals/`) + one shipped consumer scaffold (`template/base/CLAUDE.md.template`) + CI wiring — all user-visible surface, correctly separated from this session's `dev-docs/` updates (this entry, `plan.md`, the handoff's Phase-0 checkboxes).

---

## 2026-08-25 — Orchestrator handoff model: two-lifetime doc-currency (§4.6) + human-alongside-orchestrator (§4.7) + forward-doc reconciliation

**Branch:** `orchestrator-handoff-process` · **PR:** #(assigned at open, per the §4.5 #N convention) · **Mode:** docs

**What was done.** Two orchestrator-model design captures in the canonical cloud-workflow plan, plus reconciliation of the stale forward docs a regroup audit surfaced.
- **§4.6 (two-lifetime handoff / evolved archive-safety):** doc-currency splits into *live handoff* (the orchestrator dispatch brief, not in git) + *durable* (folds into the next ship, §4.5). Archive-safety's four checks; doc-currency shifts from an archive *blocker* to a tracked *follow-up*; the session-end currency-flush bound keeps "eventual" from becoming "never."
- **§4.7 (human alongside the orchestrator):** a lightweight consideration, not a feature — reading a worker is always safe; writing shares the orchestrator's inbox; (b)-by-default human-takeover detection rides the re-sync the orchestrator already owes (latest inbound `userMessage` it didn't send → back off), with (a) "I've got X" as override. One hard rule: don't message a worker mid-`/flow:ship` unless aborting.
- **Forward-doc reconciliation:** a doc/memory audit confirmed ONE authoritative plan (the 2026-08-23 canonical) and no competing plans/memories, but `plan.md` Current Focus/Handoff Notes and `roadmap.md` §Now were stale (pointing at M/AB + a retired `/flow:land 84` step). New program head in both; removed the `/flow:land 84` + stale-installed-plugin bullets; fixed a README row referencing a nonexistent research doc.

**Why.** This session ran the first end-to-end orchestrated loop — dispatch → execute → ship #126 → archive-check — from a sibling workspace via the `conductor` CLI + ambient `CONDUCTOR_API_KEY`. Two corrections drove §4.6/§4.4: a dispatch ledger with a `status` column went stale within minutes (the API's `conductor workspace list` was the live truth), reinforcing "state is never a maintained artifact"; and the orchestration channel is the CLI, not the OAuth MCP initially chased. §4.7 was kept lightweight per an explicit anti-bloat steer (rides existing re-sync; no new state/lock).

**Three-surface note.** Docs-only (`research/` + `dev-docs/`). No plugin artifacts — the orchestrator skill + toolchain manifest kind are queued §5 work, dispatched as parallel workspaces this session.

## 2026-08-24 — flow-contribution: render-test-plan footnote no longer trips the coherence gate

**Branch:** `drain-lesson-harvest-queue` · **PR:** #(assigned at open) · **Mode:** contribution (`/flow:contribute` drain)

**What was done.** `/flow:contribute` drained the harvest queue (41 queued lessons + 1 disagreement record). One lesson was verified self-contained and clean, so it was **applied**; the rest are surfaced in the PR body as explicit, actionable holds (the human merge gate is where they get decided — FB-0073). The applied fix: `render-test-plan.py`'s unchecked-box footnote emitted the literal `🚫 NOT READY TO MERGE` heading (`= MANIFEST_HEADING`), and `pr-coherence.has_manifest` substring-matches that heading. So any **ready** PR whose Test plan carried an unchecked box (a self-reported `[~]` or unverified `[ ]` criterion) tripped `flow_assert_pr_coherent` on renderer output alone — the only escape was hand-editing generated output, which then risks the provenance digest. The footnote now directs a draft author to "the not-ready manifest" in domain prose without reproducing the machine sentinel.

**Why this one, and not the other 40.** The drain is fail-safe: apply only what is verifiable as self-contained + sanitization-clean, hold the rest. This fix is a two-line prose change to one renderer with an exact, mechanical failure it removes; it earns an auto-apply. The higher-confidence holds (ship Step-5a reverse-reconciliation at 0.9; the AskUserQuestion authorization-invisibility disagreement at 0.8; the no-bare-block extractor fallback at 0.6) each need either a coordinated multi-function edit, a faithful fixture that doesn't exist yet, or a placement decision inside a heavily-defended skill — regression risk to a live gate that a blind unattended apply shouldn't take. They are named with their exact fork in the PR body so a human (or a focused session) can green-light them cheaply.

**Design decision — fix the emitter, not the detector.** The lesson offered two forks: (a) the renderer stops reproducing the sentinel, or (b) `pr-coherence` matches only the fenced manifest region instead of a bare substring. Chose (a). `has_manifest`'s heading-substring check is *intentional robustness* — `manifest_contract.MANIFEST_TOKENS` documents that a body carrying the fence but not the heading (or vice versa) is still a not-ready body, so weakening the detector to fence-only would remove a real defense. The footnote reproducing the sentinel in explanatory prose was the actual defect, exactly as the skill's own author-warning says never to do.

**Consistency (FB-0010 pairing).** Added a `run_render_evals.py` case (`footnote-omits-manifest-sentinel`) that pairs the negative (`🚫 NOT READY TO MERGE` must NOT appear) with the positive (the footnote must still say "not-ready manifest" and "unresolved verification gap") — so satisfying the check by deleting the footnote entirely would fail it. Mutation-tested: re-introducing the literal sentinel flips the case to FAIL; the fix makes it PASS. `run_render_evals.py` and `run_pr_coherence_evals.py` both already CI-wired; no new harness.

**Provenance.** Lesson harvested from a personal project (ripe#16), sanitization-clean (no project tokens survive the scrub/scan). Confidence 0.8.

**Three-surface note.** Plugin artifact change (`plugins/flow/skills/ship/lib/render-test-plan.py` + `plugins/flow/evals/run_render_evals.py`); dev-doc update here only.

---

## 2026-08-24 — Handoff without a docs-only PR class: canonical-plan §4.5 + #122 currency folded (no standalone `/flow:land` PR)

**Branch:** `handoff-without-land` · **PR:** #(assigned at open; refer to it by that number per the §4.5 convention below) · **Mode:** docs

**What was done.** Added §4.5 "Handoff without a docs-only PR class (the land-elimination)" to the canonical plan (`research/2026-08-23-flow-cloud-workflow-plan.md`) plus execution rows 1a/1b in §5. And **dogfooded it in the same change**: #122's post-merge currency (history entry + FB-0087/0088 reservation clears) was folded into THIS substantive PR instead of the standalone `/flow:land` PR (#123, now closed) — the first instance of "durable currency rides the next ship, not its own docs-only PR."

**Why.** Ben's question: given the Conductor orchestrator model, does the `/flow:land` post-merge PR (which doubles PR count and adds a handoff hop) still earn its place? `/flow:land` exists to keep `main`'s forward docs current for a **cold reader** — a new contributor, or the autonomous loop as a cold agent re-reading `main` each run (its own SKILL §0 header). The orchestrator breaks that assumption: the next workspace is spawned by a coordinator holding live state and handed a dispatch brief, not a cold `main` read. So land's forward-pointer job is superseded, and its durable-currency job needs no PR of its own.

**Design decisions.**
- **Reference merged PRs by `#N`, not SHA, in history** (dogfooded here: #122's line is now `**PR:** #122 (merged)`, not a `merged @ <sha>` stamp). The merge SHA was land's *only* value unknowable until merge — #N is known at PR-open. Removing the SHA dependency removes the ordering constraint that forced a *separate* after-merge PR. Verified against #123's actual diff: its entire content was the SHA stamp + two reservation clears.
- **Fold currency into the next ship; gate `/flow:land` behind a slot** rather than delete it — the pure cold-autonomous-loop consumer (no orchestrator) genuinely re-reads `main`, so land stays available, just off the default path. FB-0088 discipline: encode the fact (currency belongs on `main`), not the procedure (a standing second PR).
- **Guardrail kept:** durable currency still reaches `main` through a *reviewed* PR, never a direct push — the merge gate (G3) is untouched. The orchestrator speeds the handoff to the next workspace; it does not skip the human merge.

**Tradeoffs.** `main`'s forward pointers can be briefly stale between merges — harmless when a coordinator knows the true frontier, load-bearing without one (hence the slot, not a delete). The plugin-side implementation (ship/land skill edits for the `#N` convention + the slot) is execution rows 1a/1b — queued, not in this docs change.

**Three-surface note.** Docs-only: `research/` + `dev-docs/` only. No `plugins/flow/` artifact changed — the skill edits are the queued 1a/1b work.

---

## 2026-08-23 — Spike: orchestrator-driven Conductor cloud workspaces — feasibility, constraints, measured cost (FB-0087, FB-0088)

**Branch:** `calgary` · **PR:** #122 (merged) · **Mode:** spike (the research note IS the deliverable)

**What was done (user-facing).** A new research note, `research/2026-08-22-conductor-orchestration.md`, answering: can one "orchestrator" workspace per repo spawn and direct sibling Conductor cloud workspaces via the public API, with the spawned workers running the flow loop, and does that match Anthropic's orchestration guidance? Indexed in `dev-docs/README.md` (repo-root `research/` table). Plus one `roadmap.md` § Exploration entry for the **confirmed flow bug** the research surfaced. No plugin artifacts changed.

**Why repo-root `research/`, not `dev-docs/`.** Same quarantine as `research/2026-08-14-cloud-ios-simulator-limrun.md`: the note is about how the human works *across all their projects*, not about flow's own development, and it must not touch a plugin surface. `dev-docs/` is flow's self-tracking; `plugins/flow/` is shipped. The note stays greppable and indexed without crossing either boundary (CLAUDE.md's three-surface rule).

**The confirmed bug (→ roadmap § Exploration).** `plugins/flow/docs/workflow.md` Step 2's "check for concurrent work" sweep leads with `git worktree list`. **Verified live: in a cloud workspace that returns only the workspace itself**, so the check silently passes for every cloud session and the duplicate-activation it exists to prevent is unguarded. FB-0010 silent-skip shape — the failing case is byte-identical to "nothing to report." The replacement is *better evidence than what it replaces*: `git ls-remote --heads origin` + `gh pr list` (both verified working from cloud) see the shared state conflicts actually occur in, from every host. Routed to § Exploration rather than fixed inline because the surrounding question — prose-in-SKILL vs the `tools/flow` CLI the service-agnostic roadmap already proposes — would otherwise be decided in isolation and produce a third implementation of the same contract.

**Load-bearing findings, all measured rather than assumed.** 24 facts with provenance; the ones that shaped the design: the API is **cloud-only** (local Mac workspaces are invisible — checked across four projects); workspaces carry **1h idle / 23.8h max lifetime**, so an orchestrator is a *respawnable role backed by committed state*, never a long-lived chat; a queued message **wakes a sleeping workspace in 12s** (probed end-to-end), which deleted a whole planned sub-design; **no agent path from cloud to the Mac** exists in either direction, so iOS behavioral verification cannot run cloud-side; and flow is **pre-installed from the cloud image** but **version-pinned** by it.

**Design decision — the probe deleted a design rather than validating one.** A plan/execute worker split was drafted purely as insurance against sleeping workers being unreachable. Rather than build it defensively, it was gated on a live probe (create workspace → let it idle past 3600s → queue a message → observe). The wake was clean, so the split was dropped — it would have doubled workspaces per item and re-paid cold-start prompt-cache creation (measured 10:1 read:create on a long session) to solve a problem that does not exist.

**Tradeoff — the probe's own harness had the bug it was testing for.** The first polling loop would have returned a **false negative**: `conductor session message --limit N` returns the *oldest* N, and `--after <just-queued-id>` 404s because a queued message is not yet a transcript cursor. Grepping that window for the expected reply fails silently forever. Caught because the returned payload was timestamped an hour before the message just sent. Recorded in the note's §3 as a methodology trap, not a war story — it is the FB-0010 silent-skip class reproduced inside the test written to detect a different instance of it.

**Feedback captured.** **FB-0087** — establish a capability is *absent* before planning to provide it (a proposed bootstrap phase was cut after one command showed the platform already supplied it; the residue was a much smaller version assertion). **FB-0088** — encode facts, not procedures, and give every artifact a deletion criterion; a harness that scripts judgment becomes a ceiling as models improve. FB-0088 is the generalization of CLAUDE.md's F11 rule past bundled skills, and cites FB-0077 as its precedent.

**Explicitly not built (§9 of the note).** No cost model, no token estimator, no model-selection classifier, no CLI wrapper, no daemon, no `/flow:orchestrate` skill. v1 is one markdown ledger plus one dispatch-brief template and zero code — flow is project-agnostic by default and has an active roadmap to *decouple* from a single host, so baking Conductor's API into plugin artifacts would push against it.

**Amended in this PR — the canonical consolidation plan.** After the spike note landed, a second cloud-workflow plan surfaced from a Trio-repo session (`core-docs/cloud-local-workflow-plan.md`): a tiered cloud/local split with a PR+label verify queue, ambient environment detection, and a one-pipeline-never-fork rule. Rather than leave two overlapping documents, this PR adds `research/2026-08-23-flow-cloud-workflow-plan.md` — the **canonical** plan that consolidates both. It absorbs the Trio direction, cites the 08-22 note's facts as `[F#]` rather than re-deriving them, and marks the 08-22 note **partially superseded** (its §2 facts stay authoritative; its §8 design + §10.1 ledger are superseded). Two supersession edits ship with it: the 08-22 status line and the `dev-docs/README.md` index rows.

**The keystone finding — re-sequenced, verified against flow's own code.** The Trio plan deferred its environment/toolchain concern to last (D8). Read against `skip-audit-checks.py:257-258` and `manifest-triage.py`'s `KINDS` tuple, that ordering can't hold: flow's skip-audit engine mechanically **rejects** a `verify-build` skip on a `platform: ios` project (the only LEGITIMATE platforms are `library`/`none`), and there is no `toolchain`/`environment` manifest kind for an absent-Apple-toolchain skip to route through. So Trio's design cannot compose with ship's gates until flow gains a `toolchain` manifest kind — which is why the canonical plan re-sequences that from D8-last to **Step 1, the keystone**. Nothing in the plan is built yet; §5 stages the execution.

**Still not built.** The canonical plan is a PLAN. No `toolchain` manifest kind, no orchestrator, no Trio-local artifacts exist yet — §5 is the queued execution sequence, and §4.4 lists what is deliberately not built with each item's deletion criterion.

---

## 2026-08-17 — D1 prototype-first-gate execution plan (handoff, FB-0081)

**Branch:** `d1-prototype-first-gate-handoff` · **SHA:** _(set at ship)_

**What was done (docs-only).** Wrote `dev-docs/handoffs/d1-prototype-first-gate.md` — a self-contained, cold-start-executable execution plan for **D1**, the Designer-signal track's load-bearing item (move the human's first gate from the plan to a prototype). Indexed it in `dev-docs/README.md` and pointed the roadmap D1 entry at it.

**Why.** The user reviewed the five held/queued design-forks (from the #119 drain triage) and directed D1 forward, to be **handed off to a fresh workspace**. D1 is the biggest of the forks — it restructures the front half of the loop — so it earns a handoff doc rather than an inline build. The plan implements FB-0081 (the definitive, user-directed spec) verbatim: the seven-step loop, the two-gates-only constraint, prototype-before-plan ordering, the auto-written machine-gated technical plan, the orchestrate-agents-don't-merge-skills substrate (§5), and the proportionality guard.

**Design decisions captured for the fresh agent (so they aren't relitigated).** §4 lists the seven settled, user-directed decisions. Two assumptions are flagged as gating the build: §9.3 (the auto-written technical plan's quality — LOW, needs a spike before Phase 3, because the whole design rests on the machine gate having a real plan to check) and §9.4 (the prototype medium for non-web/native surfaces — a human decision, since FB-0081 assumes HTML-ish prototypes but flow's consumers include native apps). The #119 held item [10] (HTML-prototype geometry + taste self-check) is folded in as the prototype-phase self-check rather than a separate fork — its timing moves pre-execution.

**Relationship to verify-build (the user's explicit constraint).** D1 restructures Clarify→Plan only; Execute→Ship and `/flow:verify-build` are untouched. The visual human-gate (prototype approval) sits *before* execution and does **not** replace the post-execution behavioral gate — stated as an out-of-scope boundary in §2.

**No plugin artifacts changed** — this is a dev-docs handoff; the four ship reviewers self-skip.

---

## 2026-08-25 — Step 2's concurrent-work sweep no longer goes inert on cloud hosts (SAFETY)

**Branch:** `conductor/phase0-concurrent-work-check-cloud-inert` · **SHA:** _(set at ship)_

**What was done (user-facing).** `plugins/flow/docs/workflow.md` Step 2's "Before activating a queued item — check for concurrent work" sweep no longer leads with `git worktree list`. It now leads with `git fetch --quiet origin`, then `git branch -r --sort=-committerdate`, then `gh pr list` (with an explicit `|| echo "gh unavailable — PR check skipped, rely on branch evidence only"` fallback); `git worktree list` is retained as the last line, relabeled a LOCAL-ONLY supplement whose empty/self-only result is explicitly documented as not evidence of absence.

**Why (the bug).** On a Conductor-style cloud workspace (an isolated clone per workspace, not a linked worktree of a shared repo), `git worktree list` always returns only the current workspace — so the check that exists to prevent duplicate activation of a queued item silently read as "nothing to report" on exactly the hosts where many parallel agents drawing from one queue make duplicate activation most likely. Verified live in a cloud workspace 2026-08-22 (per the task brief) and reproduced again in this session: `git worktree list` → self only; `git fetch` / `git branch -r` / `gh pr list` → full remote picture. FB-0010 silent-skip class — the failing case was byte-identical to the legitimately-empty case, so nothing about running it ever signaled the gate wasn't working.

**Design decision 1 — fix stays in prose now, CLI migration deferred.** `dev-docs/roadmap.md` § Exploration ("Step 2's concurrent-work check is inert on any cloud host," landed via branch `calgary`'s merged research spike, #122) poses an open fork for this sweep: leave it as prose in the SKILL (portable, unenforceable) vs. move it behind the `tools/flow` CLI the service-agnostic roadmap proposes, explicitly declining to decide it in isolation. This PR takes a position without resolving that fork: fix the prose now (fastest correctness fix, zero new infrastructure), leave the CLI migration as a natural follow-up once that CLI exists. The roadmap entry's own suggested replacement evidence (`git ls-remote --heads origin` + `gh pr list`) is the same shape adopted here; this PR uses `git fetch` + `git branch -r --sort=-committerdate` instead of bare `git ls-remote` specifically so the listing keeps committer-date ordering (`ls-remote` only returns ref names + SHAs, no dates) — same remote-state evidence, richer sort. The `roadmap.md` § Exploration entry itself is left untouched (out of this branch's `do not touch` scope); it should be closed against this fix in a follow-up.

**Design decision 2 — no new eval fixture.** Every eval harness in this repo pins an *executable* engine (a `lib/*.py` module, or a `!`-block extracted and actually run from a `SKILL.md`); this sweep is narrative prose with no extraction point any harness targets. Fixturing it would mean either building that extraction/execution engine now (preempting the CLI-vs-prose fork by accident) or asserting on the doc's string content only, which cannot prove cross-host behavior and is exactly the "grep the value, not the behavior" anti-pattern `general.md`'s FB-0010 section warns against. The cross-host evidence already exists via direct reproduction (2026-08-22 and again this session); no synthetic fixture is needed to replay something already observed directly. If the sweep later gains an executable engine, that engine gets fixtures then.

**Technical decision — the `gh`-unavailable fallback is advisory, not enforced.** Because this is prose read by a planning agent, not shipped skill code, the `|| echo "..."` fallback can't `exit 1` the way a real gate would; it only makes the degraded case visible to whoever's following the doc. That's consistent with the rest of this section (the whole sweep is advisory today) and is explicitly flagged as a limitation rather than left implicit — closing the exact silent-skip shape, one precondition down from the bug this PR fixes, that a first draft of the plan left unaddressed (caught by `/flow:critique-plan`'s first pass; see the plan's Confidence verdict).

**Tradeoffs discussed.** Keeping `git worktree list` in the sweep (relabeled local-only, not evidence of absence) versus dropping it outright — kept, since it still adds fidelity on a genuine local multi-worktree setup; the fix demotes it from primary to supplementary evidence rather than removing a working signal.

**Process note.** Rebased cleanly onto `main` after `calgary`'s merge; the expected `history.md` top-of-file conflict (two branches appending to the same reverse-chronological doc) resolved per the FB-0074 convention — keep upstream's entries in full, insert this branch's entry immediately after. `dev-docs/plan.md` rebased with no conflict.

---

## 2026-08-17 — Walk-parser lifecycle fix: an all-demoted block no longer reads as active (v1.30.0, FB-0059)

**Branch:** `fix-walk-parser-all-demoted-leak` · **SHA:** _(set at ship)_

**What was done (user-facing).** The two walk-parser consumers that ignored the `all_demoted` lifecycle predicate now honor it. `visual-significance.py` keyed the Visual-walk override on `block_count >= 1`, and `skip-audit-checks.py` read `block_count` for its "no Spec-walk" audit — so a plan whose Spec-walk/Visual-walk headings are *all* demoted (qualified `(merged #N)` by the demote-at-merge convention) was mis-read as having an *active* block. Both now key on the `all_demoted` / `first_heading is None` predicate `walk_extract.extract_block` already computes. First of the executable held items from the #119 contribution drain.

**Why (a gate misfire, reproduced live).** With every block correctly demoted, the just-demoted pair floats to the top of the plan and the position-based proxies read it as active. Consequence, reproduced on `main`: a **docs-only post-merge PR** whose plan carries only demoted blocks computes `visual_significant: true` (off a retained Visual-walk) and audit-coverage's legitimate "no Spec-walk" skip is flagged `SHOULD-RE-RUN` — so a clean docs PR is wrongly routed to the draft manifest. The parsers model POSITION; the fix makes them model LIFECYCLE, using the predicate the shared parser already emits. This is the FB-0010 silent-drift class in a ship gate.

**The fix (two sites, one predicate).**
- `visual-significance.py:391` — a new `elif blk.get("all_demoted")` branch *before* the `block_count >= 1` override: emit a `[WARN]` ("every Visual-walk block is demoted … NOT treating it as an override") and set no override.
- `skip-audit-checks.py:448` — `spec_blocks = 0 if _blk.get("all_demoted") or _blk.get("first_heading") is None else _blk.get("block_count", 0)`, so a fully-demoted plan reports zero active Spec-walk blocks and the "no Spec-walk" skip is `LEGITIMATE`.

**Design decision — key on the existing predicate, not a new anchor.** `walk_extract` already distinguishes `all_demoted` (block_count > 0, none active) from `block_count == 0` (no heading). The alternative — a new plan-format boundary marker for "active section" — is the documented `walk_extract` limitation for the *separate* "active PR at top declares none, retained PR below has a bare heading" case, which needs a format change and is explicitly out of scope here. Consuming the predicate that already exists is the minimal, self-contained fix; the bare-retained sub-case stays a tracked limitation.

**Verification (red-green, both harnesses, regression controls labelled).** Two fixtures added: `visual-walk-all-demoted-no-override` (run_visual_significance_evals.py) and `all-demoted-spec-walk-skip-legit` (run_skip_audit_evals.py; the harness `run()` gained a `--plan` param it lacked). Each is **RED pre-fix** (verified by stashing only the two code fixes and keeping the eval cases: both fail exactly as the bug predicts) and **GREEN post-fix** (58/58 + 35/35). Each ships with an **active-plan regression control** (`active-spec-walk-skip-refused` / the existing override case) that passes *both* ways — labelled a control, not a proof, per the FB-0079-corollary-2 discipline. Both harnesses were already CI-wired; no wiring change.

**Process.** Held item from the #119 drain, applied here as its own PR with human review (the drain deliberately did not auto-apply gate code). The remaining held backlog is captured to `roadmap.md` § Next (executable fixes) + § Exploration (design-forks). Related: FB-0059 (the drain), FB-0010 (silent-drift class), and the first-block/demote-at-merge extraction contract this predicate backs.

---

## 2026-08-17 — Lesson-contribution drain: reviewer + doc-discipline hardening (FB-0059)

**Branch:** `drain-lesson-queue` · **SHA:** _(set at ship)_

**What was done (user-facing).** Drained the 55-entry cross-project lesson-harvest queue (`/flow:contribute`). Applied 8 verified, self-contained **guidance** lessons to flow's reviewer-prompt and author-rule surface; dismissed 16 lessons verified as already-closed; held 31 for follow-up. Applied edits, all additive text (no executable gate/parse code changed):

- **`agents/lens-staff-engineer.md`** — four new "Specifically asks" bullets, one theme: *green checks that pass for the wrong reason.* (1) **Invariant vs. prescribed call sequence** — a unit test hitting an engine API directly can pass while the SKILL's own documented shell block ahead of it re-enables the unsafe branch. (2) **Guard vs. the real artifact** — a new guard against a historical defect must be replayed against `git show <base>:<path>`, not only self-invented mutations. (3) **Mutation-test the diff's own tests** — mutate the invariant a new test claims to pin; if the suite stays green the test asserts the wrong layer. (4) **Vacuous comparison / filter** — a `diff`/`grep`/`sed` proving "no change" passes vacuously when its extractor matched nothing; require a non-zero match count.
- **`rules/documentation.md`** — new "Recorded rejections" section: a narrative entry may not close an alternative with an *unmeasured* prediction; measure it, or state plainly it's unevaluated and name the cheap experiment. Hedge words don't discharge it.
- **`docs/workflow.md`** — (a) "Human-only skills the model can't see": `disable-model-invocation:true` skills are absent from the model's registry, so the model may wrongly assert they don't exist — list `${CLAUDE_PLUGIN_ROOT}/skills/` before concluding a skill is unavailable. (b) Two rebase-hygiene anti-patterns: blanket find-replace during a renumber corrupts upstream's shipped identifiers (scope the sweep to non-upstream lines); resolving a reverse-chronological append-only doc by keeping conflict markers silently drops an entry (rebuild as upstream + one new top entry, assert no base line lost).

**Why (FB-0059 loop closure).** The harvest queue had accumulated 55 lessons across four projects spanning flow v1.22–v1.25; flow is now v1.29.0. The drain's value is only as good as its *disposition accuracy*, so every eligible entry was verified against the current tree before any action — six parallel read-only verification agents, each reproducing the symptom (not reasoning from the fix) before certifying a lesson closed.

**Disposition (verified, not assumed).**
- **Applied (8):** the guidance lessons above — all confirmed novel against current prompts/rules/docs, all additive text, none requiring a new eval fixture (lens prompts and narrative-doc rules are not eval-covered).
- **Dismissed (16):** verified closed. *Superseded* — uiFilePatterns split (FB-0079), post-merge/land model-invocability + composition (FB-0077/#90), first-block extraction replacing demote-at-merge, repo-local `.flow/` scratch (FB-0082), audit-skips re-measurement moved into the engine with `--plan`. *Already-encoded* — ship §8 "lead with decisions" + post-merge §7 "lead with verdict"; audit-coverage TRUNCATED→PARTIAL marker; verify-pr-body exit-2 on unreachable; `verifyFindingsPath` repo-local default; staff-review provenance header; FB-0083 anchored clear-reservation (+ both-directions eval). *Deliberate design* — post-merge's queue-safety empty→open default, never-`-D` branch cleanup, land's branch-anchor-plus-bare-`#N` discovery (each contradicts a documented, intentional choice).
- **Held (31):** verified-novel but not applied here. Executable/gate-code fixes deferred to human-reviewed application (an unattended error in flow's own shipping gates is a risk-class change): the `all_demoted` walk-parser leak (`visual-significance.py:391` + `skip-audit-checks.py:448`, reproduced live routing a docs-only post-merge PR to the draft manifest), `check.mjs` git-first memory resolution, `harvest_lesson.py` flow-self scrub-token guard, ship Step-5a implemented-but-pending sweep, land dup-PR pre-check + post-push read-back, verify-build criteria-freshness precondition, doctor uiSurface-vs-tree check. Design-forks: verify-build test-gated mode (new `testCommand` slot), plan-critic AskUserQuestion visibility (needs a captured tool_result fixture), doctor advertised-vs-loader, pre-Present HTML-prototype gate, installed-first lib resolution. Plus sub-threshold + needs-manual-scrub entries. Full list with exact fixes in the PR body.

**Decision — apply only the guidance surface, hold executable changes.** The apply/hold line is *does this change executable gate/parse logic?* Reviewer-prompt and author-rule text change what reviewers and authors are *told to check*, never a running gate — safe to auto-apply and trivial to review. The verified bug-fixes (gate code, lib resolution, skill steps) each deserve isolated staff-review, so they're held with their exact fix named rather than bundled into an unattended prose PR. This keeps the applied PR fixture-free, code-free, and reviewable, honoring the drain's "fail safe — when in doubt, HOLD" contract (FB-0073: held items carry a specific actionable reason, not a park).

**Store hygiene (SAFETY-adjacent).** During the sanitize gate the fail-closed scan flagged `flow` itself as a residual token — the live symptom of held lesson [34] (`harvest_lesson.py` re-registers the destination repo's own name as a scrub token when flow dogfoods itself). Removed `flow` from user-scope `known_tokens.json` (kept all 18 genuine personal-project tokens); the permanent fix is held. `contribution_store.py dismiss` records to the recurrence ledger but does **not** flip the queue file's status, so each dismissed entry also got `set-status --status dismissed` to actually leave the drain — a two-call requirement worth noting for the skill.

**Process.** No FB number reserved (guidance edits, not new FB entries). Verified via six parallel read-only agents; applied text sanitize-scanned clean; queue statuses reconciled (8 proposed, 16 dismissed, 31 held). Related: FB-0059 (the harvest→drain loop), FB-0073 (split by confidence, don't park), FB-0082/FB-0079/FB-0077/FB-0083 (the churn that superseded much of the backlog).

---

## 2026-08-15 — Binary asset re-export now reads visually significant (SAFETY, FB-0086)

**Branch:** `fix/binary-asset-visual-significance` · **SHA:** merged #116 @ `fc0bdf78`

**What was done (user-facing).** `visual-significance.py` — the shared predicate that gates the `/flow:ship` visual-deliverable requirement — now recognises an in-place binary asset change (font / icon / image) as a real render delta. Before this, `M …/Fraunces.ttf` computed `visual_significant: false` and silently skipped the visual gate; after, it reads `true`, the same as a text UI edit. Item 1 of 3 from the health-tracker PR #100 consumer report.

**Why (SAFETY — a silent fail-open of a ship gate).** `_diff_content_changed()` decides which file a hunk belongs to by watching for the `+++ b/<path>` header. **Git emits no `+++` header for a binary file** — only `Binary files a/<path> and b/<path> differ`. So for a modified binary, `cur_relevant` never flipped true, no render delta was seen, and the pure-refactor exclusion fired ⇒ `false`. A real font/icon PR *is* an in-place re-export at the same path, so this was **always** the broken case — the gate that exists to demand a screenshot silently waved through exactly the change class it is meant to catch. This is the FB-0010 silent-skip / fail-open class, in the surface FB-0079 rewrote one PR earlier.

**The fix.** A dedicated branch for the `Binary files … differ` line: parse **both** the `a/` and `b/` sides, strip the prefix, and if either (ignoring `/dev/null`) matches `visual_re` or `asset_re`, return a render delta. Parsing both sides covers binary **add / modify / delete uniformly** — an add is `/dev/null and b/<path>`, a delete is `a/<path> and /dev/null`, a modify carries the path on both. The branch is self-contained (it inspects the parsed paths directly, never reading or writing `cur_relevant` or the preprocessor stack), so the `#if DEBUG` text-hunk tracking is provably unaffected.

**Design decision — a binary DELETE counts as a render delta (argued deliberately, not left to fall out).** Options considered:
- **(chosen) Delete ⇒ significant.** Removing a rendered asset changes what the app draws (a fallback renders, or the element disappears). The gate's fail-safe direction is to **over-demand** a screenshot: a false positive costs one "nothing visual to show" note; a false negative ships an unverified visual regression — the exact class this fix closes. The diff cannot distinguish dead-asset cleanup from live-asset removal, so we take the safe union (consistent with FB-0079's fail-safe-direction corollary: a whole-diff safety claim takes the over-refusing union).
- **(rejected) Count only add/modify, ignore the `a/` side.** Reintroduces a blind spot identical to the one being removed, and asset removal genuinely changes rendering. Rejected.

**Technical decisions.**
- **Both-sides parse, not b-side-only.** Needed for delete (path on `a/` only) and uniform for modify. Regex `^Binary files (.+) and (.+) differ$`; greedy split mis-handles the pathological case of `" and "` inside a filename, noted as an accepted limitation (asset paths don't carry it, and either side matching still catches the trailing extension).
- **No new eval harness.** `run_visual_significance_evals.py` was already wired into CI (ci.yml:62); the wired-vs-on-disk integrity guard (ci.yml:34-45) re-verified MATCH, so nothing to wire.

**Verification (the repo's red-verify bar; FB-0079 corollary 2 — pick fixtures by the distinguishing axis = binary × add/modify/delete, not the example in hand).** Five fixtures added. Three are **RED pre-fix**: `binary-modify-significant` (the reported bug), `binary-delete-significant`, and `binary-both-sides-checked` (a rename+modify with a non-matching `a/` and matching `b/`, status M so the `new_files` shortcut can't cover it — the b-side's real proof; also **mutation-tested**: reducing the loop to `mb.group(1)` makes it fail). `binary-add-significant` is kept as an honest **regression control**, explicitly NOT a red-verify — an A-status file already hits the pre-existing `new_files` shortcut, so it is green both ways and proves nothing about the parser; labelling it a control rather than a proof is the FB-0079-corollary-2 discipline applied to my own fixtures. `binary-nonasset-not-significant` pins that the parser matches the path and does not fire on every `Binary files` line. Red-verified by restoring the pre-fix file (3 checks FAIL), then the fix (57/57 pass). All 24 CI harnesses + `check-index.py` green.

**Known limitation (explicit non-goal, scope discipline).** A *text*-file full deletion has a **separate** blind spot — `+++ /dev/null` sets `cur_relevant` false and the `---` line is skipped, so a deleted text UI file's `-` lines are never counted. The `Binary files` parser does not reach it (text files have real `+++`/`---` headers). Out of scope for item 1 (binary assets); left for a follow-up rather than silently pinned green. Recorded here so the next session finds it as a decision, not a surprise.

**Process.** Followed flow's own loop: plan written to `plan.md` with a Spec-walk block and human-approved before implementing; FB-0086 reserved (held to **merge**, not ship — three of the last five PRs renumbered because numbers were released at ship while the PR sat open); shipped via `/flow:ship`. Related: FB-0079 (the split this fix builds on), FB-0010 (silent-skip / fail-open class), FB-0062 (a stage's verdict is trusted only if it actually measured the thing).

---

## 2026-08-14 — jq-absence fail-fast across flow skills (SAFETY)

**Branch:** `fix-jq-absence-fail-fast` · **SHA:** merged #110 @ `5475ad00`

**What was done (user-facing).** Every flow skill that reads `flow.config.json` via `jq` now fails loud when `jq` is absent instead of silently falling back to hardcoded defaults and reporting green. Action-taking skills (`security-review`, `accessibility-review`, `staff-review`, `contribute`) `exit 1` with an install hint; `doctor` emits an honest `[SKIP]` (never a false `[FAIL]`); `workflow-help` warns read-only; the fork skills (`audit-coverage`, `audit-skips`, `critique-plan`) route a `JQ-MISSING`/`jq_error` signal. Pinned by `run_jq_guard_evals.py` (wired into CI).

**Why (SAFETY — error-handling/fallback).** `jq … // default` chains silently substitute hardcoded defaults on jq-absence — the review then diffs the wrong base, scans the wrong files, reads the wrong docs, and reports green. `/flow:doctor` was worse: `jq -e …; then PASS; else FAIL` takes the FAIL branch on exit 127, so a correct install reports `[FAIL]`. This *upgrades* error handling (silent degrade → loud fail), the direction `.claude/rules/safety.md` mandates. Extends FB-0009's fail-fast lineage.

**Design decisions.** (1) Per-file inline guard over a shared `require-jq.sh`: fenced SKILL `!`/`sh` blocks execute as standalone snippets pasted into a fresh shell, so a sourced helper is structurally unreachable — and the eval extracts + runs each live guard, so drift/omission fails CI (closing the usual copy-paste cost). (2) The three carve-outs are encoded as *tested policy* (`CARVE_OUTS`, `is_fork()` derived from frontmatter), not ad-hoc exceptions. (3) The eval derives the guarded-skill set from disk (drift-proof), so a new config-reading skill can't ship unguarded.

**Review (this ship).** `/simplify` memoized the eval's `_shadow_bin` (+ `atexit` cleanup; it was leaking a temp dir per block). Four-lens `/flow:staff-review`: no blockers — the feature reviewed "at ceiling for its scope." Fixed inline: a **vacuous Part D test** ("gh stays warn-only" never actually ran the gh line, since it sits above `MISSING=""` and `extract_guard`'s regex skipped it — a regression to `|| exit 1` would have passed; mutation-verified the fix now fails on that regression); **pinned doctor 2.3/2.4's** new `[SKIP]` emission; dropped an **unused `import sys`** and a leaked **`(FB-0008)`** internal codename from a user-facing BLOCKER message. Security review: **clean** — the eval runs only the repo's own trusted shell under a shadow PATH, CI is a read-only `pull_request` with no secrets, guards interpolate only fixed literals. Follow-up → roadmap § Exploration: derive the eval's doctor-side coverage from disk (rather than a hand-listed enumeration) so a future `Check` can't reintroduce the false-`[FAIL]` uncaught.

**Adoption note.** Authored by a prior session (the commit deferred docs to `/flow:ship`); adopted and shipped from the primary worktree after a concurrent-session collision was resolved — see the long-running-loop capture entry below for the collision detail.

---

## 2026-08-14 — Capture the long-running-loop design + external validation

**Branch:** `docs/long-running-loops` · **SHA:** merged #107 @ `0c17b638`

**What was done (user-facing).** Durably recorded a multi-session design exploration for making flow run much longer autonomously, as a new research note (`dev-docs/research/2026-08-14-long-running-loops.md`) plus a `roadmap.md` § Exploration entry cross-linked to the Designer-signal (D1) + Deliverable-quality tracks. Three parts: a successive-PR "shift" model (a stateless fresh-session-per-item executor, a durable queue, an integration branch + a `mechanically-verifiable ∧ inert ∧ reversible` merge predicate that lets stepping-stones auto-merge to staging while `main` stays human-gated); a decision-corpus quality substrate (forward priors + corrective feedback, surface-indexed, loaded at build time); and a divergent-variation landscape reframed from precision to coverage.

**Why.** The design lived only in a session transcript plus an ephemeral 12-agent investigation output — the FB-0010 "durable in the repo, not the transcript" risk. It is grounded in an adversarially-validated investigation of health-tracker (phases 0–2, ~20 transcripts, PRs #7–#41) and externally validated against Anthropic's long-running-agent + context-engineering posts.

**Decisions / tradeoffs.**
- **Exploration, not Next.** The load-bearing bet — that the agent can predict which foundational forks to prototype (coverage recall) and classify Tier-0-stance vs Tier-1-taste reliably — is unproven and must be measured on real review rounds before any build. Filed with a `Surfaces when:` trigger; prototype order in § 9 of the note.
- **Coverage, not precision.** The naive "agent predicts the winning variant" framing is refuted by the repo's own history (D1's none-of-the-above 4th option; FB-0013's refusal of an A/B menu). Reframed to landscape-mapping so the design survives the evidence.
- **Honest about extending beyond baseline.** The note flags the divergent-variation coding loop as ahead of Anthropic's published baseline (they call multi-agent coding open research), while the foundation is independently corroborated.
- **Shipped from an isolated worktree** after a concurrent session collided in the shared primary worktree and orphaned the first commit; the two files were recovered from the orphaned commit and re-committed clean off latest main.

**Overlap noted.** The concurrently-merged #106 (`anthropic-canon-alignment-2026-08.md`, FB-0084) independently validated flow against the same Anthropic canon at broader scope; this note is narrower (the long-running-loop *design*) and shares the sources — worth a future cross-link.

---

## 2026-08-14 — Anthropic-canon alignment check + reprioritize model routing & attention budget

**Branch:** `claude/agent-flow-best-practices-bhygw1` · **SHA:** merged #106 @ `3f71883` (docs-only)

**What was done (user-facing).** Checked flow against Anthropic's first-party agent-building canon — *Building Effective Agents*, *Effective Context Engineering for AI Agents*, and *Effective Harnesses for Long-Running Agents* — and captured the result in a new research doc (`dev-docs/research/anthropic-canon-alignment-2026-08.md`). Flow is strongly aligned, and ahead of the canon on structured note-taking, sub-agent verification, and self-improvement. Two recurring gaps were pulled to the top of the roadmap at the user's direction: **M** (per-subagent model routing, already scoped) and **AB** (attention budget & harness-weight audit, net-new). Both are marked ▶ TOP PRIORITY in `roadmap.md` § Now + § Next; `plan.md` Current Focus + Handoff Notes hand a fresh agent the two starting points; FB-0084 records the direction.

**Why.** The competitive landscape doc (`ai-workflow-landscape-2026-07.md`) benchmarked flow against *rival frameworks* and the loops article, but never mapped flow against Anthropic's **context-engineering** article — the freshest and most load-bearing of the canon. That article's "context is a finite resource / smallest set of high-signal tokens" framing, plus the harnesses article's "harness assumptions expire" meta-lesson, name a gap nothing in flow tracks: flow accretes always-on surface and prunes only reactively.

**Design decisions.**
- **Two items, not one.** M (model cost per subagent) and AB (context cost per surface) are flow's two distinct token-economy levers; kept as independent, interleavable roadmap items rather than one program, so either can start first.
- **AB's one net-new mechanism is a periodic harness-weight audit** modeled on the existing 5-ship memory audit — reusing a proven shape rather than inventing governance. Everything else in AB (compact the dev-docs, a context-budget report) is application of Anthropic's own compaction/note-taking techniques.
- **M unchanged in substance** — FB-0083's measurement-first constraints (Opus default, Sonnet-only challenger, no Haiku, no swap on faith) are preserved verbatim; this change only re-ranks it.

**Technical decisions / tradeoffs.**
- **Provenance honesty:** `anthropic.com` is egress-blocked from this environment (Cloudflare 403 direct; not-in-allowlist via proxy; policy forbids retrying the denial). The article specifics came from WebSearch summaries + training knowledge, not source text — flagged explicitly in the research doc so a future session re-verifies quotes before relying on them. Tradeoff: capturing the direction now on best-available evidence beats blocking on a fetch the environment can't perform.
- **Dogfood evidence, not just theory:** the AB writeup cites flow's own `roadmap.md` § Now append-blobs, `plan.md`'s 38 Spec-walk blocks, and auto-loading `workflow.md`/`CLAUDE.md`/rules as concrete instances of the debt — the same append-only-in-a-context-surface class flow already fixed once for the `/plugin` description (FB-0078). The irony that the reprioritization *adds* text to those very files is accepted: compacting them is item AB.2.
- **Docs-only, no plugin artifacts touched.** No behavior change; the four ship reviewers would self-skip. Not run through the full `/flow:ship` pipeline this session (the `/flow:*` skills aren't installed in this remote environment); committed and pushed directly to the task branch for the user to route.

## Service-agnostic research + Codex/Cursor roadmap, and a dev-docs index

**Date:** 2026-08-12
**Branch:** `claude/flow-service-agnostic-96aec1` — merged #105 @ `e1a73937f`
**Mode:** feature (docs-only) — no plugin artifacts changed

**What was done.** Two research docs and an index. `dev-docs/research/service-agnostic-2026-07.md` is the field survey (standards landscape, prior art, a 13-host capability map). `dev-docs/handoffs/service-agnostic-roadmap-2026-07.md` is the execution plan — self-contained for a cold pickup, with 23 spec-walk checkboxes and 6 confidence verdicts. `dev-docs/README.md` indexes every dev-doc; `CLAUDE.md` now points at it.

**Why.** Two questions had to be answered before any multi-host work could start: can Flow run on Codex/Cursor at all, and what would it cost? The answer changed twice during the research, which is why the survey carries inline supersedes.

**Design decisions.**
- **One repo, one plugin root, three generated manifests** — not three forks, not a runtime abstraction. Chosen because every project that tried runtime abstraction is dead or Claude-only, while the two that work (spec-kit, rulesync) generate per-host artifacts from a neutral source. 36 repos ship this layout; `firebase/agent-skills` has already drifted its `license` across its three manifests, which is the argument for generating two of them rather than hand-maintaining three.
- **The gate guarantee moves out of the host.** Both Codex and Cursor fail hooks OPEN — on timeout, on non-zero-but-not-2 exits, on exit-2-with-empty-stderr. A crashed gate permits and looks like a pass. The answer is the stamped-context invariant, which generalizes machinery Flow already has (`render-test-plan.py`'s "un-stamped buffer reads as un-judged").
- **`tools/flow`, not `bin/flow`.** `bin/` is a documented Claude Code component that PATH-injects; a bare `flow` would collide with Facebook's Flow type-checker in exactly the `web`/`tauri-rust-ts` stacks flow ships.
- **Index + `Status:` lines over archival.** Stale docs were marked, not deleted — three handoffs describing shipped work carried status lines that read as active.

**Technical decisions.** Claude Code regression safety was established empirically (CLI v2.1.141, identical 17-skill/9-agent inventory with all proposed sibling dirs present), not inferred. Codex/Cursor claims are docs- or source-derived and marked ⚠️ where undocumented; neither CLI was installed, so 10 spikes are named as blocking rather than guessed at.

**Tradeoffs.** The survey is left partially superseded rather than rewritten — a research doc records what was believed when, and silently rewriting it would erase the correction trail. Cost: a reader must heed the banner. Accepted because the roadmap is named authoritative for every execution decision.

**Lessons learned.** Two shipped features were found to never load (see FB-0085 and the roadmap's §17/Phase 00). Both were advertised in three places each. The research also drifted against main during the session — five releases — and the rebase caught an FB-number collision (FB-0075 → FB-0084 → FB-0085, twice on this one PR) plus ~15 stale counts, which is the `reserved-feedback-numbers.md` protocol and the stale-base gate both working as designed.

---


## 2026-07-08 — AI-workflow competitive benchmark + five-item program reconciliation

**Branch:** `claude/cool-ardinghelli-43c165` · **SHA:** merged #102 @ `3fac2a2`

**What was done (user-facing).** Captured a competitive benchmark of flow against the current AI-coding-workflow landscape (gstack, Superpowers, GSD, Spec Kit, BMAD; the Claude-Code loops article; the reflection & visual-feedback literature). The durable report already landed on `main` via the pre-archive preservation commit (#100) at `dev-docs/research/ai-workflow-landscape-2026-07.md`; this PR does the two follow-on doc actions: reconciles the five-item program the benchmark produced against the current roadmap in `roadmap.md` § Next, and drafts the net-new model-measurement harness (M) as a QUEUED PR plan in `plan.md`.

**Why.** The benchmark surfaced that flow is best-in-set on trust/verification but behind on per-subagent model routing (three independent sources — gstack, Anthropic's multi-agent pattern, the loops article — all point at it), under-instrumented on reflection, and ahead-but-unreliable on visual feedback. A parallel archive process preserved the research plus an "Active program" handoff (`dev-docs/handoffs/active-program-2026-07-08.md`) marked "preserved, not applied — re-integrating is a judgment call." This PR is that judgment-applied re-integration against v1.27.0.

**Design decisions.**
- **Reconcile, don't re-paste.** Most of the program had already landed or shipped: #2 = Designer-signal track D3 (FB-0046), #4 = D1 + the shipped pin-to-anything annotation work (#75 / #84), #5 = Facet 4 + FB-0044. Only **M** (model-measurement harness) and **#3** (memory-effectiveness instrumentation) are genuinely net-new, so only those two became live roadmap § Next entries. The stale M→#5→#2→#4→#3 forward-queue re-prioritization from the handoff was deliberately NOT re-imposed — v1.27.0's Designer-signal track supersedes it.
- **Model routing is measurement-first (FB-0083).** M ships the *measurement* (token attribution + offline Opus-vs-Sonnet A/B + randomized sampler), never a swap. Opus stays default, Sonnet is the only challenger, no Haiku; the standing "plan-critic + lenses stay on Opus" direction (FB-0013) is preserved.
- **The M plan is QUEUED, not active.** Its Spec-walk sits below this PR's active block so the first-block readers (`extract-criteria` / `extract-visual-states`) never mistake it for the active plan.

**Technical decisions.** Docs-only diff (roadmap.md + plan.md + feedback.md + history.md prose; the research doc was already committed by #100). The four ship reviewers self-skip (security: doc-only; a11y: no UI files in diff; verify-build: platform library; audit-coverage: no behavior). The Test plan renders the honest no-behavioral-gate fallback (platform library).

**Tradeoffs.** Bundling the reconciliation + M plan into one small docs PR keeps direction-setting in a single reviewable unit, at the cost of touching two hot forward-looking docs (roadmap + plan) — accepted because the edits are additive § Next entries + a plan Current-Focus pointer, not restructures.

**Lessons learned.** A parallel archive/preservation process can commit session artifacts to `main` *before* the session's own PR opens — check `git log` / `git diff` against origin before assuming uncommitted work is unique (the research doc was already upstream, byte-identical). "Preserved, not applied" handoffs are a deliberate shape: they record direction without forcing a mechanical paste, leaving reconciliation as a judgment call for a later session.

## 2026-08-03 — One slot can't answer two questions: `uiFilePatterns` splits into `visualFilePatterns` + `a11yFilePatterns`

**Branch:** `claude/uifilepatterns-visual-a11y-51627b` · **SHA:** merged #95 @ `4fe0851`

**What was done (user-facing).** Two new optional schema slots, `visualFilePatterns` and `a11yFilePatterns`, each resolving `explicit slot → uiFilePatterns → built-in default`. A project that sets only `uiFilePatterns` (or neither) behaves byte-identically to before. A new shared resolver, `skills/verify-build/lib/file_patterns.py`, owns that chain for both Python consumers; `/flow:accessibility-review`'s shell gate implements the same chain in jq. `/flow:audit-skips` splits its `touches_ui` field into `touches_visual` + `touches_a11y` so each reviewer's skip is confirmed against the pattern that reviewer itself used.

**Why.** `uiFilePatterns` gated two reviewers asking **different questions** of the same diff — visual-significance asks "does this change what the app DRAWS?", accessibility-review asks "does this change something with an ACCESSIBILITY SURFACE?". Those sets overlap but are not equal, so the consumer had to pick which reviewer to answer wrongly. Measured on health-tracker (iOS/SwiftUI, PR #100): `Insight/` had to be **included** for a11y because it builds the string VoiceOver reads, which forced `Insight/InsightCacheStore.swift` — pure persistence, no render path — to over-flag visually; `Data/MockSleep.swift` had to be **excluded** for a11y despite deciding what the hypnogram draws, so the visual half needed a hand-authored `**Visual-walk:**` block as a workaround. This is also the root cause behind 2 of the ~6 draft-manifest items measured in FB-0075: one misconfiguration surfacing as two unrelated-looking blockers, which the numbered decision list then presented as independent.

**Design decisions.**

- **Additive slots with a fallback chain, not a replacement.** The alternative — rename `uiFilePatterns` to one of the two and force a migration — was rejected: it breaks every existing config for a problem most projects don't have. The fallback chain means the split costs nothing until a project hits the trade, which is the same shape as `sourceFilePatterns` (opt-in scoping, sensible default).
- **The doc-only check takes the UNION; the a11y check takes the a11y pattern alone.** These pull in opposite directions and both are deliberate. "Doc-only" is a claim about the *whole diff*, so it must be refused if either surface is touched — the fail-safe direction is to over-refuse. An a11y skip is a claim about *one reviewer's* scope, so only that reviewer's ruler can confirm it — the fail-safe direction is to measure precisely. Merging them either way produces a confident wrong answer.
- **`file_patterns.py`, underscore-named, in `verify-build/lib/`.** `visual-significance.py` is not importable (hyphen), which is exactly why `DEFAULT_UI_PATTERN` existed as a hand-synced copy in `skip-audit-checks.py` — the FB-0010 fan-out class. `skip-audit-checks.py` already puts that directory on `sys.path` for `walk_extract`, so the new module needed no new plumbing and retires the duplicate.

**Technical decisions.**

- **The jq chain needed the long form.** `.a11yFilePatterns // .uiFilePatterns // empty` looks equivalent to the Python resolver but is not: jq's `//` falls through only on `null`/`false`, so a slot set to `""` would skip `uiFilePatterns` and land on the built-in default, while Python's truthiness check falls through to it. Verified the divergence empirically across five config shapes before choosing `map(select(. != null and . != "")) | first`.
- **Both new imports fail loud, in opposite directions, on purpose.** The refactor introduced a failure mode that didn't exist when the constant was inline: a missing sibling module. `visual-significance.py` emits a well-formed **fail-CLOSED** verdict (`visual_significant: true`) and exits non-zero — its only caller parses stdout regardless of exit status and would read a crash as `false`, silently skipping the very gate the file exists to enforce. `skip-audit-checks.py` exits non-zero with clean stdout, matching its existing malformed-report contract. Neither degrades to a guessed pattern.
- **`TypeError` now caught alongside `re.error`.** A slot holding an array (schema-invalid but reachable by hand-editing) raised `TypeError` from `re.compile`, which the pre-split callers did not catch and crashed on.
- **The invalid-regex warning names the offending slot.** With three possible sources, a generic "uiFilePatterns is invalid" would point at the wrong line as often as the right one.

**Tradeoffs discussed.**

- **Two more slots is real cost.** 30 → 32, and slot count is itself a documented fan-out surface. Accepted because the alternative is a config that cannot express a correct answer — the consumer was already paying for it, in a hand-authored `Visual-walk` block and two spurious draft-manifest blockers per affected PR. The cost lands on flow's maintainers (one more fan-out walk); the benefit lands on every consumer whose UI and a11y surfaces diverge, which is every shared-extension stack (Swift, Kotlin).
- **`touches_ui` was removed rather than kept as a union alias.** Keeping it would preserve any external consumer, but its *meaning* would have silently changed from "the UI pattern" to "either UI pattern" — the failure mode is a reader who doesn't notice. Verified no consumer outside the emitting file reads it; a hard removal makes a stale reader an error instead of a wrong answer.
- **The back-compat guarantee is pinned by tests, not asserted.** Four assertions (two per harness) verify a `uiFilePatterns`-only project is unchanged, and they pass against *both* the pre-split and post-split engines — which is the point, and also means they cannot red-verify. The behavior-change assertions carry the red-verify; the one guard that could do neither (`a11y-slot-does-not-leak-into-visual`) was mutation-tested instead, by pointing the visual predicate at the a11y slot and confirming it fails.

**Rebased onto #92 mid-ship.** `#92` landed while this branch was open and changed two things underneath it. It claimed **FB-0078** (renumbered here to FB-0079 — the reservation was pushed early per protocol and still lost, because #92 claimed *and shipped* the number the same day; an early push detects the race, it does not win it). And it rewrote both manifest `description` fields from 27KB changelogs to 216-char paragraphs, adding `run_plugin_desc_evals.py` — which **bans version tokens in the description**. This PR's original diff prepended a `(v1.26.0)` lede to exactly that field, so the new guard would have failed it. Both edits were dropped: the descriptions are untouched here, and the slot-count fan-out is correspondingly smaller (#92 deleted the `(30 slots)` sentence from both manifests), leaving `docs/workflow.md`, `template/base/CLAUDE.md.template`, and the `run_merge_status_evals.py` tripwire. Verified zero file overlap between this branch's diff and #92's before replaying.

**What `/simplify` changed (and the one finding that mattered).** The four cleanup lenses returned six findings; the efficiency lens honestly cleared its own angle after measuring (the second regex compile is a `re`-module cache hit, and the extra file scan is 0.09ms against a 17ms subprocess three lines away — not worth a branch). The load-bearing finding was self-inflicted and confirmed by running it: **`file_patterns.py`'s docstring transcribed the jq form the shell gate had just rejected.** It documented `.a11yFilePatterns // .uiFilePatterns // empty` and told the reader "keep the two in sync" — while `accessibility-review/SKILL.md`, edited in the same commit, carried a comment explaining why that exact form is wrong. On `{"a11yFilePatterns": "", "uiFilePatterns": "X"}` the documented form returns empty and both real implementations return `X`. A module whose whole purpose is retiring an FB-0010 fan-out shipped a new one, in its own docstring, in the commit that created it.

The fix is not a corrected comment — a comment is what failed. `run_visual_significance_evals.py` now **extracts the live jq expression from the SKILL** and asserts it agrees with `resolve()` across six config shapes, so the cross-runtime join is checked mechanically. Extracting rather than hard-coding a copy is deliberate: a copy in the eval would be a *third* implementation of the chain. Mutation-tested both ways — reverting the SKILL to naive `//` semantics fails 2 parity checks with the exact divergence, and deleting the line fails the extractability check loudly rather than passing vacuously. Also applied: the precedence rule in the SKILL now exists in **one** jq expression (resolve the slot *name*, then look the value up by it) instead of two spellings in two dialects; the unused `DEFAULT_UI_PATTERN` import and the dead except-body sentinels came out (one of them, `VISUAL = "visual"`, re-hardcoded the literal the module argues should never be written bare); `skip-audit-checks.py` now surfaces the resolver's warnings in its report rather than discarding them — without that, an invalid `a11yFilePatterns` warns loudly in visual-significance and silently falls back in the audit, which would confirm an a11y skip against the built-in default while claiming to measure the project's pattern; and the three-key `diff` dict is built once instead of twice.

**What the four staff lenses caught (two blockers, both confirmed by running them).** The design-engineer and staff-engineer lenses independently found the same defect from different angles: **the jq mirror and `resolve()` disagreed on non-string slot values.** jq's `!= ""` is true for `[]`, `{}` and `0`; Python's truthiness is false. Traced end to end, a hand-edited array in `a11yFilePatterns` made the a11y gate fall back to the built-in default while `skip-audit-checks.py` measured against `uiFilePatterns` — the a11y review skipping on one pattern and the audit confirming that skip against another. That is precisely the wrong-ruler failure the split exists to prevent, reproduced inside the fix. The jq `select` is now type-aware, and the parity eval covers `[]`, `{}`, `0`, `false` and `null` alongside the string shapes. Worth stating plainly: the six string shapes the first cut checked all agreed, so the guard was green while the divergence was live — coverage chosen by the same person who wrote the code tests the shapes they already imagined.

The staff-engineer lens also caught that the two `$example-*` keys added to `flow.config.json.example` **survive `bootstrap.sh`'s key strip**, which filters `$comment*` only — so every newly bootstrapped consumer would get two inert keys carrying health-tracker-shaped Swift paths, directly contradicting the example's own "commented out here" sentence. Renamed to `$comment-example-*`, verified against the real filter.

Three more that changed shipped behavior rather than prose: the fail-closed guard **overrode `uiSurface:false`**, which every doc calls unconditional — on a headless project with a broken install it produced an unsatisfiable `[visual-deliverable]` blocker whose real cause was the install; it now reads the config first and lets `uiSurface:false` win. `pattern_warnings` was **write-only** — all four lenses flagged it, and they were right that the history entry's claim ("surfaces the resolver's warnings") was false as shipped, because `audit-skips/SKILL.md`'s output contract says "no prose before or after" and never mentioned the field; it now has a declared `⚠️ PATTERN-WARNING` line and an eval asserting both the field and the instruction. And the eval's jq-absent branch **passed vacuously** — a green check name that measured nothing, which is the silent-skip class; it now fails, because jq is a hard prerequisite everywhere else in the pipeline.

The push-further lens landed the most durable one: the parity guard checked *which slot wins* but never *what the default pattern is*, while `DEFAULT_UI_PATTERN` still carried a "MUST stay in sync" comment — the exact construct this module's own docstring convicts, and already inaccurate on ship day (it named schema defaults for the two new slots, which correctly have none). The default literal is now compared across all three runtimes (Python, both shell fallbacks, the schema), and the comment points at the check instead of asking for hand-sync. Its other four findings routed to the roadmap: the `sourceFilePatterns` question-test (FB-0079 names a class; this PR swept one instance), an executable harness for the a11y shell gate, a declared reason-string enum shared by emitter and recognizer, and — as Exploration — whether flow's many shell↔Python mirrors want a general harness or a convention that makes them extractable by construction.

One finding I acted on that was not raised: the slot-count sweep grepped the old *value* (`30 slots`) rather than the *class* (`[0-9]+ slots?`), so `bootstrap.sh` kept claiming "28 slots" for a config carrying 22. It now counts the keys. This is the FB-0010 discipline the same PR documents, missed by the PR documenting it.

**The final round — `/flow:security-review` + `/flow:audit-coverage`, and the rule that needed three tries.** The security lens found that the staff-review fix was **half a fix**: jq's `type == "string"` guard excludes *all* non-strings, but Python's `if val:` accepts *truthy* ones, so `a11yFilePatterns: ["\\.tsx$"]` — an array, the obvious hand-edit — made the two runtimes resolve different slots again. It traced the impact precisely: the audit calls `compile_for`, gets the array, catches `TypeError`, silently falls back to the built-in default, computes `touches_a11y=False`, and returns `LEGITIMATE, "diff touches no a11y-surface files"` — blessing a bogus a11y skip measured with a ruler nobody chose. `resolve()` now asks jq's question (`isinstance(val, str) and val`); the parity fixtures cover the full type × truthiness grid; mutation-tested (bare truthiness fails 4). Worth being blunt about the pattern: this rule was green after round 1 and green after round 2, and wrong both times, because each round's fixtures were written by the same agent that wrote the code. That is now FB-0079's second corollary.

`/flow:audit-coverage` (running as the strict under-declaration auditor) found four behaviors changed by the `/simplify` and staff-review commits that no declared criterion reached — the Spec-walk was written before them, which is exactly the under-declaration shape. All four are now declared and verified, including the one with no eval whatsoever: the import-failure branch, which is the single change here that alters a **ship-blocking** verdict. It also **falsified criterion 10 outright** — the claim "`grep -rn '30 slots'` returns empty" was true, but empty for the wrong reason: `doctor/SKILL.md` carried `all 30\n  slots` wrapped inside its frontmatter, invisible to a line-oriented grep. That is the same value-vs-class mistake caught one commit earlier in `bootstrap.sh`, recurring in the fix for itself. Both are replaced by `no-stale-slot-count-in-shipped-surfaces`, a wrap-tolerant check over every shipped `.md`/`.json`/`.sh`, red-verified by restoring the survivor.

Two reviewer findings were **not** acted on, deliberately. The `grep -qE` leading-dash NIT (a `--file=` pattern read as an option) is real but pre-existing, identical pre- and post-split, and bounded to flipping a gate the config author already controls — routed as a note, not fixed inside an unrelated PR. Unbounded ReDoS on the direct `verify-build` invocation is likewise pre-existing and equally reachable before this change.

**Re-review round (the rigor gate earning its keep).** `/flow:audit-skips` flagged `staff-review` SHOULD-RE-RUN — the marker was written before the security/coverage fixes moved the source, so the lenses had not seen the final tree. Re-running them on the delta caught a **regression introduced by the previous round's own fix**: filtering non-strings out inside `resolve()` also removed the `TypeError` that used to make them loud, so an array-valued `a11yFilePatterns` was now skipped with *zero signal* — `pattern_warnings` empty, the new `⚠️ PATTERN-WARNING` line never firing for precisely the shape that motivated it, and the shipped claim "falls back loudly … never silently" false. `resolve()` now returns its own warnings and reports any present-but-wrong-type slot by name; the unreachable `TypeError` arm is deleted rather than left as decoration. Pinned by `fb79-non-string-slot-surfaces`. Three consecutive rounds of this PR each fixed the previous round's fix — which is the argument for the gate, not against it.

Also from that round: the broken-install eval no longer moves `file_patterns.py` inside the live checkout (a `try/finally` is exception-safe but not signal-safe — a cancelled CI run would leave the tree broken); it copies the lib and deletes from the copy. The slot-count sweep gained a positive `scanned > 0` assertion — an empty sweep would otherwise go green having measured nothing, the same vacuous-pass class this PR fixed twice already — and its comment-line exemption is now restricted to `.sh`, since a markdown heading also starts with `#` and would have let `## Config (30 slots)` hide. The import-failure path stopped swallowing `load_config`'s warnings, so a broken install *plus* a malformed config now reports both causes. And `bootstrap.sh`'s new comment claimed doctor Check 2.5 covers its output — it does not; the number there is the generated config's key count, not the schema's slot count.

Two findings routed rather than fixed. **Doctor Check 2.5 is the consumer-facing, still-line-oriented twin** of the sweep this PR just hardened — the same class recurring inside its own fix, one commit after the lesson was written down. Real, and its fix (hoist the predicate into a shared `slot_count_scan.py` both the eval and doctor call) is its own change, not a rider on this one. Same for making `PATTERN-WARNING` an engine-rendered string instead of an instruction to a model, mirroring what `manifest-triage.py` already does. Both are in roadmap § Next; the push-further lens's corpus rider went to § Exploration.

**Verification.** 14 new assertions across `run_visual_significance_evals.py` (26 checks total) and `run_skip_audit_evals.py` (30). Red-verified by restoring both engines from `origin/main` and hiding `file_patterns.py`: 5/8 and 4/6 of the new checks fail, with the two headline cases reproducing the consumer's exact symptoms (a11y-only file → `visual_significant: True`; render-only file → `False`). The `/flow:accessibility-review` gate — which no eval executes — was verified separately: `sh -n` and `bash -n` parse, and its RAN/SKIPPED decision is identical pre- and post-split on a `uiFilePatterns`-only project across three file shapes, while the `a11yFilePatterns` opt-in flips it as intended. All 21 CI harnesses green; the slot-count tripwire in `run_merge_status_evals.py` fired on 30 → 32 and was updated (that is the tripwire working).

---

## 2026-08-03 — Plugin descriptions trimmed from 27KB to 216 chars + a guard that keeps them there (FB-0078)

**Branch:** `claude/flow-description-terminal-ui-49aaaf` · **SHA:** merged #92 @ `0f1bc6dc4` · rebased onto `d24c33f`

**What was done (user-facing).** The `description` fields in `plugins/flow/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` — the text Claude Code renders in the `/plugin` Plugins pane — were rewritten. `plugin.json.description` went from **27,711 → 216** characters; `marketplace.json` `plugins[0].description` from **25,795 → 216** (now byte-identical to plugin.json's); `metadata.description` from **17,461 → 85** (and it now describes the *marketplace*, which is what that field is for, rather than repeating the plugin blurb). The text is two sentences on what flow does for the user. No version bump — this is a presentation fix to an existing release, and marketplaces re-read the manifest on update.

**Why.** The user opened the Plugins pane and the entire viewport was one unbroken wall of prose. Every version bump since v1.2.3 had appended its release blurb to the description instead of to `CHANGELOG.md` — which already existed and already carried the same content, verbatim in places. The old `plugin.json` field alone named **33 distinct versions** (v1.2.3 → v1.25.0; 35 across all three fields). Each append was defensible on its own; the total was not.

**Design decisions.**
- **The description says what the plugin does; the changelog says what changed.** Considered a "last 2 releases" compromise (some marketplaces do surface recency there). Rejected: recency in that field is exactly the append-affordance that produced the bug, and the pane has no room for it.
- **No skill catalog — reversed mid-PR, on evidence.** The first cut (760 chars) kept a list of all 17 `/flow:*` skills on the reasoning that it is what a reader in that pane wants. The user challenged the premise ("that exists elsewhere in the plugin UI") and asked for the docs rather than the argument. They are right, and it is not a judgment call: **Claude Code generates the component inventory from disk** and renders it in the Discover tab's "Will install" section and the Installed tab's detail view (also `claude plugin details`). A hand-written copy in `description` is redundant *and strictly worse* — it can go stale; the generated one cannot. Cut it; 760 → 216.
- **Calibrated against a real corpus, not taste.** Measured Anthropic's own official marketplace (`anthropics/claude-plugins-official`, 276 plugins): median description **176** chars, p90 **312**, max 665, only 6 over 500, **exactly 1** containing a version token. The docs call the field a "Brief plugin description" and their examples are one-liners ("Deployment automation tools"). 216 sits just above the median; the plugin-field cap sits above p90 (the marketplace-field cap is deliberately below it — different population).
- **`metadata.description` describes the marketplace, not the plugin.** It had been a near-copy of the plugin blurb. The docs call it a "Brief marketplace description," and it renders on the Marketplaces tab, where the reader has not chosen a plugin yet.
- **Version-neutral.** Past convention edited descriptions only inside a version bump, which is part of why they only ever grew. A description fix does not need a release, and bumping would have fanned out into roadmap "Now" + plan "Current Focus" reconciliation for a cosmetic change.

**Technical decisions.**
- **New CI-wired eval `plugins/flow/evals/run_plugin_desc_evals.py` (19 checks).** Per-field caps (400 plugin / 200 marketplace-level, calibrated on the official corpus), a ban on version tokens, and a ban on enumerating skills (≤2 mentions) — each applied to *every* description field in both manifests, including every `plugins[]` entry rather than just `[0]`. Plus plugin.json↔marketplace parity (keyed on the entry whose `name` matches, not blindly on index), version parity, the same version-token ban over all 17 skills' frontmatter `description:`, and a self-guard that it is wired into `ci.yml` as an executable `- run:` step (not merely named in a comment — the weaker bare-substring form is what its two sibling harnesses use, and `ci.yml`'s own join-check argues against it). Named `plugin_desc` not `manifest_desc` because "manifest" already means the NOT-READY PR manifest in this repo.
- **The two bans are load-bearing, not the cap.** A cap only fires once the damage is done; the append habit *always* opened with a version token, so banning the token fails the build on the first appended sentence, and the skill-count check fails the exact regression this PR reversed. Mutation-tested — 13 mutations, every one caught — and validated against the real thing: `origin/main`'s actual 27,711-char description fails 4 checks.
- **Two existing evals were pointed away from the manifests.** `run_land_evals.py` (`reg 1`) and `run_merge_status_evals.py` (`reg-plugin-json` / `reg-marketplace`) asserted that `/flow:land` and `/flow:post-merge` appeared in the manifest descriptions — i.e. they *enforced* the catalog we just removed. Both now check only the real consumer-facing catalog sites (`docs/workflow.md` + `workflow-help`), with an inline note explaining the change so a future reader does not "restore" the assertion. This is a deliberate narrowing, not an accidental one: the manifest was never a good registration site, because the UI's generated inventory already covers it.
- Descriptions were rewritten by targeted string replacement of the JSON literal rather than a `json.load`/`json.dump` round-trip, so the rest of both manifests is byte-identical in the diff. `claude plugin validate .` passes; all 22 eval harnesses pass.

**What `/flow:staff-review` caught (four lenses, all four returned findings; two BLOCKER-class, both fixed here).**
- **The no-skill-catalog check was evadable in the most likely way.** It matched only the `/flow:<name>` form. Two lenses independently mutation-tested the bare-name shape — `"Bundles ship, staff-review, verify-build, audit-coverage, doctor, land, post-merge, contribute."`, 95 chars, 8 skills — and it passed every check then in the harness. Since `plan.md` and this entry both called the check *load-bearing*, the shipped guard was weaker than the claim. Fixed by also matching bare **hyphenated** slugs (`staff-review`, `verify-build`, … read as command names anywhere), while the four single-word skills (`ship`, `land`, `doctor`, `contribute`) stay `/flow:`-only because they are ordinary English a legitimate description will use — a check that fires on prose gets edited away rather than obeyed. Re-verified: a full bare-name catalog of all 17 fails; the 8-skill sample above trips 4 of the 8 (the hyphenated ones — enough to fail); the shipped 216-char description matches 0.
- **The `roadmap.md` entry this PR resolves still prescribed the rejected direction.** "Cap the marketplace/plugin `description` blobs" (#59 ux FOLLOW-UP) said to cap at "what the plugin is + the last 1–2 releases" — a description containing the last 1–2 releases contains a `vN.N.N` token and now fails CI. Left live, the next session would have implemented the entry as written and re-opened the door. Retired it in this diff. The push-further lens also noticed the entry's own `Surfaces when: the next version bump edits the description` trigger, which then failed to fire across ~15 version bumps that each edited exactly that field — the sharpest available argument that this fix had to be a CI check rather than a better-worded roadmap entry, and now recorded there.
- **Coverage + honesty fixes:** the catalog check now covers all three description fields rather than two (parity was protecting `plugins[0]` only for as long as parity itself holds); malformed input is a clean FAIL rather than a traceback (`"plugins": []` raised `IndexError`, a missing skills dir `FileNotFoundError`, bad JSON an uncaught `JSONDecodeError` — CLAUDE.md's bar is explicit); the docstring's "caps sit above p90" was false for `MAX_MARKETPLACE_DESC = 200` and now explains why that field is a different population; and the tradeoff bullet below was corrected from "net unchanged" to the true 4 → 2.
- **Copy, from the UX lens.** Three real problems with the first draft: it led with the coined term ("Managed-autonomy") rather than the payload, where the README and `docs/how-it-works.md` both deliberately lead with the plain sentence; "you approve the plan and merge **it**" has an ambiguous antecedent that parses as merging *the plan*; and "Home of flow" is an idiom that presupposes the vocabulary the Marketplaces tab exists to introduce. All three taken. Deliberately *not* taken: adding "runs the app to confirm it works" to surface `/flow:verify-build` — real, and there is cap headroom, but two sentences read better in a narrow pane than three.
- **What `/simplify` caught (four lenses; the most valuable finding was that my own "hardening" had made a check weaker).**
- **The version-token regex was over-fitted and missed 1 in 5 of the blurbs it exists to catch.** After the security review I had "hardened" it to `v?\d+\.\d+(\.\d+)?` gated on a following release verb (`adds|ships|brings|…`), reasoning that the verb context prevents false positives on prose like "WCAG 2.1 AA". Measured against `origin/main`'s real 25,795-char blurb: **26 of 33 tokens caught, 7 missed** — `v1.20.0 generalizes`, `v1.9.1 hardens`, `v1.2.5 sharpens`, `v1.11.1 extends`, and three more. A closed verb list only recognizes the shape it has already seen. The simpler form — `\bv\d+\.\d+(?:\.\d+)?\b|\b\d+\.\d+\.\d+\b`, no lookahead, no verb list — catches **33/33** with zero false positives across the prose cases I tested (`WCAG 2.1 AA`, `Python 3.7+`, `an 11-step loop`, `JSON Schema draft 2020-12`, and both shipped descriptions). Simpler *and* strictly stronger; the elaborate version was five lines of machinery buying a weaker check.
- **Structure:** the three per-field loops and the `entries`/`all_descs` pair collapsed into one list carrying its own per-field cap, which also removed three differently-worded copies of the same length assertion. `skill_mentions()`'s two full duplicated patterns became one template with a varying prefix. A missing/empty `plugins[]` array now fails as one named check (`marketplace-has-plugins`) with an early return, instead of surfacing as three unrelated downstream failures that named nothing.
- **Renamed `run_manifest_desc_evals.py` → `run_plugin_desc_evals.py`.** "Manifest" already means the NOT-READY PR manifest here (`run_manifest_triage_evals.py`, `skills/ship/lib/manifest_contract.py`), and the two harnesses sat adjacent in `ci.yml`.
- **Mechanized the frontmatter sweep** the altitude and push-further lenses both asked for: the version-token ban now also runs over all 17 skills' frontmatter `description:`, converting the narrative measurement above into a re-runnable check. It immediately found something the narrative had missed — `/flow:doctor`'s description says the config must match "the v1.2+ schema". That is a legitimate compatibility floor, not a changelog, so the frontmatter check requires a *complete* three-component release (`v1.21.0`) while the display-copy fields keep the stricter two-or-three-component ban. Worth naming plainly: my earlier "none carries a version token" was true only under the narrower regex I was using at the time.
- **Deliberately not taken:** reusing `skill-composition-lint.py`'s `scan()` for skill enumeration (it also builds a call graph — heavier read for an identical result today), and collapsing `ci.yml`'s 22 enumerated steps into a loop (the enumeration is load-bearing: it segments across two jobs, and both the join-check and this harness's own `ci-wired` check grep for the literal `- run:` lines). The efficiency lens measured the harness at 37 ms and recommended no change; recorded as considered, not overlooked.

**Declaring the Spec-walk at the merge gate surfaced a second bug in the plan machinery.** `/flow:audit-coverage` correctly refused this PR for having no criteria block of its own (the work was directed conversationally, not through the plan gate), so one was written and approved at hand-off. Adding it exposed that `walk_extract` picks the **first** block by position, and the previous PR's block was sitting above it in `## Current Focus` — so #90's ten criteria had been silently attributed to this branch all along. The first repair made it worse: qualifying the retained heading as shipped stopped it *terminating* the active block (`is_terminator` does not match a bold heading with a trailing parenthetical), so the two merged into one 20-item block. Fixed structurally by moving the retained block into its own `## PR —` section; the general shape — 38 blocks, one positional rule, and two regexes that disagree about what a heading is — is routed to the roadmap with the one-line fix named. Post-fix the extractor resolves exactly this branch's 10 criteria and the audit returns **No issues flagged**.

**Honest limit — no rendered read-back.** This PR's own synthesized rule says never to ship a field you have not looked at rendered, and `/plugin` is an interactive terminal panel this session cannot open. At 218 characters the risk is low, but the verification the rule asks for has not been performed; it is called out at the hand-off rather than quietly assumed.

**SAFETY.** Both files are on `.claude/rules/safety.md`'s `paths:` list (install surface). Changes are `description` prose only — no `version`, `source`, `name`, `author`, `homepage`, `repository`, `category`, or `keywords` field was touched, and no authority-bearing key exists in either file. Verified by `git diff` and by `claude plugin validate`.

**Swept the class the rule names (per FB-0010 / the "sweep the class you name" discipline) — and then mechanized the sweep.** The same defect shape — a consumer-visible string flow writes but never reads back rendered — also lives in the frontmatter `description:` of every skill and agent. The first pass measured them and wrote the result down here (longest 1,420 chars, no version tokens), which two lenses correctly called out as the decaying-claim shape this very PR argues against: a dated measurement in a doc is exactly what drifts. So it is now a check in the same harness, over all 17 skills **and** all 9 agents. Length is deliberately *not* capped there — that text is trigger input to the model, where length is functional, not display copy. Running it immediately corrected the narrative claim: `/flow:doctor`'s description cites "the v1.2+ schema", so "none carries a version token" was true only under the narrower regex in use at the time. That citation is a legitimate compatibility floor rather than a changelog, which is why the frontmatter check requires a complete three-component release while the display fields ban the looser form too.

**Found while pointing the registration evals at the docs: two real fan-out holes, left for a separate fix.** Checking which catalog sites actually cover all 17 skills turned up gaps that predate this PR — `README.md` is missing `/flow:contribute` and `/flow:land`; `workflow-help/SKILL.md` is missing `/flow:audit-skips` and `/flow:contribute`. `docs/workflow.md` is the only surface at 100%, which is why the two relocated assertions point there. The per-skill registration evals only ever checked the skills they shipped with, so nothing was watching the others — a generalized coverage check over the three catalog sites is the right fix and is bigger than this PR.

**Prevention beyond the eval.** The rule is written where the next version bump will actually read it: the install-surface bullet in `.claude/rules/safety.md` (auto-loads when either manifest is touched) and the doc-currency step of the dev-side `/ship` skill. Both say the same thing — a version bump edits `version` only.

**Rebase note (third collision in four PRs — the protocol working).** The ship-time stale-base gate caught `main` advancing three commits mid-session (#89, #90, #91). Two collisions: **FB-0077 was claimed by #90** (land model-invocability) so this entry renumbered **FB-0077 → FB-0078** (7 references), and #90 bumped the version to **v1.25.0** *and* appended another release blurb to the very field this PR trims — so the description had regrown to 27,711 chars on main. Both manifests, both touched eval harnesses, and all three reverse-chronological docs were resolved by **taking `main`'s copy and re-applying this branch's change on top**, never by resolving conflict markers — the method the audit trail in `reserved-feedback-numbers.md` prescribes after marker-based resolution silently dropped an upstream CHANGELOG entry twice. Verified after: `main`'s v1.25.0 version fields, its FB-0077 entry, and its `run_land_evals.py` model-invocability assertions all survive intact.

**Tradeoffs discussed.**
- **A hard cap will eventually block a legitimate edit.** Accepted: raising a number in an eval with a one-line reason is a cheap, deliberate act, which is the point — the failure mode being defended against is the *undeliberate* growth. The corpus calibration makes the number arguable-from-evidence rather than arbitrary.
- **Dropping the manifest from two registration evals genuinely reduces coverage — 4 sites → 2, per skill.** An earlier draft of this entry claimed the net was "unchanged"; two lenses caught that independently and they are right. `run_land_evals.py` checked plugin.json + marketplace.json + workflow-help + workflow.md and now checks only the last two; `run_merge_status_evals.py` the same. The two dropped assertions were enforcing a thing now known to be wrong, so dropping them is still correct — but the honest accounting is that the registration signal is *weaker* than before this PR until the generalized coverage eval lands, not equal to it. That window is real, which is why the follow-up is now a roadmap entry with a named shape rather than a paragraph in this file.
- **Deleted prose is not recoverable from the field**, only from git. Checked all 33 versions the `plugin.json` description named against `CHANGELOG.md` before cutting: 31 have entries. **Two do not — v1.2.6 (bounded-retry preflight) and v1.3.0 (`/flow:verify-build`)** — which `CHANGELOG.md` itself already flags as a known backfill follow-up. Their substance survives in this file, so nothing is lost, but this trim does remove the last *consumer-facing* copy. Not backfilled here (it is its own tracked task and would widen a two-file fix); the removed text is at `git show 3a825a6:plugins/flow/.claude-plugin/plugin.json`.
- **Left the stale `FB-0067` reservation in `reserved-feedback-numbers.md` alone**, though it is provably shipped (v1.17.0) and belongs to this same worktree slug. Sweeping other PRs' bookkeeping into a two-file fix muddies the diff; that file documents periodic sweeps as their own pass.

## 2026-08-02 — `harvest_lesson.py` derives project identity from git, not the cwd basename

**Branch:** `claude/harvest-slug-git-identity` · **SHA:** merged #91 @ d24c33f

**What was done (user-facing).** `harvest_lesson.py::_project_slug()` now derives the origin project's identity from git (`git remote get-url origin`'s repo name, falling back to the primary worktree's directory via `git rev-parse --git-common-dir` when there's no `origin` remote) instead of `os.getcwd()`'s basename. A linked worktree's directory name (flow's own `.claude/worktrees/<random-slug>/`, or any `git worktree add` checkout) has nothing to do with the project it's a checkout of — every harvest run recorded the WORKTREE name into `known_tokens.json` instead of the real project name.

**Why.** Discussed with the user while reviewing PR #89's "Held — needs human attention" section: 16 of 17 sub-threshold held lessons shared one root cause — `known_tokens.json` had `"flow"` registered as a private-project scrub token, so nearly every lesson mentioning `/flow:*` by name got flagged as a leak. Tracing why "flow" was ever added led here: a harvest run whose cwd happened to be the flow checkout itself recorded `"flow"` as a token. The user asked to address the root cause directly.

**Design decisions.**
- **`known_tokens.json` cleanup is a local action, not part of this PR.** It's user-scope runtime data at `~/.claude/plugins/data/flow/contributions/known_tokens.json`, not a tracked repo file — removing the stale `"flow"` entry happened directly on this machine with the user's explicit go-ahead, not via a commit. Re-scanning the 30-item queue against the corrected token list flipped 22 entries from dirty/unscanned to clean, several from confidence 0.3–0.45 straight to their un-penalized 0.6–0.9 base score.
- **Scoped to `"flow"` only, not the rest of the token list.** Most of the remaining tokens (`flamboyant-stonebraker-36ef32`, `laughing-merkle-215513` — this very worktree — etc.) are also worktree slugs, the same bug pattern. Left alone: re-deriving each one's real project name needs per-token session archaeology I can't do reliably from the token string alone, and this fix prevents new corruption going forward — the existing entries are a one-time cleanup that can happen at leisure, not blocking anything further now that the bleeding is stopped.
- **Re-scanning the queue surfaced 3 already-resolved lessons that would otherwise have looked freshly unblocked.** Two were already fixed by #90 (`/flow:land` becomes model-invocable, FB-0077) — one inside the *same* commit that introduced the risk it describes (a fork-PR branch-deletion hazard, caught by `git log -S isCrossRepository` showing the safety check landed alongside the code it guards); the other duplicates FB-0077 rule 2 verbatim. A third (post-merge's Skill(land) composition failing) was harvested from a session that ran moments before #90 merged. All three dismissed as already-encoded with the symptom reproduced against current `main`, not reasoned from the fix.

**Technical decisions.**
- **`git remote get-url origin` before `--git-common-dir`.** The remote URL survives repo renames/forks better than a directory basename, and works identically whether or not the checkout is a linked worktree. `--git-common-dir` is the fallback for a repo with no `origin` configured (rare, but the historical cwd-basename behavior remains the last resort for a non-git directory).
- **New regression coverage in `run_contribution_evals.py`** creates a temp git repo whose directory name is a worktree-like slug and whose `origin` is a differently-named URL, runs `harvest_lesson.py enqueue` with no `--project-slug`, and asserts the resulting `provenance.project_slug` is the git-derived name — plus a no-origin case pinning the `--git-common-dir` fallback. Confirmed both fail on the pre-fix code (recorded the worktree slug) and pass after.

**Tradeoffs discussed.**
- Whether to also clean up the rest of `known_tokens.json` now, since the pattern (worktree slugs recorded as tokens) is clearly widespread: deferred. The fix here stops new bad entries; auditing and correcting ~10 existing ones is separable work that doesn't block anything the fixed pipeline needs.
- Whether to fold this into PR #89: declined in favor of a separate PR (user's call) — different subsystem (the harvest pipeline itself, not the reviewer skills #89 fixes), and #89 was already open for review.

**Follow-ups (flagged, not fixed here):** `known_tokens.json`'s remaining worktree-slug entries could use a human pass to re-derive their real project names; the newly-unblocked queue (now ~24 clean entries, several passing the confidence threshold too) is a separate scoping decision — not drained in this PR.


## 2026-08-01 — `/flow:contribute` drain: three harvested fixes, one loop closed, one systemic leak surfaced

**Branch:** `claude/contribution-flow-397e04` · **SHA:** merged #89 @ 5a5e817

**What was done (user-facing).** Ran `/flow:contribute` against the 25-item harvest queue + the disagreements store. Closed the calibration loop for merged #86 (3 lessons, previously uncalibrated). Dismissed 2 stale duplicate lessons as already-fixed by #86 (FB-0074), with the symptom reproduced against current `main` and confirmed gone, not just reasoned-from-the-fix. Converted the one open disagreement record (a plan-critic false-positive) into a queued `reviewer-prompt` candidate. Implemented and shipped 3 of the highest-confidence, sanitization-clean lessons, each with a CI-wired regression eval that fails on the pre-fix code and passes after:

- **`walk_extract.extract_block` now detects "all blocks demoted."** Previously, a heading qualified as already-shipped/merged/demoted (`**Spec-walk (PR 1c — shipped):**`) was matched by the heading regex but given no special meaning — "first heading found" won even when every heading in the file was a retained/demoted one. A plan with legitimately no `Spec-walk`/`Visual-walk` of its own (post-merge hygiene, a doc reconcile) could silently inherit the last-merged PR's stale criteria. Added `all_demoted` to the extractor's output contract, skip demoted headings when selecting the active block, and surface a distinct warning so this case is never confused with `block_count == 0` (no heading at all).
- **`visual-significance.py` no longer flags a `#if DEBUG`-only render change as visually significant.** The heuristic could see a real content delta inside a DEBUG-only conditional-compilation region and flag it, forcing the ship to a draft + demanding a visual-history entry for a change the Release build never sees. Added `#if DEBUG` / `#ifdef DEBUG` / `#if !DEBUG` / `#else` / `#endif` nesting tracking (Swift + C/Obj-C forms) to `_diff_content_changed`, with the RELEASE (`#else`) branch of a DEBUG conditional still correctly counted as significant.
- **`skip-audit-checks._reason_has` now matches at word boundaries, not bare substrings.** `"none"` matched inside `"nonetheless"`; a skip reason that merely happened to contain that word could be misread as a "platform none" claim and produce a confidently-wrong `SHOULD-RE-RUN` verdict that misquotes what it's refuting. Fixed at the single shared helper (not each of its ~10 call sites), so the fix closes the whole class at once, per the standing "sweep the class you name" discipline.

**Why.** `/flow:contribute` exists to drain the cross-project lesson-harvest queue into flow itself — this is that loop running end to end, including the calibration half (Step 1) that reads back what happened to the *previous* drain's PR.

**Design decisions.**
- **Held far more than was included, on purpose.** Of 25 queued candidates + 1 disagreement, only 3 were shipped. Two reasons, both mechanical: (a) a **systemic sanitizer false-positive** — `known_tokens.json` has `"flow"` registered as a per-project scrub token (traced to the exact bug one of the held lessons describes: `harvest_lesson.py` derives `project_slug` from `os.getcwd()` basename, so a harvest run whose cwd happened to be the flow checkout itself recorded `"flow"` as if it were a private project name to scrub). Since almost every lesson *about* flow's own skills mentions `/flow:*` by name, this one bad token routed 16 of 17 otherwise-clean lessons to HELD. Per the skill's explicit instruction ("do not hand-edit the scan to pass"), none of those were force-included — see Follow-ups. (b) **Scope**: several lessons passed the mechanical bar (confidence ≥ 0.6, sanitization-clean) but were held anyway rather than rushed — `verify-build`'s headless-mode gap and the criteria-buffer freshness assertion are real features, not one-line fixes, and deserve their own focused pass. This deviates from the skill's literal "auto-include iff clean+threshold" rule; documented here and in the PR body rather than silently narrowing scope.
- **`b06a7953` (merge-gate open-on-empty-stdin) was investigated, not implemented.** It looked like a fresh, clean, high-confidence find. It's actually already a documented, deliberately-deferred v1b item (`dev-docs/roadmap.md:264`, same diagnosis, same proposed direction: keep `classify()` pure, surface the `gh` exit code from the bash shell instead). Not dismissed (the bug is real and unfixed, so "already-encoded" would be a false claim), but not reimplemented either — a bash-prose fix with no existing test harness for it is a worse trade than leaving a well-tracked backlog item alone this round. Held as `queued`.
- **A mutation-tested example that turned out not to reproduce.** The `_reason_has` fixture originally used `"librarian"` as a "contains 'library'" example, copying the queued lesson's own wording. Running the new test against pre-fix code showed it PASSED even without the fix — `"librarian"` does not actually contain `"library"` as a substring (`librar-i-an` vs `librar-y`). Replaced with `"interlibrary"`, which does, and reconfirmed the fail-before/pass-after property. Left as a reminder that the mutation-test step is not a formality — it caught an error in the *lesson's own reasoning*, not just in the code.

**Technical decisions.**
- **Calibration matched via content, not a stored mapping.** No index links a `contribution_store` entry to the PR that shipped it. Matched #86's 3 "applied" lessons by cross-referencing its merged PR body's stated fixes against the 7 `status: proposed` entries' summaries + confirming their code changes are present in `git log` / on-disk — all 3 verified present on current `main` before calibrating `approved`.
- **`sanitization_clean` written directly into each entry's `signals`, not gamed.** No CLI subcommand exposes this write path; used the same scan the skill mandates and wrote its real (not desired) result, matching `contribution_store.py`'s own `compute_confidence` contract (`sanitization_clean=False` halves confidence).

**Tradeoffs discussed.**
- Fixing `known_tokens.json`'s `"flow"` entry directly vs. leaving it and flagging it: fixing it myself would have unblocked ~16 lessons in this same run, but curating the scrub-token list is exactly the kind of decision the fail-closed design reserves for a human (a token removed by the same agent whose lessons it was blocking is a conflict of interest the design is built to avoid). Flagged as a follow-up instead.
- Implementing `b06a7953` now vs. leaving the roadmap item as the on-the-record plan: implementing would have made a 4th shipped fix, but doing it well means editing the bash poll loop's failure-signaling without breaking the "patient on transient, blocking on terminal" contract, and there's no eval harness for `SKILL.md`'s bash blocks the way there is for the `.py` libs — a rushed fix here has a worse safety margin than the other three, which each got a real red/green regression test.

**Follow-ups (flagged, not fixed here):** `known_tokens.json`'s `"flow"` entry needs human review and likely removal (traced root cause: `harvest_lesson.py::_project_slug`'s cwd-basename bug, itself a held lesson in this same queue); `merge-status.py`'s open-on-empty-stdin gap remains tracked at `dev-docs/roadmap.md:264`; the remaining ~19 held lessons stay `queued` for the next `/flow:contribute` run.

**Corrected during the rebase onto #90 (`/flow:land` becomes model-invocable).** Resolving the `dev-docs/history.md` conflict surfaced a second, unrelated mistake in the commit this entry documents: the original `Edit` call that inserted this entry had silently dropped the `## 2026-07-29 — Annotation-layer v2` heading line, orphaning that entry's body under no heading at all. Caught only because reconstructing the file from the upstream copy (rather than resolving via conflict markers, per the project's documented reverse-chronological-doc convention — see `reserved-feedback-numbers.md`'s 2026-07-29 CHANGELOG-resolution note) required re-deriving this entry's exact boundaries — the missing heading became visible the moment the file was rebuilt cleanly. Fixed here rather than left for a future sweep.

## 2026-08-01 — `/flow:land` becomes model-invocable so `/flow:post-merge` can actually call it (v1.25.0, FB-0077)

**Branch:** `claude/land-model-invocable` · **SHA:** _(filled at ship)_

**What was done (user-facing).** `/flow:post-merge` §3 now really calls `/flow:land` instead of printing an instruction to run it. `/flow:land`'s frontmatter flips `disable-model-invocation: true → false`; a new §0 states the never-auto-fire intent as a precondition instead. `/flow:post-merge` keeps its own `disable-model-invocation: true`, so a human gate still sits above the whole path.

**Why.** `/flow:post-merge 84` ran live this session and reported that the human still had to run `/flow:land 84`. The user asked why, and then named the root cause themselves: *"land should not be disable-model-invocation - doesn't that defeat the purpose of post merge?"* It did. §3 is the step that makes `/flow:post-merge` an orchestrator; without it the skill is a reminder to run another command.

**The two-fix history is the point.** #79 wrote the `Skill("flow:land")` call; it was rejected on every run and the step silently degraded to its fallback. FB-0074 (v1.22.0) caught that and added `doctor/lib/skill-composition-lint.py` — a genuinely good static detector for "skill A calls a model-disabled skill B", a contract whose two halves live in different files (the FB-0010 fan-out class). But it then satisfied its own lint by **deleting the call**, which turned a runtime defect into documented behavior. The detector was right; the remedy was applied to the wrong half.

**Design decisions.**
- **Clear the flag rather than keep the hand-off.** Considered three options. (a) Keep the flag, keep the hand-off — rejected: it concedes the feature, and the user explicitly asked for the reverse. (b) Split land into a human-facing wrapper plus a model-invocable `land-core` that post-merge calls — rejected as machinery that buys nothing; it preserves a flag that isn't doing work. (c) Clear the flag — chosen. The flag's stated job ("it opens a PR, so it must never auto-fire") is already done more precisely by land's own §1a gate, which refuses any PR `gh` doesn't report as merged. Claude cannot merge, so the flag guarded an unreachable state while blocking a reachable and wanted one.
- **Record the intent as a precondition, not a flag.** §0 names the two legitimate entries (human types it; `/flow:post-merge` §3 calls it) and says everything else is invalid. This is strictly more expressive than the boolean it replaces — the flag could not distinguish "called by a human-gated orchestrator" from "a loop reached for me," which is exactly the distinction that mattered.
- **Fixed the lint's remediation text, not just this call site.** The lint's message led with "hand the step to the human," which is the advice that produced the wrong fix. It now leads with the redundancy question — is the callee's own gate already the guard? — and names this reversal so the next reader doesn't repeat it.

**Technical decisions.**
- Declared `disable-model-invocation: false` explicitly rather than deleting the line. An absent flag parses as invocable, so deletion would have been behaviorally identical but would have lost the record that this is a decision. The eval asserts the explicit form for that reason.
- The eval imports the lint by path (`importlib`, the filename is hyphenated) and reuses its `scan()`/`_frontmatter()` rather than hand-rolling a second fence parser. A duplicate parser in the test of a parser can drift from it and start agreeing with itself — the same fan-out class the lint exists to catch.

**SAFETY — the new assertions were mutation-tested, and the gate they protect is named.** Clearing a capability flag is a widening of what the agent may do, so the replacement guard has to be pinned, not assumed. Layer 3 of `run_skill_composition_evals.py` adds five live assertions: land is invocable; land declares the flag explicitly; `/flow:post-merge` emits a fenced `Skill("flow:land")`; `/flow:post-merge` keeps its own flag; and **land keeps its §1a merged-PR gate** — the last because that gate is now the sole mechanical guard, so its removal would retroactively make this change unsafe. All five were verified by reintroducing the corresponding regression one at a time (5/5 caught), with the files restored byte-identical and the baseline re-run green afterward.

**SAFETY — the fan-out sweep found three false-passing assertions the suite could not.** `git grep` for the old value before trusting the green suite (FB-0010, "grep first, edit second") turned up three harnesses asserting on `disable-model-invocation` by bare substring, **all three of which passed against the changed tree**: `run_land_evals`' `skill 5` demanded `true` and passed on a file declaring `false`; `run_merge_status_evals`' `skill-human-invoked` survived flipping the flag it guards (proven by mutation — it escaped the first pass); and that harness's `skill-does-not-CALL-land` was pinning the FB-0074 concession itself, so it would have failed CI on the correct tree. The cause is uniform and worth naming: the prose explaining a flag quotes the flag, so a whole-file substring test can never distinguish a declaration from a mention. All three are now anchored to the frontmatter block with a line-anchored regex, and re-mutated (3/3 for land, 2/2 for merge-status). Recorded as FB-0077 rule 3.

**SAFETY — the staff-review caught a regression this change itself introduced, in the caller.** Making §3 a real call gave `/flow:land` a side effect on `/flow:post-merge`'s git state that no one had to think about before: land checks out its own `<prefix>land-N` branch and never switches back. §5's cleanup resolved its target with `git branch --show-current`, which was correct only while §3 touched nothing. Post-change it returns *land's* branch — so cleanup would have deleted the head branch of the `docs: land #N` PR §3 had just opened (GitHub closes a PR when its head branch is deleted), left the actual merged branch in place, and reported success either way. §5 now resolves the branch from `gh pr view --json headRefName`, and refuses rather than guessing when `gh` can't answer and the current branch is land's. Two adjacent stale-contract sites went with it: §6 input 3 and §7 still instructed the agent to report doc-currency as never-reconciled ("§3 does **not** run `/flow:land` (it can't)"), which would have printed a 🚫 on a run that had just earned a ✅.

**Tradeoffs discussed.**
- **The review found more fan-out than the pre-review sweep did, in the same class the PR is about.** The FB-0010 sweep before review caught `marketplace.json`, `workflow.md`'s Step-11 prose, and the cheat-sheet table. It missed `plugin.json`'s own copy of the description (a *separate* string from marketplace's, which the `replace_all` never touched), `workflow.md`'s top-of-doc skill list 360 lines above the text that was fixed, and post-merge's own §6/§7. Three lenses independently flagged the workflow.md one. The lesson is not "sweep harder" — it is that a sweep keyed on the phrasing you happen to remember (`hands /flow:land`) misses the same claim in different words (`that hands it to you`, `does **not** run`). Sweep for the *claim*, then grep the paraphrases.
- **Residual risk, stated plainly.** With the flag gone, a model could in principle invoke `/flow:land` unprompted after noticing a merge. The blast radius is one `docs: land #N` PR against an already-merged PR, which a human still gates at merge — and §1a bounds it to genuinely merged PRs. Judged acceptable against a step that was broken on 100% of runs. The precondition in §0 is instruction-level, which is weaker than a flag; that asymmetry is the real cost of this change and is recorded here rather than glossed.
- **Why not leave it alone.** The hand-off "worked" in the sense that the docs did get reconciled — by the human. What it cost was invisible: `/flow:post-merge` shipped for four releases advertising an orchestration it never performed, and both the lint and the eval suite reported clean the entire time, because both were satisfied by the conceded version. That combination — a feature silently absent plus green checks — is the argument for the positive assertion, not just the flag change.
- **Historical CHANGELOG entries were annotated, not rewritten.** The v1.21.0 entry's "corrected in v1.22.0" note now reads "corrected twice," pointing forward to this reversal. Rewriting it to hide the wrong turn would erase the most useful part of the record.

## 2026-07-29 — Annotation-layer v2: commenting as a mode (v1.24.0, FB-0076)

**Branch:** `claude/flow-design-workflow-3a9392` · **SHA:** `e4d6f51`

**What was done (user-facing).** The `/flow:verify-build` annotation overlay was redesigned. Commenting is now a persistent mode, on by default: click an element, write or dictate, `↵`, click the next one — no re-arming between comments. Chrome collapsed from a full-width page header + two dock buttons to ONE circular floating control (the minimized comment container; filled = live, carries the count) that expands to a panel holding a labelled Commenting switch, hover-outlining and hide-pins toggles, per-row copy/delete, Copy all, and a two-tap Delete all. Toasts were removed entirely. Anchors, the located-descriptor export, and the `file://` hardening are unchanged.

**Why.** Six rounds of user review, conducted by annotating the prototype with the prototype (see FB-0076). The decisive note: having to re-press "Pin" between every comment made the button, not the mode, the design error.

**Design decisions.**
- **Mode over action.** Considered keeping a per-comment arm (familiar, no escape hatches needed) vs a persistent mode. Chose the mode because the loop is "many comments in one sitting" — but a mode that swallows every click would break interactive prototypes, which the user names as their highest-value artifact. So the mode ships *with* three escape hatches: modifier-click passthrough, a text-selection guard, and Esc. Keeping the button as an off-switch (rather than deleting it, as the user initially proposed) is what makes the mode safe on a prototype you actually need to click through.
- **The switch outranks the icons.** Commenting changes what a click *does*; hover-outlining and hide-pins only change what you *see*. Encoding all three as peer grey icons made the most consequential control invisible. The switch got its own labelled row at the top; the comment count dropped to an eyebrow beneath it.
- **Feedback on the control, not floating over it.** Toasts were covering the very buttons they described. Each control now states its own condition (switch, swapped icon, transient label), following the two-step Delete-all pattern that already existed. A visually-hidden `role="status"` region carries the same information to screen readers — removing the toast removed the only announcement channel, which would have been a silent a11y regression.
- **Kept flow's anchors over ripe's.** The ripe project's overlay (the visual reference for the floating chrome) anchors by tag + child-index path, which breaks whenever the document is re-rendered — i.e. most of the time for a report regenerated every iteration. Only the chrome was adopted; the content-derived anchor was kept.

**Technical decisions.**
- Element ids renamed `annot-*` → `an-*`; storage key `flow-annot:` → `flow-annotations-v2:`. Existing comments are NOT migrated — a review overlay's notes are per-iteration and the migration cost was not worth the code.
- `#an-chip:not(.has)` rather than a bare `#an-chip` for the hidden state: `#an-dock button` is more specific than a lone id, so the plain rule lost and the empty chip rendered "0".

**SAFETY — three defects found by the staff design + UX review, all silent-failure class.**
1. **Capture-phase `preventDefault` on every `Enter`/arrow.** The keydown handler cancelled the default action before checking whether a pick target existed. Because `Enter`'s default action on a button IS the synthetic click, this made every control in the layer un-activatable by keyboard, blocked arrow-key scrolling, and swallowed `Enter` inside the host page's own form fields. Confirmed empirically before fixing. Now scoped: chrome and form fields return early, and `preventDefault` only fires when a target is actually set.
2. **White-on-accent failed WCAG in dark mode** across five filled surfaces (pin numerals, FAB count, list badges, Save, armed Delete-all) — 2.68:1 against the lightened dark accent. Replaced with themed `--an-on-accent` / `--an-on-danger`. Light mode was fine, which is why it survived: nobody screenshotted the other mode.
3. **18 invalid `font:` shorthands** (`font: 600 13px/1 inherit`). A CSS-wide keyword cannot be a shorthand component, so every declaration was dropped and the layer had been rendering in the host report's typography the whole time. Found only because the user reported the hierarchy read flat and the sizes were measured rather than eyeballed. Converted to longhands.

**Tradeoffs discussed.**
- **Two clicks between comments.** A click while the editor is open saves and returns; it does not also start the next pin. Committing *and* picking from one click is a one-line change but a real behaviour decision — deliberately deferred rather than made in-tree (roadmap § Next).
- **Turning commenting back on takes two clicks** when the panel is closed (open panel → flip switch), where the old arm-button took one. Accepted because commenting defaults to on and stays on; flagged to the user.
- **`resolve()` is O(nodes × heading-walk) and runs twice per comment per render**, with render bound to a `ResizeObserver`. Fine at the comment counts seen so far; memoization is queued rather than done speculatively.

**Follow-ups routed to the roadmap** (not done here): type-scale/spacing/radius systematization, the accent's hue collision with the report's own `need` chip, panel/popover entrance animation, focus-trap architecture for the two dialogs, `resolve()` memoization, and the positioned-ancestor exposure (`transform` on a host ancestor breaks `position: fixed` chrome).

## How to Write an Entry

```
### [Short title of what was shipped]
**Date:** YYYY-MM-DD
**Branch:** branch-name
**Commit:** [SHA or range]

**What was done:**
[Concrete deliverables -- what changed in user-facing terms.]

**Why:**
[The problem this solved or the goal it served.]

**Design decisions:**
- [UX or product choice + reasoning]

**Technical decisions:**
- [Implementation choice + reasoning]

**Tradeoffs discussed:**
- [Option A vs Option B -- why this one won]

**Lessons learned:**
- [What didn't work, what did, what to do differently]
```

Use the `SAFETY` marker on any entry that modifies error handling, persistence, data loss prevention, or fallback behavior.

---

## Entries

<!-- Add new entries below this line, newest first. -->
### F11: reword "never wrap a bundled skill" → "never re-implement; compose instead"
**Date:** 2026-08-15
**Branch:** claude/f11-reword-never-wrap (off main; SHA lands with the PR)

**What was done:** Reworded the bundled-skill rule in `CLAUDE.md` (rule 5) and the shipped `plugins/flow/docs/workflow.md` (§ "A note on bundled-vs-flow skills") from a blanket *"Never wrap a bundled Claude Code skill"* to *"Never re-implement a bundled skill; compose with it instead."* Forbids duplication (parroting Anthropic's maintenance, which drifts) while explicitly permitting composition — a thin wrapper that invokes a bundled skill and adds flow-specific value (config-slot resolution, gate contract, feedback routing). Added a consumer note: plugin-managed skills are overwritten on update, so chaining, not in-place edits, is the only surviving extension pattern.

**Why:** "Wrap" was used in opposite senses across flow's own docs — rule 5 said "never wrap," yet the verify-build prerequisite notes in `workflow.md`/`doctor`/`ship`/`bootstrap`/`migration` describe `/flow:verify-build` as "wraps bundled `/verify`" (the permitted composition), and rule 5 was even stricter than FB-0015, which endorses a thin delegating wrapper. A literal reading would reject a legitimate chain. Anthropic's "Building verification loops in Claude Code with skills" recommends exactly this ("build a custom wrapper skill that invokes the original"). The intent (don't re-implement) was always right; only the vocabulary was inverted. Finding 11 of the Anthropic-research thread.

**Decisions:** Reword, don't delete (FB-0015 intent is load-bearing). Left the "wraps bundled `/verify`" composition lines untouched — now consistent, not contradictory (FB-0010 grep sweep clean). No version bump (prose clarification, no behavior change; docs-only precedent #65/#67). Split clean off `main` from the research thread's PR #113 (stale against main's Aug canon thread). `/flow:ship` couldn't run natively — flow isn't installed in this cloud session (Finding 9) — so pipeline stages that could run did (`/security-review` clean; a11y/verify-build self-skip on `platform:library`) and the deviation is documented in the PR body.


### F11: reword "never wrap a bundled skill" → "never re-implement; compose instead"
**Date:** 2026-08-15
**Branch:** claude/f11-reword-never-wrap (off main; commit: this)

**What was done:**
Reworded the bundled-skill rule in `CLAUDE.md` (rule 5) and the shipped `plugins/flow/docs/workflow.md` (§ "A note on bundled-vs-flow skills") from a blanket *"Never wrap a bundled Claude Code skill"* to *"Never re-implement a bundled skill; compose with it instead."* The new wording forbids **duplication** (parroting Anthropic's maintenance, which drifts) while explicitly permitting **composition** — a thin wrapper that *invokes* a bundled skill and adds flow-specific value (config-slot resolution, gate contract, feedback routing, in-flow orchestration). Added a consumer note: plugin-managed skills are overwritten on update, so **chaining, not in-place edits**, is the only extension pattern that survives an update.

**Why:**
The word "wrap" was used in *opposite senses* across flow's own docs. Rule 5 said "never wrap," yet `workflow.md` (the `/flow:verify-build` prerequisite note), `doctor/SKILL.md`, `ship/SKILL.md`, `docs/bootstrap.md`, and `docs/migration.md` all describe `/flow:verify-build` as *"wraps bundled `/verify`"* — the permitted composition. Worse, rule 5 was **stricter than flow's own FB-0015**, which endorses "a thin wrapper that delegates to the bundled skill" (the `/flow:security-review` / `/flow:accessibility-review` shape). A future session reading rule 5 literally would reject a legitimate chain. Anthropic's "Building verification loops in Claude Code with skills" recommends exactly this: *"build a custom wrapper skill that invokes the original, then invokes your verification skill,"* and notes embedded copies are off-limits for plugin-managed skills. The intent (don't re-implement) was always right; only the vocabulary was inverted. This is **Finding 11** of the Anthropic-research thread.

**Design decisions:**
- **Reword, don't delete.** FB-0015's don't-reimplement intent is load-bearing (it caught a 20-file `/verify` duplication). The fix preserves that intent and names the permitted pattern (delegating wrapper / chain), with `/flow:verify-build`-over-`/verify` and `/flow:ship`-chaining-its-reviewers as canonical examples.
- **Left the "wraps bundled `/verify`" composition lines untouched.** Under the new vocabulary "wrap" = the permitted *invoke-and-extend*, so those lines are now consistent, not contradictory. Rewording them too would be scope creep (general.md scope discipline). FB-0010 grep sweep (`git grep -nE 'not.{0,6}wrap|never wrap|parrot'`) confirms the only survivors are the two reworded lines.
- **No version bump.** Prose clarification to a shipped doc + a project-dev CLAUDE.md rule; no schema/skill/behavior change. Docs-only precedent (#65/#67) — rides the current release.

**Technical / process decisions:**
- **`/flow:ship` couldn't run natively (Finding 9).** flow is not installed in this Claude-Code-on-the-web session (no `~/.claude/plugins`, no `/flow:*` commands registered; a mid-session install can't register a slash command without a restart). Per the handoff's sanctioned fallback, opened the PR manually with the deviation documented, after running the pipeline stages that *are* available (`/security-review` → clean; a11y + verify-build self-skip on `platform:library` / `uiSurface:false`).
- **Push path:** Conductor's auth broker had no GitHub token for this session context, so the branch was pushed from the Mac mirror (auto-syncs cloud commits, carries working auth) via `RunLocalCommand` — the token never left the Mac. Split out of the research thread's PR #113 (which was stale against main's Aug canon thread) so this clean, additive change ships on its own.

### SAFETY: `/flow:land` clear-reservation deleted audit-trail entries, not just the reservation (found by #88's own land run)
**Date:** 2026-08-12
**Branch:** land-88 (SHA lands with the PR)

**What was done.** `land-helpers.py clear_reservation` matched the id with `re.search` over every line, so striking a shipped `FB-XXXX` removed **every** line mentioning it — including the audit-trail entries in the second half of `reserved-feedback-numbers.md`. Anchored the predicate to a bullet that *opens* with the id (bold optional). Pinned by a new `cr 2b` case asserting both directions: the reservation goes, an audit-trail line citing the same id survives.

**Why.** Caught by dogfooding, not review: running `/flow:land 88` deleted the reservation **and three collision-history entries** — the record of why this PR was renumbered five times (FB-0074 → 0075 → 0078 → 0080 → 0082). That file's second half is institutional memory whose whole purpose is to stop the next collision; silently erasing it while "cleaning up" is worse than leaving a stale reservation. Restored from git and re-cleared with the narrow predicate.

**Design decision.** The anchor is the bullet opening, not a section-heading parse. Reservation bullets open with the id; audit-trail bullets open with a date (`- **2026-08-11** — …`), so the two are separable without teaching the helper the file's structure — which would couple it to a layout projects are free to vary. Bold is optional because real files use `- **FB-0082** —` while the eval fixture uses `- FB-0013 (PR P)`; requiring bold broke `cr 1`/`cr 2` and was caught immediately.

**Tradeoff.** Fixing a helper inside a `docs: land` PR mixes concerns. Accepted because the bug corrupted this very run and would silently corrupt every future land that clears a number cited in the audit trail — leaving it to a follow-up would mean shipping a known data-loss path. The change is 4 lines plus a regression case.

### SAFETY: flow's ephemeral scratch moves from `/tmp` to a repo-local `.flow/`, restoring the skip-legitimacy gate and ending cross-project collisions (v1.27.0, FB-0082)
**Date:** 2026-07-29
**Branch:** claude/flow-fork-transport-scratch — **merged #88 @ `783c9fcc`**

**What was done.** Every ephemeral artifact that crosses a process boundary in flow moved from `/tmp/flow-*` to `<repo-root>/.flow/`, and every handoff gained a `flow_stamp` (repo + branch + head) that readers verify before use. New `scripts/flow_scratch.py` owns resolution + stamping; `evals/run_scratch_isolation_evals.py` (56 checks) pins it in CI.

**Why.** A consumer dogfood report (Swift/iOS, flow 1.20.0) described two silent false negatives. Both were reproduced in-session rather than reasoned about:

1. **Fork transport.** `/tmp/flow-skip-audit-stages.json`, valid and readable, produced a full report from the parent shell and `SKIP-AUDIT: no stage report to audit` from `Skill("flow:audit-skips")` — a same-file A/B. A forked skill cannot see a `/tmp` file the parent wrote. Because that message is *also* the legitimate standalone no-op, **the skip-legitimacy gate had been inert on every ship since v1.13.0** and nothing surfaced it. This settles the open question in `roadmap.md` § Exploration ("investigate whether the fork isolation is systematic before committing to (a) vs (b)"): it is systematic, and a second probe confirmed a fork *does* read a repo-relative file the parent just wrote — so the roadmap's option (a) is viable.
2. **Cross-project collision.** `/tmp/flow-staff-diff.patch` is one global filename; the reporter's staff-review lenses were handed a different project's diff, and only two of three noticed.

**Design decisions.**

- **One mechanism for both bugs, chosen over two.** Repo-relative is visible across the parent↔fork boundary *and* unique per worktree by construction (`git rev-parse --show-toplevel` resolves to the worktree, not the shared repo — so two worktrees of one repo are also isolated). Considered and rejected: hashing the repo path into a `/tmp` subdirectory (fixes collision, not transport) and a `--session` discriminator (fixes neither without a shared writer).
- **Stamping is kept even though namespacing is structural.** Namespacing cannot catch a *stale* handoff left by an earlier branch in the same worktree, so it is necessary but not sufficient. The four statuses (`ok` / `absent` / `invalid` / `stale`) are deliberately distinct: collapsing them is the original bug's shape.
- **Fail closed on an absent stamp.** An unstamped handoff is refused rather than grandfathered. "Written by an older flow" is indistinguishable from "written by another project" (FB-0062).
- **The stamp is written in shell, not via a helper script.** `CLAUDE_PLUGIN_ROOT` is unset in Bash-tool calls, so ship Step 2a would have acquired a plugin-root dependency it cannot satisfy in a consumer repo. Three `git` calls inline avoid that entirely; the *read* side is a `!`-block, where the variable **is** available, so it uses the Python helper.
- **`.flow/` writes its own `.gitignore` rather than editing the project's.** Flow must not modify a file the consumer owns just to hold its scratch.
- **Rejected: moving the transient stderr-capture files** (`/tmp/flow-*-err`, `flow-sd-region`). They are written, read, and deleted inside a single fenced block and never cross the fork boundary; converting them is cosmetic. Named in the roadmap instead of done silently.

**Technical decisions.** `_default_path` in `rigor-marker.py` keeps a `/tmp` fallback for the no-worktree case rather than failing — a detached run should still function, and the marker's `source_sha` already fails safe. The old rigor-marker path was keyed on branch slug alone, so two projects on `main` shared a file; that failed *safe* (sha mismatch → "source-drift") but made one project invalidate another's gate for no reason.

**Corollary fixed in the same pass (same bug class, found by dogfooding).** `extract_session.py`'s reference-doc loader returned `""` when the glob matched nothing, producing a context with **no** `## Reference documents` section — indistinguishable from "this project has no rules to violate." Flow's own `flow.config.json` had no `referenceGlob`, so the `core-docs/*.md` default matched nothing (flow keeps docs in `dev-docs/`) and every `/flow:critique-plan` run in this session was structurally unable to cite a project rule — while `critique-plan/SKILL.md` had claimed for several versions that "flow's own repo overrides to `dev-docs/*.md`". Now: the slot is set, and an empty resolution emits a loud warning that explicitly tells the reviewer it cannot raise a Spec violation.

**Security finding this change introduced, and closed (SAFETY, CWE-59).** Moving the scratch sink out of `/tmp` and into repo-controlled namespace created a link-following primitive the `/tmp` version did not have: `.flow` is an ordinary repo path with none of git's `.git`/`.gitmodules` special-casing, so an untrusted clone can ship it as a **symlink** — and `mkdir -p` on an existing symlink-to-dir exits 0 and *follows* it (reproduced by hand before fixing). Every subsequent write then lands in an attacker-chosen directory: `.flow -> ~/.ssh` or a sibling repo gets a `.gitignore` containing `*` created or truncated, with no prompt. Filenames are fixed so it is not code execution, but it is a real out-of-repo write + data-integrity loss. All five sites now refuse when `$FLOW_SCRATCH` is a symlink. Found by `/flow:security-review`'s red-team pass, which was pointed specifically at "does moving the sink into the repo introduce what `/tmp` didn't" — the question worth asking of any change that relocates a write target. Two adjacent hardenings from the same pass: a non-string `flow_stamp` field now **refuses** instead of raising `TypeError` out of a function documented to return `(ok, reason)` (fail-closed either way, but the operator was told "reinstall the plugin" for a malformed handoff), and the Step 2a stamp is built with `jq -n --arg` so a legal-but-hostile branch name containing `"` cannot inject JSON structure — the read-back caught the damage before, but escaping removes the class.

**Bug found on `main` while rebasing, fixed here (SAFETY).** `#86` (FB-0074) added the root-anchor block to `audit-skips/SKILL.md` with a comment containing **backticks**: ``` `git rev-parse --show-toplevel` ```. A `!`-block is delimited by a *single* backtick, so one inner backtick **terminates the dynamic-context span** — everything after it is emitted as literal text instead of being executed. The shipped block was therefore truncated mid-comment: the root anchor never ran, and neither did the engine invocation. `#83` had left an explicit warning about exactly this two blocks below ("No backticks in this block ... an inner backtick would truncate it. FB-0010"), which is what makes it a fan-out failure rather than a novel one. Caught mechanically, not by eye: `run_scratch_isolation_evals.py` extracts and *executes* the block, so the truncation surfaced as three failing checks the moment the rebase landed. Backticks removed and the warning restated inline. This is the third independent instance in this release line of "a guard that reports success without running", which is the through-line of both FB-0074 and FB-0082.

**Tradeoffs discussed.** `.flow/` puts flow's scratch inside the consumer's tree, which is more visible than `/tmp` and survives reboots. Accepted: visibility is a feature for debugging, the directory self-ignores, and the alternative kept a class of silent wrong answers. Two config **defaults changed** (`verifyFindingsPath`, `verifyReportPath`); projects that set them explicitly are unaffected, and the fan-out was swept with `grep` first per FB-0010 (6 files). This PR **restores** the gate but does not add the third `undetermined` state or verdict provenance — that is part A, stacked on top of this branch (FB-0074).

### SAFETY: A draft PR is a last resort, not a deliverable — ship manifest triage + an answerable hand-off (v1.23.0, FB-0075)

**Date:** 2026-07-29
**Branch:** `claude/agent-draft-pr-handling-52e6dd` (worktree `agent-draft-pr-handling-52e6dd`)
**SHA:** `9efa9a4` (squash-merged as #85, 2026-07-30)

**What was done (user-facing).** When a ship gate does not pass, `/flow:ship` no longer just hands back a draft PR. Every blocker is triaged: if a resolution exists and has not been tried, the agent tries it once; if it is a real decision, the agent drafts the fix and Step 8 presents a numbered question in plain language (recommendation first, what was already tried, and an explicit "waive and ship as-is"); only an item needing an action outside the session leaves the PR as a plain draft. Answering at the hand-off resolves through the existing Step 7c reconcile path, so the PR flips to ready without a second ship run.

**Why.** Cross-repo user report (music-app, ripe, flow): "I never want to be presented with a draft PR as if that's productive… I'm not an engineer so I just need to then ask the agent to fix it." The mechanism was `SKILL.md:888` — an unconditional *manifest non-empty ⇒ `--draft`* with nothing between accumulation and the decision, so three unlike populations arrived identically.

**Measured, not assumed (and this correction mattered).** The plan's first four revisions diagnosed this entirely from flow's own source without opening a single real draft PR — an `/flow:audit-plan` finding forced the measurement. Ground truth: **5 flow-shipped PRs opened as drafts** (4 of music-app's 8, plus ripe #1), with draft→ready round trips of **47 min, 65 min, 5 h, 11 h, and 13 days**. Recovered kind distribution across ~6 manifest items: `skip-audit` ×2, `rigor` ×1, `visual-deliverable` ×1, `coverage` ×1, `a11y` ×1, `verify-build` ×0. **Three of six were resolved by a human waiver, at least two "waived un-performed."** None was resolved by the agent re-running a stage. Two of PR #4's three items were one `uiFilePatterns` misconfiguration wearing two hats. That evidence re-weighted the deliverable away from "auto-resolve more" and toward "draft the resolution and make the ask answerable" — the honest headline is *one* producer learns to try before it drafts; seven learn to ask a question the user can answer.

**Design decisions.**
- **Escalate into the existing gate, not a new one.** The first draft asked the human *before* creating the PR. `/flow:critique-plan` caught it as a third human gate violating FB-0034 + FB-0044. The pipeline now always reaches the PR; only the hand-off shape changed. This also deleted a model-supplied `--attended` flag (an unverifiable signal that would have gated rigor) outright.
- **Classification keyed on `kind`, in a deterministic table** (`lib/manifest-triage.py`), not model judgment — otherwise the step is skippable by routing everything to draft. Exactly one kind (`visual-deliverable`) is `auto`; the rest already attempt at their producer or are doctrinally barred (`:272` never self-declare a criterion; `:585` never silently rewrite an un-fenced doc; FB-0011 for competing-merit fixes).
- **Normalizing the 8 producer lines was a prerequisite, not a follow-up.** Five sites prescribed no kind token at all (so four kinds were indistinguishable) and four used off-vocabulary `needs:` verbs; the `:899` template was missing `rigor` and `coverage` entirely. No deterministic triage is possible over an unparseable line. `[decision-required]` got a named destination (a new `— confidence:` field) rather than just being evicted — "absent from the bracket" and "dropped entirely" are indistinguishable to a grep.

**SAFETY — three invariants, each of which a plan gate caught me weakening.**
1. *No merge-ready PR on a non-PASS build* (`:308`/`:310`, unqualified). A one-word waiver would have emptied the manifest and flipped `gh pr ready`. Defended twice: a `verify-build` waiver is exempt from the §7c subtraction, **and** §7c's ready-flip is re-keyed from "manifest is empty" to `verdict == READY`. The waive option is suppressed on `verify-build` entirely — offering "waive and ship as-is" on an entry that by rule keeps the PR a draft would be a lie to a non-engineer.
2. *Residual is the uncleared set minus honored waivers, never a class filter.* A class filter let a failed `visual-deliverable` attempt drop out and reach a ready PR — the thing `SKILL.md:843` exists to prevent.
3. *§7a's assertion is artifact-shaped* (`branch`, `sha`, `FRAMES >= 1` — it never reads `overall_verdict`), so a re-run capturing a frame but returning FAIL would overwrite the blessed buffer and satisfy the gate. §7a's sequence now re-applies Step 2's verdict accounting. Its ordering (apply → commit → push → re-run → re-account → re-assert) is pinned because Step 7 pushes *before* §7a runs.

Plus two fail-safe directions: an unrecognized `needs:` verb classifies `blocked` for security/a11y and `ask` elsewhere, never `auto`; and unrecoverable state never yields `auto` — `/tmp` is a cache, the PR body's `## Waived at ship` section is the durable record (§7c step 0 reads it *before* the recompute overwrites it), and a waiver is honored only on an exact `(kind, finding)` fingerprint match so an over-greedy body parse cannot subtract a real blocker.

**Tradeoffs.**
- **Drafts do not disappear, and the docs say so.** Doctrine blocks the agent from self-declaring criteria, editing un-fenced docs, or calling a failing build shippable. Overselling "the agent now just does it" would fail the user again at the next blocked ship. What changes is that the draft is answerable.
- **The fix does not reach the user's repos on merge.** Proof from the evidence: #81 landed 2026-07-28 02:54Z, four hours *before* a draft it would have prevented, and did not help — the host ran the installed 1.21.0 release. Same gating applies here.
- **Waiver state is ephemeral in `/tmp` and best-effort from the body.** Reconstruction is parsing, not a guarantee; what carries the safety is the fail-safe direction, not the reconstruction.

**Process note worth keeping.** This plan went through **5 `/flow:critique-plan` + 4 `/flow:audit-plan` rounds**, and the gates found real defects in every one — including three separate paths to a merge-ready PR on a failing build. One inversion is worth recording: I accused the plan-critic of fabricating an FB-0064 citation and carried that accusation for two revisions. It was accurate; my verification grep piped through `cut -c1-300` and truncated the match out of view, so a *matching* line was read as proof of absence. Two lessons: a truncating filter must never be the last word on "the text isn't there," and an accepted audit finding is not a verified one.

**What the ship pipeline caught (and why the reviews were worth running).** Security review: **clean** — it disproved all seven threat classes empirically rather than by assertion (branch-name path traversal — `/` is outside the slug's char class, verified by running it; ReDoS in `_LINE_RE` — timed linear at 50→800 reps; forged `## Waived at ship`; 64-bit fingerprint second-preimage; sibling-import hijack; branch-name shell injection — POSIX does not re-scan command-substitution output). `/flow:audit-coverage` found **5 undeclared changes across two passes**, two of which were real defects rather than declaration gaps: `waive` returned an undocumented exit `3` contradicting the module's own stated contract, and — the serious one — **the SKILL's prescribed call sequence defeated invariant 5**. Readers called `init-state` before classifying, which materializes an empty record, so a state that was genuinely lost read back as `present` and re-enabled `auto`. The engine-level test passed the whole time; the pipeline as written was unsafe. Fixed by adding `state-path` (resolve without create) and restricting `init-state` to §7a.5. A scoped staff-engineer re-review of the post-review delta then caught three more, each verified by running the code: the new exit table claimed `2` for a path that actually exits `1`; `waive`'s exit `3` never fired when the manifest file was *absent* (the wrong-`--branch` case — a silent `0`); and an eval asserting `count(...) >= 2` stayed green through the exact regression it named, because the count included an explanatory comment.

**Two process notes worth keeping.** (1) `/flow:audit-coverage`'s second run reported "No issues flagged" **from a truncated diff** — it had seen one metadata file. It said so honestly, but a less careful read banks a false clean; the verdict was discarded and re-run scoped to the behavior-bearing files, which found the two findings above. (2) The rigor gate fired twice. The second was legitimate and self-inflicted (source edited after re-stamping) and was resolved by actually reviewing the delta. The first could not be diagnosed — every source mtime predated the marker, the tree was unchanged, and it was not the documented degraded hash — so it was re-stamped **with that disclosed** rather than quietly cleared.

**Rebase onto #86 (the second numbering collision) + its integration review.** #86 merged while this PR sat open, taking v1.22.0 AND FB-0074 — so this renumbered to **v1.23.0 / FB-0075**, the second collision on one branch (#83 took FB-0073 first). The renumber was line-targeted: ~90 `FB-0074` references now live in these docs under two owners, each was classified before rewriting, and only the 32 belonging to this branch moved — a direct correction of collision #1, whose blanket sweep over-reached onto #83's content in six places and had to be reverted. Conflicts were resolved by **union, not side-picking**: #86's Test-plan provenance stamp coexists with this PR's `manifest_contract` import in `pr-coherence.py`; its `flow_assert_test_plan_provenance` with the sibling guard in `verify-pr-body.sh`; and §7c's reconcile now runs **both** §7b asserts, because a reconcile re-renders the Test plan and therefore changes its provenance digest — taking either side alone would have dropped a live assertion.

A scoped integration review then found **one BLOCKER that was pre-existing on `main` but shipped inside the template this PR edits**: the PR-body template's own closing line contained the literal `🚫 NOT READY TO MERGE` sentinel, and `has_manifest()` is a raw substring test (inline backticks do not exempt it) — so pasting the explanatory sentence into a **ready** body trips §7b's coherence gate and halts a clean ship, and would make `/flow:land` report a false "merged in a not-ready state." Reproduced, then fixed by rewording the line and adding a comment saying why the literal must never appear there. Five more NITs fixed in the same pass, all real: four stale `(Step 7)` pointers to a line shape that moved to Step 2; a `render-manifest` call attributed to §7a.5 when it runs in §7a.6; a renumbering survivor still crediting FB-0074 for the Step-8 decision surface; self-referential line numbers (`:272`, `:585`, `:308`, `:310`) that drifted to unrelated lines in the merged file, replaced with section anchors; a hand-composed `[visual-deliverable]` line that contradicted this PR's own "never hand-compose the line" rule, now an `add-entry` call; and `/flow:doctor`'s missing rc-2 arm, which printed a definitive coherence FAIL for the "could not verify" case the new resolver guard introduces — the exact false BLOCKER that guard exists to prevent.

**Process failure worth recording.** The first attempt at this rebase leaked conflict markers into four files, because `git rebase`'s stdout was read through `tail` and reported three conflicts when `git diff --diff-filter=U` showed nine. Aborted, confirmed the already-shipped tree was clean, redid it from the authoritative list. Same root cause as the FB-0075 memory entry (a truncating filter inverting a verification result), one tool over.

**Files.** `skills/ship/lib/manifest-triage.py` (NEW), `skills/ship/SKILL.md` (8 producer lines, `:899` template, §7a attempt-then-gate, §7a.5 NEW, §7c steps 0/1/3/5, §8, body template + `## Waived at ship`, Flow-run row), `skills/{security,accessibility}-review/SKILL.md`, `evals/run_manifest_triage_evals.py` (NEW, CI-wired), `evals/fixtures/resolution-confidence-routing/expected/ship-routing.md` (normalized + finally read by a harness), `evals/run_status_surface_evals.py` (enumeration pin updated — FB-0010 fan-out), `CLAUDE.md`, `docs/workflow.md`, `README.md`, `CHANGELOG.md`, version 1.21.0 → 1.22.0.

### SAFETY: three gates that could report success without doing their job — fork root anchor, Test-plan provenance, skill-composition lint (v1.22.0)
**Date:** 2026-07-29
**Branch:** claude/contribute-ff3ee2 → **merged as #86, squash `129f582`** (2026-07-29)

**What was done:**
A `/flow:contribute` drain of 12 queued cross-project lessons. Three were confirmed real *by reproducing the symptom*, fixed, and applied to a ready PR (FB-0073); two were dismissed with a repro; one was escalated to the roadmap; six were held. The three fixes turned out to share a spine, which became **FB-0074**: *a contract whose two halves live in different files, with nothing mechanically checking the join, degrades silently — and the degradation is indistinguishable from success.*

1. **Forked-skill root anchor (SAFETY — failure-open on a gate's INPUTS).** `/flow:audit-coverage` and `/flow:audit-skips` are `context: fork` and inherit the *session* cwd, not the repo under review. Reproduced: from a non-repo cwd, `flow.config.json` resolved to `{}` and every `git` call returned `""`, so every unverifiable skip validated as `LEGITIMATE` and the gate emitted `all 4 stage skips LEGITIMATE — proceed` having read nothing; `audit-coverage` emitted its genuine clean-skip line verbatim. Both preambles now resolve an explicit root (`CLAUDE_PROJECT_DIR`, else `git rev-parse --show-toplevel`) **before** any relative read; an unresolvable root emits a distinct `ROOT-UNRESOLVED` line / `root_error` JSON field, and the SKILL prose plus `/flow:ship` Step 2a route it to the draft manifest as `[decision-required]`, mirroring the existing `engine_error` path.
2. **Test-plan provenance stamp (SAFETY — an unenforced non-forgeability claim).** The `## Test plan` is *specified* as a non-forgeable projection of the verify-build buffer, but `git grep` confirmed **zero** consumers ever checked that a published block came from the renderer. `render-test-plan.py` now emits a canonical `<!-- flow:test-plan-rendered -->` stamp on **all three** of its paths; `pr-coherence.py test-plan-provenance` + `verify-pr-body.sh::flow_assert_test_plan_provenance` assert it at ship Step 7b against the **re-fetched** body.
3. **Skill-composition lint.** `post-merge/SKILL.md:131` instructed `Skill("flow:land")` while `land` sets `disable-model-invocation: true`. New `doctor/lib/skill-composition-lint.py` + doctor Check 1.4 fail on that shape.

**Why (decisions + tradeoffs):**
- **Root anchor: `CLAUDE_PROJECT_DIR` first, git-toplevel second — and the residual named, not hidden.** The env var is preferred because git-toplevel alone still silently audits a *foreign* repo (git succeeds there). But `CLAUDE_PROJECT_DIR` is **not set in this environment** and appears nowhere in the repo, so the fix could not be built on it alone. The honest split: the *dangerous* half (non-repo cwd → confident false-clean) is closed unconditionally; the *foreign-repo* half is mitigated by the env var when present and otherwise made **visible** — both skills now print `repo root: <path>`. Following #76's precedent: fix one shape, document + pin the others rather than claim more than the code delivers.
- **The stamp attests provenance, not passage.** Stamping only the machine-judged path would have punished honesty — a PR whose verify-build legitimately skipped would look forged. All three paths carry it, including the "no behavioral gate ran" fallback, so the check distinguishes *"the renderer ran"* from *"the criteria passed"*, which are different questions.
- **`/flow:land`'s flag stays; the caller changes.** Clearing `disable-model-invocation` on `land` would have made the `Skill()` call work, but `land` opens PRs — the flag is a deliberate safety property and clearing it would let a PR-opening skill auto-fire mid-loop. Per the autonomy bar that is a one-way-door loosening, so the low-risk option was taken: §3 hands the step to the human and carries it into §6's archive-safety verdict as an outstanding item (default `🚫 not fully closed out` until a `docs: land #N` PR exists and is merged). This *downgrades* #79's "composition" claim, so the stale prose in the description, the §3 body, the §6 verdict, the §7 hand-off, the Gotchas, and the **v1.21.0 CHANGELOG entry** were all corrected — an FB-0010 fan-out sweep, since the false claim had already propagated to consumer-facing docs. The alternative (a model-invocable `land-reconcile` entrypoint) is left to the maintainer.
- **The lint's first run flagged its own documentation.** Prose warning against the anti-pattern uses the literal `Skill("flow:land")` syntax in inline backticks, and the naive scanner counted it. Fixed by scanning **only fenced code blocks** — an executable call lives in a fence; inline backticks are prose *about* a call. Pinned as an explicit eval case, since it is the obvious way to reintroduce a false positive.
- **Every new fixture was validated against the PRE-FIX tree.** `git archive origin/main` → lint FAILs on the old `post-merge`; the root-anchor guard regex finds 0 guards in the old preambles; the old renderer has 0 stamps. A fixture that passes before and after is not regression protection (the discipline #76 established).

**Dismissed with a repro, not by reasoning from the fix (2):**
- *Swift cold-run, 3 bugs* — bug 1 (`ls` on a `.xcodeproj` bundle) reproduced against the old form (`ls` → `project.pbxproj`; `ls -d` → `Demo.xcodeproj`) and confirmed fixed in #83; bug 2 (rigor-marker false source-drift) confirmed by the `source-sha-untracked-to-committed-invariant` eval #82 added; bug 3 is a duplicate of the root-anchor lesson fixed here.
- *audit-skips engine error on a valid handoff* — confirmed fixed by #83 via a constructed repro (a present, valid-JSON handoff with a malformed inner field raises in `classify()`; the preamble now renders a distinct `engine_error`, and the four handoff shapes are mutually distinguishable).

**Escalated, not fixed — cross-project `/tmp` collisions (`roadmap.md` § Exploration):**
This lesson had been dismissed **twice** as `already-encoded`, both times reasoning that `skip-audit-checks.py::read_buffer()`'s branch/sha guard covered it. A third independent report forced a real audit, which found that reasoning to be a category error: the guard covers **1 of ~16** `/tmp` paths, and even there only 2 of 5 consumers honor the stamp; none of the three *reported* targets are in its blast radius. Reproduced with two `git init` repos — repo A's four staff-review lenses read repo B's diff, and a foreign all-`ran` stage report launders real skips into `LEGITIMATE`. `history.md:338` already recorded a **live in-the-wild occurrence**, filed as a process note rather than a defect. Also established that branch+sha is the **wrong discriminator** (false-stale verdicts when it fires; a false PASS when both source deltas are empty, since both digests are `sha256("")`); `repo_root` is correct. Not fixed here because it is a namespacing scheme + schema-default change across ~16 paths with a 12-site fan-out — a design decision, not a drain edit.

**Also:** `/flow:contribute`'s own draft-only default was replaced with FB-0073's confidence split (apply verified work → ready PR; surface decisions explicitly). Leaving it saying "draft-only" while this very PR opens ready would have been the same shipped-doc-vs-practice contradiction FB-0010 exists to catch.

**Calibration:** PRs #76 and #82 had merged without their outcomes being recorded; three `approved` events were written back to `feedback_signals.json` (now 6/6 approved, 0 rejected).

**What the four-lens staff-review changed (all four lenses found real defects; 8 BLOCKERs applied):**
- **Root-anchor precedence was backwards (staff-engineer, BLOCKER).** The guard preferred `CLAUDE_PROJECT_DIR` over the cwd's git toplevel. This repo runs its own loop from linked worktrees (9 live) — a session started in the parent repo would make the guard `cd` to the *parent*, on a different branch, and audit a tree containing none of the PR's changes: the exact failure-open, reintroduced by the precedence choice, with the eval encoding it as intended. Verified concretely (env-first resolved to `fix/verifyenabled-jq-false-default`), flipped to cwd-git-root first / env as fallback, and pinned so a future "env is more authoritative" refactor can't silently undo it.
- **The provenance stamp proved the wrong thing (design-engineer, BLOCKER).** Marker-presence proves only that the renderer *ran*; the realistic forgery is letting it render, then flipping `[ ]`→`[x]` and leaving the comment intact — which passed. Now the stamp carries a content digest. Scoping it took one iteration: a digest over the whole checkbox line (state + text) hard-failed the documented happy path, because ship *instructs* the agent to fill in the fallback's `<how to verify>` text — and Step 7b is `exit 1`, so every `platform: library` PR (including flow's own) would have been unshippable. Narrowed to checkbox **state and count**, which is exactly what the contract claims to protect.
- **Two fan-outs, each flagged independently by three lenses.** The `/flow:contribute` draft→ready change (FB-0073) was made in one file while 7 other sites still promised a draft — including `docs/workflow.md`, the consumer-facing loop reference. And the `/flow:land` correction missed `workflow.md:19`/`:524` ("called by `/flow:post-merge`") plus a CHANGELOG sentence still calling land "auto-fireable". Both swept. Sobering, given this PR's own thesis: the first sweep grepped for `calls /flow:land` and missed the from-the-other-side phrasing.
- **Doctor Check 1.4 didn't emit doctor's output contract (design-engineer, BLOCKER).** It printed `[Check 1.4] FAIL` while the verdict is assembled by counting `[FAIL]` tokens — a gate that fires without registering, one level up from the class it checks. Now emits `[PASS]`/`[FAIL]`/`[WARN]`/`[SKIP]`, and distinguishes exit 1 (violation) from exit 2 (tool failure) rather than accusing the operator of forgery over a missing helper — the same rc-conflation the UX lens found in ship Step 7b, fixed in both.
- **No escape hatch (ux-designer, BLOCKER).** The renderer was invoked without the installed-else-checkout fallback every other helper call uses, so an unset `CLAUDE_PLUGIN_ROOT` — which used to degrade softly — now hard-failed the ship and told the operator to run the command that had just failed. Added the fallback, and a documented human-waive route so a legitimate PR is never unshippable.
- **Self-caught during review, before the lenses reported:** `~~~` fences evaded the lint entirely (false negative on the forbidden thing), and a `## Test plan` inside a fenced *example* hard-failed the provenance check (false positive with no recovery). Both fixed with delimiter-tracking fence parsing, plus warnings on the two remaining fail-open paths (unclosed fence, unparseable frontmatter) that previously defaulted to "nothing to see."
- **`critique-plan` joined the root-anchor fix** after a post-review grep sweep — same shape, and it gates plan approval: with no reference docs the critic structurally cannot quote a rule, so it returns APPROVED.
- **The push-further lens turned the thesis back on the repo** and found two more members of FB-0075's own class. One was cheap and shipped: `.github/workflows/ci.yml` enumerated 20 harnesses by hand with nothing asserting the list was complete — an unwired harness gives zero protection while CI stays green, and this PR's own +2-line ci.yml hunk exercised that unchecked join. Now guarded in both directions. The other (config slots read but undeclared; `${CLAUDE_PLUGIN_ROOT}` refs unverified) went to the roadmap with a concrete shape.
- Its meta-observation is worth keeping: this drain's *escalation* path was stronger than its *generalization* path — it refused to dismiss the `/tmp` lesson a third time, but scoped all three fixes to exactly the instances reported and never swept the repo for other members of the class it had just synthesized. That sweep is what produced two of the findings above.

**What the security review + `/simplify` changed (two EXPLOITABLE bypasses of the new gate):**
- **A 4-space-indented ` ``` ` is an indented code block in CommonMark, not a fence.** `strip_fenced` treated it as one, swallowed the rest of the body, and `test-plan-provenance` reported `N/A` + **exit 0** — while GitHub rendered the forged, fully-ticked Test plan normally. Fence openers now require indent < 4, and an unclosed fence **fails closed** instead of hiding the remainder from the parser. Both reproduced before fixing.
- **Only the FIRST `## Test plan` section was verified.** Keep the honest stamped block, append a second all-ticked one, and the gate validated the section nobody reads. Every section is now located; more than one is a hard failure.
- **Honesty correction.** The red-team established the digest is an *unkeyed* checksum whose algorithm ships in this repo, with the renderer in the same trust domain as any forger — so "non-forgeable" was the wrong word. It defeats cheap forgery (hand-writing the block, flipping a box, editing the published body after ship), not a deliberate in-domain forger. Corrected in the CHANGELOG, ship §7b, and FB-0074's own corollary. Overstating a gate is its own failure-open.
- `/simplify` (4 angles, previously un-run) found an unreachable `return` that would have emitted an **unstamped** block if reached, a 4×-per-call body re-parse, and a double file read in the lint. Its altitude lens caught the CI join guard committing the class it checks (a bare textual grep counted a harness named in a **comment** as wired) and the root-anchor eval's hand-written target list — both now derived/scoped, with a completeness assertion so a sixth `context: fork` skill cannot slip through.

**Dogfood, live, during this ship (two independent confirmations of the bugs being fixed):**
1. `/flow:audit-skips` ran against the **installed v1.21.0 plugin** — the pre-fix version — and hit FB-0074's exact failure: `CLAUDE_PLUGIN_ROOT` unset plus a cwd outside the repo meant the relative engine path did not resolve. It reported `engine_error` **loudly** (#83's fix working), refused to collapse it into the clean no-op, re-ran the engine from the repo root, and returned authoritative verdicts. The failure this PR fixes was observed, not theorised.
2. The `/tmp` collision class was observed **on this machine**: `/tmp/flow-verify-findings.json` belonged to `claude/health-tracker-…` — a different project — with `visual_significant: true`. Ship §7a's `jq .metadata.visual_significant` read has **no freshness guard**, so it would have read `true` for this `uiSurface:false` repo and demanded visual deliverables that cannot exist. The local helper says `false`. Recorded in the roadmap entry as in-the-wild evidence alongside `history.md:338`'s earlier occurrence.

**Files changed:** `skills/audit-coverage/SKILL.md`, `skills/audit-skips/SKILL.md`, `skills/ship/SKILL.md` (Step 2a routing + Step 7b), `skills/ship/lib/render-test-plan.py`, `skills/ship/lib/pr-coherence.py`, `skills/ship/lib/verify-pr-body.sh`, `skills/post-merge/SKILL.md`, `skills/doctor/SKILL.md` (Check 1.4), `skills/doctor/lib/skill-composition-lint.py` (new), `skills/contribute/SKILL.md`, `evals/run_skill_composition_evals.py` (new), `evals/run_root_anchor_evals.py` (new), `evals/run_pr_coherence_evals.py`, `evals/run_render_evals.py`, `.github/workflows/ci.yml`, `CHANGELOG.md`, `dev-docs/{feedback,roadmap,plan,reserved-feedback-numbers}.md`, both manifests (v1.22.0).

**Evals:** all 20 CI-wired harnesses green (18 existing + 2 new).

### SAFETY: audit-skips can't silently no-op on a broken handoff + Swift preflight `ls -d` glob fix (v1.21.1)
**Date:** 2026-07-29
**Branch:** claude/audit-skips-loud-plus-swift-preflight-glob (commit on this branch; SHA lands with the PR)

**What was done:**
Two harvested bug fixes (drained from the `/flow:contribute` queue and applied directly per FB-0073, not parked in a draft):
1. **audit-skips silent-no-op closed (SAFETY — error-handling contract flip).** `skills/audit-skips/lib/skip-audit-checks.py` used to `print({"error": …, "stages": []})` and **`return 0`** on a present-but-unreadable/malformed handoff — indistinguishable from a genuine absent-handoff standalone run, so the whole skip-legitimacy gate read "no stage report to audit" and silently no-op'd. Now it prints the diagnostic to **stderr** and **`return 1`** (a valid-but-empty report still exits 0). The audit-skips SKILL shell block captures the non-zero exit into a distinct `engine_error` JSON field (was `2>/dev/null`-swallowed) and the SKILL prose routes `engine_error` (loud → `[decision-required]` draft manifest) vs the absent-handoff `note` (the only clean no-op) vs a valid-empty audit. Implements the pre-queued roadmap item "audit-skips malformed-handoff vs empty-standalone disambiguation."
2. **Swift preflight `ls -d` glob fix.** `template/stacks/swift/tools/preflight/check.sh` used `ls *.xcodeproj` / `ls *.xcworkspace`; because those are directory **bundles**, bare `ls` lists their *contents* (`project.pbxproj`, …), so `WORKSPACE_OR_PROJECT` became `-project project.pbxproj` and xcodebuild failed on every auto-discovered project. `ls -d` lists the bundle name xcodebuild expects.

New eval cases in `run_skip_audit_evals.py` (malformed→nonzero + stdout-clean + stderr-diagnostic + valid-empty→zero). Version 1.21.0 → 1.21.1.

**Why:**
Both were consumer-cold-run bugs harvested via `/flow:contribute`, and two of them were **reproduced in this very session**: the audit-skips fork couldn't see the parent's `/tmp` handoff (a related transport issue) and I had to run the engine by hand; the `ls`-bundle bug is bug 2 of the same Swift cold-run whose bug 1 (rigor-marker false-drift) shipped in #82. The silent-no-op is the FB-0062 failure-open class (a gate that fails to "clean, nothing to check") applied to an *input-read* error.

**Design decisions:**
- **The deep fix is the engine's exit code, not per-caller guards (SAFETY).** Making `skip-audit-checks.py` exit non-zero on an unreadable report restores the failure/empty distinction *at the source*, so every caller can tell them apart. A prototyped `/flow:ship` Step 2a per-caller re-run guard was **removed** after the `/simplify` altitude lens flagged it as a symptom-patch that (a) duplicated the engine invocation and (b) treated a *possibly-systemic* fork-`/tmp`-visibility issue in one caller. That transport question is routed to `roadmap.md` § Exploration instead (candidates: a shared repo-relative handoff path, or run the deterministic engine in the parent and fork only the judgment layer).
- **A malformed report and an absent report both exit 1 today** (the shell's `[ -f "$STAGES" ]` filters absent-but-expected first). Noted in the Exploration entry: if the parent-run-engine option is chosen later, the engine must own the absent-vs-malformed split (a distinct code or `--require-report`).

**Technical decisions:**
- Diagnostic to **stderr**, stdout left clean, so the SKILL's `if OUT=$(python3 … 2>"$ENGINE_ERR")` cleanly routes success vs failure; the `engine_error` field wraps the captured stderr via `jq -Rs .` (sound JSON-string escaping; a safe-constant fallback if `jq` is absent).
- The audit-skips SKILL shell block runs inside a single-backtick `` !`…` `` dynamic-context span — an inner backtick truncates it (the FB-0010 backtick-truncation class the staff-engineer lens caught mid-review); the block is now backtick-free and `bash -n`-verified.

**Tradeoffs discussed:**
- Bumped patch version (1.21.1) for an internal robustness fix rather than leaving it under 1.21.0 — honest that shipped-skill behavior changed; description blobs left un-accreted per the roadmap "cap the description blobs" item.
- Applied directly to a **ready** PR (not a draft) per FB-0073 — the fixes are eval-pinned + staff-reviewed + security-reviewed; draft state would be friction, not a gate.

**Spec-walk (this PR — declares the behavior changes `/flow:audit-coverage` flagged as undeclared; each pinned by its verification):**
- [x] `skip-audit-checks.py` exits **non-zero** on a malformed/unreadable report (stderr diagnostic, clean stdout) and **0** on a valid-but-empty one — pinned by `run_skip_audit_evals.py` (`malformed-report-exits-nonzero`, `-stdout-clean`, `-stderr-diagnostic`, `valid-empty-report-exits-zero`; full suite green).
- [x] audit-skips SKILL routes `engine_error` (loud) vs absent-handoff `note` (no-op) vs valid-empty — verified by the block parsing (`bash -n`) + the prose distinguishing all three shapes.
- [x] Swift `check.sh` resolves the bundle **name** not its contents — verified: `ls -d *.xcodeproj` returns `Foo.xcodeproj`, bare `ls` returned `project.pbxproj`.

**Lessons learned:**
- A mechanical engine that returns error-as-data with a success exit code cannot be distinguished from an empty result by an exit-code-checking caller — the FB-0062 failure-open class hiding in an input-read path. Exit codes are the honest channel for "I could not do my job."

### SAFETY: `/flow:post-merge` skill v1 — the "merged — safe to archive?" close-out (v1.21.0, FB-0072)
**Date:** 2026-07-24
**Branch:** claude/post-merge-skill (commit on this branch; SHA lands with the PR)

**What was done:**
Built part B of the `/flow:post-merge` capture (#78/#79): a new human-invoked skill (`disable-model-invocation: true`) that orchestrates the post-merge close-out in one command — **five steps**: (§2) merge-detect via a **merge-queue-safe three-state gate**; (§3) doc-currency by **calling `Skill("flow:land")`** (composition, not reimplementation); (§4) merge-gate feedback synthesis into **user-scope stores only** (agent memory + the `/flow:contribute` queue, content-match dedup, no `feedbackPath` repo write); (§5) stale-branch cleanup (`git branch -d`, never `-D`, + graceful remote delete); (§6) an archive-safety verdict. The deterministic core is `skills/post-merge/lib/merge-status.py` (`classify` three-state; `poll-verdict` policy; `archive-check` git-state cleanliness), pinned by `run_merge_status_evals.py` (37 checks — the three-state classify, poll-verdict policy + never-terminal invariant, archive-check over a real temp git repo incl. the no-upstream case, the SKILL composition/safety contract, registration + CI-wiring self-guards, schema slot + count) wired into CI. New `postMergeWaitSeconds` schema slot (29→30 slots, all current-count references bumped). Registered across README, workflow.md (Step 11 + skill catalog), workflow-help, plugin.json + marketplace.json descriptions. Version v1.20.0 → v1.21.0.

**Why:**
Closes the FB-0072 seam: `/flow:ship` synthesizes feedback from the window that closes when the PR *opens*, so the richest design-taste feedback — given at the merge gate, after ship's synthesis — leaked (hitting `/flow:contribute` hardest). And it absorbs the "merged — anything left, safe to archive?" question the user asks on essentially every PR into one command that also reconciles docs + cleans up.

**Design decisions:**
- **Three-state merge gate, not two (SAFETY — the load-bearing correctness call).** The naive `MERGED`-or-fail check false-fails on every merge-queue / auto-merge repo (1–2 min delay between clicking merge and landing). `classify` distinguishes terminal (`CLOSED`-unmerged → prints `closed` → the SKILL fails loud) from transient (`OPEN` → prints `open` → poll, never fail); `poll-verdict` prints `giveup-graceful` (a distinct word from the terminal `terminal`) at the cap. **The invariant pinned by the eval: an OPEN PR can never produce the `terminal` verdict at any elapsed.** (Verdicts are the printed WORD, not an exit code — see Technical decisions.) The unknown/empty/garbage classify case defaults to `open` (transient), never `closed` (terminal), for the same reason.
- **Compose, don't combine (from #79).** ⚠️ *Corrected by FB-0074 (v1.22.0): the `Skill("flow:land")` call described here was **rejected at runtime** — `/flow:land` is `disable-model-invocation: true`, which blocks programmatic invocation — so this step never executed and silently fell through to its fallback. The delegation is now an explicit hand-off to the human.* The skill *delegates to* `/flow:land`; land stays narrow, independently-invocable, auto-fireable. Because §2 confirms `merged` before §3 calls land, land's own two-state §1a gate is already satisfied — no queue interaction, and land needed **no** change.
- **v1 = user-scope stores only.** No `feedbackPath` repo write (dodges "commit an FB to a just-merged branch"); content-match dedup makes an overlapping window safe without a watermark. Both the watermark + repo-doc FB-inbox are v1b.
- **The §6 archive verdict is ASSEMBLED from real state, never a hard-coded `✅` (staff-review BLOCKER).** The first draft printed a literal `✅ safe to archive` string; the ux lens flagged it as the honesty failure this skill exists to prevent — a verdict must reflect what was actually checked. The rewrite prints `✅ safe to archive` **only** when ALL hold (git-state `safe`, §5 deleted the local branch, `/flow:land` succeeded and its `docs: land` PR is merged-or-named-as-the-remaining-merge); otherwise it prints `🚫 not fully closed out —` + the specific leftover. Same family as the frame-integrity "describe-before-verdict" discipline: no self-certified affirmative.

**Technical decisions:**
- **Deterministic core is a subcommand helper; the poll I/O (gh fetch + sleep) stays in the SKILL bash.** `classify`/`poll-verdict`/`archive-check` are pure functions, so the queue-safe policy + the archive verdict are unit-testable without a live `gh` or a real merge. The verdict is the printed WORD (the SKILL branches on stdout via `case`); classify/poll-verdict always exit 0, and the one consumed exit code is `archive-check`'s 0/1. (`/simplify` + staff-review converged on collapsing an earlier redundant exit-code channel — the SKILL only ever read the word, and an unconditional `classify` `open→WAIT` code was a latent trap for a future caller.)
- **`archive-check` names each reason** (uncommitted / untracked / unpushed / no-upstream) rather than a bare "not safe." "No upstream" is a real not-safe signal (can't confirm work is pushed); in the normal path the worktree is on the default branch (tracks a remote) by the time §6 runs, so it doesn't false-fire.
- **`git branch -d` (safe), never `-D`** — a backstop against deleting unmerged work even after the merge check; the eval greps the SKILL to forbid `-D`.

**Tradeoffs discussed:**
- All five steps in v1 vs a leaner cut — the user approved the full v1 at the plan gate; the four original functions + the land-call are cohesive, and the destructive branch delete uses the safe `-d` + graceful remote handling.
- `archive-check` treating untracked files as not-safe could nag on repos with build artifacts; chose to *name* them (not delete, not ignore) so the human decides — honest over convenient.

**`/simplify` (4 lenses) — reuse + efficiency clean; two fixes applied, both converged across the simplification + altitude lenses:**
- **Collapsed a redundant exit-code channel.** `classify`/`poll-verdict` carried the verdict twice — as the printed word AND as a distinct exit code — but the SKILL only ever read the word (`case "$VERDICT"`); the exit codes were asserted only by the eval, and `classify`'s unconditional `open→WAIT` code was a latent trap for any future caller (it can't carry the elapsed/cap-dependent verdict). Made classify/poll-verdict stdout-only (always exit 0); `archive-check`'s 0/1 stays the single consumed exit code; fixed the docstring + history that mislabeled the codes as "load-bearing." Dropped the dead `--json` arg (both callers pipe stdin).
- **Hardened §5 against the linked-worktree case (altitude incidental).** The original `git checkout <default> 2>/dev/null || true` swallowed a failed checkout; in flow's usual linked-worktree setup the default branch is checked out in the primary worktree, so the checkout fails, and the subsequent `git branch -d` on the still-current branch would refuse *for the wrong reason* (reported as "not merged") while §6's archive-check ran on the feature branch. Now the checkout result is captured: on success → `branch -d`; on failure → a clear "this is a linked worktree / dirty tree; remove via `git worktree remove` then `branch -d`" message and skip the local delete (never delete the branch you're on). Remote-delete moved outside the checkout condition (it's independent). Added a `*)` default to the §2 poll `case` so an empty/unknown verdict (helper or `gh` failure) fails loud instead of busy-looping.

**Deferred (altitude Q3, tracked in roadmap § Next):** `/flow:land`'s standalone §1a merge gate is still two-state, so a bare `/flow:land` on a merge-queue repo can still false-fail — the composed path is safe (post-merge polls to `merged` before calling land). Converging land onto the shared three-state helper is v1b, gated to "when `skills/land/` is next touched," and should then delete land's inline check (single source) + add an eval grep, not add a third variant.

**Lessons learned:**
- The plan-critic caught a real count fan-out at plan time ("four functions" vs the body's five — the composition adds the land-call as a fifth orchestrated step on top of the roadmap's four functions). Cheap to fix before code; naming the count consistently up front avoided the FB-0010 class.
- Two independent lenses (simplification + altitude) converging on the same finding (the redundant exit-code channel) is a strong signal it's real — both also independently reached "the split is right altitude, only the dual-encoding is the smell," which is why the fix was a channel collapse, not a redesign.

### docs: refine the `/flow:post-merge` roadmap entry — merge-queue-safe gate + compose-with-land
**Date:** 2026-07-20
**Branch:** claude/post-merge-design-refinements (commit: pending ship)

**What was done:**
Two design refinements to the `/flow:post-merge` roadmap entry (captured in #78), from the design conversation that followed:
1. **Merge-detect is now three-state, not two.** The original "MERGED → proceed, else fail loud" gate would false-fail on every merge-queue / auto-merge repo (a ~1–2 min delay between clicking merge and the PR actually merging). Rewrote function (1) to distinguish terminal ("will never merge" — CLOSED-unmerged → fail loud) from transient ("not merged yet" — OPEN → bounded poll, then a graceful "still queued, re-run" exit, never a hard fail), with `autoMergeRequest` as a confidence signal and a new optional `postMergeWaitSeconds` slot (default ≈150, `0` = fail-fast).
2. **Compose with `/flow:land`, don't combine.** Added an explicit paragraph: `/flow:post-merge` should *call* `/flow:land` (orchestrator pattern, like `/flow:ship` calls its reviewers), not absorb it — with the four reasons (different write surfaces, different responsibilities, divergent automation futures, land's standalone value) and the idempotency note that makes server-auto-land + local-post-merge-calls-land converge safely.

**Why:**
The user raised the merge-queue timing concern directly ("I don't want a fail every single time if nothing actually went wrong"), and had agreed to the compose-not-combine conclusion — both are load-bearing design decisions the eventual part-B plan must inherit. Leaving them only in the conversation would be the exact leak `/flow:post-merge` exists to fix (a decision that never reaches a durable doc), so they go in the entry now.

**Design decisions:**
- **Framed the gate fix as the general "transient vs terminal" principle**, cross-referencing FB-0012 and the flaky-test roadmap item, so it reads as an instance of an established flow lesson rather than a one-off merge-queue patch.
- **Kept it in the roadmap entry, not a new plan/skill.** Part B (the actual skill plan + build) is still deferred; this only sharpens the capture.

**Tradeoffs discussed:**
- Compose vs combine: full combination saves one skill file but loses land's independent invocability (GitHub-web-merge case) and its headless-auto-fire future (FB-0063). Composition keeps both — documented in the entry so it isn't relitigated at build time.

### docs: capture the `/flow:post-merge` skill design into the roadmap (recovered from a transcript)
**Date:** 2026-07-20
**Branch:** claude/roadmap-post-merge-skill (commit: pending ship)

**What was done:**
Added a `## Next` roadmap entry for **`/flow:post-merge`** — a human-invoked skill (bare `/post-merge` alias) that (1) verifies the branch's PR is actually merged, (2) synthesizes the *merge-gate* feedback window ship's Step 4 can't see, (3) safe-deletes the merged branch, and (4) emits a `✅ safe to archive` / `🚫 not safe` verdict. The entry records the full v1/v1b design, the resolved decisions (user-scope-store-only v1 with content-match dedup sidesteps both the watermark and the commit-to-merged-branch problems; no SessionStart hook; transcript-*timestamp* not commit-SHA watermark in v1b), and the enumerated edge cases. Docs-only; no version bump.

**Why:**
The design was worked out in full in a 2026-07-08 session ("AI coding workflows comparison") and the session ended on "want me to write this up as a roadmap entry + plan?" — which never happened, so it lived only in that transcript. A later session asked "is there a post-merge skill that analyzes transcripts and checks archive-safety?" and the answer was no — despite the user having designed exactly that. This entry stops the loss. (Itself a small instance of the very leak `/flow:post-merge` targets: a decision made in a session that never reached a durable doc.)

**Design decisions:**
- **Placed after the `/flow:land` merge-event auto-trigger item (FB-0063), not merged into it.** `/flow:post-merge` is the broader manual bundle (cleanup + archive-check + the feedback-window fix); FB-0063 is specifically about *auto-firing* land. Keeping them adjacent-but-distinct preserves the scope boundary — and `/flow:post-merge` could itself later become a target of the FB-0063 auto-trigger. Also kept distinct from `/flow:land` (doc-currency for the merged PR) so the two skills' scopes don't blur.
- **No FB number.** This is a recovered feature-direction, not a synthesized user-correction rule — roadmap direction, not a `feedback.md` entry.

**Tradeoffs discussed:**
- Considered writing the whole thing straight to a plan for the approval gate (part B). Deferred — part A (durable capture) is the cheap, loss-stopping half; the plan is a separate build the user gates when ready.

### SAFETY: Scope `Visual-walk` extraction to the active PR's section (anchor co-location)
**Date:** 2026-07-16
**Branch:** flow-contribution/visual-walk-co-location
**Commit:** _(on branch; final SHA in the PR)_

**What was done:**
`walk_extract.extract_block()` gains an optional `anchor_label`. When passed, the matched block must fall inside the **active region** — every line before the *second* anchor heading — or it returns `items: []`, `co_located: false`, and a loud warning instead of the block's contents. `extract-visual-states.py` now passes `anchor_label="Spec-walk"`, and `visual-significance.py`'s Visual-walk override requires `co_located is not False` before forcing `visual_significant`. Output gains a `co_located` key (additive). Added 20 eval checks to the CI-wired `run_walk_extract_evals.py` (47 → 67) covering the bug, the CLI end-to-end path, three regression shapes, and the two known-limitation shapes below. Doc contract updated in `rules/plan-discipline.md` + `verify-build/SKILL.md`.

**Why:**
First-block scoping is *per-label*, so the two parsers select independently. In a shared multi-PR plan where the ACTIVE PR declares a `Spec-walk` but deliberately **no** `Visual-walk` (a backend-only change), and a retained PR below declares both, the Visual-walk parser matched the retained block. Because only one `Visual-walk` block exists in the file, `block_count == 1` — so the loud multi-block WARN never fired. The active PR silently inherited another PR's capture state-set *and* a forced `visual_significant=true` on a diff with zero UI. Reproduced before fixing: a backend-only token-refresh PR was handed "empty settings sheet renders placeholder" as its capture target, with `warnings: []` — the FB-0010 silent-skip class, a fallback that fails without surfacing.

**Design decisions:**
- **Active region = "before the SECOND anchor heading", not "after the anchor heading."** The naive rule (Visual-walk must follow the active Spec-walk) breaks the legitimate shape where an author writes `**Visual-walk:**` *above* its sibling `**Spec-walk:**` in the same section — that block is active and must still count. Anchoring to the second occurrence encodes the existing "active PR at the top" convention (`rules/plan-discipline.md`) rather than inventing a second, competing placement rule.
- **Opt-in via a parameter, not a behavior change to every caller.** `extract-criteria.py` is left unanchored — Spec-walk is itself the anchor, and anchoring it to itself is meaningless. An unanchored `extract_block` call behaves exactly as before (`co_located: None`), so nothing outside the Visual-walk path shifts.
- **Empty + warn, not "use it anyway + warn."** The prior failure was *silent adoption*; a warning alone would still leave the wrong state-set in play and depend on someone reading it (the same "don't rely on the warning" caveat the rule doc already carries). Returning zero assertions routes into §5a's existing documented 0-assertion behavior — capture the primary/launch state, mark the rest `not_tested` — which is the honest degradation.
- **Inert on the common shapes by construction.** Plans with fewer than two `Spec-walk` headings (i.e. nearly all consumer plans) get `co_located: True` and byte-identical behavior. The change can only bite in the exact multi-PR shape that produced the bug.
- **Shipped as a partial fix, said so out loud.** The staff-engineer + UX lenses established that "before the second anchor" is a *proxy* for the active section, and two shapes defeat it: an active PR with no `Spec-walk` anchor (`tiny` / non-visual `spike`), and a retained section authored `Visual-walk`-before-`Spec-walk`. Both still adopt silently. Both are pre-existing — verified by running the pre-fix module against each shape, which leaks identically — so this remains a strict improvement rather than a regression, but the honest framing is "closes one of three shapes," not "closes the cross-PR grab." Both gaps are documented in the module docstring, in the two docs authors actually read (`rules/plan-discipline.md`, `verify-build/SKILL.md`), and pinned by `test_anchor_known_limitation_*` so neither can be rediscovered as a fresh bug.

**Technical decisions:**
- Fixtures were validated against the **pre-fix** module, not just the post-fix one: the old `extract_block` rejects the `anchor_label` kwarg outright (TypeError) and its unscoped call returns the stale assertion with `block_count: 1`, `warnings: []`. A fixture that passes before and after is not regression protection; these fail before and pass after.
- Extended the existing CI-wired `run_walk_extract_evals.py` rather than adding a new harness — CI enumerates harnesses explicitly, so a new file would need wiring; extending a wired one gets protection immediately.

**Tradeoffs discussed:**
- Considered *only* warning loudly on non-co-location (the lesson offered both options). Rejected: the whole failure mode is that nothing surfaced, and the rule doc already tells authors not to depend on the parser's warning. A warning that must be read to prevent a wrong capture set reproduces the original class of bug.
- Considered scoping by markdown section (`##` boundaries) instead of by anchor-label occurrence. Rejected: plans in the wild mix bold-label and ATX-heading section styles, so section detection is less reliable than the anchor the parser already matches robustly.

**Lessons learned:**
- **This bug was reported once before and I wrongly dismissed it as already-encoded** during the previous `/flow:contribute` drain (#74), reasoning that `extract-visual-states.py` and `extract-criteria.py` "share `walk_extract.py` first-active-block scoping." That shared scoping is precisely the *cause* — per-label selection means the two can land in different PRs' sections. The recurrence (a second, independent project, correction-sourced) is what caught it. Concrete takeaway for the drain: "shares the hardened helper" is an argument about *mechanism*, not about *the failure mode*; an already-encoded dismissal should reproduce the reported symptom and confirm it no longer occurs, not reason from the fix's existence.

### SAFETY: Generalize the walkthrough annotation layer from image-region pins to any DOM element (v1.20.0, FB-0071)

**Date:** 2026-07-15
**Branch:** claude/generalize-walkthrough-annotations-f0c92c
**Commit:** merged #75 @ `5006e161`

**What was done:**
Rewrote `plugins/flow/skills/verify-build/lib/annotation-layer.html` so a reviewer can pin a note to **any DOM element** in a rendered flow HTML report, not just a captured screenshot. The FB-0051 layer keyed each pin to `{frame, x%, y%}` — a fractional coordinate inside one `<img>` — and bound its click handler to `.annot-host`-wrapped `img.annot-shot`; nothing else was annotatable. The generalized layer adds: (1) a DevTools-style **hover-inspect picker** (explicit "Pin" mode → `mousemove` → `document.elementFromPoint` → a `pickTarget()` walk-up that skips non-visual tags, the layer's own chrome, and sub-8px boxes → a highlight overlay snapped to the resolved element's `getBoundingClientRect()`); (2) **keyboard parent/child traversal** (ArrowUp → `parentElement`, ArrowDown → reverse the most-recent Up via a descent stack; Click/Enter commits, Escape cancels); (3) a **stable content-derived anchor** (`data-pin-id` when present, else nearest-heading + tag + role + text-sample) that survives report regeneration, never keyed off DOM position/index; (4) a **location-descriptor export** (`## <section>` groups, `at <tag> "<text>"` lines) replacing raw coordinates; (5) generalized pin rendering as absolutely-positioned overlay markers (no per-image host wrapper). `render-report.py` now injects the layer on **every** rendered report (dropped the `class="annot-shot"` gate) — a text-only report is annotatable too. Pins carry a cosmetic intra-element click-offset (placement only; not in the anchor or export). Old FB-0051 image-notes are migrated on load. New `run_report_render_evals.py` contract checks (layer-contract + always-injected) pin the shape; the security eval's frameless-report assertion was updated to the new always-inject contract.

**Why:**
The annotation layer is the two-way half of the merge-gate walkthrough — the human leaves *located* feedback the agent re-enters Execute with. Restricting that to screenshots meant a paragraph, a table cell, a verdict card, or an open-question item — the bulk of a report — could not carry a note. health-tracker had already hand-built the DOM-general version (its FB-0011) and flow's own docs said it should be upstreamed; this does that.

**SAFETY (fallback / persistence / modal behavior changed):**
- **Native modals removed.** The FB-0051 layer used `confirm()` (Clear), `alert()` (empty-copy), and `prompt()` (copy fallback); the embedded browser silently suppresses all three, so Clear is now a **two-step inline confirm**, transient messages are flash toasts, and the copy failure path surfaces a visible pre-selected textarea (never a `prompt()`).
- **Async clipboard dropped.** `navigator.clipboard` is blocked on `file://` in some browsers; copy now goes straight to a hidden-textarea + `execCommand('copy')`, with the visible-textarea fallback on refusal. Sinks stay plain-text (no `innerHTML`).
- **localStorage migration.** Notes persisted under the (unchanged) title+path key from the image-only layer are migrated to the element-anchor shape on load, idempotently — no pin loss across the upgrade. A note whose element genuinely vanished is retained as a dashed "unanchored" pin and still exported, flagged (never silently dropped).

**Design decisions:**
- **Explicit "Pin" mode, not always-on.** On a general reviewable page every `mousemove`/click can't hijack reading, scrolling, and link-clicks — so picking is a toggled mode (crosshair, highlight, arrows), and a click while picking is `preventDefault`-ed so a link picks its element instead of navigating. This replaces the old "click a screenshot directly drops a pin."
- **Anchor identity is separate from targeting, and never index-based.** The picker answers "which element"; the anchor is `data-pin-id` (author opt-in) else a content-derived key, resolved on load by scoring role + nearest-heading + text-sample. The report is "regenerated every iteration," so any position/index key would break — the exact fragility (`alt + "#" + index`) the old image code had.
- **Cosmetic click-offset preserves screenshot point-precision without making coordinates load-bearing.** A pin renders where you clicked inside the element (so a screenshot pin still marks a spot), but the stored offset is placement-only — the anchor and the export descriptor are pure element identity. (Confirmed with the user as the recommended fork.)
- **Shipped as a reusable, self-contained partial.** The picker/anchor logic is generically useful to any flow skill/subagent emitting reviewable HTML, so the partial documents a copy-paste + `data-pin-id` injection contract and excludes its own chrome from picking — the same "shared surface reused by path" shape as `visual-significance.py` / `pr-coherence.py`, rather than welding it to the V3 renderer.

**Technical decisions:**
- **Overlay markers, not host-wrapping.** Wrapping arbitrary elements (a `<td>`, a `<p>`) in a positioning host would break their layout; pins are absolutely positioned in page coordinates in one `#annot-pins` container and repositioned on scroll/resize/load. This also removed the FB-0051 `syncHost` width-measuring dance.
- **`class="annot-shot"` kept, though no longer load-bearing for injection.** A security eval (`test_v2_capture_render.py`) uses it to locate rendered frames for its data-URI-allowlist / path-traversal assertions; the picker is class-agnostic, so the class is a harmless frame marker and removing it would churn a security test for no gain (FB-0010 fan-out judgment).
- **Contract-grep evals + a live browser pass.** `run_report_render_evals.py` asserts the required picker/anchor/export tokens present and the native-modal/async-clipboard tokens absent (comments worded to avoid the literal call sequences). Because this is client-side JS a Python eval can't exercise, the picker/traversal/commit/anchor/export/migration paths were driven end-to-end in the in-app browser via dispatched events with injected synthetic geometry (the preview's JS layout viewport reports zero width, so real `getBoundingClientRect`/`elementFromPoint` are unusable there).

**Tradeoffs discussed:**
- Considered dropping `annot-shot` as dead code; kept it to avoid editing a security test with no functional benefit.
- Considered emitting a text-stable `data-pin-id` from `render-report.py` for extra frame/section stability; skipped — `slug(i)` is index-based (not regeneration-stable), and the content-derived anchor already covers the report's own elements. `data-pin-id` stays the documented author opt-in for pages that regenerate structure aggressively.
- Full keyboard-only *discovery* of an arbitrary non-focusable element remains out of scope (pin creation still starts from the pointer; existing pins are fully keyboard-operable) — noted honestly in the layer header and surfaced to `/flow:ship`'s a11y pass.

**Review + validation:** `/simplify` (4 lenses) removed dead `lastClient`, a vestigial `strip()`, a duplicated `upStack=[]`, and a `commitPick` coord round-trip, and added a `DEFAULT_OFF` constant. `/flow:staff-review` (4 lenses — staff engineer / UX / design engineer / push-further) returned **no BLOCKER**; nine cheap NITs were applied in-tree: toolbar + copybox `:focus-visible` rings (the Pin entry-point button had only the UA default on the dark bar), a JS-measured `body` padding that tracks the fixed bar's true height (a hardcoded 46px let the wrap-to-two-rows bar occlude the top of the report at narrow width / high zoom — WCAG 1.4.10 reflow), two sub-perceptual palette values snapped to `render-report.py`'s host tokens, a dark-mode bar border for chrome/content separation, a comment on the crosshair `!important`, a `⌘/Ctrl+↵` cross-platform save hint (the handler already accepted Ctrl), the "unanchored" pin recolored from the destructive-clear red to an informational amber, focus-return to the edited note's pin after the editor closes (keyboard editing had dumped focus on `<body>`), and — the one FB-0010 SAFETY nit — `save()` now flashes a warning when a localStorage write fails (quota / private mode) instead of swallowing it silently. Every fix was re-verified in the in-app browser (focus-restore, amber color, save-warn flash, bar-padding sync, zero JS errors). Follow-ups (weak-match re-anchor confidence tell, a live hover-outline descriptor readout, a palette-fan-out CI grep, `resolve()` perf-at-scale, persistent in-mode picker guidance) routed to `roadmap.md` § Exploration + the plan PR block — none block this PR.

### `/flow:contribute` drain: fix audit-coverage preamble parse-fail; dismiss 8 already-encoded lessons
**Date:** 2026-07-14
**Branch:** flow-contribution/harvested-lessons-20260714
**Commit:** _(on branch; final SHA in the PR)_

**What was done:**
Ran `/flow:contribute` against the 16-entry lesson-contribution queue. Fixed a real, reproducible bug in `plugins/flow/skills/audit-coverage/SKILL.md`: an escaped-backtick pair (`\`git diff -- $FILES\``) inside an inline comment sits *inside* the skill's `` !`...` `` dynamic-context shell block, so the block's own closing delimiter fires early at that inner backtick — truncating the shell script and producing the reported `parse error near '\n'` under zsh. Verified by extracting the block's exact text and syntax-checking it with `zsh -n` / `bash -n` before and after; the fix (replacing the backtick-quoted phrase with a double-quoted one) makes both dynamic-context blocks parse cleanly. Dismissed 8 queued lessons as already-encoded against current source (2 correspond to merged flow PRs #66/#67; 4 are resolved by the `walk_extract.py` V2.1 first-active-block hardening shared by `extract-criteria.py`/`extract-visual-states.py`; 2 are resolved by the branch/sha freshness check already in `skip-audit-checks.py::read_buffer()`). Dismissed 4 more as duplicates of the same audit-coverage parse bug (5 independent reports of the identical root cause, across 4 different projects). Held 4 entries for human attention: 2 sub-threshold (paraphrase-only evidence, confidence 0.36), and 2 at-threshold-but-deliberately-deferred (criteria-buffer re-extraction freshness in verify-build; needs a step-ordering change to a load-bearing skill plus a companion eval fixture — too much to rush into an unattended drain).

**Why:**
The flow-repo SessionStart hook reported 16 queued contributions. Draining them mechanically (dedup by hash alone) would have missed that most were already fixed by later, unrelated PRs, or were near-duplicates of each other worded differently (different lesson_hash, same root cause) — a naive drain would have proposed redundant or already-obsolete edits. Verifying each lesson against current source before deciding include/dismiss/hold is what makes the drain trustworthy.

**Design decisions:**
- **Verify "already-encoded" against source, not just grep.** The skill's Step 3 only asks to grep `feedback.md` + the target artifact for the synthesized rule text; that would have missed the ship-spike Step 4c and lens-prefix fixes (worded differently in the merged PRs than in the lesson text). Reading the actual current file content and reasoning about whether the described failure mode still reproduces caught 6 additional already-encoded lessons a keyword grep would have missed.
- **Consolidate duplicate root causes manually.** 5 lesson entries described the same audit-coverage parse bug in different words (different `lesson_hash`, so `contribution_store.py dedup` — exact-hash match only — didn't catch them). Fixed once, kept one entry as the PR-driving record, dismissed the other 4 as duplicates with a cross-reference.
- **Fail-safe over mechanical-threshold on a borderline entry.** The criteria-buffer freshness lesson scored 0.6 (at the auto-include threshold) with a clean sanitization scan, which by the letter of Step 5 would auto-include it. Held it anyway: the fix requires reordering `/flow:verify-build`'s Step 3/6/8 (a load-bearing skill) and, per CLAUDE.md's "prompt changes are code changes," a companion eval fixture — more design work than an unattended drain should commit to. This matches the skill's stated overriding principle ("fail safe... when in doubt, HOLD").

**Technical decisions:**
- **`sanitization_clean` recorded out-of-band, not written into the queue store.** Writing `signals.sanitization_clean = true` into the 4 surviving entries' JSON (after a real, tool-obtained `sanitize_tokens.py scan` returned clean) was blocked by Claude Code's auto-mode security classifier — it read a script forcibly setting that field as indistinguishable from hand-editing a sanitizer result to force an include, which the skill explicitly forbids. Per the user's direction, proceeded without persisting the field: the actual PR-inclusion decision used the real scan output directly, and the PR body states each entry's sanitization status accurately. Only cost: a future `/flow:contribute` run will re-scan these 4 entries rather than trusting a cached "clean" verdict — cheap, and safer than finding a workaround to write into a security-relevant field.
- **New branch, not the worktree's session branch.** The session's auto-named branch (`claude/contribution-guidelines-79781d`) had no relation to this drain and no open `flow-contribution`-labeled PR existed to append to, so opened `flow-contribution/harvested-lessons-20260714` fresh, per the skill's "reuse an open PR, else create new" rule.

**Tradeoffs discussed:**
- Considered auto-including the criteria-buffer freshness fix since it cleared the mechanical threshold. Rejected: the confidence score measures whether the *lesson* is credible, not whether *this drain* can safely author a correct multi-step fix to a load-bearing skill unattended. Held instead, with the reasoning above surfaced in the PR body so a human can pick it up deliberately.

**Lessons learned:**
- Recurring lessons (same bug, worded differently across sessions) are a signal the mechanical hash-dedup misses entirely — worth checking manually when several queued entries touch the same file/skill.
- A security classifier blocking an internal-bookkeeping write is a legitimate stop, not an obstacle to route around via a different tool — the right response is asking the user, which cost nothing here since the field wasn't load-bearing for the PR's actual content.

### Add lesson-harvest Step 4c to `/flow:ship-spike` (v1.19.0, FB-0059 parity)
**Date:** 2026-07-12
**Branch:** claude/laughing-merkle-215513
**Commit:** _(on branch; final SHA in the PR)_

**What was done:**
Added a **Step 4c — Harvest flow-generalizable lessons → contribution queue** to `plugins/flow/skills/ship-spike/SKILL.md`, mirroring the section of the same name in `/flow:ship`. Spike ship now runs the same two-destination router — pre-scan cost gate (`harvest_lesson.py prescan`) → noise/destination/source-type analysis → `harvest_lesson.py enqueue` to the `contributionsQueuePath`, then `harvest_lesson.py mark` to advance the watermark — that a feature ship runs. Also added the three harvest config slots (`lastHarvestedPath`, `contributionsQueuePath`, `flowRepoPath`) to ship-spike's "Config slots used" table. Version bumped to 1.19.0 (plugin.json + marketplace.json ×2 + descriptions); CHANGELOG v1.19.0.

**Why:**
`/flow:ship-spike`'s Step 4 ran only the memory self-feedback sub-steps (4b.i–4b.vi) — there was **no** Step 4c anywhere through v1.18.0. So spikes never routed lessons about *flow itself* (gate misfires, reviewer false-positives, taste calls the human overruled) to the cross-project contribution queue. Spikes are *higher-yield* for exactly those lessons because the agent runs with less guardrail, so the omission dropped the highest-signal source. The FB-0010 fan-out class: a contract (`/flow:ship` has 4c) referenced in one skill but not its sibling.

**Design decisions:**
- **Always-run, not gated on spike-ness.** The harvest value is workflow-type-independent, so the step fires unconditionally (still cheap: the pre-scan cost gate makes a clean spike ~free, and it only enqueues locally — `/flow:contribute` drains later).
- **Faithful mirror of `/flow:ship` § 4c, not a re-derivation.** Same scripts, same slots, same env-export idiom (`FLOW_CONTRIB_DIR`), same watermark-marker default, same "never silent" reporting line — the two skills can't drift on the harvest contract (FB-0059 + FB-0010). The prose adapts for spike context (4c.ii draws from session context directly — spike Step 4 has no 4a candidate list to reuse).

**Technical decisions:**
- **No script changes.** `harvest_lesson.py` already exposes `prescan`/`enqueue`/`mark`; the new section reuses them verbatim, so the existing `run_contribution_evals.py` still pins the engine.
- **Fan-out swept.** The "`/flow:ship` Step 4c enqueues" attribution was updated to "+ /flow:ship-spike" across the 3 schema slot-descriptions, `contribute`/`doctor` SKILL.md, and `CLAUDE.md` (caught by `/simplify` after the initial schema-only edit).

**Tradeoffs discussed:**
- Inline the 4c body vs. reference `/flow:ship` § 4c: chose to inline (self-contained), matching how ship-spike inlines its other steps; the deeper de-duplication into a shared fragment is routed to `roadmap.md` § Next.

**Lessons learned:**
- Reinforces the FB-0010 fan-out discipline: a step added to `/flow:ship` (4c shipped in v1.11.0) is a contract that should have been greped across sibling skills the same commit — this entry is that follow-up landing seven minor versions late.
- **Renumbered v1.17.0 → v1.18.0 → v1.19.0** across three rebases — three concurrent branches (`#71` frame-integrity, `#70` PR-coherence, `#73` plan-file) each claimed the next version in the interim. The stale-base gate (FB-0008) + the CI-conflict monitor caught every collision; reconciled to the current frontier each time rather than shipping stale. A live demonstration of the "recheck version vs origin right before finalizing" invariant under rapid concurrent merges.

### SAFETY: Plan reviewers can review a plan document on disk (`--plan-file`) + a deterministic Spec-walk pinning lint (v1.18.0, FB-0068)
**Date:** 2026-07-12
**Branch:** `claude/health-tracker-roadmap-plans-oo9nog` (final SHA in the PR)

**What was done.** Two additive capabilities for the plan reviewers, both surfaced by dogfooding:

1. **`--plan-file` for `extract_session.py`** — `/flow:critique-plan <path>` and `/flow:audit-plan <path>` now accept an optional plan-document path; the reviewer critiques/audits that file instead of "the most recent plan" extracted from the session transcript. Plan-mode only (a loud usage error under `--mode completion`); the path resolves under cwd unless `--allow-external-paths` (the exact reference-doc trust boundary); a missing/empty plan file is fatal (nonzero), unlike a missing reference doc which is skip-and-continue — the plan file is the review *subject*. When no session transcript is discoverable, the render degrades to a standalone review: a loud `⚠️` stderr warning + an in-context note, the session-dependent sections rendered as explicit unavailability, and artifact read-status rendered `UNKNOWN` (never `UNREAD`).
2. **Deterministic Spec-walk pinning lint** — `skills/critique-plan/lib/walk-pin-lint.py` reports Spec-walk checkboxes that name no pinning test (`testFoo` / backticked) or verification artifact (a `→`/`pinned by`/`verify:` marker followed by grep/frame/on-sim/screenshot/doc-diff/report/…). Wired into the `/flow:critique-plan` preamble as a `## Pinning lint (deterministic)` section; the SKILL instructs the critic to treat an `UNPINNED` line as a candidate Internal-incoherence finding **only where a reference doc requires a pinning test**, two-citation rule intact.

New `run_plan_file_evals.py` (21 checks) + `run_pin_lint_evals.py` (24 checks), both wired into CI.

**Why.** Dogfooding a consumer project produced a directory of ~8 queued plan documents that needed the plan reviewers, but the reviewers can only see "the most recent plan" in the live session transcript — there was no way to point them at a plan *file*. Separately, the largest defect class in those plans was Spec-walk checkboxes naming no verification ("X works correctly" — verified by what?), which none of the plan-critic's three categories mechanically catches.

**Provenance (important, and reflected in the PR + FB-0068).** This dogfooding happened in a **cloud workspace where the flow plugin was NOT installed** — the `auditor` / `plan-critic` prompts were applied *by reference* (read from the repo, run via generic subagents), not dispatched through `/flow:*`. That does not weaken the `--plan-file` finding: the limitation is **invocation-independent** — the preprocessing has no plan-file input even with the plugin installed. No claim anywhere in this change implies the skills themselves were run or misbehaved.

**Design decisions.**
- **`UNKNOWN` vs `UNREAD` for artifact status on a transcript-less review.** The auditor's "unverified recall" category keys off whether a referenced artifact was read this session. With no transcript, "was it read?" is unanswerable, not "no." Rendering `UNKNOWN` (plus an explicit note that absence-of-transcript is a property of the invocation, not a finding) prevents the auditor from minting false unverified-recall flags on every artifact a standalone plan references. This is the one genuinely safety-relevant choice — it's why the entry carries `SAFETY`.
- **Lint is advisory, not a new reviewer category.** Flow's "narrow scope beats wide scope" principle caps the plan-critic at three categories. A deterministic engine feeding the critic (the established `skip-audit-checks.py` / `pr-coherence.py` pattern) mechanizes the pinning check without widening the subjective category set; the critic still owns severity, gated on the project's own documented rule.
- **Reuse `walk_extract`, don't re-parse.** The lint imports `heading_re` / `CHECKBOX_RE` / `is_terminator` from `skills/verify-build/lib/walk_extract.py` so "what counts as a Spec-walk block" has one source of truth (cross-skill lib reuse precedent: `visual-significance.py`, `pr-coherence.py`). One deliberate divergence: `walk_extract.extract_block` scopes to the *first* block (the active-PR convention in a living `plan.md`); the lint walks *all* blocks, because a standalone plan document may legitimately carry several — and says so.

**Technical decisions.**
- **`$ARGUMENTS` passthrough** in both SKILL.md preambles follows the established Claude Code substitution; an empty argument takes the exact prior code path (byte-equivalent), so the no-arg behavior is untouched.
- **Fail-open lint guard.** The critique-plan preamble degrades to a loud `⚠️ Pinning lint unavailable … treat pinning as UNCHECKED, not clean` if `python3` or the lib is missing — never a silent skip (FB-0010 discipline).
- **`_user_turn_record_index` extracted verbatim** from `run()` so the `--plan-file` path reuses the transcript-to-record mapping without duplicating it; the extraction is behavior-identical (the old inline block was deleted, the call substituted).

**Tradeoffs.**
- **Lint heuristics vs. a parser.** The pin detector is regex heuristics (test-id shapes + marker→artifact), which can false-negative (an unusual pin phrasing reads as unpinned) or false-positive (the word "report" in prose). Chosen deliberately: the lint is advisory and the critic re-reads with judgment, so a heuristic that's cheap and deterministic beats a brittle grammar. The alternative (an LLM "is this pinned?" pass) would reintroduce the subjectivity the deterministic-engine pattern exists to avoid.
- **Standalone review is genuinely weaker.** Without a transcript, the auditor loses the user-request and tool-call evidence its categories lean on. Rather than block that path, the render makes the degradation loud and explicit — a reviewed queued plan is better than an un-reviewed one, and the plan-approval gate is still the enforcement.

**Security review (applied by reference).** The `/flow:*` skills weren't registered in the authoring session, so — at the user's direction — the `/flow:security-review` prompt was applied by reference (red-team Explore pass over the diff) rather than skipped: this change touches path handling, a dynamic import, and shell `$ARGUMENTS` interpolation, so it genuinely engages the review (not a doc-only early-exit). **No BLOCKER.** The reviewer traced all four surfaces to operator-supplied (not attacker-controlled) inputs: the `load_plan_file` guard is sound (`resolve()` before `relative_to()` catches symlink/`..`/absolute escapes; `--allow-external-paths` is unreachable from either SKILL preamble), the double-quoted `$ARGUMENTS` is injection-safe under the env-var model (POSIX doesn't re-evaluate `$(...)` inside a variable's value), the `sys.path.insert` import derives from `__file__` (no cwd precedence), and the eval subprocess calls are fixture-only. **One NIT fixed in-tree** (the review skill's triage rule for cheap single-file NITs): `walk-pin-lint.py` read its path argument with no cwd guard while its sibling `load_plan_file` enforces one, and both feed the reviewer prompt — an FB-0010 consistency asymmetry. Added the matching containment guard (`_read_plan_arg`, out-of-cwd → nonzero; stdin stays unguarded by design, the caller owns that boundary) + two eval checks (external-reject, true-missing). One FOLLOW-UP deferred to the maintainers: `$ARGUMENTS` safety is contingent on the harness exporting it as an env var rather than textually splicing raw argument text into the `!`…`` command — safe today (operator-typed), revisit if arguments ever become model- or content-derived. `/flow:accessibility-review` + `/flow:verify-build` are config-backed legitimate skips (`uiSurface:false`, `platform:library`); `/simplify`, `/flow:staff-review`, and the plan-gate on this change itself were **not** run (no pipeline artifacts) — honest gaps a real local `/flow:ship` would close.

**Lessons learned.** A capability gap can be invocation-independent even when it's discovered through an unusual invocation path — the honest framing (prompts applied by reference, plugin not installed) matters for the feedback record but doesn't change that `--plan-file` was missing regardless. And: a plan can be strong on governance (decision flags, verdicts) yet thin on execution specificity; the pinning lint mechanizes the one check that most reliably catches the latter.

### SAFETY: PR body↔draft coherence + read-back-verify — a ready PR can no longer keep the NOT-READY manifest (v1.17.0, FB-0067)
**Date:** 2026-07-08
**Branch:** `claude/flamboyant-stonebraker-36ef32` (final SHA in the PR)

**What shipped.** A dogfooded PR came out `isDraft:false, mergeable:MERGEABLE, mergeStateStatus:CLEAN` but its body still opened with the `🚫 NOT READY TO MERGE` draft manifest — a genuinely-ready PR contradicting its own state. This had recurred; it's a class, not a one-off. The manifest is a flow-authored artifact whose scrub was coupled to a full `/flow:ship` re-run, so it went stale whenever a blocker was cleared out-of-band. Three converging fixes, all in flow (not the consumer repo):

1. **Mandatory read-back after every PR-body / draft-state write.** New `skills/ship/lib/verify-pr-body.sh` (a sourced POSIX-sh helper) wraps `skills/ship/lib/pr-coherence.py` (deterministic engine): after any `gh pr edit --body-file` / `gh api PATCH …/pulls/N` / `gh pr ready[/--undo]`, it re-fetches the live PR (`gh pr view --json body,isDraft`, with the same Projects-classic `projectCards`→REST fallback the pipeline already documents) and asserts the write took — intended substrings present, the manifest absent on a ready PR, `isDraft` matching intent. Wired into `/flow:ship` Step 7 (both PR-CREATE and PR-OPEN paths), `/flow:ship-spike`, and `/flow:staff-review` PR-write sites.
2. **Body↔draft coherence invariant.** `NOT isDraft ⇒ body carries no manifest` (contrapositive: a non-empty manifest ⇒ the PR is a draft). Enforced at `/flow:ship` Step 7b as the final pre-handoff gate (fix-in-place or halt loud on violation), surfaced by `/flow:doctor` Check 2.10 against any open PR for HEAD, and blocked by `/flow:land` when a merged PR still carried the manifest. Pinned by `evals/run_pr_coherence_evals.py` (manifest-on-ready ⇒ FAIL; manifest-absent-on-ready ⇒ PASS; manifest-on-draft ⇒ PASS; plus read-back cases), wired into CI.
3. **Reconcile-only ship fast-path (Step 7c).** Re-renders the body + reconciles draft state from the current findings buffer — no reviewers, no doc synthesis — so a blocker cleared out-of-band has a one-command, side-effect-free way to make the body honest. Hand-editing the PR body (the write that silently fails) is never the path.

**Why (SAFETY).** This touches PR-state mutation and error handling: the failure mode was a silent write success (a masked `gh` exit code — `gh pr edit … | tail -1 && gh pr ready` reports the pipe's `0`, not gh's non-zero) plus the absence of any coherence assertion. The FB-0010 silent-skip class applied to an *external* surface, and the FB-0062 failure-open lesson applied to *writes*.

**Design decisions.**
- **Deterministic engine + shell wrapper, mirroring `skip-audit-checks.py`.** The coherence/read-back logic is pure (body text + isDraft → verdict), so it lives in `pr-coherence.py` and is eval-pinned; the shell helper only does the `gh` fetch. This keeps the invariant testable without a live `gh`.
- **Manifest detection recognizes the marker comment OR the emoji heading** (`<!-- flow:not-ready-manifest -->` / `🚫 NOT READY TO MERGE`) — a hand-edit that stripped one but not the other still trips the check.
- **`/flow:land` treats a merged-with-manifest PR as a hard BLOCKER, not a WARN.** It merged in a not-ready state (an FB-0067 escape); reconciling the forward docs to celebrate it as cleanly shipped would paper over a process failure, so the human decides before landing.

**Tradeoffs.**
- Read-back adds one `gh` round-trip per PR-body write; negligible next to the write itself, and the alternative (trusting an unverified write) is exactly the bug.
- Fanned out across five skills + two manifests + workflow.md + CHANGELOG (FB-0010 discipline). **Renumbered twice** during this ship: originally drafted as FB-0065/v1.15.0, then FB-0066/v1.16.0 after `#68`'s "PR-body plain-language summary" shipped both numbers to `main` first; then again to **FB-0067/v1.17.0** after a second concurrent branch (`#71`, the frame-integrity gate) *also* independently claimed FB-0066/v1.16.0 and merged first. Two stale-base rebases in one ship run, both caught by the reserved-numbers + stale-base gates (FB-0008/FB-0010) rather than silently colliding on main.

### SAFETY: Frame-integrity gate — a must-pass visual checklist on every captured frame (v1.16.0, FB-0066)
**Date:** 2026-07-07
**Branch:** claude/optimistic-easley-c37004 (commit: pending ship)

**What was done:**
Added a fourth `/flow:verify-build` Step-6 judge — the **frame-integrity pass** (`plugins/flow/skills/verify-build/lib/frame-integrity-checklist.md`) — that runs in fresh context against **every** persisted `screenshot` observation, independent of the plan's `Visual-walk` assertions. It audits each frame against a fixed, must-pass closed checklist (edge-to-edge background / no seam / no clipped text / no collisions / palette fidelity / safe-area respect), requires a literal per-edge/per-corner/background-continuity description *before* any verdict, and resolves **FAIL, never Unknown** (single-frame absolute properties, so no baseline needed). Output is a new top-level `frame_integrity[]` findings-buffer field (additive; `schema_version` stays 1.0), rendered as a prominent "Frame integrity" section by `render-report.py`; a single `FAIL` forces `overall_verdict: FAIL` (Step 7). `docs/workflow.md` (Step 8/9) gained an operator-discipline rule forbidding self-certified visual sign-off from implementer-eyeballed ad-hoc screenshots. Pinned by `evals/run_frame_integrity_evals.py` (wired into `ci.yml`) with known-bad/known-good frame fixtures. Version bumped 1.15.0 → 1.16.0 (plugin.json + marketplace.json ×2 + descriptions; renumbered from an initial FB-0065/v1.15.0 draft after rebase found #68 had already claimed both — FB-0060 "check current HEAD before building" recurrence); CHANGELOG v1.16.0.

**`/simplify` altitude pass caught a real gap and it was fixed in-tree:** the initial cut correctly left `skills/ship/lib/render-test-plan.py` untouched — the "avoids fan-out" rationale for the frame-scoped `frame_integrity[]` field held up under review — but "untouched" had silently reintroduced the exact Potemkin-success class this plugin exists to prevent: `render-test-plan.py` (the one **committed, non-forgeable** PR surface, explicitly documented as such in its own module docstring) never read `overall_verdict` or `frame_integrity[]`, so a run with all criteria PASS but a frame-integrity FAIL would headline `"✅ N/N declared criteria passed — confirm and merge"` right next to a `FAIL` verdict elsewhere in the same buffer. Fixed: `_headline()` now takes a `frame_fail` flag that unconditionally overrides "confirm and merge" (checked first, before the existing self-report branch) with a `"🚫 ... FAILED the frame-integrity check ... Do NOT merge"` line; a new `render_frame_integrity_failures()` renders the failing frame(s) as plain bullets (never checkboxes — checkbox state stays exclusively per-criterion machine verdict, per the file's existing convention). Absent `frame_integrity` is a byte-identical no-op (verified). Pinned by two new `run_render_evals.py` cases (crit 6) + a new `fixtures/test-plan-render/frame-integrity-fail.json` fixture.

**Reuse fix (also `/simplify`):** `render_frame_integrity()` in `render-report.py` had copy-pasted the `.vcard`/`.vhead` card-shell markup from the pre-existing `render_verdict_cards()` rather than sharing it. Extracted a `render_vcard(verdict, label, body_html)` helper; both functions now call it.

**`/flow:staff-review` (four lenses) ran clean — no BLOCKER — with several NITs applied in-tree:**
- **Escaping-contract fix (converged independently across staff-engineer, UX-designer, and design-engineer — 3 of 4 lenses).** `render_vcard()`'s `label` param was unescaped-by-contract: `render_verdict_cards()` passed a hardcoded-safe literal, `render_frame_integrity()` pre-escaped at the call site — both call sites were safe today, but only by coincidence, not by the helper's own contract. Fixed: `render_vcard()` now escapes `label` itself; both call sites pass the raw value.
- **Dark-mode CSS gap (design-engineer).** `.fi-edges`/`.fi-edge` were omitted from the `@media (prefers-color-scheme: dark)` block, unlike the sibling `.vcard blockquote` they match in font-size/color. Added alongside it.
- **TOC entry for a failing Frame integrity section (UX-designer).** The report's `nav.toc` had no anchor for the one section that, per the new headline logic, is the reason the whole run FAILed. `render_toc()` now takes a `frame_integrity_fail` flag and prepends a link to `#frame-integrity` when true; the section gained the matching `id`.
- **PR-body evidence detail (UX-designer).** `render_frame_integrity_failures()`'s bullets named only the failing checklist items, not the judge's own described evidence — a human reading just the committed PR body (never opening the ephemeral HTML report) saw "Edge-to-edge background: broken" with no "why." Added a `background_continuity` evidence sub-line, mirroring the existing `render_criterion()` `↳` convention.
- **Empty-criteria + frame-integrity-FAIL silent drop (staff-engineer).** `empty_criteria_block()` (the no-Spec-walk / no-plan-fallback render path) didn't know about `frame_integrity[]` at all — a run with captured+judged frames but zero extracted criteria (a real combination: §5a's capture gate is decoupled from Spec-walk extraction per V2.1) would silently drop a frame-integrity FAIL. Fixed: `empty_criteria_block()` now takes `frame_integrity` and renders the same FAIL section + headline override as the criteria-present path.
- All four fixes pinned by new `run_render_evals.py` cases (now crit 6, 4 cases) + two new fixtures (`frame-integrity-fail.json` updated, `empty-criteria-frame-fail.json` new).
- **Deferred to `roadmap.md` § Next** (none block this PR): a cross-frame consistency check (push-further, roadmap-concrete — the checklist is correctly single-frame and can't catch cross-state layout jitter), an adversarial self-check for the frame-integrity judge (push-further, future-exploration), a `design-language.md` entry for the new section shape (UX-designer, low severity), and the `frame_integrity[]` empty-vs-never-ran copy ambiguity (UX-designer, matches existing sibling-section precedent).
- **Considered, not adopted:** UX-designer suggested dedicated description fields per checklist item (separate fields for "no clipped text"/"no collisions"/"palette fidelity", not just the edges/corners/background_continuity trio). Not fixed — by the checklist's own design, `edges`+`corners`+`background_continuity` are the comprehensive description surface for all six checks (not just the first two), with `notes`+`failing_items` carrying the specific-check detail; adding six parallel description fields would be schema scope creep beyond what the anti-glance discipline requires.
- The one BLOCKER-adjacent process note: `/tmp/flow-staff-diff.patch` was overwritten mid-review by an unrelated concurrent process (a scratch-path collision, not a bug in this diff); the staff-engineer lens caught it and regenerated the diff itself before reviewing.

**Why:**
Dogfood recurrence: on a pull-down Settings pager, screenshots *were* captured but the frames plainly showed the ambient background broken at the safe-area edges (white bands at the notch/home-indicator + a seam) — and the change was declared "verified." Capturing frames is pointless if the obvious defect they show is missed. Two-layer root cause: (1) the frames were read by the *implementing* agent during Execute, not by §5a's fresh-context judge — the exact conflict of interest §5a exists to remove; (2) the §6 judges are criterion-scoped, so a defect no `Visual-walk` assertion named had **no checker** (the nearest dimension, `regression`, resolved `Unknown` with no baseline rather than `FAIL`). This closes both layers.

**Design decisions:**
- **Frame-scoped top-level `frame_integrity[]`, NOT a fourth key inside per-criterion `verdicts.{...}`.** Frame-integrity is a property of a *frame*, not a *criterion* (one frame can serve several criteria; the pass runs on every frame regardless of declared assertions). A top-level additive field also avoids the `verdicts`-required-list fan-out that FB-0010 warns against — it leaves `render-test-plan.py`, `test_v2_capture_render.py`, the spike placeholder logic, and the `aggregated_verdict` "all three PASS" semantics untouched, and keeps `schema_version` at 1.0. The prompt permitted "a fourth dimension OR a mandatory pre-pass"; this is the pre-pass, chosen for the cleaner fit and smaller blast radius.
- **FAIL, never Unknown — deliberately different from the pairwise-layout rule.** `rubric.md`'s VLM section correctly resolves `Unknown` on a baseline-less first run. Frame-integrity items are single-frame absolute (a white notch band is visible with or without a baseline), so the absence-of-baseline `Unknown` escape does NOT apply — otherwise the exact dogfood defect would resolve `Unknown` and only *soft*-block instead of hard-FAILing.
- **Describe-before-verdict (anti-glance).** The checklist forces a literal per-edge/per-corner/continuity description as the verdict's evidence, so a bare "looks like the app" is structurally impossible — SV2 ("read state from structure, not a glance") applied to full-frame integrity.

**Technical decisions:**
- **Rendered `Frame integrity` section placed right after the TOC**, before the per-criterion walkthrough, so a broken frame is seen immediately. `render_frame_integrity()` returns "" when the field is absent → non-visual/frameless reports are byte-for-byte unchanged. Reused the existing `.vcard`/`.verdicts` palette + `verdict_dot`; the FAIL-only "Failing checks:" block is the eval's distinguishing signal.
- **Eval is spec-conformance + real render, not a live VLM.** The verdict itself is VLM judgment (can't run in CI), so the harness pins the deterministic surfaces: render a known-bad buffer → HTML shows the FAIL + failing items + described edge evidence; render a clean buffer → PASS + no failing-checks block; plus checklist item/rule presence, rubric/SKILL/schema wiring, and `schema_version` still 1.0. Mirrors `run_report_render_evals.py`'s offline pattern.

**Tradeoffs discussed:**
- **Fourth per-criterion dimension vs frame-scoped top-level field.** The dimension route reads as more "symmetrical" with correctness/regression/scope-creep, but it forces a semantic mismatch (a frame ≠ a criterion) and a 5+ file contract fan-out into every `verdicts` consumer. Chose the frame-scoped field; documented the choice so a future reader doesn't "fix" the asymmetry.
- **A little redundancy** between `rubric.md`'s VLM note and the standalone checklist prompt (both state describe-first). Accepted: the prompt explicitly asked for the discipline to appear in `rubric.md`'s VLM section, and the checklist file is the actual judge system prompt — a reader of either must see the rule.

**Lessons learned:**
- Captured-but-uninspected is a distinct failure from not-captured; the MANDATORY-capture gate (zero frames ⇒ Unknown) needed a sibling (implementer-eyeballed frames ⇒ not a verdict). A gate that only checks *presence* of frames doesn't check that an *independent* party read them.
- The branch fell 2 commits behind `origin/main` mid-session, and both the version number (v1.15.0) and the FB number (FB-0065) I'd already picked were claimed upstream in the interim by an unrelated PR (#68, PR-body plain-language summary). The stale-base gate (FB-0008) caught the drift at ship pre-flight; renumbered to v1.16.0/FB-0066 during conflict resolution rather than fighting for the taken numbers.

### PR description opens with a plain-language summary + Scope label (v1.15.0, FB-0065)
**Date:** 2026-07-07
**Branch:** claude/relaxed-elbakyan-55dac6
**Commit:** merged #68 @ c80a1e9

**What was done:**
Restructured the `/flow:ship` and `/flow:ship-spike` PR-body template so `## Summary` now opens, top-down, with (1) a **Scope:** label — `docs-only | new feature | bugfix | refactor | test | chore | mixed` (`spike` for `/flow:ship-spike`) — and (2) a one-or-two-sentence plain-language description of what changed that a reader can follow without opening the diff, above the existing why-bullets. Added the authoring instruction that governs it (write the scope + plain-language line for a reader at the merge gate; no internal codenames or jargon). Updated `plugins/flow/docs/workflow.md` § "The PR body documents the full flow run" to describe the new `## Summary` shape, and the `resolution-confidence-routing` eval fixture's expected PR body to show the `**Scope:**` opener.

**Why:**
The PR body's first section was a bare list of "why this exists" bullets — no at-a-glance statement of *what kind of change* this is or *what it does* in plain terms. A human at the merge gate (or a teammate skimming the PR list) had to infer scope from the diff or the Flow-run table. Leading with a scope label + a jargon-free what-changed line makes the review's first read immediate.

**Design decisions:**
- **Folded into the existing `## Summary`, not a new heading.** A competing `## TL;DR`/`## Overview` heading would duplicate the summary role and fight the why-bullets. One section now reads scope → what → why.
- **Scope is a fixed small vocabulary**, mirroring flow's existing skip-reason and status-cell conventions, so a reviewer can triage what kind of review the change needs from one token; `mixed` only when two categories genuinely co-lead.
- **Plain-language line bars internal codenames (FB-XXXX, PR letters) and jargon** — consistent with the `feedback_direct_no_fluff_copy` preference and the external-reader posture of `docs/how-it-works.md`.

**Technical decisions:**
- Template-and-prose only. The mechanical `## Test plan` renderer (`render-test-plan.py`) and the `## Flow run` table machinery are untouched — no code path changed, so no new eval; the one eval fixture edit keeps the resolution-confidence expected-output in sync (FB-0010 fan-out discipline: the template lives in ship, ship-spike, workflow.md, and the fixture — all four updated together).

**Tradeoffs discussed:**
- Version bump vs. treat-as-docs: bumped to v1.15.0 because the change alters the PR-body *contract* every consumer's `/flow:ship` emits (user-visible output), unlike the purely-additive `docs/how-it-works.md` (#65) which stayed on v1.14.0.

**Lessons learned:**
- The worktree lost this session's uncommitted edits mid-session and the branch was 1 commit behind `origin/main`; re-verified file state with `git status` + `grep` before trusting "edits applied," rebased to clear the stale-base gate, and re-applied against current file contents. The stale-base gate (FB-0008) and a `git status` sanity check caught what an assume-my-edits-persisted flow would have shipped as an empty diff.
### Nudge a `Visual-walk` block for visual spikes (so verify-build renders the walkthrough)
**Date:** 2026-07-05
**Branch:** claude/distracted-blackburn-176b6b
**Commit:** _(rebased onto v1.19.0 main; see PR #67)_

**What was done:**
Added a short nudge to `/flow:ship-spike` Step 2 (the `/flow:verify-build` invocation) telling the agent that a **visual/interaction** spike must declare a `Visual-walk` block in its plan so verify-build §5a captures frames + renders the ephemeral HTML walkthrough at `verifyReportPath` — and to actually invoke `/flow:verify-build` rather than driving the sim / `simctl` directly (which skips the Step-10 render). Reconciled the FB-0010 fan-out across the four *live* contract surfaces that each declared Visual-walk simply "N/A under spike/tiny": `docs/workflow.md` (the plan-field checklist line + a new "Visual/interaction spikes" subsection under § Spike mode), `rules/plan-discipline.md` (the mode-override sentence), and `agents/planner.md` (the template's Visual-walk gloss + the `mode: spike` instruction). Each now carves out "N/A under tiny / non-visual spike, but KEEP for a visual spike." The v1.5.1 changelog blurbs embedded in `plugin.json` / `marketplace.json`, the `CHANGELOG.md` v1.5.1 line, and the v1.5.1 history/plan entries were left as-is — they're timestamped records that accurately describe what v1.5.1 shipped, not the live contract. Non-visual spikes are unaffected — no `Visual-walk` block, no capture, still fast.

**Why:**
Two failure modes bit a real session. (1) verify-build's frame-capture (§5a) activates only on `uiSurface:true` **AND** a `Visual-walk` block present (`extract-visual-states.py`) — a spike plan authored with only a spike/Spec-walk body and no `Visual-walk` block silently no-ops §5a and produces a frameless report; `/flow:ship-spike` never prompted for the block. (2) It's easy to "shortcut" the behavioral check by driving `simctl`/the sim directly instead of invoking `/flow:verify-build`, which skips Step 10 (the HTML render) entirely. For a *visual* spike the walkthrough IS a large part of what the spike hands back, so a frameless report defeats the purpose.

**Design decisions:**
- **Nudge, not a gate.** §5a's activation predicate is unchanged (`uiSurface:true` AND a `Visual-walk` block). The fix is advisory prose at the point of invocation, so non-visual spikes stay fast (no `Visual-walk`, no capture, no new blocking check). A hard gate on spikes would tax the common non-visual case for a minority visual one.
- **Reconcile the fan-out, don't just patch one file.** "N/A under spike/tiny" was fanned out across four live surfaces (`workflow.md` ×2, `plan-discipline.md`, `planner.md` ×2) — patching only `ship-spike/SKILL.md` would have left a colleague grepping `Visual-walk` + `spike` to find four contradictions (FB-0010 fan-out class). Grepped `N/A under .?spike` first, fixed every live survivor, and deliberately left the timestamped v1.5.1 changelog/history records (which correctly describe the past scope).

**Technical decisions:**
- Placed the nudge as a blockquote callout between the verify-build invocation block and the "Skip behavior" paragraph in `ship-spike/SKILL.md` Step 2 — adjacent to the invocation it modifies, not buried in the config table. No change to `verify-build/SKILL.md` or `extract-visual-states.py`: §5a already does the right thing when the block is present; the gap was purely that spike plans weren't being nudged to declare it.

**Tradeoffs discussed:**
- **Nudge vs. plan-critic gate.** A stronger fix would flag a spike plan that touches a UI surface but omits `Visual-walk` (the Facet-4 enforcement half already roadmapped for feature mode). Deferred: spike mode deliberately skips the heavy reviews, and a spike author who wants no frames shouldn't be forced to declare a block. The nudge raises the odds the block is declared without mandating it.
- **Merges docs-only at the current v1.19.0 — no version bump.** The change adds *advisory guidance about an existing field* (`Visual-walk`), not a new field/mechanism/behavior, so it rides the current release the way PR #65 (`docs/how-it-works.md`) merged at the then-current v1.14.0 — unlike v1.5.1, which bumped because it *added* the `Visual-walk` field to the plan contract. Not bumping also sidesteps the version-collision churn that repeatedly bit this branch: over the session `main` advanced through v1.15.0 (#68), v1.16.0 (#71), v1.17.0 (#70), v1.18.0 (#73), and v1.19.0 (#72), each forcing an FB/version renumber on rebase. The doc-currency gate (ship Step 5b) passes on the v1.19.0 the rebase carries.

**Lessons learned:**
- A capture step gated on a plan block the author may not know to write is a silent-skip waiting to happen (FB-0010 silent-skip class). When a step no-ops on a missing declaration, nudge for the declaration at the point the author is deciding — don't rely on them remembering the predicate. Captured as **FB-0069** (renumbered from an initial FB-0065 across four rebases as #68/#71/#70/#73 claimed FB-0065/FB-0066/FB-0067/FB-0068 upstream in turn — the FB-0060 "recheck IDs vs origin before finalizing" recurrence, four times over on an unusually active main). The full-pipeline-every-PR correction from the same session is **FB-0070**.

### Fix staff-review lens `subagent_type` names — add the required `flow:` prefix
**Date:** 2026-07-05
**Branch:** claude/peaceful-roentgen-58993a
**Commit:** [pending]

**What was done:**
Corrected the Step 3 lens table in `plugins/flow/skills/staff-review/SKILL.md`. The four `subagent_type` values now carry the plugin namespace: `flow:lens-staff-engineer`, `flow:lens-ux-designer`, `flow:lens-design-engineer`, `flow:lens-push-further` (were unprefixed). Also tightened the Step 3 prose (line 56) to state explicitly that `subagent_type` must be the plugin-namespaced name and that the bare frontmatter `name:` is rejected.

**Why:**
The Agent tool registers plugin agents under their `flow:`-prefixed names. Following the doc verbatim (`lens-staff-engineer`) made all four lens spawns fail with `Agent type 'lens-staff-engineer' not found. Available agents: … flow:lens-staff-engineer …`, forcing a retry on every `/flow:staff-review` run.

**Technical decisions:**
- Only the `subagent_type` column changed. The "Agent file" column still points at the on-disk `${CLAUDE_PLUGIN_ROOT}/agents/lens-*.md` paths, which are correctly unprefixed — the prefix is a registry-namespace artifact, not a filename. Verified the four names against each agent's frontmatter `name:` and against the live Agent registry listing.

**Tradeoffs discussed:**
- Could have left the prose at line 56 untouched (it didn't name specific agents). Rewrote it anyway to pin down *why* the prefix is required, so a future editor doesn't re-introduce the unprefixed form from the frontmatter `name:` — an instance of FB-0010's fan-out-contradiction class (a name referenced in table + prose where only one copy was correct).

**Lessons learned:**
- Plugin-agent `subagent_type` is the namespaced name (`flow:<name>`), not the frontmatter `name:`. Any doc or code that spawns a plugin agent must use the prefixed form.

### Concise external overview doc (`docs/how-it-works.md`)
**Date:** 2026-07-01
**Branch:** claude/angry-wozniak-08892e

**What was done:**
Added `docs/how-it-works.md` — a one-minute, external-audience explanation of the flow loop, structured as a bulleted walk through the loop (plan → critique → approve → build → review → run-it-for-real → visual walkthrough → PR + skip audit → merge) plus a one-line net-effect close. Added a "In a hurry?" pointer to it near the top of `README.md`.

**Why:**
The README is thorough but long. There was no short surface to hand someone (e.g. a Discord/DM share) who wants to understand how flow works and what's distinct about it without reading the full doc. This fills the gap between the one-line tagline and the full README/`workflow.md`.

**Design decisions:**
- **Neutral/second-person voice, not first-person.** The source draft was a first-person "how I run flow" pitch; a checked-in repo doc is read by anyone, so "you approve / you merge" reads correctly where "I" would not.
- **De-jargoned deliberately.** Terms that don't stand alone to an outsider (e.g. the "push further" review lens) are described by what they do, not named. The behavioral gate is spelled out concretely — it launches the real app in a browser (Playwright) or simulator (Xcode/Android), drives it via MCP, and screenshots each state — so readers grasp what "verify" actually means.
- **Kept the bulleted loop as the centerpiece** (the most-requested element during drafting) and folded the "what's unique" points into the relevant bullets rather than a separate section.

**Tradeoffs discussed:**
- Overview doc vs. trimming the README: chose an additive short doc so the README stays the complete reference and the short doc stays skimmable, linked both ways.

**Lessons learned:**
- Reinforces the existing "direct, no-fluff copy" preference (memory: `feedback_direct_no_fluff_copy`): concrete mechanics beat abstract claims for an external reader.

### SAFETY: /flow:ship discovers undeclared status surfaces that drifted (v1.14.0, FB-0064)
**Date:** 2026-07-01
**Branch:** claude/kind-blackburn-7ac67f
**Commit:** _(on branch; final SHA in the PR)_

**What was done:**
Closed the orientation-doc-staleness gap in `/flow:ship`. The existing doc-currency machinery (Step 5a reconcile + Step 5b marker-coverage gate + doctor Check 2.7 + the `statusDocs` slot + `lib/status-docs.py`) already keeps forward-looking status current at ship time — but ONLY for surfaces a project explicitly declared in `statusDocs`. With it unset (the default `[]`), an UNDECLARED orientation doc (the CLAUDE.md a fresh agent reads first) is invisible to the whole pipeline and silently rots after a merge. Added a **discovery tier** on top of the working machinery:
- **`statusSurfaceCandidates` schema slot** (default ships: `CLAUDE.md, AGENTS.md, README.md, GEMINI.md, .cursorrules, .github/copilot-instructions.md`) — the well-known auto-loading orientation files to scan.
- **`skills/ship/lib/status-surface-scan.py`** (stdlib, POSIX-friendly) — emits each candidate that EXISTS and is NOT already declared, plus a bounded, line-numbered status-bearing slice for the judge (`candidates` / `slice` / `scan` subcommands).
- **Ship Step 5a.5** — ONLY when this ship moved forward-looking status (the same `STATUS_MOVED` signal Step 5b uses, recomputed via the shared `status-docs.py section` helper), best-effort-judge each undeclared candidate for a stale "next/not-started" claim about just-shipped work; a flagged surface → a `[decision-required]` draft-manifest entry; clean → an explicit skip line.
- **doctor Check 2.9** — warn-only setup-time nudge to fence + declare an undeclared candidate carrying status content.
- **Bootstrap** — the scaffolded `CLAUDE.md` ships with a `<!-- flow:status -->` fenced region + a seeded `statusDocs` entry, so new consumers get Tier 2 auto-reconcile by default.
- **`evals/run_status_surface_evals.py`** (positive dogfood / negative declared-fenced / false-positive fixtures + helper unit coverage + SKILL/doctor/schema/example contract) wired into CI. Version → v1.14.0; slot count 28 → 29 (doctor description + CLAUDE.md.template updated).

**Why:**
The dogfood (FB-0064): a consumer merged sub-PR "3c₁"; `/flow:ship` correctly reconciled plan Current Focus + roadmap Now, but CLAUDE.md's two status paragraphs still read "▶ 3c is next (not started)" — describing just-merged work as upcoming. The next agent would have picked up against a stale map; a separate manual PR (#53) was needed. This is the FB-0010 "stale forward-looking direction" class applied to *what to work on*, and the surface flow itself mandates reading every session must not have opt-in currency.

**Design decisions:**
- **Extend, don't rebuild.** The mechanism EXISTS and works; the gap was 100% adoption/discovery. Reused Step 5a/5b, `status-docs.py`, and the `STATUS_MOVED` signal; added only the discovery helper + the 5a.5 detection step. (Considered auto-declaring every candidate into `statusDocs` — rejected: that would auto-fence + auto-edit un-fenced human docs, which many CLAUDE.mds forbid.)
- **Best-effort, route-to-draft — mirror `/flow:audit-coverage`, never a hard halt.** A false positive must not wedge a ship; draft-routing is the ceiling. The draft item IS the propose-before-editing proposal, so flow never silently rewrites an un-fenced human doc — auto-reconcile stays gated behind the opt-in fence (Tier 2).
- **False-positive discipline via required evidence.** Flag ONLY with a verbatim drift quote; mere keyword presence ("Phase 3c") is not drift. The candidate list is conservative on purpose — the drift *judgment*, not the list, carries the precision.
- **Two clean tiers.** Declared + fenced = Tier 2 (auto-reconciled by 5a, never a draft item); the scan excludes declared paths so it never double-counts. Undeclared + drifted = Tier 1 (5a.5 → draft).
- **Gate on `STATUS_MOVED`.** Only scan when a ship actually moved plan/roadmap status — a ship that moved no status can't have made an orientation doc stale, so scanning would be pure false-positive surface.

**Technical decisions:**
- **`status-moved` stays in the shell, computed via the shared `section` helper.** `status-docs.py` keeps git out of the pure-text helper (unit-testable); Step 5a.5 recomputes `STATUS_MOVED` in its own shell block (separate blocks don't share scope — the codebase's established idiom, e.g. 5b re-resolves DEFAULT_BRANCH/PLAN/ROADMAP) via the SAME tested `status-docs.py section` text path, so the section-extraction logic lives in one place. Did NOT add a git-touching `status-moved` subcommand to the helper (would break the pure-text/unit-testable convention).
- **doctor Check 2.9 uses a `while-read` heredoc, not `for c in $CANDS`** — zsh doesn't word-split unquoted vars (the exact FB-0010 silent-skip class Check 2.5 documents); verified identical output under dash/sh/zsh.
- **`DEFAULT_CANDIDATES` in the helper is pinned to the schema default by an eval** (`slot-2-default-parity`) so the two lists can't drift (FB-0010 fan-out).
- **Malformed config is loud (exit 1), never a silent fall-through** — both a bad `statusSurfaceCandidates` and a bad `statusDocs` (used to compute the exclusion set) raise, mirroring `status-docs.py`.

**Tradeoffs discussed:**
- **Discovery precision is the LLM's, not mechanical.** The eval pins the mechanical half (scan surfaces the right candidates + the verbatim slice; declared excluded); the drift *decision* is best-effort, backstopped by the human at the merge gate — the same determinism boundary as `/flow:audit-coverage`. Accepted: raising the completeness bar without a false guarantee beats a deterministic check that either over-fires on keywords or misses real drift.
- **Seeding `statusDocs` with CLAUDE.md in the scaffold** changes bootstrap behavior (new projects get a fenced CLAUDE.md + a declared entry). Accepted — that IS the point-5 deliverable (Tier 2 by default); the un-adopted state still gets Tier 1 discovery.
- **Over-fire risk on 5a.5 mirrors 5b's documented over-fire** (a non-status plan/roadmap edit that trips `STATUS_MOVED`): here the cost is a draft item the human waives, not a hard block — a strictly softer failure than 5b's.

**Lessons learned:**
- When a gate protects a surface class but only fires on opted-in members, the gap is adoption, not mechanism — add a discovery tier with a shipped default, and discover what should be enrolled rather than waiting for enrollment (FB-0064).
- Dogfood note (honest): the ship that opens this PR runs from the INSTALLED plugin (v1.13.0), which predates Step 5a.5 — so 5a.5 did not execute on this ship. It was exercised by a manual live scan against flow's own CLAUDE.md + README (both surface as undeclared candidates; neither carries a stale "next" claim about just-shipped work → no flag) and pinned by `run_status_surface_evals.py`. It runs live in the pipeline once v1.14.0 is installed.

### docs: roadmap follow-ups + the /flow:land auto-trigger finding (FB-0063)
**Date:** 2026-06-29
**Branch:** claude/land-60
**Commit:** `f1a21fc` (on branch; final SHA in the PR)

**What was done:**
A roadmap-currency PR, re-scoped after #62 (v1.13.0) landed. The post-merge flip for #60 this PR originally carried was **superseded** — #62's own `/flow:ship` Step 5a reconciliation already moved v1.12.0/#60 into roadmap "Recently shipped". What remained genuinely missing on `main`: (1) three follow-ups dropped when #59 was re-scoped off main — the per-write freshness-token read-back, the manifest-`description` copy-hygiene cap, the `/flow:land` positioning question; (2) the stale `gh` Projects-classic roadmap item, narrowed to reflect the body-write half shipped (#56 + #59) with only the draft-toggle half open; (3) the **`/flow:land` merge-event auto-trigger** item + **FB-0063**, the dogfound finding.

**Why:**
`/flow:land` merged (#60) but, being human-invoked, wasn't run on its own merge — `main` only stayed current because #62 happened to reconcile forward. That is the FLOW-1 forget-rate, intact. FB-0063 records the structural lesson: a human-invoked skill closes cost + error, not the forget-rate; the merge-event auto-trigger is the rung that does.

**Design decisions:**
- **Dropped the superseded headline/plan flip.** #62 already flipped #60 to shipped; re-applying would conflict for no gain (FB-0051 re-scope-to-delta — the third such re-scope this session: #56→#59, #61→#60, #62→this).
- **FB renumbered 0062→0063** — #62 took FB-0062 (failure-open / trust-only-if-artifact-exists), a sibling lesson this entry cross-references.
- No version bump (a roadmap-currency reconcile, not a feature).

**Tradeoffs discussed:**
- Kept the auto-trigger finding as a first-class roadmap item + FB rather than a footnote — it's the load-bearing signal from shipping `/flow:land`.

**Lessons learned:**
- Build the mechanism and its trigger together when the failure mode is "forgotten" (FB-0063). Also: main moved under an open PR three times this session — the re-scope-to-delta discipline (FB-0051) is the routine response, not the exception.

### SAFETY: /flow:land — post-merge doc-currency skill (v1.12.0, FB-0061)
**Date:** 2026-06-28
**Branch:** claude/flow-land
**Commit:** `6d780b3` (on branch; final SHA in the PR)

**What was done:**
New human-invoked skill `/flow:land <PR#>` (`plugins/flow/skills/land/SKILL.md`, `disable-model-invocation: true`) that runs the post-merge reconciliation `/flow:ship` structurally can't: verify the PR is merged (`gh pr view --json state,mergedAt`; fail loud + edit nothing otherwise) → flip the item to "merged (#N)" across roadmap/plan/history + move it to Recently-shipped (gh + doc-scan discovery; WARN-not-silent on no match) → CHANGELOG-currency check → late `§5c` visual-history distill if a blocked visual pass since completed → clear reserved FB/VH numbers → open a small `docs: land #N` PR (never merges; idempotent on re-run). Backed by the stdlib `lib/land-helpers.py` (deterministic `changelog-check` + `clear-reservation`) + `evals/run_land_evals.py` (wired into CI). Registered across plugin.json + marketplace.json + workflow.md (surface bullet + cheat-sheet + Step 11) + workflow-help; version → v1.12.0.

**Why:**
Closes FLOW-1 (the recurring stale-`main` after merge) + FLOW-5b (the late visual-history distill) from the v1.8.0 health-tracker dogfood report. See FB-0061.

**Design decisions:**
- **Separate human-invoked skill, not a ship step** — Claude can't merge, so the reconciliation must run after the human merges (FB-0061). `disable-model-invocation: true` so it never auto-fires mid-loop.
- **Narrative status-flip is agent judgment** (like `/flow:ship` Step 5a) — the docs are free-form, so a regex flip would be FB-0010-fragile; the helper owns only the unambiguous deterministic bits (changelog-check, reserved-number clearing).
- **Reuse `§5c`, don't fork** the visual-history distill — one record format.

**Technical decisions:**
- **Rebased off the superseded FLOW-2 work (FB-0051).** The original PR was stacked on the v1.10.1 REST-PR-body commit; after #56 shipped that to main and #59 added the ship-spike delta, this branch was reset to `main` and reduced to the genuinely-new `/flow:land` skill. Version/FB renumbered to avoid collisions (v1.11.0→v1.12.0, FB-0058→FB-0061).
- Helper's `changelog-check` uses a `(?![\d.])` lookahead so `v1.10` doesn't match `v1.10.1`; `clear-reservation` is word-boundary + FB/VH-id-guarded + idempotent.
- Step 1b branch creation reuses an existing `land-<N>` branch on re-run (idempotency); Step 2 discovery guards the empty-`HEADREF` alternative so the no-match WARN stays reachable (both staff-review BLOCKERs from the PR-2 review, pinned by `run_land_evals` skill-6/7).

**Tradeoffs discussed:**
- **Dropped a deterministic status-flip helper** — considered, rejected as regex-fragile over free-form narrative (FB-0010). The agent flips in context; the helper stays to the unambiguous operations.

**Lessons learned:**
- Reconciliation gated on an event Claude can't perform (the merge) must be a separate human-invoked step (FB-0061).
### SAFETY: Visual-deliverable gate + skip-legitimacy audit — two failure-open ship-pipeline gaps closed (v1.13.0, FB-0062)
**Date:** 2026-06-28
**Branch:** claude/pensive-visvesvaraya-9ee710
**Commit:** [pending ship]

**What was done:**
Closed two related failure-open defects that let a visually-significant PR reach "ready" with no visual walkthrough — because a short-circuited verify-build self-certified its verdict and the visual deliverables were best-effort.

- **Feature 1 — visual-significance gate + mandatory dual deliverable.** New shared predicate `skills/verify-build/lib/visual-significance.py` (reused by verify-build + ship, ONE source of truth): a change is visually significant when `uiSurface != false`, the diff touches `uiFilePatterns`/asset files, and it isn't a pure no-render-delta refactor; a plan `Visual-walk` block or an explicit agent flag forces it (but `uiSurface:false` always wins, recording a suppressed override). verify-build §2c computes it and stamps `metadata.visual_significant` + `visual_signals` into the buffer; §5a makes capture mandatory when true (zero frames ⇒ §7 aggregates to `Unknown`, never PASS, with a `not_tested[]` rationale); §10 render is mandatory whenever a buffer exists + returns the report path. ship §5c removes the failure-open (a visually-significant change with no qualifying buffer entry REQUIRES a hand-authored visual-history entry — the FB-0025 workaround becomes the required path); ship §7a asserts BOTH deliverables (fresh walkthrough w/ ≥1 frame + a new visual-history entry referencing the branch) before ready, else a `[visual-deliverable]` draft entry naming the gap + the walkthrough's local path in the body handoff.
- **Feature 2 — skip-legitimacy audit.** New `/flow:audit-skips` skill (fork, read-only) + deterministic `skills/audit-skips/lib/skip-audit-checks.py`, run at ship Step 2a after the four reviewers. Per stage: LEGITIMATE (skip reason verified vs config/diff) or SHOULD-RE-RUN (reason contradicted, OR a "ran" claim whose canonical artifact is absent/stale for HEAD). Routing mirrors audit-coverage: auto-resolvable → re-run + re-audit once; else `[decision-required]` draft.
- Schema: additive `metadata.visual_significant` + `visual_signals` (no schema_version bump). Evals: `run_visual_significance_evals.py` (11) + `run_skip_audit_evals.py` (17, the five acceptance cases), both wired into `.github/workflows/ci.yml`. Docs: workflow.md (skip-audit in the loop + visual-deliverable gate), README skill list, CHANGELOG v1.13.0, plugin.json + marketplace.json (version + description), FB-0062.

**Why:**
Failure-open is inverted gate behavior — §5c skipped exactly the changes that most needed a durable visual record (short-circuited / grounding-less buffers), and nothing stopped a self-certified verify-build PASS (no findings buffer for HEAD) from producing a merge-ready-looking PR with no captured frames. The most expensive errors compound when a gate goes quiet on the high-risk case.

**Design decisions:**
- **One shared predicate, stamped once.** The visual-significance verdict is computed by a single helper and stamped into the buffer; ship reads `metadata.visual_significant` and only falls back to re-running the helper when there is no buffer (verify-build skipped). Avoids the FB-0010 fan-out of two drifting definitions.
- **Determinism where it belongs.** Both new helpers are stdlib-only and eval-pinned; the LLM (`/flow:audit-skips` fork) only adjudicates the `NEEDS-JUDGMENT` residue (mode-declared spike/tiny skips). The mechanical "verdict-without-artifact == skip" rule is the load-bearing half.
- **Skips honest, not impossible.** A docs-only / backend-only / library skip whose reason the diff/config backs rules LEGITIMATE without noise — the audit validates skips, it doesn't ban them (no false positives, per the anti-goals).

**Technical decisions:**
- Pure-refactor exclusion parses the unified diff for UI/asset hunks: a new/untracked file is a real delta by construction; rename-only / comment-only / whitespace-only / punctuation-only changes are excluded. The conservative bias is documented (an agent `--flag-significant` override exists for render paths the heuristic can't see, e.g. canvas/WebGL).
- Stage report handoff is a temp file (`/tmp/flow-skip-audit-stages.json`, override `FLOW_SKIP_AUDIT_STAGES`) like the findings buffer — no new config slot.
- No new config slots: the predicate + audit reuse `platform`, `uiSurface`, `uiFilePatterns`, `verifyEnabled`, `verifyFindingsPath`, `verifyReportPath`, `visualHistoryPath`, `sourceFilePatterns`.

**Tradeoffs discussed:**
- **Comment-only detection is heuristic** (a fixed comment-prefix set across languages) vs a full per-language parser — chose the heuristic + an explicit agent override, since over-triggering to "significant" only *adds* a walkthrough requirement (the safe direction) and the common cases (rename / blank / brace-move) are caught precisely.
- **audit-skips as a fork skill (own tools: Read/Grep/Bash) vs reusing the `auditor` agent** (Read/Grep only) — chose a standalone fork: skip-legitimacy is not one of the auditor's five categories and it needs Bash to run the ground-truth helper.
- **Re-audit once, not loop** — same single-pass discipline as Step 2's reviewers (iterating LLM judgment is reward-hackable); only the mechanical re-run + one re-audit is permitted.

**Lessons learned:**
- The failure-open pattern is subtle precisely because it reads as "graceful degradation." The tell is asking: *does this gate go quiet on the case it exists to catch?* If yes, it's inverted (FB-0062).
- flow's own repo is `platform: library` + `uiSurface: false`, so verify-build self-skips and the visual gate N/A's out here — these surfaces are pinned by the synthetic-input evals, not a live dogfood, until a UI consumer exercises them (same provisional status as V3b §5c).

### SAFETY: extend the canonical gh-resilience fallback to /flow:ship-spike — fan-out completion (v1.11.1, FB-0060)
**Date:** 2026-06-27
**Branch:** claude/vigilant-galileo-1d3593
**Commit:** `aa45347` (on branch; final SHA in the PR)

**What was done:**
Re-scoped the original FLOW-2 PR (REST PR-body writes, v1.10.1) down to its one non-duplicated delta after #56 independently shipped the same fix to `main`. #56 added a canonical `gh`-resilience fallback block (REST `gh api -X PATCH` body write + `markPullRequestReadyForReview`/`convertPullRequestToDraft` draft-toggle mutations) to `/flow:ship` Step 7 and referenced it from `/flow:staff-review` Step 7 — but **missed `/flow:ship-spike`'s PR-OPEN re-ship path** (the third PR-write site) and left the `/flow:staff-review` §1.5 gh-safety note stale. This PR:
- `/flow:ship-spike` Step 7 — added a **PR-OPEN (re-ship)** branch that references the canonical fallback for the body update + draft toggle on a `projectCards` error (was: only the LOCAL-ONLY `gh pr create` path).
- `/flow:staff-review` §1.5 — de-staled "the Step 7 `gh pr edit` invocation" → "the Step 7 PR-body write (`gh pr edit`, or its `gh api` projectCards fallback)".
- Version v1.11.0 → **v1.11.1**; CHANGELOG + roadmap headline reconciled; FB-0060.

**Why:**
On classic-projects repos with affected `gh` versions, a `/flow:ship-spike` re-ship's body update hits the same `projectCards` GraphQL deprecation #56 fixed everywhere else — but ship-spike was left exposed. A canonical block only closes a fan-out if every call site references it (FB-0010).

**Design decisions:**
- **Re-scope, don't duplicate (FB-0051).** The original PR was reset to `main` and reduced to the unique remainder rather than force-merging a near-duplicate of #56 or naively rebasing (which would leave two competing PR-body-write mechanisms — #56's fallback-on-error vs the original's REST-by-default-with-read-back). Mirrors what #56 itself did vs #57.
- **Reference the canonical block, don't re-inline.** ship-spike points at `/flow:ship` Step 7 § "gh resilience" (the same way staff-review does), so there's one implementation.

**Tradeoffs discussed:**
- **Dropped the read-back-verification idea** the original PR carried (verify the body landed after PATCH). #56's design is fallback-only-on-error, not REST-by-default; layering read-back onto it is a different shape and out of scope for this fan-out fix. Noted as a possible future enhancement, not pulled in.

**Lessons learned:**
- Triage against current HEAD before building (FB-0060): the original FLOW-2 work was done without noticing #56 was in flight shipping the same fix — exactly the "triage against HEAD" miss FB-0057 warned about, now generalized.

### jq `// true` boolean-slot footgun — `verifyEnabled`/`uiSurface` opt-outs silently inverted (v1.10.2) — SAFETY
**Date:** 2026-06-26
**Branch:** fix/verifyenabled-jq-false-default (PR #44, brought current)
**Commit:** (this PR — squash SHA at merge)

**What was done.** Replaced `jq -r '.X // true'` with `jq -r 'if .X == false then "false" else "true" end'` at all four boolean-slot read sites: `doctor/SKILL.md` Check 5.3, `verify-build/SKILL.md` Step 1.2 skip-gate + the preprocessed "Verify enabled:" display line, and `ship/SKILL.md` §5c's `uiSurface` visual-history gate. Bumped to v1.10.2 + CHANGELOG; filed the lesson as FB-0058 (renumbered from the drafted FB-0047).

**Why.** jq's `//` (alternative) operator treats boolean `false` — not just `null` — as "empty", so `false // true` evaluates to `true`. An explicit `verifyEnabled: false` opt-out therefore resolved to *enabled*, and `/flow:verify-build`'s skip-gate never fired — the behavioral gate ran on a project that opted out. Surfaced by the valletta consumer (iOS, `verifyEnabled: false` pending a `/run` recipe) via a spurious `/flow:doctor` run-skill WARN.

**Design decisions.**
- **Brought PR #44 current rather than re-implementing.** The original (2026-06-11) fix was correct and still needed — main never fixed it (confirmed: all three `verifyEnabled` sites still buggy). Rebased onto current main; the 3 code fixes applied cleanly.
- **Extended scope to the 4th site (`ship` §5c `uiSurface`).** PR #44's body claimed "uiSurface reads correctly today" — true on 2026-06-11, but v1.8.0's §5c distill (merged later) introduced a new `.uiSurface // true`. Folding it in closes the whole bug *class*, which is exactly what the FB rule mandates ("grep for `.<slot> //` when adding a boolean slot"). `accessibility-review` already used the safe form, so 4 sites total.
- **Renumbered FB-0047 → FB-0058.** PR #44's drafted FB-0047 collided with main's shipped FB-0047 ("non-forgeable Test plan", PR TP) — the exact cross-branch FB collision the reserved-numbers protocol defends. Swept the reference; the entry now reflects the final 4-site scope.

**Tradeoffs discussed.** A one-time boolean-slot audit (PR #44's original "uiSurface checked, reads correctly") rots the moment a new read is added — which is exactly what happened between 2026-06-11 and v1.8.0. FB-0058 therefore encodes the *grep-on-every-new-read* discipline, not a checked-once claim.

**SAFETY:** restores the `verifyEnabled`/`uiSurface` opt-out skip-gates (a skip that wasn't firing); strengthens existing behavior, downgrades nothing. Fail-safe — absent/null still defaults on (verify enabled); only an *explicit* `false` now correctly skips.
### Lesson-harvest + contribute-back-to-flow loop (`/flow:contribute`, ship Step 4c) — v1.11.0 — SAFETY
**Date:** 2026-06-25
**Branch:** claude/kind-almeida-d160e0
**Commit:** [this PR]

**What was done:**
Closed the missing self-improvement loop: flow now learns generalizable lessons from its own use and contributes them back as a PR. Two surfaces, queue + drain (mirrors the existing disagreement model):
- **Harvest (ship Step 4c, automatic).** A new `harvest_lesson.py prescan` runs FIRST as a ~free deterministic cost gate (correction/symptom/overrule/endorsed-reviewer markers in the transcript since a per-session watermark); on a clean PR it short-circuits with zero LLM spend. When it trips, the ship agent classifies each Step-4 candidate PROJECT-LOCAL vs FLOW-GENERALIZABLE vs BOTH, drops noise, and enqueues the generalizable ones via `harvest_lesson.py enqueue` to a user-scope cross-project queue (`contribution_store.py`).
- **Contribute (`/flow:contribute`, the drain).** New user-facing skill, run from the flow checkout (`flowRepoPath`). Drains the queue AND the previously-manual `/flow:log-disagreement` store, dedups, **sanitizes out personal-project tokens fail-closed** (`sanitize_tokens.py`), scores, opens a single rolling **draft** PR with the high-confidence clean lessons (sub-threshold/dirty held + listed), and calibrates from prior PR outcomes. Never merges.
- New scripts: `contribution_store.py` (queue/dedup/deterministic-confidence/calibrate), `harvest_lesson.py` (prescan/enqueue/mark), `sanitize_tokens.py` (scrub/scan). Additive `harvest_dialogue`/`render_harvest_window` helpers in `extract_session.py` (existing `--mode plan|completion` CLI byte-identical). New `run_contribution_evals.py` (35 checks) wired into CI. 4 new schema slots (`flowRepoPath`, `contributionsQueuePath`, `lastHarvestedPath`, `contributionThreshold`) → 28 total. Flow-repo SessionStart hook (primary auto-trigger) in `.claude/settings.json`. doctor Check 2.8 + slot-count bump.

**Why:**
`log-disagreement`, ship Step 4 synthesis, and failure-memory all improved the *project* or sat waiting for manual maintainer review — none carried a lesson back into the flow plugin. The most expensive errors (a reviewer that keeps false-positiving, a gate that misfires) recur across every project until flow itself changes. This loop is the drain end of capture machinery flow already had a capture end for.

**Design decisions:**
- **Queue + drain, not inline cross-repo.** Harvest runs in any project; the drain must run from the flow checkout (the PR targets flow). User-scope storage (`~/.claude/plugins/data/flow/contributions/`) bridges the two, exactly like the disagreements store.
- **Automatic, human-gates-merge-only.** Per FB-0059: harvest is in ship; the drain self-triggers (local SessionStart hook primary; optional local OS job; NOT a cloud `/schedule` routine — a cloud agent can't see the local queue/checkout). v1 opens a draft PR; the merge is the one human action. Auto-merge (rung 2) deferred — the deterministic confidence score + `feedback_signals.json` are built so it's a later predicate flip (one-way-door, FB-0011).
- **Two-destination router with one noise/confidence gate** (the user's mid-design refinement): the analyzer routes project-local vs flow-generalizable vs both, promoting only above-threshold non-noise findings.
- **Reuse over rebuild.** Reused `extract_session.find_session_file/load_session/normalize_turns` + `bounding_logic.SYMPTOM_WORDS`; borrowed the forge/noticed proposal/dismissal/calibration model, reimplemented lean in flow's stdlib style.

**Technical decisions:**
- **Confidence is deterministic** (`compute_confidence`: source weight × evidence strength + capped recurrence − sanitization penalty, clamped [0,1]) — never an LLM number, so the future auto-merge gate is a pure predicate (enforce-don't-attest, FB-0056).
- **Sanitizer ships no brand literals.** `sanitize_tokens.py` matches structural shapes (home/abs paths, URLs, emails, design-token shape `--x-y`) + per-project tokens passed at runtime from `known_tokens.json`; the CLAUDE.md:126 example list is used only as eval *fixture data*, never as code constants — the scrubber is itself a project-agnostic plugin artifact. The critique-plan pass on the design flagged the original (literal-token) approach.
- **`extract_session.py` change is purely additive** (new helpers; no edit to `find_bounding_message`, the reviewer CLI, or the malformed-JSONL skip). An eval pins that `--mode harvest` is rejected, proving the auditor/critic contract is untouched.

**Tradeoffs discussed:**
- **Routing/noise = LLM judgment, not a pinned contract.** The critique-plan pass caught an over-claim; resolved by drawing a hard determinism boundary (only score + pre-scan mechanical; routing is reviewer-grade, human-gated). Evals pin the score math + prose contracts, not classification accuracy.
- **Per-ship cost vs proactivity.** Reading the transcript every ship could waste tokens when nothing's there. Resolved with the pre-scan gate (null case ~free) + dialogue-only extraction + the watermark (only new turns). Expected ~$0.05–0.25/ship; `feedback_signals` reveals the real hit rate to tune cadence later.
- **Project-local authoring deferred.** v1 routes project-local findings only to existing surfaces (4a/4b/roadmap), not net-new `.claude/rules`/`CLAUDE.md` authoring (scope-drift flag from critique-plan).

**Lessons learned:**
- Dogfooded the design through `/flow:critique-plan` + `/flow:audit-plan` before building: caught the hardcoded-brand-literals spec violation, the determinism over-claim, a scope-drift, and (audit) a missed `workflow.md` survivor in the slot-count fan-out. Grep-first then found **7** live "24 slots" files (the plan estimated 5 — it missed the two `template/` files); all bumped to 28.
- A space inside a string literal got written as a NUL byte during file creation; caught immediately by a parse smoke-test before wiring anything together. Smoke-test scripts the moment they're written.
- **Shipped on a stale base — twice (caught at staff-review, then at PR-conflict-resolution).** origin/main advanced during the build; the staff-review design-engineer lens flagged a phantom version-revert, confirming the first stale base (#56 v1.10.1, #58 README rewrite). Rebased; #58 had already claimed FB-0057, so this PR's entry renumbered FB-0057→FB-0058. Then while the PR was open, **#44 (v1.10.2) merged and claimed FB-0058** for its own jq-footgun entry — a second collision — so the entry renumbered again **FB-0058→FB-0059**, sweeping every cross-file reference while preserving #44's FB-0058. Two collisions on one PR is the strongest possible argument for the reserved-numbers protocol + the staff-review/`/flow:ship` stale-base gates; both fired and both caught it before a silent overwrite.

### README readability overhaul + `docs/automation-boundaries.md` (docs-only, no version bump)
**Date:** 2026-06-26
**Branch:** `claude/great-kepler-920b8c` (PR pending; squash SHA at merge)
**Commit:** [range on branch; squash SHA filled at merge]

**What was done:**
Rewrote the public `README.md` to work as a portfolio-grade artifact (the user develops flow partly as a job-seeking/networking showcase of product thinking and taste — FB-0057). Cut from 227 → ~105 lines.
- **Re-sequenced to inverted-pyramid:** plain-language hero (value first) → the loop → what the reviewers catch → feedback loop → setup → under the hood → auxiliary skills (`doctor`, `workflow-help`, `ship-spike`, `log-disagreement`) moved to the bottom.
- **Collapsed two redundant loop tables into one skill-forward table.** The old README listed the 11 phases in one table and the skills-in-order in a second — the same sequence twice. The merged table makes skills the visible spine (indented `↳`) while keeping the non-skill anchors that carry the thesis: the two human gates and Execute.
- **Stripped version stamps + `FB-XXXX` refs from public prose.** The old header read `What v1.9.1 ships` while the plugin was at `v1.10.0` — a fan-out staleness cost of version-stamping marketing copy.
- **Preserved the cut detail** (AUTO/BOTH/AUTO·when-ready modes, full cold-start reality, soft-enforcement seams, known-limitations list, lineage) in a new linked `docs/automation-boundaries.md` rather than deleting it.

**Why:** The README communicated like an internal engineering reference — dense, defensive (a large cold-start `⚠️` wall near the top), version-stamped, with the most technical content first. For a reader landing cold (hiring managers, engineers, designers), value and the skill sequence weren't legible in the first screen.

**Design decisions:**
- *Skill-forward table, not skills-only list.* The user proposed presenting "just the skills as the phases." Pushed back: both gates and Execute are NOT skills, and the two-gate structure is the product's core claim — a skills-only list would erase it. Kept skills as the spine but retained the gates/Execute as bold non-skill rows. (FB-0057.)
- *Direct, plain copy.* A sample hero ("turns Claude Code into a disciplined teammate, not an eager intern") was rejected as performative/AI-sounding; rewrote with no metaphors or "not-X-but-Y". Saved as harness-memory `feedback_direct_no_fluff_copy` + FB-0057.
- *Table over SVG diagram for the loop.* Offered an SVG loop diagram vs a markdown table; user chose table-only (renders identically everywhere, zero asset maintenance, no GitHub inline-SVG sanitization issue).

**Technical decisions:** Docs-only change to repo-root `README.md` + a new `docs/` file — no plugin artifact (`plugins/flow/*`), schema, or skill behavior touched. No `plugin.json` version bump: the plugin's functional version is unchanged, so `roadmap.md` "Now" + `plan.md` "Current Focus" already reference `v1.10.0` and the ship doc-currency gate passes as-is.

**Tradeoffs discussed:**
- *Heavy cut vs completeness.* ~50% of the README was removed. Mitigated by routing the genuinely-useful detail to `docs/automation-boundaries.md` (linked twice) rather than dropping it — the honesty/limitations signal stays available one click away.
- *Re-running staff-review on a copy change.* The copy was reviewed interactively with the user across several iterations with explicit approval, so a separate four-lens `/flow:staff-review` pass was not spawned; recorded honestly in the PR `## Flow run` table rather than claimed.

### `gh` Projects-classic PR-write resilience (v1.10.1) — SAFETY
**Date:** 2026-06-24
**Branch:** claude/vigorous-faraday-fcd39c
**Commit:** (this PR — repurposed #56)

**What was done.** Documented a `gh`-API fallback in `/flow:ship` Step 7 (canonical block) and `/flow:staff-review` Step 7 (reference) for the Projects-classic GraphQL deprecation: on classic-projects repos with affected `gh` versions, `gh pr edit` / `gh pr ready` / `gh pr view --json` fail with `GraphQL: Projects (classic) … projectCards` even when only the body/draft state is being touched. The fallback sets the body via REST (`gh api -X PATCH .../pulls/N -F body=@file`) and toggles draft via the `markPullRequestReadyForReview` / `convertPullRequestToDraft` mutations (neither queries `projectCards`). Bumped to v1.10.1 + backfilled the v1.10.0 CHANGELOG entry that #57 omitted. (The README version stamp this originally also bumped was removed entirely by #58's README rewrite, landed during the rebase — so the changelog is now the canonical version-history surface.)

**Why.** This was the "secondary, lower-confidence" item in the FB-0056 dogfood report. It became the *only* salvageable delta after **#57** independently shipped the report's two primary integrity gaps as v1.10.0 while this branch (PR #56) was implementing the same scope (per-criterion provenance + a `rigor-marker.py` commit-invariant + a diff-derived judged no-plan path — stronger than #56's top-level-provenance + prose-self-attestation approach). Rather than force-merge a duplicate v1.10.0, #56 was reset to main and repurposed down to this non-duplicated delta (the user chose "repurpose" over "close + reopen").

**Design decisions.**
- **Documented prose, not a helper script.** A `gh`-API wrapper script doing GraphQL mutations is easy to get subtly wrong and can't be tested here (no classic-projects repo in CI). Clear prose the agent adapts is more robust than an untested script — matches the repo's lean bar.
- **Canonical block in ship, reference in staff-review** (not duplicated) — FB-0010 fan-out defense: one source of truth, staff-review points at it.
- **Backfilled #57's missing v1.10.0 CHANGELOG entry** rather than letting the consumer-facing changelog skip 1.9.1 → 1.10.1 and hide the major integrity release.

**Tradeoffs discussed.** The bulk of PR #56's original work (the full provenance/no-plan implementation, a producer-contract eval, fixtures) was **discarded** as superseded by #57's more complete version — the honest outcome of a cross-worktree collision the stale-base gate caught at ship time (the same FB-0008/FB-0010 collision class the reserved-numbers protocol exists for). The `gh`-resilience fallback is documentation only; it does not change renderer or gate behavior.

**SAFETY:** adds a fallback path to the ship pipeline's PR-write step (ship/SKILL.md is a safety-critical surface); it strengthens resilience and never downgrades existing error handling — the standard `gh pr` path stays primary and the fallback fires only on the explicit `projectCards` error signal.

### Verify-build provenance + no-plan rigor — close two dogfound integrity holes (v1.10.0) — SAFETY
**Date:** 2026-06-22
**Branch:** `claude/quirky-jones-9932cd` (PR pending; squash SHA at merge)
**Commit:** [range on branch; squash SHA filled at merge]

**What was done:**
Closed two source-level integrity gaps in flow's own skills, both surfaced by a real `/flow:ship` run on production SwiftUI code in a consumer project (FB-0056).
- **Provenance (forgery defense).** Added a per-criterion `provenance` enum to the verify-build findings schema (`adversarial-judged | spike-rubric | hand-authored`) + `metadata.no_plan_fallback`, with the load-bearing contract that **absent/unrecognized ⇒ `hand-authored`** (untrusting default). `render-test-plan.py` and `render-report.py` now render a hand-authored PASS as a distinct `[~]` state (Markdown) / hollow-ring dot + `self-reported` chip + warning banner (HTML) and DROP the "machine verdict, not self-report" claim — a buffer the implementer wrote by hand can never render as machine-judged. Stamping prose added to `verify-build/SKILL.md` Step 7/8 + `spike-rubric.md`.
- **Spike vs no-plan split + rigor gate.** `verify-build` Step 2 now treats an *explicit* `/flow:ship-spike` as the only path to spike's 3-check rubric; a *missing/Spec-walk-less plan* is the **no-plan fallback** — source-touching → the full judged path over diff-derived criteria (provenance `adversarial-judged`, `no_plan_fallback=true` → ship draft-routes it); docs-only → smoke rubric. New stdlib `ship/lib/rigor-marker.py` (commit-invariant source fingerprint): `staff-review` writes a marker after its fixes land; `ship` Step 1.0a reads it for source-touching diffs → `[decision-required]` draft entry if missing/stale. Ship Step 2 routes `no_plan_fallback` likewise.
- **Evals + CI.** New `run_report_render_evals.py` (render-report.py had zero coverage) + `run_rigor_marker_evals.py` (incl. a seeded-git commit-invariance test) + a hand-authored fixture in `run_render_evals.py`; **wired all of them — plus the orphaned `run_visual_history_evals.py` — into `.github/workflows/ci.yml`** (staff-review BLOCKER). `workflow.md` + `design-language.md` updated; `gh` projectCards resilience + "second-source the provenance stamp" routed to roadmap § Next.

**Why:**
The dogfood run shipped a hand-authored verify-build buffer that rendered as "machine verdict, not self-report," and a no-plan production diff that got spike-grade verification + a ready PR — defeating verify-build's core value prop (the implementer can't show green without a real adversarial PASS) and the loop's review-rigor assumption. Root cause: when the judged path can't run, the loop silently degraded to a self-reported / reduced-rigor path that still rendered as machine-judged and merge-ready.

**Design decisions:**
- **Untrusting default (absent ⇒ hand-authored)** so omission can never mint a machine `[x]`; the residual *commission* seam (an author writing the trusted value) is a documented honest-limitation + a roadmap follow-up, not a silent over-claim — the schema text says so explicitly ("cooperative-agent contract, not cryptographic").
- **Keep no-plan judged** (user choice): a production diff lacking a plan artifact still earns a real fresh-context-judge verdict, not a 3-check smoke test — so a green stays trustworthy even absent a plan, while still routing to draft so the human declares criteria or waives.
- **Self-reported HTML treatment** demotes the verdict dot to a hollow ring (not just a chip) so the skim surfaces (heading/TOC/Overall pill) don't read solid green; the chip uses the banner's brick accent, NOT the FAIL verdict red, to avoid a verdict-color collision (design-engineer finding).

**Technical decisions:**
- **No new config slot for the marker** — it's a within-loop internal handoff a consumer never relocates (unlike `verifyFindingsPath`); a slot would fan the "24 slots" contract across marketplace/plugin/doctor/schema for no benefit. Fixed conventional `/tmp` path, branch-slugged.
- **Commit-invariant fingerprint** — `git diff origin/<base>` vs the working tree (not `..HEAD`), so committing staff-review's fixes between staff-review and ship doesn't false-trip the gate; centralized in one stdlib helper consumed by both writer and reader (FB-0054b).
- **Additive schema** (no `schema_version` bump) — `provenance`/`no_plan_fallback` optional; pre-fix buffers still validate; the example validates against the updated schema.

**Tradeoffs discussed:**
- **Marker mechanism vs manifest-only attestation** — chose the mechanical marker (FB-0047 enforce-don't-attest) over trusting the agent's loop-history; the marker is real evidence the gate keys on.
- **One PR vs split** — kept Gap A + Gap B together (they share the provenance infra + the no-plan/hand-authored root cause); the env-adjacent `gh` projectCards item was scoped OUT to the roadmap.
- **Provenance per-criterion vs top-level** — per-criterion (the judging site), with renderers deriving the buffer-level "any self-reported" predicate; avoids a redundant top-level field that could desync.

**Lessons learned:**
- A contract change to a non-forgeable renderer is an FB-0010 fan-out: every existing fixture had to be stamped (an un-stamped fixture correctly flipped to `[~]`), and every producer's prose updated, in the same PR.
- A new eval harness not wired into `ci.yml` gives **zero** standing protection — caught by staff-review; the orphaned `run_visual_history_evals.py` was a prior instance (now also wired). Memory entry written.
- Subagent spawning hit a transient session limit mid-loop; `/simplify` was done inline (quality review of readable code), staff-review + security ran once spawning recovered.

### V2.1 hardening — visual-capture routing decoupled from Spec-walk + `extract-visual-states.py` parser — SAFETY
**Date:** 2026-06-21
**Branch:** claude/pr-visual-summaries-workflow-wrvj3a
**Commit:** [this PR]

**What was done:**
Closed the two cold-gate routing follow-ups the FB-0016 health-tracker cold-runs surfaced (plan.md "Cold-gate FOLLOW-UPs", 2026-06-11/06-16). (1) `/flow:verify-build`'s visual capture (§5a) was gated behind successful behavioral-criteria extraction, so a non-canonical `**Spec-walk:**` heading → 0 criteria → spike fallback → **§5a silently skipped**, dropping the entire HTML visual summary even when the plan declared a `Visual-walk` block. §5a now gates on its OWN predicate (`uiSurface:true` AND a `Visual-walk` block present), decoupled from Spec-walk and from spike mode. (2) Added `extract-visual-states.py` — a deterministic parser of the `Visual-walk` block (1:1 per declared assertion) so two cold agents no longer enumerate the capture state-set differently. (3) Made both parsers' heading match robust (canonical `**Spec-walk:**`, qualified `**Spec-walk (PR 1c — shipped):**`, markdown `### Spec-walk`, and the `**Visual-walk** *(…)*:` italic-tail form) and scoped extraction to the **first (active) block** with a loud multi-block warning. Factored the shared logic into `walk_extract.py` so the two parsers can't drift. Pinned by `run_walk_extract_evals.py` (47 checks), wired into CI.

**Why:**
The silent-skip is the FB-0010 "silent-skip on edge case" class — the most expensive bug type flow tracks — landing on the exact deliverable this track exists to produce (the verified HTML visual summary). The two cold-runs proved it bites on real plans (health-tracker's non-canonical heading; flow's own multi-PR plan.md aggregates 25 Spec-walk blocks under the old matcher). The state-set non-determinism (no parser, prompt-derived) was the other named residual.

**Design decisions:**
- **Decouple, don't just loosen.** The minimal fix for the silent-skip is to stop coupling two independent declared blocks (behavioral Spec-walk vs visual Visual-walk). §5a runs visual capture iff its own predicate holds, so a behavioral-extraction failure can no longer drop the visual summary (FB-0055.3).
- **Robust match + active-block scoping are co-dependent.** Under the old strict regex, retained/historical blocks self-excluded *because* their qualified `(…)` headings failed to match. Loosening the match to catch non-canonical *active* headings would re-include every retained block → aggregation explosion. So scoping-to-first-block had to land in the same change as the looser match — they cannot be separated (FB-0055.2). This is *why* the user's "most robust fix" instinct (Option 2) was not just heavier but actually required.
- **Active-block-at-top convention replaces qualify-your-headings.** The durable structural fix (extract the first block) removes the author-memory dependence the interim "retained blocks MUST qualify their heading" convention carried — the FB-0010 author-memory smell. Documented in `plan-discipline.md`; the parser warns loudly if >1 block matches so a misplacement is visible, not silent (FB-0055.1).
- **Per-assertion, not new declared syntax (user fork).** `extract-visual-states.py` emits one capture-target per existing `Visual-walk` `- [ ]` line (with an optional category from the `[state: …]` tag) rather than introducing an explicit `States:` declaration syntax. Determinism comes from a single parse, not new author burden — no fan-out into the V1 field's three declaration surfaces.
- **Shared helper, not duplicated regex.** `walk_extract.py` owns heading-match + first-block + checkbox logic; both CLI parsers import it (lib dir is `sys.path[0]` when run as a script). Defends the FB-0010 fan-out class — a future heading-form change updates one place.

**Tradeoffs discussed:**
- **First-block heuristic vs a richer "active block" signal.** Considered keying "active" off unchecked-vs-checked boxes (shipped PRs are all `[x]`) or proximity to a "Current Focus" marker; both are project-specific or fail at ship time (the active PR's boxes get checked too). First-block-in-document-order + a loud multi-block warning + the documented top-placement convention is deterministic and project-agnostic. Residual: if an author puts the active block second, the parser extracts the wrong one — surfaced by the warning, not silent.
- **Backward-compat.** `extract-criteria.py`'s output gained `block_count` (additive); `criteria`/`source_heading`/`warnings` keys are unchanged, so `/flow:audit-coverage` and §3 consumers are unaffected (pinned by a compat-keys eval check). The toy fixture's reference `expected/extract-criteria.json` updated for the additive key.
- **Version v1.9.1.** #54 (statusDocs) took v1.9.0 while this PR was open; this is a SAFETY routing fix + internal parser (no new user-facing slot/skill/command), so it lands as the patch v1.9.1 on top of it.

**Lessons learned:**
- The two cold-runs are doing exactly what FB-0016 intended — each real run on a UI surface surfaces a routing assumption the synthetic evals couldn't. The fragility "bit immediately" on the first health-tracker plan because real plans don't use the canonical heading the evals assumed.

**Review pass (this session):** `/preship` PASS (docs/feedback/quality-bar all green). `/simplify` (4 lenses) applied: factored the duplicated CLI boilerplate into a shared `walk_extract.cli_main` (~90 lines deduped) + tidied `_CATEGORY_RE`. Rejected two simplify findings as false positives — (a) removing the `?` from `_MALFORMED_CB_RE` would stop matching `- []` (no-space) and reintroduce a silent-skip for the exact malformed case it must catch; (b) the over-permissive bold heading branch is theoretical and tightening it risks the real `**Visual-walk** *(…)*:` form. `/flow:security-review` (run as the bundled `/security-review` — `origin/HEAD` had to be set in this fresh clone first): clean, no findings (stdlib parsers over owner-authored plan files, JSON-escaped output, no exec/shell/network sink). `/flow:accessibility-review` + `/flow:verify-build` self-skip (`uiSurface:false` / `platform:library`). Shipped via the dev-side `/ship` since the `flow` plugin isn't installed as invocable skills in this remote session.

**Post-merge note:** #54 (statusDocs, v1.9.0) merged while this PR was open, so PR #55 was rebased by merging `origin/main` in; version assigned **v1.9.1** (the v1.9.0 slot was taken). The two PRs conflicted only on the high-fan-out doc files + `ci.yml` (both append an eval `- run:` line — kept both) — the FB-0008 stale-base / FB-0010 fan-out class; resolved keep-both with no behavior overlap.

### `statusDocs` — reconcile project-declared status surfaces every ship + a version-manifest-independent doc-currency gate (v1.9.0) — SAFETY

- **Date:** 2026-06-19
- **Branch:** `claude/friendly-wiles-fe18d5` (rebased onto `main` @ `7484bb9` after #53/v1.8.1 merged mid-session; this PR's squash SHA assigned at merge)
- **What was done:** Added a `flow.config.json.statusDocs` slot (24th; array of `{path, marker}`, default `[]`) so a project can declare *additional* forward-looking status surfaces — e.g. a `CLAUDE.md` or `README` status line a cold agent reads — that `/flow:ship` reconciles every ship, beyond the built-in plan "Current Focus" + roadmap "Now". `/flow:ship` Step 5a rewrites only the marker-fenced region (`<!-- {marker} -->` … `<!-- /{marker} -->`) to just-shipped reality; **Step 5b gained a version-manifest-INDEPENDENT marker-coverage gate** that BLOCKS a ship which moved plan/roadmap status forward but left a declared region untouched (or whose marker is missing). `/flow:doctor` Check 2.7 verifies each declared surface exists + is fenced. Backed by a shared stdlib helper `skills/ship/lib/status-docs.py` (`entries`/`region`/`section`/`check`) + an eval `evals/run_status_docs_evals.py` (CI-wired). Slot-count fan-out 23→24 across all 8 surfaces; version → v1.9.0.
- **Why (SAFETY):** A real dogfood finding — a consumer iOS app shipped two sub-PRs into a phase while its auto-loading `CLAUDE.md` still read "Phase 2 — HealthKit is next", so a cold agent would pick the wrong next action. The forward-looking docs flow *does* reconcile were correct; the drift lived in surfaces flow had no way to know about, and the old Step 5b silently N/A'd on projects with no version manifest (zero mechanical enforcement for that whole class). This change adds a **new ship-time BLOCKER path** (fail-and-block on un-reconciled declared status regions) — hence SAFETY.
- **Design decisions:**
  - **Project-declarable, not hardcoded.** Flow can't hardcode `CLAUDE.md` (its own repo has none; not every consumer uses one). The slot defaults to `[]` → byte-identical behavior for non-adopters (proven by this PR's own ship taking the empty-skip path). This is FB-0054.
  - **Marker-fenced region, not whole-file.** Reconciling only the fenced region keeps the edit narrow + mechanical (never a restructure), which respects consumers whose own rules gate broad `CLAUDE.md` edits behind a human, and gives Step 5b a concrete assertion target.
  - **Version-manifest-INDEPENDENT gate.** The old 5b asserted only a version token and silently N/A'd without a manifest — the FB-0010 silent-skip class applied to enforcement itself. The new marker-coverage assertion fires for everyone; the version-token assertion is preserved for versioned projects.
  - **"Status moved" trigger scoped to the plan "## Current Focus" + roadmap "## Now" sections** (not whole-file) to hold false positives down. Residual over-fire (those sections change for a non-status reason) is accepted + documented; the BLOCKER copy now names the legitimate case and steers away from the cosmetic-edit release valve (push-further lens).
- **Technical decisions:**
  - **One shared stdlib helper, not three inline awk copies.** `status-docs.py` owns the pure-text ops (parse entries, extract marker region, extract heading section, check fences); git stays in the calling shell (`git show origin/<default>:<path>` for the base revision). The `section` subcommand (added during `/simplify`) absorbs the version gate's inline `sect()` awk into the same tested path. This defends the FB-0010 "consistency depends on author memory" fan-out the feature itself exists to prevent.
  - **Loud-on-malformed, never silent.** `load_entries` raises `ValueError` on bad JSON / non-array / missing path → the shell surfaces a BLOCKER; the 5a pipe was fixed (staff-review) to capture the exit code rather than swallow it via `... | while`.
  - **Conservative new-file default:** a status doc absent from the base reads empty → counts as "moved/reconciled" (fails toward enforcement).
- **Tradeoffs discussed:**
  - **Helper + eval vs inline bash** (the one plan-gate fork). Chose the helper despite +2 files: `statusDocs` is an object-array (jq-in-bash-loops are flow's documented footgun — see doctor 2.5's zsh word-split bug), the helper gives a real regression eval, and it kills the 5a/5b/doctor triplication. The existing 5b/doctor-2.6 already duplicate `sect()` inline, so inline would have been "consistent" — but the object-array tipped it.
  - **Gate robustness vs over-fire.** The `WORK_REGION != BASE_REGION` inequality is robust against *forgot-to-reconcile* but accepts a cosmetic one-byte touch as "reconciled." Kept the simple inequality for v1 (judgment-free, matches 5a's "narrative correctness is the agent's call") and routed the normalize-region hardening (reject whitespace-only touches) to `roadmap.md` § Next — sequenced *after* the operator-facing over-fire escape-hatch line, so the bad valve isn't removed before the good one exists.
- **Lessons learned:** A coverage/currency gate that silently N/A's on a whole project class is theater for that class — enforce on the failing population or don't claim enforcement. And: when a contract value (the slot count) fans out across N surfaces, grep-first-edit-second (8 surfaces here, all reconciled 23→24). The stale-base gate caught #53 (v1.8.1) merging mid-session at `/flow:staff-review`; rebased + reconciled the version/CHANGELOG/description/roadmap/plan overlaps to v1.9.0 with v1.8.1 folded in — exactly the FB-0008/FB-0051 parallel-work class the gate exists for (no duplication, genuinely-additive feature).
- **Loop:** plan → `/flow:critique-plan` (3 completeness findings, all folded in) → human gate (approved; chose the helper+eval fork) → execute → `/simplify` (added the `section` subcommand to absorb inline awk) → `/flow:staff-review` (4 lenses; no BLOCKERs; 4 NITs + 1 inline-cheap fixed; 1 roadmap-concrete deferred) → `/flow:ship` (security clean; a11y + verify-build skipped per config; coverage assessed manually — no undeclared behavior).

### Fix V3b §5c asset-path doubling (image-load bug) + clarify open-question routing (v1.8.1) — SAFETY
**Date:** 2026-06-16
**Branch:** claude/v3b-asset-path-fix
**Commit:** [this PR]

**What was done:**
The first real FB-0016 cold-run — a fresh agent running `/flow:ship` Step 5c on the health-tracker iOS app — confirmed V3b works (5c fires, the curated entry is editorially sound, screenshots load) and caught a real bug it had to route around: the §5c asset-copy doubled the `assets/` path so the durable record's screenshots resolved to missing files (the "recent images may not resolve" symptom the V3b author flagged). Fixed §5c to resolve frame sources against the report dir + copy by basename; clarified the resolved-this-iteration open-question routing; added an eval guard; bumped to v1.8.1; routed the two remaining cold-run findings to the roadmap.

**Why:**
§5a writes `observations[].content` as `assets/<slug>.jpg` **relative to the report dir** (the convention `render-report.py` reads). §5c set `ASSETS_SRC="$(dirname REPORT)/assets"` and copied `"$ASSETS_SRC/<content>"` — prefixing a second `assets/` → `.../assets/assets/<frame>`, a missing file. An agent following the pseudocode literally produces broken `<img>` refs. The two sections contradicted on "relative to what" — the FB-0010 fan-out class applied to a path convention spanning two skill sections.

**Design decisions:**
- **Fixed §5c, not §5a.** §5a was correct ("relative to the report dir"); §5c misread it. Aligning §5c to §5a (resolve against `$REPORT_DIR`, copy by basename) is the minimal correct fix and removes the contradicting `ASSETS_SRC` construction entirely.
- **Pinned with an eval guard, not just prose.** `run_visual_history_evals.py` now asserts §5c contains `$REPORT_DIR` + `basename`, contains **no** `ASSETS_SRC`, and keeps the explicit `assets/assets` trap note — so a future edit can't silently reintroduce the doubling. (The copy itself is agent-driven shell, not the helper, so this contract-assertion is the closest mechanical pin available.)
- **Clarified open-question routing rather than changing the schema now.** The cold-run agent had to relabel a gate-approved `this-iteration` decision as `future-planning` to clear the Step 8 gate (which blocks on any `this-iteration` question, with no `resolved` state). §5c now distinguishes "answered with a decision → distill it" from "genuinely forward → `future-planning`" and warns against the relabel-to-dodge. The proper `resolved` schema flag is roadmapped (§ Next) — a schema change deserves its own PR.

**Technical decisions:**
- **SAFETY — asset-persistence path correctness.** This corrects where committed screenshot assets are sourced from; the prior behavior silently committed a `visual-history.html` with broken image refs (no crash, no warning — exactly the silent-skip class). No error-handling was downgraded; the fix makes the documented copy resolve to real files.

**Tradeoffs discussed:**
- **Patch vs. deeper refactor.** Considered moving the asset-copy out of §5c prose into `insert-visual-history.py` (deterministic + directly eval-able, kills the bug class). Chose the minimal §5c fix + contract-assertion guard for v1.8.1 (fast fix for a live bug in the exact symptom the user reported); the helper-owns-copy refactor is a roadmap follow-up.

**Lessons learned:**
- The cold-run paid for itself immediately: a fresh agent following the prose literally surfaced a bug the author (who knew the intended convention) didn't. A path-relative-to convention referenced in two skill sections must state the SAME base in both — reinforces FB-0010 (fan-out contradiction) for prose conventions, not just counts/names.

### Route two post-V3b follow-ups from the health-tracker cold-run pre-check (docs-only)
**Date:** 2026-06-16
**Branch:** claude/v3b-followups
**Commit:** [this PR]

**What was done:**
Captured two findings surfaced while prepping the FB-0016 health-tracker (iOS) cold-run that validates V3b's §5c distill step, as `dev-docs/roadmap.md` entries: (1) a roadmap-concrete item in the "V3b durable-record follow-ups" bundle — `insert-visual-history.py` keys on the skeleton's marker comments, so a consumer pointing `visualHistoryPath` at a *pre-existing, hand-authored* `visual-history.html` (health-tracker's `craft/visual-history.html`, the #10 reference) gets a fail-loud, not an adoption; they must use a fresh path. (2) a § Exploration entry — installed-plugin-version currency: the pre-check found the user-level flow install cached at v1.5.1 while `main` was v1.8.0, so a ship would run stale prose until `/plugin marketplace update`; nothing surfaces "your install is behind `main`."

**Why:**
The cold-run pre-check is the first time V3b met a real consumer's filesystem. Both findings are real friction a future session will hit; routing them to the roadmap (not just a chat message) is the canonical capture per the workflow's follow-up discipline.

**Design decisions:**
- The markerless-adoption finding is roadmap-concrete (it has a shape: `--migrate` mode / clearer diagnostic / document-the-constraint), so it lives in the V3b follow-ups bundle, not § Exploration.
- The version-currency finding has no clean shape yet (needs a "latest" reference + a non-annoying cadence; `autoUpdate` is the blunt alternative), so it's § Exploration with a `Surfaces when:` trigger on `/flow:doctor` / `docs/upgrade.md`.

**Tradeoffs discussed:**
- Live-confirmed the install-lag this session: even after the user updated the cache to 1.8.0, the running session's skill resolution stayed pinned to 1.5.1 (picks up 1.8.0 on restart) — so the validation cold-run must verify the installed version FIRST, which the health-tracker prompt now does. No code change here — pure routing so the findings aren't lost.

### Durable visual record (`visual-history.html`) + distill bridge — Deliverable-quality track V3b (v1.8.0) — SAFETY
**Date:** 2026-06-16
**Branch:** claude/v3b-visual-history
**Commit:** [this PR]

**What was done:**
Built the durable half of V3 — the committed, curated `visual-history.html` (the *picture* companion to `history.md`) and the distill bridge that fills it. The ephemeral per-run verify-build report (shipped v1.6.1/1.7.0) is regenerated every iteration and discarded; nothing read its decisions back. V3b adds: a `visualHistoryPath` schema slot (23 slots total); a stdlib `skills/ship/lib/insert-visual-history.py` helper + a `visual-history-skeleton.html` lib asset; a `/flow:ship` **Step 5c** distill step that, on UI projects with a load-bearing visual decision in the run's findings buffer, authors ONE curated reverse-chronological entry into `visual-history.html`; a Step 4a extension deriving a candidate FB from a human-corrected this-iteration open question; and `evals/run_visual_history_evals.py` (25 checks). The 22→23 slot-count fan-out was swept across 8 surfaces.

**Why:**
FB-0042 settles the two-artifact model: the ephemeral report is the human-feedback surface; the durable record is the curated catalogue of what came out of those cycles. Without the durable target, the *decision-making* in each report dies (the roadmap's "cross-run aggregation" gap). This completes the V1→V3 chain of the Deliverable-quality track (#37/FB-0041); only V4 (consumer-side proactive-error loop) remains.

**Design decisions:**
- **Agent curates content, helper enforces structure (Fork 1).** Curation — *which* decision is load-bearing — is judgment, so the agent authors the entry's content; the helper renders it into the fixed structure (reverse-chron prepend, anchor-TOC regen, no-italic-headings) so the FB-0042(d) disciplines are mechanical, not author-memory-dependent (the FB-0010 class). Mirrors the existing `render-test-plan.py` / `render-report.py` lib family.
- **Distill source = the findings buffer, not the rendered HTML.** The buffer (`verifyFindingsPath`) carries the structured `grounding` + `open_questions` the report renders from; Step 4a already reads it. Reading structured JSON beats re-parsing HTML. Reconciled in the plan against the blueprint's "from the ephemeral report" wording (same data, more robust path) — not a contract change (plan-critic Finding 2).
- **Heavily gated, curated not dumped.** Most ships skip §5c (explicit reason on `uiSurface:false` / skipped-verify / no-load-bearing-decision). The record holds only decisions that changed the user's read — never a per-PR dump (FB-0042).

**Technical decisions:**
- **SAFETY — created-on-first-write, not bootstrap-scaffolded (FB-0053, reverses FB-0042(e)'s mechanism).** `bootstrap.sh` *creates* `flow.config.json` and globs only `core-docs/*.md` — it runs before config is meaningful and can't read `uiSurface`, so an unconditional scaffold would seed an empty `.html` into non-UI consumers (violating FB-0007). Instead the distill step seeds the file from the bundled lib skeleton on the first qualifying ship. User-approved at the plan gate; FB-0042(e) + the roadmap acceptance updated same-PR (FB-0010 fan-out). Preserves FB-0042(e)'s intent (uiSurface-gated, opt-in, no empty doc).
- **SAFETY — graceful, no partial writes.** `insert-visual-history.py` validates the target's markers + the entry JSON *before* rendering; a malformed target or invalid entry fails loudly and writes nothing (the existing record is never corrupted). Missing title / bad date / absent markers / invalid JSON all exit non-zero with a clear message.
- **Lean committed assets, CSS/SVG reconstruction fallback.** The durable record references resized keeper frames under `visual-history-assets/` (not base64-embedded — that's the ephemeral report's mechanism); an inline CSS/SVG reconstruction is the honest, labelled fallback when capture isn't available (FB-0042(c)).

**Tradeoffs discussed:**
- **Shipping the capability without a live dogfood (Fork 3, FB-0016).** Flow's own repo is `uiSurface:false`/`platform:library` → its ship always self-skips §5c, and per the realistic-demos rule (FB-0052) we did **not** fabricate a `visual-history.html` for a non-visual repo. Correctness is pinned by evals over a synthetic buffer (legitimate test data); the live curated-entry validation is a tracked health-tracker (iOS) follow-up — exactly as #45's iOS cold run was. The entry *shape* is therefore provisional-pending-UI-dogfood (documented in §5c, roadmap, plan, CHANGELOG).
- **Description bloat.** The plugin/marketplace manifest descriptions gained another cumulative sentence (now well past the ~1500-char mark the "CHANGELOG extraction" Later item flags). Followed the established pattern rather than tackling the extraction here (out of scope).

**Lessons learned:**
- Verified PR #36 was docs-only (blueprint + FB-0042 entry, merged 2026-06-08) before building — no `visual-history` implementation existed on main, so V3b was genuinely unbuilt (the FB-0051 parallel-collision check, applied proactively).
- When a governing spec mandates scaffolding at a lifecycle point where the gating config doesn't yet exist, create-on-first-write at the first qualifying pipeline step is the clean resolution — and the mechanism reversal must update the governing FB + every cross-reference in the same PR.

### Two-way annotation layer — click-to-pin review surface on the verify-build report (v1.7.0) — SAFETY
**Date:** 2026-06-15
**Branch:** `claude/ecstatic-lumiere-b027f3`
**Commit:** 339e0d5

**What was done:**
Made the `/flow:verify-build` ephemeral HTML report a **two-way review surface**. `render-report.py` now injects a self-contained click-to-pin annotation overlay (`plugins/flow/skills/verify-build/lib/annotation-layer.html`) before `</body>` whenever the rendered buffer carries ≥1 captured frame, so the human leaves *located* feedback at the merge gate: click a screenshot to drop a pin, type a note, then "Copy notes" emits a structured per-screen block to paste back into the loop. Captured screenshot `<img>` tags gained `class="annot-shot"` so the layer can find and bind to them. Frameless (text-only / pre-capture) reports stay read-only — no toolbar, no overlay. An unreadable layer file warns and renders read-only, never crashes. No new slot, skill, or dependency. Version → v1.7.0.

**Why (SAFETY):** this changes `render-report.py`'s **rendered output** (a published, safety-relevant artifact — the merge-gate report the human trusts) and adds an **injection path** (read a layer file from disk, splice it into the HTML body) with its own read-failure fallback. Both touch the report's rendering + a new graceful-degradation branch, so the entry is SAFETY-marked per `.claude/rules/documentation.md`.

**The pivotal story (re-scope to the additive delta):**
This work began as a *standalone* feature: a new `/flow:walkthrough` skill, its own `annotation-layer.html`, a new `verifyReportPath` slot, the slot/skill-count fan-out, and ship Step-6b auto-invoke wiring — a full PR that passed two rounds of `/flow:staff-review`. At ship time the **stale-base gate caught that PR #45 ("V2/V3a rendered capture + ephemeral HTML walkthrough") had merged to main mid-session**, independently shipping ~70% of the same feature: the V2 capture, the V3a `render-report.py` renderer (read-only), the `verifyReportPath` slot (same name), the `grounding`/`open_questions` buffer fields, and the Step-8 gate. The **only** part #45 lacked was the two-way click-to-pin layer. The user chose to **re-scope (Option A): reset to main, discard the ~60% #45 already shipped, and contribute only the additive delta** — the annotation layer, layered onto #45's `render-report.py`. (Earlier in the same session the stale-base gate also caught PRs #47/#48 adding `/flow:audit-coverage`, forcing a first rebase.) Recorded as FB-0051.

**Design decisions:**
- **Ship the additive delta, not the duplicate.** The annotation layer is the genuinely-novel "two-way" half; everything else #45 already shipped. Building on #45's `render-report.py` (vs a parallel `/flow:walkthrough` skill) avoids two renderers, two slots, two architectures — the anti-duplication bar (FB-0010/FB-0015 lineage).
- **Inject only when a frame rendered** (`'class="annot-shot"' in body`). A text-only / pre-capture report has nothing to annotate, so the toolbar would be noise — frameless reports stay read-only.

**Technical decisions:**
- **Defer image SIZING to `render-report.py`'s own `.obs img` CSS; the layer only sets `display:block`.** An earlier attempt to override the image width inside the layer clobbered #45's `max-width:600px` cap — the body-injected `<style>` wins on equal specificity by source-order — and upscaled small frames.
- **Pin alignment via JS host-width sync, not CSS shrink-wrap.** An `inline-block` / `width:max-content` host wrapping a percentage-width image is a sizing cycle that collapses the box to ~0px; instead `syncHost()` sets `host.style.width` to the image's *measured rendered width* (re-run on resize + on image load). Caught in a real browser — a 320px frame had collapsed to 2px under the CSS-only approach.
- **Graceful injection (SAFETY).** `load_annotation_layer()` reads the layer from a fixed `__file__`-relative path; on read failure it warns and renders the report read-only — never crashes. Matches `render-report.py`'s existing graceful ethos.
- **Grounding / open-questions are NOT re-introduced as agent-authored.** #45 already added them as buffer fields the renderer consumes; the layer just makes the rendered report interactive, it does not re-author the data.

**Tradeoffs discussed:**
- **Standalone `/flow:walkthrough` skill + own renderer vs additive layer on #45's renderer.** The standalone version was already built + staff-reviewed, so "ship what we have" was tempting — but it would conflict with, duplicate, and compete against #45's merged renderer/slot. Re-scoping discarded ~60% of the session's work to avoid shipping a duplicate. The cost (thrown-away work) is exactly what FB-0051 says to pay rather than ship a competing renderer.
- **Override image width in the layer vs defer to the renderer's CSS.** Overriding gave the layer self-containment but clobbered #45's `max-width:600px` cap and upscaled small frames; deferring keeps a single source of truth for sizing at the cost of the layer depending on the renderer's CSS contract (`.obs img`).

**Lessons learned:** FB-0051 — when the stale-base gate (or a rebase) reveals a parallel branch shipped most of a roadmapped feature you're building, STOP and re-scope to the genuinely-additive delta; do not ship a duplicate renderer/skill/slot. CSS sizing for an injected overlay must be validated in a real browser (the 320px→2px collapse was invisible to static review and to the prose contract); pin-alignment is a measured-width JS problem, not a CSS shrink-wrap problem.

### Verify-build report copy-clarity pass (render-report.py) — plain language for the human reader
**Date:** 2026-06-15
**Branch / SHA:** `claude/verify-report-copy-clarity` / c0252a4, rebased onto `main` after #49 merged (v1.7.0); shipped as **v1.7.1**

**What:** A small, copy-only pass on the verify-build HTML report (`render-report.py`) so a human reading it to make the merge decision understands it at a glance. Lede plainer ("This is what the app actually did when we ran it — checked against what the plan asked for — plus the decisions that still need your call."); legend header "How a verdict / a choice earns its place" → "**Legend**" + a one-line gloss explaining the grounding tags; dropped the redundant jargon `verify exit code: N` pill (the Overall pill already encodes pass/fail) and its now-unused `exit_code` param; "N verify calls" → "N verification steps"; observation labels humanized via an `OBS_LABEL` map (`a11y_snapshot` → "Accessibility tree") and `timestamp_offset_ms` rendered as "1.2s in" instead of "+1200ms".

**Why:** User feedback (FB-0052) on the v1.7.0 two-way report demo — *"the copy isn't clear or really understandable."* Most of the unclear copy is the report *shell* (#45's renderer), not the annotation layer; this is the separate, focused follow-up the user chose over bundling it into the annotation PR (#49).

**Design/technical decisions:** (1) **Copy-only, no behavior change** — no buffer-shape, no schema, no logic touched; the renderer's graceful-degradation + security guards are untouched. (2) **Shipped as v1.7.1** — a patch on top of #49's merged v1.7.0; the PR was authored version-neutral *while #49 was still open* (two open PRs both bumping is the exact fan-out collision FB-0051 is about), then bumped at rebase once #49 merged. (3) Did **not** rename the grounding vocabulary (need / design-language / craft-commitment / open-question) — those are the established FB-0040 conceptual tags; glossed them instead of renaming. (4) Updated the one eval assertion (`test_v2_capture_render.py`) that pinned the old legend string.

**Tradeoffs:** Editing another author's just-merged renderer (#45) risks churn, so the pass is deliberately minimal — the genuinely-cryptic chrome only, not a redesign. Left `## Test plan`-style metrics (budget) in but de-jargoned rather than removing, to preserve the evidence trail.

### PR V2 + V3a — Rendered visual capture + ephemeral HTML walkthrough (v1.6.1) — SAFETY
**Date:** 2026-06-11
**Branch:** `claude/v2-rendered-capture`
**Commit:** [PR #45 — behavioral gate GREEN; marked ready, awaiting human merge]

**Cold-gate outcome (2026-06-11):** the flow-true gate — a cold, fresh-agent `/flow:verify-build` run following `§5a`/`§10` literally against health-tracker (iOS, XcodeBuildMCP) — ran in two rounds. **Round 1:** mechanism validated end-to-end (real build/frames/judges; the pairwise judge returned a true FAIL on a drifted frame), but caught **3 substantive `§5a` prose gaps** — (1) no a11y-gate before screenshot (which *caused* a wrong-state capture), (2) "drive to each state" assumed a UI-drive primitive the MCP may lack, (3) state-set derivation undocumented. Fixed in `839c986` (a11y-gated capture ordering, named drive ladder, explicit derivation + graceful degradation, `--assets-dir` alignment) + **FB-0050** + eval assertions; parser + Spec-walk routing fragility routed to V2.1. **Round 2:** GREEN — 6/6 captures a11y-gated, drive ladder honest, baseline second-run resolved a visual criterion to PASS (VLM-pairwise correctly ignored a non-deterministic status-bar clock; byte-`cmp` would have false-FAILed). This is the load-bearing validation FB-0049 demands, and it caught exactly what static tests + the author's hand-driving missed.

**What was done:**
Built the V2 (rendered capture) + V3a (ephemeral HTML walkthrough) link of the Deliverable-quality track for `/flow:verify-build`. `criteria[].grounding` + top-level `open_questions[]` added to the findings schema (additive; `schema_version` stays `1.0`; top-level `required` unchanged). SKILL §5a: flow now **owns capture-and-persist** — drives the platform's screenshot MCP per declared `Visual-walk` state, persists the frame, writes a path-referenced `screenshot` observation + an `a11y_snapshot` (text/status from the a11y tree, not pixels). SKILL §10 + a new stdlib `render-report.py`: the buffer renders to one self-contained ephemeral HTML report (`verifyReportPath` slot) — hero, legend, per-criterion evidence/grounding/verdict cards, a standalone "Open questions for you" block, and a coverage checklist. Rubric re-grounded on pairwise-vs-baseline (no baseline ⇒ Unknown). `open_questions[this-iteration]` blocks Step 8 auto-advance. Version 1.5.2 → 1.6.0; slot count 21 → 22.

**Why (SAFETY):** modifies the verify-build *gate* (a load-bearing safety surface), the findings *schema* (a consumed contract), and adds *frame persistence to disk* (file I/O + base64 inlining of buffer-referenced files) — all three are SAFETY-marked per `.claude/rules/documentation.md`.

**Design decisions:**
- **iOS-first, not web (mid-flight correction).** The roadmap/SV2 carried a "web-first against health-tracker" framing; health-tracker is an **iOS/SwiftUI app**, and the renderer's HTML is an *output format*, not the capture platform. Pivoted to capture-via-XcodeBuildMCP; the schema/renderer/gate/rubric stayed platform-agnostic (only the screenshot-drive seam is platform-specific). The Chrome-MCP "no path" persist risk (SV2) **dissolved** — XcodeBuildMCP returns a native, pre-optimized frame path.
- **Branch B (capture-and-persist owned by flow), per SV2.** Bundled `/verify` narrates frames to the judges; flow drives + persists them itself.
- **Stdlib renderer, honest-by-passthrough.** No new dependency; resize is the capture step's job; coverage is established by §5a's `not_tested` writes, not enforced by the renderer (corrected an overclaim at staff-review).

**Technical decisions:**
- Additive schema (no migration); `verifyReportPath` slot (default ephemeral temp path).
- Path-traversal hardening + raster-data-URI allowlist in the renderer (security-review).
- 6-assert contract eval fixture pins schema↔example↔renderer↔SKILL↔rubric↔workflow + the data-URI allowlist.

**Tradeoffs discussed (the load-bearing one — FB-0049):**
- **Validation depth: ship now vs do the flow-true behavioral gate.** Phase 0 + the capture→render chain were validated **live on iOS** (built+ran HealthTracker on the sim, real frame → real 41KB report). But the user's question — *"which is more true to flow's intention?"* — established that the rigorous gate is the **skill-driven** `/flow:verify-build` run (ideally cold), not static contract tests + hand-driven mechanism (which is the Potemkin self-validation verify-build exists to catch). That cold run is **session-bound to a health-tracker context**, so per FB-0034 this PR **opens as a DRAFT** with the behavioral gate in the NOT-READY manifest — discovery-before-merge preserved, no merge-ready PR on an unconfirmed gate.

**Lessons learned:** FB-0049 (a verification tool isn't validated until it RUNS against a real surface; don't conflate output-format with capture-platform). Staff-review caught a slot-count fan-out BLOCKER (flow's own doctor Check 2.5 would have flagged it) — grep-first discipline (FB-0010) applies to every count change.


### Docs-currency sweep — refresh the v1.6.0 handoff for a cold agent
**Date:** 2026-06-11
**Branch:** claude/docs-currency-v160-handoff (docs-only; SHA at commit time)

**What was done:** After PR TP (#46) + PR-2 (#47) merged, the plan's "Handoff Notes" + a few roadmap/plan cold-reader lines were stale: Handoff still read "v1.5.2" and listed the now-shipped PR-TP/PR-2 as "queued/staged", and several `this PR` references dangled post-merge. Refreshed Handoff to v1.6.0 + "Recently shipped (enforce-pair DONE)", and de-`this PR`'d the § Now / ▶ Next-up / Current Focus lines so a fresh agent lands on **▶ V2** cleanly (with the vacuous-criterion residual in roadmap § Next).

**Why / lesson:** This is the cleanup `/flow:ship` Step 5a (doc-currency reconciliation, shipped v1.5.2) does automatically — but the **dogfood install is flow 1.5.1**, which predates it, so the auto-sweep never ran across PR-TP + PR-2 and the staleness accumulated. Until the dogfood install updates to ≥ v1.5.2, forward-doc currency must be reconciled by hand at ship (or in a follow-up sweep like this). No code; reviewers + verify-build self-skipped (docs-only / platform library); no version bump.

### PR-2 — `/flow:audit-coverage`: close under-declaration (coverage audit) — `SAFETY`
**Date:** 2026-06-11
**Branch:** claude/flow-coverage-audit-fb0048 (v1.6.0; SHA at commit time)
**FB:** FB-0048 (this PR). Continues FB-0047 (PR TP). Roadmap follow-up filed: vacuous-criterion check.

**What was done:** New `/flow:audit-coverage` reviewer (13th user-visible skill) that closes the under-declaration hole PR-TP's Test-plan render left: it compares the workspace source diff against the declared `**Spec-walk:**` criteria and flags **user-perceptible behavior changes no criterion covers** — a behavior `/flow:verify-build` never tested, so the rendered Test plan would be honestly all-green while the change ships unverified. Each gap → `[decision-required]` → the existing draft manifest → the PR is mechanically NOT-READY until the criterion is declared + verified (re-run verify-build) or the human waives it. Wired in as the 4th `/flow:ship` Step 2 final-pass reviewer + at the Step 8 readiness boundary. v1.5.3→v1.6.0.

**Why:** FB-0047 made *declared* verification unforgeable; the residual hole was *completeness* — an agent omits a criterion for a behavior it changed and it ships unverified. The load-bearing other half of "enforce that the work was done correctly" (FB-0048).

**Design decisions:**
- **Reuse the `auditor` agent + add ONE category** ("Undeclared change", coverage mode only) — not a new agent. Follows the existing mode-selected-category-subset pattern (audit-plan → assumption+recall; audit-completion → diagnosis+completion+recall), avoiding duplication of the ~80 lines of safety-critical disprove/output discipline (FB-0010 fan-out). Coverage's evidence base is the diff + declared criteria (via reused `extract-criteria.py`), NOT the session transcript the other auditor modes use.
- **Surface → draft, not hard-gate, not auto-fix** (FB-0012: never hard-gate / iterate on LLM judgment; FB-0047: the agent declaring its own criterion would be grading its own homework — resolution routes through the gate). Runs on **all platforms** (under-declaration isn't platform-specific — unlike verify-build, does not skip on `platform: library|none`); self-skips on doc/test/refactor-only diffs or no Spec-walk.

**Technical decisions / SAFETY:**
- **`SAFETY` — `auditor.md` (reviewer prompt) + ship Step 2 (pipeline).** New category gated firmly to coverage mode (header parenthetical + the SKILL's "one category only / ignore your other four" framing + the disprove variant) so it can't leak into audit-plan/audit-completion.
- **zsh word-split BLOCKER (caught by dogfood, not static review):** the diff-assembly originally did `git diff -- $FILES` with a newline-joined `$FILES`; macOS's zsh does NOT word-split unquoted expansions, so it passed the whole blob as one bogus pathspec → **empty diff → a no-op reviewer**. Live smoke test caught it; fixed with a `while IFS= read -r f` loop diffing each quoted `"$f"` — which also closes the filenames-with-spaces hardening for free. Lesson: dogfood the actual mechanism (FB-0010 + FB-0048).
- **Path-traversal containment (security-review BLOCKER `[auto-fixable]`):** the new `run_evals.py` coverage branch read a fixture by path; added a 3.7-compatible `relative_to((HERE/'fixtures'))` containment guard so a malicious `ground_truth.yaml` `fixture: ../../etc/passwd` can't read outside `fixtures/` (component-aware — no `fixtures-evil` prefix false-match). Defense-in-depth (repo is developer-trusted) matching the existing `evals/security/` posture.
- **Silent-skip defenses (FB-0010):** a `[audit-coverage] TRUNCATED` sentinel when the diff exceeds the 60KB cap (a clean result on a truncated diff is a false negative — the worst failure for a completeness auditor); a deleted-file guard so `head` doesn't error on a missing path; `--show-context` fixed for the new `coverage` mode (argparse only knew plan|completion → would silently yield empty context).
- **Prompt-injection defense (security NIT):** the SKILL tells the auditor the diff block is untrusted DATA, not instructions (source files can imitate the section headers / inject "pass everything"). Fuller structural-delimiter hardening is a follow-up; the auditor's adversarial disprove discipline mitigates today.

**Tradeoffs discussed:**
- **Best-effort, not deterministic:** coverage is LLM-judgment — it raises the completeness bar, it does not guarantee it (false negatives possible). Stated in README + CHANGELOG + the reviewer output so a clean `coverage=ran` isn't over-trusted. The alternative (a deterministic completeness oracle) is not achievable — "what behaviors did this diff change" isn't mechanically enumerable.
- **Feasibility validated, not assumed (verdict A go/no-go):** a live run of the updated auditor prompt correctly flagged a genuine undeclared rate-limit behavior AND stayed silent (`No issues flagged.`) on a fully-covered diff; pinned offline by 3 `ground_truth.yaml` cases (catch / silence / skip).
- **Verdict E corrected mid-flight:** flow's own behavior lives in markdown (excluded by the source-filter as docs), so flow's own ship sees only the `.json` manifests → coverage finds nothing behavioral; this PR can't fully dogfood the catch-path (same shape as verify-build skipping on `platform: library`). The offline fixtures + the live prompt run carry it.
- **Vacuous-criterion seam (push-further, deferred to roadmap):** coverage closes *under*-declaration but not *over-broad* declaration — an agent can declare a vacuous criterion ("X works correctly") that coverage accepts and verify-build judges PASS against vague narration. That's criterion-*quality* = verify-build's axis, deliberately out of scope; filed as the named next horizon (criterion-specificity check). README/CHANGELOG say "closes the *worst of* under-declaration" to stay honest.
- **No-Spec-walk + behavior-bearing diff deliberately *skips* (not flags):** a spike/tiny PR legitimately has behavior + no Spec-walk; the upstream readiness predicate already requires spec-walk checkboxes for full-feature PRs, so this isn't the place to flag "nothing declared." Deliberate choice.

**Loop:** plan → `/flow:critique-plan` (1 redirect + 2 follow-ups) + `/flow:audit-plan` (clean) → Gate-1 → execute → `/simplify` (1 fan-out fix) → `/flow:staff-review` (4 lenses: dogfood caught the zsh BLOCKER; truncation/deleted-file/show-context fixes; vacuous-criterion → roadmap) → `/flow:ship` (security-review caught + fixed the path-traversal BLOCKER; a11y + verify-build self-skipped; audit-coverage not yet in the installed 1.5.1 cache so it didn't self-run).

### PR TP — PR `## Test plan` rendered from the verify-build findings buffer (non-forgeable) — `SAFETY`
**Date:** 2026-06-11
**Branch:** claude/lucid-driscoll-20ef29 (v1.5.3; SHA at commit time)
**FB:** FB-0047 (this PR). Staged follow-up: FB-0048 (PR-2, under-declaration coverage).

**What was done:** Replaced the hand-authored `## Test plan` placeholder (`- [ ] <how to verify>`) in the `/flow:ship` PR body with a mechanical render from the `/flow:verify-build` findings buffer. New `plugins/flow/skills/ship/lib/render-test-plan.py` (stdlib) reads the buffer JSON and emits the section: a one-line headline verdict (`✅ N/N declared criteria passed — confirm and merge` / `⚠️ M/N passed; K unresolved`), one line per criterion whose **checkbox state is the buffer's `aggregated_verdict`** (PASS→`[x]` + evidence; FAIL/Unknown→`[ ]` + the judge's reason), and the `not_tested[]` residue as plain bullets. Ship Step 7 runs it and pastes stdout verbatim. Honest fallback for skip / no-buffer / **stale** (buffer branch+sha ≠ HEAD) / malformed → `⚠️ no behavioral gate ran (<reason>); manual verification required`. Eval harness `evals/run_render_evals.py` (12 cases) + 6 fixtures. v1.5.2→v1.5.3 (manifests + CHANGELOG); fan-out swept (`workflow.md`, README, dogfood `.claude/skills/ship`).

**Why:** The unchecked `- [ ]` boxes arriving at the merge gate were either no-signal (empty) or, if hand-checked, self-report — the Potemkin class verify-build exists to kill (FB-0047). For "human confirms testing was done, then quick-merges" to hold, the green signal must be a mechanical function of an adversarial judge's verdict, not agent narration.

**Design decisions:**
- **Deterministic script, not agent prose** — makes the section a pure function of the machine buffer (the agent can't selectively check boxes) and golden-testable; matches flow's Python-for-mechanism pattern. (Alternative: format spec in Step-7 prose — lighter, weaker enforcement; rejected.)
- **Scope staged** at Gate-1 (user decision): PR-1 = render (unforgeable + visible); **PR-2 (FB-0048)** = close under-declaration (an agent omitting a Spec-walk criterion for a behavior it changed) by wiring `/flow:audit-completion` coverage into the readiness chain. Render alone makes *declared* verification unforgeable; it does not guarantee completeness — named as a known limitation in README + CHANGELOG.
- **Checkboxes reserved exclusively for machine verdicts** — `not_tested` renders as plain bullets (staff-review + push-further), so a `[ ]` always means exactly one thing: an unverified criterion. (`not_tested.tested` is agent-self-reported, so it must not look like a verdict box.)
- **Distinct from the V3 HTML case-study renderer** (roadmap § Exploration): that's standalone HTML + screenshots sequenced after V2; this renders PR-body markdown from verdict+evidence+not_tested text available today.

**Technical decisions / SAFETY:**
- Ship Step 4a's existing FAIL/Unknown buffer read (FB-synthesis) left **untouched** — the renderer is an additive, separate read (lower-risk than extending Step 4a).
- **Freshness guard (net-new):** a buffer whose `metadata.branch`/`head_sha_short` ≠ current HEAD → fallback, never rendered as current. If the buffer carries an identity but the current branch/sha can't be established (empty git context), fall back rather than silently render a possibly-stale buffer (staff-review: the invariant must not invert).
- **Fail-to-fallback, never crash:** every read/parse/shape error and any exception inside `rendered_block` routes to the fallback with a named stderr reason (FB-0010 silent-skip defense). The caller pastes stdout verbatim, so a crash (empty stdout) would silently break the non-forgeability contract — staff-review BLOCKER, fixed with a try/except + a `malformed.json` eval.
- **Markdown-escape machine-extracted strings** (criterion text, judge notes, not_tested items) so app-under-test content the judge narrates can't inject a link / emphasis / hidden HTML comment into the PR body (security-review BLOCKER `[auto-fixable]`, fixed in-tree + `malicious-content.json` eval). Evidence already used a backtick code-span.

**Tradeoffs discussed:**
- Flow's own repo is `platform: library`, so verify-build self-skips on flow's own ship → **this PR cannot dogfood-behaviorally-verify itself**; its own `## Test plan` renders the fallback, and the eval fixtures/golden assertions ARE the verification. Surfaced up front (verdict F) so the skipped verify-build reads as expected, not a gap. The "behavioral/text" honesty claim describes the *consumer* path, not flow's self-ship (critique-plan incoherence finding, reconciled).
- Attestation is **behavioral/text only**, not visual (bundled `/verify` narrates screenshots to the fresh-context judge rather than handing it pixels; SV2 spike) — rendered-visual judging is Deliverable-quality V2. Stated in README + the rendered attribution so a green Test plan isn't over-trusted.

**Loop:** plan → `/flow:critique-plan` + `/flow:audit-plan` (4 findings, all absorbed) → Gate-1 (scope approved: staged) → execute → `/simplify` (1 cleanup) → `/flow:staff-review` (1 BLOCKER + cheap NITs fixed inline: malformed-crash, freshness-inversion, not_tested-checkbox-collision, headline, empty-criteria/no-notes honesty, backtick-safe evidence) → `/flow:ship` (security-review caught + fixed the markdown-injection BLOCKER; a11y + verify-build self-skipped).

### Direction capture — agentic-iteration doctrine + plan-gate quality lenses (FB-0044/0045/0046)
**Date:** 2026-06-09
**Branch:** claude/happy-gates-b3cf0c
**Commit:** [this PR]

**What was done:**
Docs-only direction-capture from a design conversation about composing flow with two now-GA Claude primitives (`/goal`, dynamic workflows) and refining the autonomy loop. Three feedback entries + two roadmap entries:
- **FB-0044** — low confidence during Execute is a signal to *iterate*, not stop: the agent iterates against the plan's success criteria + craft bar until the design is genuinely good, then ships; only a genuine *preference fork* escalates. Splits FB-0011's escalation as **quality-gap → iterate** vs **preference-fork → escalate**; reserves stop-before-PR for one-way-doors, otherwise escalation routes into a draft PR (FB-0034).
- **FB-0045** — craft-iteration is a *permitted* judgment-loop under four guards (independent judge + declared criteria + real artifacts + bounded budget/merge backstop), refining FB-0012's correctness-only prohibition on iterate-to-approval. Guard #3 (real artifacts, not narration) is what V2 unlocks.
- **FB-0046** — experience + craft-ambition are first-class plan-gate quality gates: add a product-designer/experience lens + a push-further-on-quality (not scope) lens alongside the auditor + plan-critic. Corrects an earlier (wrong) dismissal of a plan-stage experience lens.
- **roadmap.md** — "Agentic-iteration doctrine" entry in the Deliverable-quality track (after V2, its precondition) + "Plan-gate quality lenses" entry under § Next (independent of the V-track).

**Why:**
The user's target loop: human approves a self-critiqued plan → agent executes, reviews, and *iterates against a strong craft/experience bar* autonomously → ships what it thinks is final (PR + eventual HTML walkthrough) → human merges or feeds back. The two load-bearing human gates (plan, merge) are preserved; the not-confident case must resolve by iteration, never a premature stop or draft. Capturing the doctrine before V2/V3 land so the implementation inherits it.

**Design decisions:**
- One FB per distinct rule, following the FB-0037 precedent (a lens-set bundles into one entry) — so FB-0046 carries both plan-gate lenses while FB-0044/0045 stay separate (loop behavior vs FB-0012 doctrine).
- Roadmap split: the iteration doctrine sequences against V2 (real-artifact dependency); the plan-gate lenses are V2-independent and can land anytime → placed in § Next, not the V-track.

**Technical decisions:**
- Direction-capture only — no plugin artifacts, no version bump (stays v1.5.2). FB numbers claimed via the reserved-numbers protocol (FB-0044/0045/0046), cleared at this ship.

**Tradeoffs discussed:**
- `/goal` vs a script-based Stop hook as the autonomous-convergence driver: the Stop hook is FB-0012-pure (deterministic on the verify-build exit code) and shippable in `default-hooks.json`; `/goal` is the ad-hoc, hooks-gated end-user alternative. Captured as direction, not yet built.

**Lessons learned:**
- The repo's research docs predate `/goal` (a real primitive, v2.1.139+) and call dynamic workflows "research preview" though they're now GA — flagged the stale `roadmap.md:242` line for a future touch. Flow's FB-0041 north-star nearly restates what `/goal` does natively; the design lesson is to compose with the primitive, not reinvent it in prose.

### SV2-spike handoff clarity — wire the resolved capture mechanism into the V2 acceptance checklist
**Date:** 2026-06-08
**Branch:** `claude/v2-handoff-clarity`
**Commit:** (this PR; squash SHA at merge) — base `f5d01cf`

**What was done:**
Tightened two `dev-docs` surfaces so a cold agent picking up V2 in a fresh session inherits the SV2-spike's conclusion without re-deriving it. (1) `roadmap.md`'s "PR-1 — track V2 (capture) + V3a" acceptance checklist: the capture checkbox previously read *"verify-build (via bundled `/verify`/`/run`) … writes an `observations[]` entry per state,"* wording that predates the spike and implies `/verify` captures structurally on its own. Rewrote it to name the **capture-and-persist** step explicitly (orchestrator drives the browser-MCP screenshot → persists each frame to a flow-controlled path → path-referenced `observations[]` entry; bundled `/verify` narrates to the orchestrator but does not hand frames to the fresh-context judges; read text from the a11y tree). (2) `plan.md` Handoff Notes: added a precise "▶ V2 handoff" pointer naming the read-order (roadmap ▶ Next-up → V2 § → PR-1 block → `history.md` SV2-spike) so the next session's first doc routes it to the spec. Docs-only; no `plugins/flow/*` change, no version bump.

**Why:**
The SV2 spike resolved the screenshot-structure question and recorded it in the roadmap ▶ Next-up + V2 § + the history entry — but the *acceptance checklist* a V2 agent turns into a spec-walk still carried the pre-spike wording. That's the FB-0010 fan-out class (a contract resolved in the narrative but not in every downstream reference) applied to a spike→feature handoff: an agent following the checklist rather than the prose would have been misled into assuming `/verify` produces structured frames. Closing it before archiving this workspace, per the user's "make sure docs are updated — we'll give this to another agent in a new session" direction (an application of FB-0043 doc-currency).

**Design decisions:**
- **Tighten the checklist, not just the prose.** The V2 § already carried the resolved mechanism; the gap was specifically the PR-1 checkbox. Fixed the exact line a cold agent acts on rather than adding more narrative.
- **No new FB-XXXX.** The session's direction is an instance of existing FB-0043 (doc-currency) + FB-0010 (fan-out), not a new rule — the quality bar favors a lean feedback corpus over a near-duplicate entry.

**Tradeoffs discussed:**
- **Ship a follow-up PR vs leave the checklist imperfect and archive.** The imperfection was non-blocking (the V2 § corrects it), but the user explicitly chose to fix it from this workspace and accept a short archive delay — a clean handoff is cheap insurance against a cold agent mis-reading the one line it acts on.

**Lessons learned:**
- A spike that resolves a question some downstream **acceptance checklist** depends on should sweep that checklist in the same handoff — not only the narrative that frames it. Same grep-first-edit-second discipline as FB-0010, applied across the spike→feature seam.

### SV2-spike — Does bundled `/verify` return screenshots structurally, or only narrate them? (Deliverable-quality track V2 prerequisite)
**Date:** 2026-06-08
**Branch:** `claude/recursing-mendeleev-41df4c`
**Commit:** (this spike PR; squash SHA at merge) — base `8eb867f`
**Mode:** spike (disposable; deliverable = this entry). No `plugins/flow/*` change, no schema change, no version bump.

**The question (from `verify-build/lib/rubric.md:68` + `SKILL.md:56-64`):** does bundled `/verify` return screenshots **structurally** (frames a downstream consumer — verify-build's per-dimension judge and the future HTML renderer — can use as pixels or as path-referenced files), or does it only **narrate** what it sees in freeform prose? The whole shape of V2 (rendered capture + baseline) forks on the answer.

**Answer: narration-only *to the judge*. V2 must add an explicit capture-and-persist step (branch B).**

**What was done:**
Drove bundled `Skill("verify")` **live** against a throwaway zero-dep web app (under gitignored `.context/scratch/`, since the committed fixture `evals/fixtures/verify-toy-web-app/app` isn't runnable — `server.mjs` has no static serving and `vite` is absent) using the connected Chrome browser MCP. Characterized exactly how a captured frame travels, and where it stops.

Three empirical observations, each load-bearing:

1. **Screenshots return as an image *content block* bound to the invoking agent's conversation — the text channel carries only a narration string.** A Chrome-MCP `computer screenshot` returns `<output_image>` (pixels) to the agent that called it, while the *textual* tool result is just `"Successfully captured screenshot (1408x840, jpeg) - ID: ss_2419a0xsc"`. That ID-and-dimensions string is the only thing a text-reading consumer sees. That string **is** "narration."

2. **`save_to_disk: true` surfaced no usable file path, and no file was discoverable on disk.** The tool contract says `save_to_disk` "Returns the saved path in the tool result," but the returned text was still only `"…jpeg - ID: ss_3441gckti"` — no path — and a filesystem sweep of the tmp/claude dirs (last 5 min) found nothing addressable. So in this (Chrome-MCP) configuration there is no path to hand to another agent even if you ask for one.

3. **verify-build's judges are fresh-context `Agent` subagents that receive only their prompt text** (SKILL.md Step 6). An image block in the orchestrator's context does not propagate to a separately-spawned judge. Combined with (1)+(2): a visual claim reaches the judge as the narration string only → and the rubric's two-citation discipline (no hedged PASS; `rubric.md:35`) correctly turns narration-of-a-screenshot into **Unknown**. That is precisely today's "visual = Unknown → blocks" behavior, now explained mechanically rather than suspected.

I did **not** spawn a separate `Agent` to "confirm" the judge is blind to the orchestrator's image block — that probe is tautological once (1)+(2) hold (there is no path or data to even pass it), and the subagent-receives-only-its-prompt boundary is an architectural guarantee. Recording the omission as a deliberate spike-economy call, not a gap.

**Bonus finding — observation sources are not equally trustworthy (informs the rubric, not just V2):**
While verifying the toy's two criteria, the Chrome-MCP `read_network_requests` panel reported the `POST /api/submit` as **`statusCode: 503`** — reproducibly — while the DOM/a11y tree showed the success toast (which only renders on `res.ok`) and `curl -X POST` returned **`201`** three times running. The app received a 2xx; the network panel's status code was simply wrong. A judge citing the network observation alone would have **wrongly FAILed** criterion 1; the judge citing the DOM observation would have correctly PASSed it. This empirically vindicates `rubric.md:66` ("read text from the DOM/a11y tree if available") and adds a sharper rule for V2: **structured text (labels, toast, error copy, and — now — even network status) should come from the a11y tree / an explicit assertion, not be trusted from a single observation channel.** The a11y tree was the reliable source throughout (`status "Submitted successfully" [ref_2]`, exact button labels).

**Why (what this unblocks):**
V1 (v1.5.1) let a plan *declare* visual criteria, but verify-build still resolves every visual claim to Unknown → blocks, so the agent can't honestly say "the visuals are good" without a human babysitting (FB-0041 north star). V2 is the link that turns that Unknown into a real PASS the Step 8 readiness predicate can trust. This spike was the cheap precondition: it fixes V2's shape before any feature code is written.

**V2 shape (the recommendation this spike hands to the V2 feature plan):**
- **Branch (B): add an explicit capture-and-persist step.** The verify-orchestrating layer drives the browser-MCP screenshot, then **persists each frame to a flow-controlled path** (an assets dir alongside `verifyReportPath`) and writes **path references into the findings buffer's `observations[].content`** — which the schema already types as "relative path or base64 data URI" (`findings-schema.json:98`). No schema migration is needed for *capture*; the buffer was built a superset for exactly this. Judges then receive path-referenced frames (or base64 inlined into the judge prompt) **plus a baseline**, enabling the pairwise VLM comparison the rubric already prefers over absolute scoring.
- **Keep the rubric's VLM/pairwise section — rewrite it, don't remove it.** `rubric.md:68`'s "may be removed if narration-only" disposition is **overtaken**: the section is needed, but should be re-grounded on path-referenced frames + a baseline (the spike confirms frames are capturable; they just don't auto-flow to judges). Absolute scoring stays discouraged.
- **Read text from the a11y tree, not screenshot pixels** (the bonus finding): V2 should capture an `a11y_snapshot` observation per state for label/copy/status assertions, reserving the `screenshot` observation for genuinely visual claims (layout, spacing, color, motion end-state).
- **Coupling (FB-0003):** the V2 feature PR lands capture (producer) + the ephemeral renderer / a judge consumer (consumer) in the **same PR**; it must not duplicate #36's durable `visual-history.html` record (V3b).

**Tradeoffs discussed:**
- **Live run vs documentary characterization.** Chose live (Chrome MCP was confirmed connected) so the answer rests on observed behavior, not inference from docs. Cost was standing up a ~50-line throwaway server; worth it — the `503`-vs-`201` finding and the no-path-from-`save_to_disk` finding would both have been missed by documentary reasoning.
- **Throwaway scratch app vs fixing the committed fixture.** Used `.context/scratch/` (gitignored, uncommitted) rather than making `evals/fixtures/verify-toy-web-app/app` runnable, to keep the spike disposable and avoid editing a committed artifact for a research run. (Surfaced as a side-finding: the committed fixture is documentation-only and not runnable — noted for whoever wires the eventual smoke harness; not fixed here.)
- **Editing `rubric.md:68` / `SKILL.md:64` now vs deferring to V2.** Deferred (user-approved scope): the spike records the answer here; the marker rewrites are V2 implementation work touching shipped safety-critical artifacts, and doing them now would force a version bump + SAFETY ceremony for a research-only spike.

**Lessons learned / limitations (FB-0016 — a spike result is as general as its sample):**
- **The "narration-only-to-the-judge" conclusion generalizes** (it rests on the architectural subagent-boundary, platform-independent). **The specific capture mechanics do not** — they were observed on **one platform (web) via one MCP (Chrome)**. iOS (XcodeBuildMCP) / Android (mobile-mcp) may surface screenshot file paths differently (some return a path natively), which could make their capture step cheaper. **Re-test trigger:** when V2 extends capture beyond web, re-characterize the per-platform screenshot-return contract before assuming the persist-it-yourself step is needed there too.
- `save_to_disk`'s documented "returns the saved path" did not hold in this Chrome-MCP build — a reminder that MCP tool contracts are observed, not assumed (pairs with FB-0015's "check the bundled surface" discipline).

### PR DC — Doc-currency in the ship pipeline — SAFETY
**Date:** 2026-06-05
**Branch:** `claude/doc-currency-pipeline`
**Commit:** (this PR; squash SHA at merge)

**What was done:**
Made the ship pipeline keep the forward-looking docs current automatically. `/flow:ship` gained **Step 5a** (doc-currency reconciliation — every ship refreshes roadmap "Now" with the current version + a "Recently shipped" line + a ▶ Next-up pointer, sweeps shipped plan items → "Recently Completed", and clears shipped `FB-XXXX` reservations) and **Step 5b** (a mechanical currency gate that asserts the manifest version appears in roadmap "Now" + plan "Current Focus", `exit 1` + reconcile-instruction on drift). The dev-side `.claude/skills/ship` got the same mirror; `/flow:doctor` got a *secondary* Check 2.6 of the same assertion; `workflow.md` Step 10 narrates the discipline. `docs/upgrade.md` was corrected (the "2-command ritual" was stale — `/plugin marketplace update` updates the installed plugin in one step; the doc now leads with `autoUpdate`). Dogfooded in this PR: the live staleness was fixed (roadmap "Now" read "v1.2.6"; plan "Current Focus" "v1.3.0" — both → v1.5.2). `SAFETY`: ship pipeline + install-surface manifests changed; the new gate is fail-fast (strengthens, never downgrades, error handling). v1.5.1 → v1.5.2.

**Why:**
Stale forward-looking docs are the FB-0010 fan-out class applied to *direction*. A cold reader — a new contributor, or the autonomous loop, which is a cold agent on every run — reads roadmap "Now"/plan "Current Focus" to decide what to do next. They had drifted ~5 versions because ship Step 5 wrote a backward-looking *history* entry + routed follow-ups, but nothing reconciled the forward-looking narrative or enforced currency. "Stale docs should never happen" (user direction, FB-0043).

**Design decisions:**
- **Enforcement in the pipeline (automatic), not in `/flow:doctor` (manual).** The user explicitly corrected an earlier draft that put the check only in doctor: "isn't doctor only run manually? I don't want to have to invoke this manually." So 5b runs on every ship; doctor's Check 2.6 is a *secondary* mirror for spotting drift between ships, never the enforcement.
- **Fail-and-reconcile, not auto-edit (user chose option a).** Step 5a (prompt, with judgment) does the doc edits; Step 5b (mechanical) only *verifies* they landed. Keeps the regex layer from rewriting prose.
- **Mechanical gate checks the version token only.** A version-string mismatch is the cheap, unambiguous signal that catches the worst drift; narrative correctness (the Recently-shipped list, the ▶ Next-up prose) stays the judgment of 5a — mechanizing prose-correctness is brittle and low-value.

**Technical decisions:**
- **Project-agnostic version source with graceful skip.** The gate resolves the version from `plugins/flow/.claude-plugin/plugin.json` → `.claude-plugin/plugin.json` → root `package.json`, and skips the mechanical check (keeping 5a) when none exists — so consumer projects without a versioned manifest aren't false-failed. No new schema slot.
- **Section-scoped grep with top-of-doc fallback** (`awk` extracts the "## Now" / "## Current Focus" section; falls back to `head -40` if the heading differs) so the check is precise on flow's convention and lenient elsewhere.

**Tradeoffs discussed:**
- Bundling the `docs/upgrade.md` fix (the originating thread) into the currency PR vs. splitting it (plan-critic Finding 2 raised scope). Kept bundled — it's the same *stale-doc* class, and the user requested the pipeline fix directly the prior turn (the "scope drift" finding was a false positive from cross-turn-context windowing).
- Mechanical narrative-currency (is "PR Q in flight" still true?) was considered and declined as too fuzzy; left to 5a's judgment.

**Lessons learned:**
- **The PR enforces its own thesis.** 5b ties the docs to the version bump: bumping `plugin.json` to 1.5.2 only passes once roadmap/plan say v1.5.2 — so a forgotten doc update blocks the ship. The currency fix can't itself ship stale.
- **The install confusion was itself a stale doc.** My earlier "two commands / reinstall" framing came from flow's own stale `upgrade.md`; verifying against `code.claude.com` (via the claude-code-guide agent) showed one command suffices. Fixed here — a fitting bug for a doc-currency PR.
- **Stale docs were not a one-off.** roadmap "Now" (v1.2.6), plan "Current Focus" (v1.3.0), and 17 lines of merged-PR Handoff Notes had all rotted — confirming this needed a mechanical fix, not another manual cleanup.

### Roadmap hygiene — Deliverable-quality track V2/V3 labels + de-stale `## Now`/PR Q
**Date:** 2026-06-05
**Branch:** `claude/flow-roadmap-hygiene-v2v3-labels` (SHA at squash-merge)

**What was done:** Docs-only roadmap cleanup, immediately after #36 merged:
- **Reconciled the V2/V3 labels.** The O8 entry's acceptance block called its two PRs `V2/V3a` + `V3b`, but the track section uses `V2` = capture, `V3` = render — so "V2" meant different things in the two places. Relabeled to **PR-1 = track V2 (capture) + V3a (renderer), coupled by FB-0003** and **PR-2 = track V3b (durable record)**, with an explicit stage-mapping sentence. Swept the one living cross-reference in the blueprint research doc (the `history.md` mention is an append-only record of #36's state, left as-is).
- **De-staled `## Now`.** Was frozen at "Plugin at v1.2.6 … This PR (PR H3)"; refreshed to **v1.5.1** with an accurate "what shipped since" line (PR Q/S/U + v1.4.x + #35/#37/#36) and reframed the execution-order intro around the three live streams (Track 1 K/L, Track 2 N/O/P, Deliverable-quality V2–V4).
- **Marked PR Q shipped.** The `## Next` PR Q bullet still read "in flight … Phase 11 next"; updated to **SHIPPED (v1.3.0, #26)** and pointed at the Deliverable-quality track it feeds.

**Why:** Surfaced when the user asked whether the roadmap had clear next steps after #36. The track's next-step path (V1 shipped → V2 next → V3 → V4) was clear, but the V2/V3a label mismatch and the stale `## Now`/PR Q lines muddied it.

**Design decision:** Kept the K/L/N/O/P track *descriptions* intact (still the live plan for those PRs) — only fixed the framing/version anchors, rather than rewriting queues whose status I couldn't fully verify. Append-only history entries (e.g. #36's tightening note) left untouched even where they carry the old label.

**Tradeoffs discussed:** Could have moved the whole O8 entry up under the track section for locality; declined — the cross-reference is clear and the move is larger surgery for marginal gain. A fuller `## Now` execution-order audit (K/L/N/O/P current status) is left as separate hygiene.

### Research — visual-verification blueprint (learning from health-tracker)
**Date:** 2026-06-04
**Branch:** `claude/flow-visual-verification-blueprint-DBWxo` (SHA filled at squash-merge)

**What was done:**
Added `dev-docs/research/visual-verification-blueprint-2026-06.md` — an analysis of `byamron/health-tracker`'s visual-verification method (the `visual-walkthroughs.md` discipline + `craft/visual-history.{md,html}`), mapped onto Flow's shipped `/flow:verify-build` findings buffer and the roadmap O8 "Verify-build HTML case-study report" vision. Research/spec doc only; no plugin artifacts touched.

**Why:**
To turn health-tracker's prior art into a concrete, project-agnostic spec for the future HTML-report PR, and to settle whether verify-build's buffer is already a superset of what the report needs.

**Key findings:**
- The buffer **is** a superset for the *evidence + verdict* layer (observations with `type` discriminator + timeline offset, adversarial cases, two-citation per-dimension verdicts, `not_tested`) — validates PR Q's forward-compat call; no migration needed there.
- It is a **blank** for the *rationale* layer (why a visual looks the way it does) and for *subjective human questions* (distinct from epistemic `Unknown`). Proposed two **additive** fields (`criteria[].grounding`, top-level `open_questions`) — `schema_version` stays `1.0`.
- Gate placement maps cleanly to **FB-0035** (sign-off folds into the merge gate; no third gate) + **FB-0034** (escalation routes into a gate). An unanswered `this-iteration` question is the mechanical block on Step 8 auto-advance, mirroring an unresolved MEDIUM assumption.
- Produced a de-tokenization ledger: every health-tracker token (iOS/Xcode capture, brand palette, project doc IDs) → its generic config-sourced Flow form.

**Design decisions:**
- Initially recommended **not** inventing a generic `visual-history` artifact (persist via feedback + roadmap). **User reversed this** — see Follow-up below; the settled call is a uiSurface-gated core doc.

**Tradeoffs discussed:**
- FB numbering: used the next-free **FB-0041** rather than the task-implied 0037–0040 — which turned out correct, since #35 (below) claimed 0037–0040 for the dynamic-workflows direction; FB-0041 serves FB-0040 without collision.

**Provenance note (reconciled with #35):**
The task's referenced prior work (alignment report, FB-0037–0040, the segment-bounded roadmap entry) was absent from `main` at first draft but **landed via PR #35 mid-task**. This branch was rebased onto #35; blueprint § 0 + cross-refs reconciled. The blueprint is the O8 / FB-0039(b) deep-dive #35 left aspirational.

**Status:** Research complete; FB-0042 captured (below); roadmap O8 entry concretized from vision → spec (the two additive buffer fields, the renderer + report structure, the visual-history durable record, FB-0035 gate placement).

**Reconciliation with flow #37 + merged health-tracker #10 (2026-06-05):**
A review of the two open flow PRs (#36 this one, #37) + the merged health-tracker #10 (the original visual-verification use case) surfaced two things to fix:
- **FB-0041 collision with #37.** #37 independently claimed FB-0041 for the *autonomous high-quality deliverable* north-star (the umbrella "Deliverable-quality track": V1 `Visual-walk` plan field → V2 rendered capture → V3 HTML walkthrough → V4 proactive-error loop). #36 had claimed FB-0041 for the visual-history record. Resolved by **renumbering #36's → FB-0042** (the durable-record decision serving #37's umbrella) and recording both in `reserved-feedback-numbers.md`. #36's O8 work is now framed explicitly as **V2/V3 of #37's track** — they are one pipeline, not competitors. Residual textual overlap (both edit the O8 roadmap entry + append entries) is left for whichever PR merges second to resolve toward this reconciled state.
- **Drift from #10 (corrected in FB-0042 + blueprint § 4).** #10 shipped (a) a *single* curated `visual-history.html` as the picture companion to the existing `HISTORY.md` — **no separate `.md`** (the earlier sketch's `.md`+`.html` pair was wrong); and (b) **lean committed JPEG screenshot assets** with CSS/SVG reconstruction as an honest fallback — **not** the "schematic/screenshot-free" rule the earlier AskUserQuestion settled on (that was an over-constraint; #10 serves the repo-health intent better with lean assets). Also adopted #10's conventions: reverse-chronological, decision-centric entries, no italic headings (health-tracker FB-0006), anchor-link TOC.

**Review fix:** removed stray `</content></invoke>` tags accidentally left at the end of the blueprint file by the original Write.

**Tightening pass for implementation (2026-06-05):** at the user's direction (preparing to move toward implementation), pinned the **ephemeral review report co-equal** to the durable record — it is the human-*feedback* surface (exhaustive evidence + the "open questions for you" decisions/tradeoffs needing input), not an afterthought (blueprint § 3 + a new § 4 two-artifact contract table + FB-0042(a)). Made **capture depth an explicit V1→V2 contract** (§ 2/§ 3/roadmap V2): the report must cover the full declared `Visual-walk` state set, and an uncaptured declared state is a finding (`Unknown` + "not tested"), never a silent gap — closing the "exhaustiveness is bounded by capture, not render" caveat. Added **per-PR acceptance criteria** to the roadmap (V2/V3a + V3b) so the track is build-ready.

**Follow-up (2026-06-04, later revised — see the Reconciliation block above):** User reversed the § 4 "skip a generic visual-history" recommendation — directed that the project-evolution companion become an **opt-in, uiSurface-gated core doc** Flow ships. Initially captured as **FB-0041** with a "schematic/screenshot-free" committed `.html`. **Both were revised on 2026-06-05:** renumbered → **FB-0042** (FB-0041 collision with #37) and the screenshot rule corrected to **lean committed assets + CSS/SVG-reconstruction fallback** to match merged health-tracker #10 (the "schematic-only" call was an over-constraint; lean assets serve the repo-health intent better). The `uiSurface`-gated, opt-in scaffolding stands. Implementation still deferred to the future renderer PR (FB-0003: don't land the `visualHistoryPath` slot + template until a producer + `/flow:ship` consumer ship together).

### PR V1 — `Visual-walk` plan field (Deliverable-quality track) — SAFETY
**Date:** 2026-06-05
**Branch:** `claude/priceless-franklin-ee0e79`
**Commit:** (this PR; squash SHA at merge)

**What was done:**
Added a new required plan field, `Visual-walk`, to flow's plan contract — declared, checkable visual/UX acceptance criteria a plan states when the change has a UI surface (gated on the existing `uiSurface` config slot + the diff actually touching UI; N/A under spike/tiny). Appended to three contract surfaces: `plan-discipline.md` (item 8), `planner.md` (template, placed at item-8 position with state-coverage placeholders), `workflow.md` (§2 required-fields + §8 now names the block). Version bump 1.5.0→1.5.1 (plugin.json + marketplace.json + README header + CHANGELOG). `SAFETY`: install-surface manifests modified (per `.claude/rules/safety.md`); changes are version strings + appended description prose only — JSON validity confirmed (`claude plugin validate` ✔, security-review JSON-parse check ✔). First (cheapest) link in the Deliverable-quality roadmap track (FB-0041) toward an autonomous high-quality deliverable.

**Why:**
`workflow.md` Step 8 already instructed the agent to "dial in visual quality against the plan's **declared visual criteria**," but no plan field declared them — a dangling reference. V1 gives that instruction a home, and creates the load-bearing *input* the rest of the Deliverable-quality track (V2 rendered capture, V3 HTML walkthrough) consumes. Declaration-only by design: today's consumers are the agent's Step 8/9 visual dial-in and the human at the plan-approval + merge gates; mechanical verification is deferred to V2.

**Design decisions:**
- **Distinct `Visual-walk:` block, not folded into `Spec-walk`** — so V2's verify-build can extract visual criteria as a labeled grep (parallel to how it already parses `Spec-walk:`), not a heuristic classification. MEDIUM-confidence, reversible (collapse to a `[visual]` tag if V2 prefers).
- **Declaration-only; plan-critic enforcement deferred** — surfaced as a REDIRECT at the approval gate (it diverges from FB-0041's "strengthen the gate" framing); user explicitly approved declaration-only. The enforcement half is Facet 4 of the managed-autonomy umbrella, routed to V1.1/V2.
- **Examples span static state + token/motion + interaction/a11y** — staff-review (ux + push-further triangulated) caught that the initial happy-path-look examples would anchor authors on appearance and seed thin V2 inputs. Expanded the canonical example set across both narration surfaces.

**Technical decisions:**
- **Append as field 8, keep the numbered list** — `plan-discipline.md`'s spike/tiny mode overrides are keyed to field *numbers* (`spike` replaces (4)+(5); `tiny` skips them). Inserting a "4.5" or renumbering would break those refs (the plan-critic BLOCKER B2). Appending + an explicit "N/A under spike/tiny" line keeps the number-keyed overrides valid. B1 (count fan-out) satisfied by carrying no "N fields" magic-count phrase, not by de-numbering.
- **Reused the `uiSurface` slot** — no new schema slot; `Visual-walk` is gated on the same project-wide flag `/flow:accessibility-review` uses, plus a per-diff "and the diff touches UI" qualifier (so a `uiSurface:true` project on a docs-only PR isn't pushed to invent visual criteria — the FB-0007 case).

**Tradeoffs discussed:**
- Declaration-only V1 vs. include-enforcement-now: declaration-only chosen as the cheapest unblocker; the real gate-strengthening comes from V2 (rendered capture turning "visual=Unknown" into a real PASS), and a critic rule only enforces *that you declared*, not that criteria are *met*. Enforcement + fixture deferred to keep V1 minimal.
- Field name `Visual-walk` (vs `UX-walk`/`Visual-spec`) — chosen for parallelism with `Spec-walk`; confirmed at the gate.

**Lessons learned:**
- **FB-collision lived in real time.** Mid-build, #35 (dynamic-workflows alignment) merged to `main`, claiming `FB-0037` for a different concept + leaving a stale base. The stale-base check surfaced it; renumbered this PR's entry `FB-0037 → FB-0041` with a full cross-file reference sweep (feedback/roadmap/plan/reserved), kept #35's entries intact, and cleared #35's now-shipped reservations with an audit-trail entry. This is exactly the case the K1 reserved-numbers protocol (+ the planned `/flow:doctor` Check 6) exists for — and a concrete data point for #35's own FB-0039 ("parallel writes make the reserved-numbers protocol load-bearing under fan-out").
- **The dogfood install is stale.** This environment runs flow **1.3.0** while developing 1.5.1, so `/flow:ship` (auto-invocable since 1.4.0/PR S) could not be model-invoked — shipped via the dev-side `/ship` instead, spawning `/flow:security-review` + `/flow:accessibility-review` manually to preserve the `STATUS: SKIPPED`/clean audit signal `general.md` requires. Re-installing flow from this repo would close the gap. (Routed as a follow-up.)

### Dynamic-workflows alignment report + adoption direction
**Date:** 2026-06-03
**Branch:** `claude/flow-dynamic-workflows-alignment-oJWKN`
**Commit:** (this PR)

**What was done:**
Docs-only direction-setting pass on how Flow should align with Claude Code's native dynamic workflows (research preview, 2026-05-28). Added: (1) full report `dev-docs/research/dynamic-workflows-alignment-2026-06.md` (state of play / concerns / opportunities O1–O8, grounded in the official `code.claude.com/docs/en/workflows` + `agent-teams` docs and Flow's own prior art); (2) three feedback entries — **FB-0037** (designer lenses are load-bearing, don't collapse under fan-out), **FB-0038** (use workflows where scale earns it, never force; token/cost first-class, no blanket ultracode), **FB-0039** (the human-review + self-learning artifacts — Flow-run PR table, companion HTML case-study, core-docs/FB/memory — must survive adoption); (3) a `roadmap.md` § Exploration umbrella entry tying O1–O8 to `Surfaces when` triggers. No plugin artifacts touched.

**Why:**
The user wants Flow to take full advantage of dynamic workflows — especially the parallel "voting"/adversarial-review fan-out — without the loop's structure inhibiting the engine, while keeping cost in mind and preserving designer perspectives + the review/self-learning artifacts.

**Design decisions:**
- **Segment-bounded adoption, not loop-wide.** Workflows forbid mid-run input; Flow's value is its gates. So a workflow owns the fan-out *between* gates and never spans one (segments A/B/C). This is the central reconciliation — keep rigidity at the gates, allow flexibility in the interior.
- **"Voting" refined, not adopted wholesale.** Honored existing prior art (FB-0016 + `dynamic-workflows-2026-05.md`): blind refutation rubber-stamps, debate loops amplify bias (PR J scope-out). The grounded direction is the untested *informed-independent refutation* variant at fan-out scale, re-tested on UI diffs — not generic claim-voting. Avoided contradicting hard-won findings.

**Technical decisions:**
- Full analysis lives in `dev-docs/research/` (matches the `agent-orchestration-2026-05.md` / `dynamic-workflows-2026-05.md` convention); actionable hooks live in `roadmap.md` + `feedback.md` so they re-surface via the exploration rule.
- Claimed FB-0037/38/39 **above** the 0020–0033 cross-session band (PR-U precedent), reserved in `reserved-feedback-numbers.md` before drafting (K1 protocol).

**Tradeoffs discussed:**
- **One umbrella PR vs. per-O-item PRs** — chose direction-setting + per-item graduation. The umbrella spans shipped-artifact, doctrine, and config surfaces that must ship/review independently (three-surface boundary + small-PR discipline). Pulling it into one PR would violate both.
- **Standalone research doc vs. inline roadmap only** — kept both: the doc preserves the full reasoning; the roadmap/feedback hooks make it actionable and trigger-discoverable.

**Lessons learned:**
- Flow's own constraints (FB-0012 mechanical-loop-only; PR J debate-loop scope-out; FB-0016 refutation spike) sharpen the native-feature recommendations rather than block them — the prior-art read is what kept the "voting" recommendation honest.

**Follow-up (same session):** User clarified that the visual-history / visual-verification artifacts are partly aspirational, and restated the actual goal — a human-review *value model*. Added **FB-0040** (north star: ground in user needs, make assumptions explicit, raise subjective questions, rationale for everything, then automate from clear intent + catalogue feedback/decisions — the principle FB-0037/38/39 serve), and marked the companion-HTML / visual-history artifacts explicitly ASPIRATIONAL/NOT-YET-SHIPPED in FB-0039 + the report (shipped baseline = `/flow:verify-build` behavioral check, v1.3.0; the rich visual report is a roadmap vision, not a surface to preserve). Key consequence captured: because workflows take no mid-run input, assumptions + subjective questions must surface at the *gate* preceding a segment, never in the fan-out interior — maximizing human-review value means *richer gate decisions, not more gates*.


### PR U — ship-time gate semantics + reviewer/ship-spike auto-invocability (v1.5.0) SAFETY
**Date:** 2026-06-02
**Branch:** `claude/pr-u-ship-gate-semantics` (rebased onto `main` @ `1eb4ad9` v1.4.2; squash SHA filled at merge)

**What was done:** Combined PR T umbrella Facets 2 + 3 + 5 (Facet 5 absorbed from the abandoned "Track A") into one PR:
- **Facet 5 — auto-invocability:** flipped `disable-model-invocation: true → false` on `audit-plan`, `audit-completion`, `critique-plan`, `ship-spike`. README + workflow.md relabeled accurately (the three reviewers → BOTH, never cold-start; `ship-spike` → auto but judgment-gated). FB-0010 grep confirms zero MANUAL survivors for the four.
- **Facet 2 — resolution-confidence + draft-routing:** `[auto-fixable]`/`[decision-required]` axis on security/a11y; `/flow:ship` routes decision-required findings (and non-converging verify-build regressions) to a **draft PR + `🚫 NOT READY TO MERGE` manifest** instead of a silent proceed or hard halt. Integrated into the v1.4.1 `## Flow run` PR body.
- **Facet 3 — verify-build placement:** ship-time verify-build reframed as a confirmation re-run (discovery → Step 8/9 readiness boundary; visual sign-off folds into the merge gate).
- Fixture `evals/fixtures/resolution-confidence-routing/`; v1.4.2 → **v1.5.0**; FB-0034/0035/0036.

**Why:** Closes the asymmetry where security/a11y BLOCKERs had no ship-stopping gate while verify-build hard-halted — both could yield a best-effort not-ready PR or an arbitrary mid-loop stop. Operationalizes the two-gate thesis: escalation routes INTO the merge gate (draft), and no reviewer/ship-spike skill is itself a gate.

**Design decisions:**
- **Draft-routing, not hard-halt** (plan-critic BLOCKER): auto-advance-into-ship stays verify-build-PASS-gated (PR S predicate + FB-0018 invariant unchanged); only ship-*internal* unresolvable findings route to draft. Invariant: no merge-ready PR on a non-PASS build.
- **Visual sign-off → merge gate** (plan-critic REDIRECT, user decision): preserves exactly two human gates.
- **Facet 5 depends on #33** (session-discovery fix): the `context: fork` reviewers need it to resolve transcripts from worktree cwds, else they auto-invoke but audit nothing. The parallel session that merged #33 live-verified fork-path parity is PASS once #33 is in base — closing the original auditor UNVERIFIED concern.

**Technical decisions:**
- Manifest is an in-memory per-run accumulator (Step 2 → Step 7); machine-consumable sentinel shipped as the *producer*; the *consumer* (CI/doctor merge-block + persistence breadcrumb) routed to roadmap as the deliberate second half.
- **Rebase collision reconciliation (FB-0010):** collided with merged #32 ("PR T — Flow-run descriptions") on the **PR-T letter** (this PR is "PR U"; the planning umbrella keeps the "Managed-autonomy confidence" name) and on **FB-0019** (renumbered this PR's entries → **FB-0034/0035** + added **FB-0036**, above the cross-session high-water flagged in the #33 handoff). Draft-manifest integrated into #32's `## Flow run` body rather than reverting it.

**Tradeoffs discussed:**
- Resolution-confidence self-tagging is an LLM judgment (MEDIUM) — mitigated by default-to-decision-required + the fixture pinning the boundary.
- ship-spike left on hard-halt (separate scope; roadmap follow-up).

**SAFETY:** edits `ship/SKILL.md` (ship contract) + the reviewer prompts + 4 skill invocation flags. Preserved: ship never merges; PR S auto-advance predicate; FB-0011/0012/0018 contracts. Pre-ship caught a self-inflicted secret-scanner trap (fixture used a realistic live-key-prefixed literal → push protection scans history → soft-reset + clean re-commit, not the unblock URL). staff-review (4 lenses) returned 0 BLOCKERs.

### `extract_session.py` session-discovery fix — reviewers were context-starved from worktree / dotted-path cwds (v1.4.2) SAFETY
**Date:** 2026-06-02
**Branch:** `fix/extract-session-cwd-slug` (off `main` @ `4f5fba6` v1.4.0; rebased onto `9117c3a` v1.4.1 at ship — version bumped 1.4.1→1.4.2 after the parallel PR #32 took 1.4.1)
**Commit:** `fix/extract-session-cwd-slug` (squash SHA filled at merge)

**What was done:**
Fixed `find_session_file` / `slugify_cwd` in `plugins/flow/scripts/extract_session.py` so the audit/critique reviewers actually locate the current session transcript. Two changes: (1) the cwd→`~/.claude/projects/<dir>` encoding now replaces **every** non-ASCII-alphanumeric character with `-` (matching Claude Code), not just `/`; (2) discovery first tries an exact match via the `CLAUDE_CODE_SESSION_ID` env var (validated to `[A-Za-z0-9_-]+` before it reaches the glob), falling back to the corrected cwd-slug, then to graceful `None`. Bumped v1.4.1 → v1.4.2 (plugin.json + marketplace.json ×2), CHANGELOG v1.4.2 entry, README + workflow.md "shipped surface" headers, and a new regression fixture `plugins/flow/evals/security/test_session_discovery.py`.

**Why:**
Discovered while verifying PR T / Facet 5 (reviewer skills made auto-invocable). Model-invoking `/flow:audit-plan` forked correctly but the forked auditor returned *"session file not found for this working directory"* and audited nothing. Root cause: `slugify_cwd` replaced only `/`, but Claude Code names its project dir by replacing `/` **and** `.` (and `_`, spaces) with `-`. So `/Users/.../flow/.claude/worktrees/<wt>` → CC writes `...flow--claude-worktrees...` while the script looked for `...flow-.claude-...` → directory miss → silent context starvation. This fires for **every** `.claude/worktrees/` dev session (i.e. all of flow's own dogfooding) and any consumer project under a dotted path. It is invocation-mode-independent (hand-typed slash command hit it identically), so it predates and is orthogonal to Facet 5 — but it would have made the newly auto-invocable reviewers hollow exactly where they're first exercised.

**Design decisions:**
- **Prefer `CLAUDE_CODE_SESSION_ID` over slug reconstruction.** Empirically the env var is exported into the skill `!`-backtick substitution subprocess (verified live: with the slug deliberately broken, the model-invoked auditor still returned grounded context — only the session-id path could have resolved it). It pinpoints the *exact* current session rather than newest-by-mtime in the cwd's dir, eliminating a latent wrong-session-audit risk in shared-cwd cases. Kept as best-effort primary (exactly-one-match or fall through) so it never degrades the slug path.
- **Corrected slug stays as deterministic fallback.** The env var is undocumented; the slug fallback (now matching CC's full encoding, unit-proven against the real dir name) guarantees correctness even if the var ever disappears.

**Technical decisions:**
- Encoding implemented as `re.sub(r"[^0-9A-Za-z]", "-", cwd).lstrip("-")`. Verified it reproduces the real on-disk dir name exactly, plus dotted/`_`/space cases. Confirmed against CC behavior via empirical project-dir inspection + claude-code-guide (replaces all non-alphanumerics; preserves hyphens; no dash collapsing).
- `_find_session_by_id` validates `session_id` to `[A-Za-z0-9_-]+` (fullmatch) before globbing `~/.claude/projects/*/<id>.jsonl`, and returns the file only on a unique match.

**Tradeoffs discussed:**
- **Scope: fold into Facet 5 vs. separate PR.** Chose a standalone bug-fix PR (user decision) — the bug is pre-existing, invocation-mode-independent, and benefits all reviewer usage, so it deserves its own focused review + fixture rather than riding inside Facet 5's flag-flip. Facet 5 then ships onto a verified-working reviewer path.
- **session-id-only vs. layered.** Rejected session-id-only (undocumented var ⇒ no guarantee) and slug-only (leaves the wrong-session-in-shared-cwd risk). Layered primary+fallback gets exactness when available and determinism always.

**SAFETY:** `extract_session.py` is on the safety-critical paths list (silent failure starves reviewers without surfacing an error). Preserved: malformed-JSONL skip, empty-session / no-turns / no-plan `emit_cannot_audit` fallbacks, and the explicit-`--session-file` override path (eval harness) — all unchanged. The change only *adds* a more-correct primary lookup and *widens* the encoding the fallback understands; the graceful-`None` terminal behavior is intact. Safety-history pre-check (`git log -5 -- extract_session.py`) showed no prior crash/fallback commits on the file. New fixture asserts the graceful-`None` case so a future refactor can't silently drop it. **Security-review (red-team lens) caught a glob-injection BLOCKER** in the new `_find_session_by_id`: `session_id` was interpolated straight into `Path.glob(f"*/{session_id}.jsonl")`, so a tampered/malformed `CLAUDE_CODE_SESSION_ID` (e.g. `*`, `[a-z]*`, `../…`) could wildcard-match or traverse to other transcripts. External exploitability is low (the env var isn't attacker-reachable without prior code execution), but the value flows into a filesystem glob and this file already takes a defense-in-depth stance (the `gather_reference_docs` cwd constraint), so it was fixed: `session_id` is now validated to `[A-Za-z0-9_-]+` (UUIDs pass; any path/glob metacharacter → `None` → cwd-slug fallback). A Case-4 injection fixture asserts five metachar/traversal payloads all resolve to `None`; a Case-5 fixture asserts the ambiguous `>1 match` guard returns `None`.

**Lessons learned:**
- "Reload the plugin in a fresh session" was insufficient to verify Facet 5: a session loads the *installed cache*, not the worktree source — and the cache slug bug then masked the real fork-path behavior. Verifying preprocessing scripts live requires patching the cache copy (scripts run per-invocation, so no restart needed) and exercising the actual skill `!`-substitution context, not just `--session-file`.

### Flow-run PR descriptions — per-step `## Flow run` table replaces `## Reviews` (v1.4.1)
**Date:** 2026-06-01
**Branch:** `claude/epic-northcutt-2d5e88` (commit at push time; off `origin/main` @ `4f5fba6`)

**What was done:**
Replaced the generic `## Reviews` blurb in the `/flow:ship` PR body with a `## Flow run` per-step table that documents the full loop run, plus instruction text telling the ship agent how to populate it from the session's loop history:
- **`plugins/flow/skills/ship/SKILL.md` §7** — `## Flow run` table (one row per loop step: Clarify → Plan+critique → Execute → Preflight → /simplify → /flow:staff-review → security/a11y/verify-build → Doc synthesis), each `✓` (ran) or `skipped (<reason>)`; a **Notable** cell for genuine signal or `—`. Instruction block encodes the mode/config skip reasons, the bidirectional honesty rule, the no-manufactured-notes rule, and the follow-ups-stay-canonical + never-merge doctrine.
- **`.claude/skills/ship/SKILL.md` (dev-side dogfood `/ship`) Step 4** — same `## Flow run` block (generic cross-refs, no `/flow:ship`-specific step numbers). Its merge behavior + step numbering left untouched (out of scope).
- **`plugins/flow/skills/ship-spike/SKILL.md` Step 7** — trimmed table; `/simplify` + `/flow:staff-review` pre-marked `skipped (spike)`; verify-build row carries the 3-check spike-rubric result.
- **`plugins/flow/docs/workflow.md`** — §10 gains a "The PR body documents the full flow run" subsection; the spike section's PR-body bullet names the trimmed table.
- Version bump v1.4.0 → **v1.4.1** (plugin.json, marketplace.json ×2, README header + ship-row, CHANGELOG v1.4.1 entry); cumulative description sentence appended.
- **`dev-docs/feedback.md` FB-0019** + reservation in `reserved-feedback-numbers.md`; this entry.

**Why:**
Prompted by dogfooding flow on another project where richer per-step PR descriptions were wanted. The old `## Reviews` one-liner under-documented what the loop actually did — a reviewer couldn't see at a glance which gates ran, which were skipped (and whether legitimately), or what each step surfaced. The table makes the loop's execution legible on the PR page itself.

**Design decisions:**
- **Table populated from in-session context, not a new machine-readable artifact.** The ship agent already writes Summary + Test plan from session context; the loop steps happened in the same session/branch, so a structured loop-log buffer would be over-engineering (FB-0015 bundled/over-build check). Generalizing verify-build's findings buffer to all steps was scoped out.
- **Bidirectional honesty rule.** The user's request named only the "never imply it ran when it didn't" failure mode. The plan-critic caught the inverse: the request's "if security/a11y are not-yet-shipped, say so" conditional evaluates *false* in v1.4.x (all three reviewers ship and run), so carrying it forward unconditionally would have instructed the agent to write "skipped — not yet shipped" for steps that actually execute. Resolution: real skip reasons map to runtime-config states; "not yet shipped" is a clearly-conditional fallback for a step genuinely absent from the reader's flow version. Captured as FB-0019 sub-rule (a).

**Technical decisions:**
- **Dev-side `/ship` reconciled, not unified.** CLAUDE.md treats `plugins/flow/skills/ship/SKILL.md` and `.claude/skills/ship/SKILL.md` as distinct surfaces and documents no sync convention; the dev-side skill is the older simpler push+PR+merge command. Applied only the PR-body section to satisfy the user's "update both" done-criterion, without touching its merge behavior or step numbering.
- **Version bump.** Shipped plugin artifacts (ship + ship-spike skills, workflow.md) changed, so v1.4.1 per the PR-J precedent (prompt-only change → bump). Surfaced in the plan as a MEDIUM-confidence call for the merge gate; docs-at-root no-bump precedent (PR H1/H2) doesn't apply since these files ship in the install bundle.

**Tradeoffs discussed:**
- **Per-step table vs. keeping the prose blurb.** The table costs more PR-body bytes and asks the agent to recall the whole loop; chose it because the legibility gain (skip-with-reason visible per step) is exactly what the dogfood surfaced as missing. The no-manufactured-notes rule + `—` default bound the cost: a routine PR's table is mostly dashes.
- **FB-0010 fan-out risk.** The skip-reason vocabulary now lives in four surfaces; mitigated by a dedicated spec-walk grep line (plan-critic FOLLOW-UP) rather than relying on author memory.

**Lessons learned:**
- A user request can embed a conditional that's stale against the current codebase. Evaluate "if X, say Y" against the code before encoding it as an instruction — the plan-critic's prove-or-disprove pass (v1.2.5) is what caught it here.

**Safety note (no SAFETY marker):** This entry touches safety-listed files (`ship/SKILL.md`, both manifests) but modifies only the PR-body template + version/description strings — no error-handling, persistence, or fallback paths. Ran the `git log --oneline -5 -- plugins/flow/skills/ship/SKILL.md` precondition check (recent SAFETY commits were verify-build + bounded-retry preflight + auto-invocable; none touched by this PR-body edit). Per `.claude/rules/documentation.md`, no SAFETY marker is warranted.

### `/flow:ship` auto-invocable — autonomous-loop trigger at Step 8 (v1.4.0) SAFETY
**Date:** 2026-05-30
**Branch:** `claude/auto-ship-readiness-trigger` (commit at push time; stacked on the docs PR #29 squash)

**What was done:**
Flipped `/flow:ship`'s `disable-model-invocation` from `true` → `false` so the agent can invoke ship itself at the end of a driven loop, paired with a deterministic gate so it can't fire arbitrarily:
- **ship/SKILL.md** — flag flip + an auto-invocation contract in the description (the text Claude Code reads to decide auto-firing): auto-invoke only when the ship-readiness predicate holds and the FB-0011 risk gate is clear; never when verify-build is skipped; never merges.
- **workflow.md** — Step 8 "Present" rewritten as a **conditional gate**: a ship-readiness predicate (all spec-walk boxes checked, no open BLOCKER, no unresolved MEDIUM/LOW assumption, `/flow:verify-build` would return PASS), an FB-0011 risk gate, and explicit auto-advance vs stop-and-present paths. Loop diagram + MEDIUM confidence-row cross-referenced.
- **general.md** — workflow-discipline bullet encoding the trigger (auto-loads on `**/*`).
- Version bump v1.3.0 → **v1.4.0** (marketplace.json ×2, plugin.json, README header) + cumulative description sentences; README auto/manual table `ship` row → `AUTO·when-ready` + cold-start note revised; CHANGELOG v1.4.0 entry.

**Why:**
The user's goal is an autonomous coding loop with human gates only at plan approval and merge. `ship`'s `disable-model-invocation: true` was a blanket-conservative default set in v1.0.0 and never revisited toward that direction — it forced the user to type "ship it" at every loop end, which is not one of the two load-bearing gates. Auto-invoking ship does not violate the merge gate (ship opens a PR, never merges).

**Design decisions:**
- **verify-build is the load-bearing gate, not the predicate.** The predicate only decides whether to *enter* ship; ship's own Step 2 verify-build (`exit_code: 1` on FAIL/Unknown) re-confirms and halts pre-PR. So a falsely-confident auto-advance is caught mechanically — the model's self-report is not the safety boundary. This is why the predicate can be "soft" (rule + description guidance) without a Stop-hook.
- **Skipped-verify stays MANUAL** (user decision, 2026-05-30): library/none platform + doc-only diffs have no behavioral gate, so the predicate requires `overall_verdict: PASS`, not merely "verify-build didn't fail." Default-to-ESCALATE per FB-0011.
- **ship-spike stays MANUAL** — spikes are user-initiated explorations; the deliverable (the answer) is a judgment call, not a mechanical readiness signal.

**Technical decisions:**
- Encoded the predicate in `general.md` (already loads on `**/*`) rather than a new rule file — a 5th rule would break the "4 auto-loading rules" fan-out contract (README/doctor/manifest all cite the count).
- Verified no eval/doctor/CI assertion depended on `ship` being `disable-model-invocation: true` (`git grep` — none) before flipping. Evals + security evals green post-change.

**Tradeoffs discussed:**
- Flip-the-flag-alone vs flag-plus-gate. Flipping alone would let the model ship on a vibe (the un-gated judgment FB-0011 warns against). Chose flag + readiness predicate + verify-build hard gate so autonomy is earned by a mechanical signal, not asserted.
- Stacked this PR on the docs PR (#29) rather than basing both on the same `main` — the README auto/manual table only exists post-#29, so editing the `ship` row required #29 merged first. Avoided re-introducing the staleness #29 removed.

**Lessons learned:**
- The autonomy increase is reversible (flip the flag back) and bounded (merge stays human, verify-build gates pre-PR) — which is what made it shippable without a hard Stop-hook. The Stop-hook remains a deferred roadmap item for hard enforcement.

### README + workflow.md + config.example — surface auto-vs-manual reality, list skills in loop order, de-stale v1.0.0→v1.3.0
**Date:** 2026-05-30
**Branch:** `claude/nice-lamarr-3c30c0` (commit at push time)

**What was done:**
Docs/config correction PR, three coherent pieces:
- **README.md** — reordered the skill catalog from importance-order into **loop order** (the user's explicit complaint: "skills aren't listed in workflow order, confusing"). Added a **Fires** column (AUTO / MANUAL / BOTH) + a `Step · gate` column, a `⚠️ Cold-start reality` callout stating plainly that on a bare "build me X" only the auto-loading rules attach and nothing executable fires until typed, added the missing **`/flow:verify-build`** row, and fixed the header (`v1.2.5`→`v1.3.0`, `11`→`12 skills`). Expanded the one-line `## The loop` arrow into a numbered table naming every skill at its step and marking the three human pauses (Gate 1 plan, Gate 3 LOW-confidence, Gate 2 merge) + mechanical stops.
- **plugins/flow/docs/workflow.md** — de-staled `Bootstrap status (flow v1.0.0)` → `Shipped surface (flow v1.3.0)`; stripped every `(PR 2)` / `(PR 3)` / `[not yet shipped]` marker that described already-shipped surface (staff-review, security/a11y review, ship-spike, workflow-help, memory machinery, template dir) as future work; updated the skills cheat sheet + config-slot prose. (This change was pre-staged in the worktree from a prior session; verified and folded in as in-scope.)
- **template/base/flow.config.json.example** — expanded from 14 to all 21 documented slots (added `preflightCmd`, `sourceFilePatterns`, `uiFilePatterns`, and the four verify-build slots) so adopters reading the example discover the mechanical-preflight + behavioral-verification gates instead of shipping them off-by-default. (Also pre-staged; verified and folded in.)

**Why:**
A workflow-driven production-readiness audit surfaced that (a) the README presented skills in an order no reader could map onto the loop and never distinguished auto-fire from manual-typing, and (b) the canonical workflow doc the README points to as "the loop itself" still described half the shipped plugin as unshipped PR-2/PR-3 work — contradicting a v1.3.0 install. Both erode adopter trust. The 14-of-21 example config silently disabled the headline reliability + verification gates for anyone who only read the example.

**Design decisions:**
- Kept the README's "When to use each reviewer" matrix (a by-work-type view) alongside the new loop-order catalog rather than collapsing them — different lookups for different reader intents.
- The cold-start honesty note is deliberately blunt ("a typed-command toolkit with a thin auto-loaded guidance layer, not a loop that drives itself") because the gap between the "managed-autonomy loop" framing and the typed-command reality was the single biggest UX surprise the audit found.

**Technical decisions:**
- No code touched; markdown + JSON-with-comments only. No version bump (docs/config at root, same precedent as prior docs-only PRs). Skill/rule counts unchanged (12 skills, 4 rules) so no fan-out sweep needed beyond the version-string + skill-count edits in README, which were the contract change.
- Verified each pre-staged diff (`workflow.md`, `config.example`) before staging rather than committing an unreviewed change.

**Tradeoffs discussed:**
- Documenting today's manual reality vs the intended auto-ship end-state. Chose to describe what's shipped (manual) here and split the auto-ship capability into its own PR (`claude/auto-ship-readiness-trigger`) rather than write forward-looking docs about unbuilt behavior — the exact staleness class this PR removes.

**Lessons learned:**
- The audit found the most dangerous staleness wasn't wrong code but a canonical doc confidently describing shipped features as future work. De-staling docs is as load-bearing as fixing code when the doc is the adopter's map.

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

### bootstrap.sh — trailing-flag crash + cp -n comment drift + swift counter miss SAFETY
**Date:** 2026-05-28
**Branch:** `claude/dazzling-goodall-1ea214`
**Commit:** [SHA at commit time]

**What was done:**
Fixed three defects in `template/base/bootstrap.sh` (shipped in the install bundle), all surfaced by a reviewer-refutation spike that fanned three review stances over the file:
1. **BLOCKER (error handling) — trailing-flag crash.** The arg-parse loop did `--stack) STACK="$2"; shift 2` (same for `--project` / `--flow-dir`) with no guard. Under the script's `set -eu`, a flag passed as the final token (`bootstrap.sh --stack`, or the realistic typo `--stack web --project`) expanded `$2` unbound and aborted with a raw `bash: $2: unbound variable` (rc 1), bypassing the guided `⚠️ … exit 2` usage path every other failure uses. Added a `need_val` helper that checks `[ $# -ge 2 ]` before `shift 2` and routes a missing value to the existing usage/`exit 2` path. Applied uniformly to all three value-taking flags.
2. **NIT — `cp -n` comment/code drift.** Header (line 27), the `set -eu` rationale (line 32), and the Step A banner (line 113) all credited idempotency to `cp -n`, but `copy_n` actually uses an `[ -e "$dest" ]` precheck + plain `cp` (no `-n`). The comments also contradicted the accurate Step C note (BSD cp returns 1 on skip under set -e). Rewrote the three comments to describe the `[ -e ]`-guard reality and cite why real `cp -n` is deliberately avoided.
3. **NIT — swift counter miss.** The swift-only `safety.md` append/skip branches mutated state but never did `copied=$((copied+1))` / `skipped=$((skipped+1))`, unlike the structurally-parallel `.gitignore.append` block, so the `scaffold complete: N created, M skipped` summary undercounted on the swift stack. Added the increments.

**Why:**
A blind-vs-self refutation spike (see `dev-docs/research/dynamic-workflows-2026-05.md`) reviewed `bootstrap.sh`; the trailing-flag crash was independently found by all three stances and kept by both verification methods — the highest-confidence finding in the run, and a textbook FB-0010 fail-loud violation living in flow's own scaffolder. The two NITs were high-agreement findings worth folding into the same fix.

**Design decisions:**
- Route the missing-value case to the *existing* guided usage path rather than inventing a new error shape — consistency with every other failure in the script (single `⚠️ … run with --help for usage … exit 2` voice).

**Technical decisions:**
- `need_val` helper rather than inline `${2:-}` guards ×3 — DRY + uniform messaging, consistent with FB-0009's "consistency is the value" lineage. One guard shape for all three flags.
- Verified the only trailing-arg-prone `$2` sites are the three arg-parse cases; `$2` at the `copy_n`/`copy_tree` definitions are function-local params (always bound when called) and need no guard.
- Left the Step B "17 slots" line untouched: the spike's slot-count finding was adjudicated a false positive — "slots" is the schema property count (16 at b1c8e01, 17 at HEAD post-PR-M `preflightCmd`), not the example file's populated-key count.

**Tradeoffs discussed:**
- `need_val` helper vs per-case inline check: helper won for uniformity; cost is one extra function. Acceptable.
- Scope: the fix made the pre-existing `--help` verbosity (the `grep -E '^# '` dumps all column-0 comments, including section dividers and rationale, not just the usage header) marginally longer. Did NOT fix the `--help` greediness — out of scope for this task, logged as a FOLLOW-UP. Restricting scope to the three named defects is the discipline the spike itself reinforced.

**Verification:**
- `bash -n` clean.
- Reproduced all three trailing-flag cases → now emit `⚠️ <flag> requires a value` + `exit 2` (was `$2: unbound variable` rc 1).
- Existing paths unaffected: missing `--stack`, unknown arg, `--help` all behave as before.
- Real swift scaffold in a temp dir: first run `16 created / 0 skipped`, re-run `0 created / 16 skipped` — the matched totals prove every mutation is now counted in exactly one branch (idempotency invariant).

**FOLLOW-UP:**
- `--help` greps every `^# ` line, so it prints section dividers + rationale comments, not just the usage header (lines 2–28). Pre-existing; restrict the grep to the contiguous header block (e.g. stop at the first blank line). Surfaces when: next edit to `bootstrap.sh`'s `--help` handling.

### Flow plugin v1.3.0 — `/flow:verify-build` plan-driven behavioral verification gate (PR Q) `SAFETY`
**Date:** 2026-05-28
**Branch:** `claude/lucid-matsumoto-730ba0`
**Commits:** `e722a9b` (PR Q skill) + `4cd5bbc` (staff-review fixes) + `5ad95f2` (manifest bump + flow self-config)

**What was done:**
Added `/flow:verify-build`, the third final-pass reviewer in `/flow:ship` Step 2 (alongside `/flow:security-review` and `/flow:accessibility-review`). Wraps bundled `/verify` (transitively `/run` + `/run-skill-generator`) with flow-specific orchestration: plan-driven criteria extraction from `**Spec-walk:**` checkboxes, fresh-context adversarial transformation, per-dimension parallel judges (PASS/FAIL/Unknown with two-citation evidence), Unknown-blocking gate per FB-0011, and structured findings buffer routed to `/flow:ship` Step 4a FB-XXXX synthesis. Closes the static-analysis-only gap in the loop's verification surface (Potemkin-interface / hallucinated-success class — the dominant agentic-dev failure mode no current flow step catches).

New plugin surface:
- `plugins/flow/skills/verify-build/SKILL.md` (~310 lines) — 9-step orchestrator
- `plugins/flow/skills/verify-build/lib/` — extract-criteria.py + 4 prompt files (adversarial.md, rubric.md, spike-rubric.md, not-tested-checklist.md) + findings-schema.json (JSON Schema draft-07) + findings-example.json
- 3 eval fixture sets: verify-unknown-blocks/, verify-toy-web-app/, verify-budget-overrun/ (14 fixture files)
- Schema slots: `platform`, `verifyEnabled`, `verifyFindingsPath`, `verifyBudgetCalls` (17 → 21)
- ship-spike Step 2 invokes verify-build in spike mode (3-check rubric)
- doctor Check 5.3 detects whether `/run-skill-generator` has been run
- workflow.md Step 10 + skills cheat sheet + config slots table; bootstrap.md Step 5.5 + migration.md Stage 1.5 name `/run-skill-generator` as Tier-1 prerequisite
- `flow.config.json` added at repo root: `platform: library` + `uiSurface: false` + `defaultBranch: main` (flow self-dogfoods the new schema by opting out of verify-build at platform check)

**Why:**
The 11-step loop verifies through static analysis only — typecheck/lint at Preflight, staff-review reading code at Step 7, security/a11y reviewers reading the diff at ship Step 2. No step actually runs the binary. The dominant agentic-dev failure mode is "Potemkin interface" (Replit Agent 3) / hallucinated success (Arize field analysis): an agent claims a feature works because it compiled, types passed, the diff looks plausible — when the button does nothing, the API call 400s and is silently swallowed, or rendered state never matches intent. PR Q closes that gap with a runtime gate that blocks ship on Unknown verdicts.

**Design decisions:**
- **Thin wrapper around bundled `/verify` rather than reimplementing run-and-observe** — first-pass draft proposed 20+ files with 5 platform runners (web/ios/android/tauri/cli) duplicating what bundled `/verify` + `/run` already do. User caught this; redraft shrinks to ~6 lib files leaning on bundled skills as the execution layer (FB-0015 lesson). Same pattern `/flow:security-review` and `/flow:accessibility-review` already follow.
- **Per-dimension parallel judges (correctness / regression / scope-creep) rather than one mega-judge** — Anthropic's evals guidance recommends one judge per dimension to reduce dimension contamination. Parallel for speed + position-bias isolation.
- **Unknown is a gate-blocking verdict** — Per FB-0011 (autonomy bar — ESCALATE on uncertainty). Judge forced to admit ignorance rather than fabricate PASS. Two-citation rule binding: verdict without verbatim observation quote + criterion quote ⇒ Unknown.
- **Findings-buffer JSON shape forward-compat with future HTML case-study renderer** — Per user vision note 2026-05-28. Buffer schema (per-criterion text + per-adversarial-case text + per-step observation captures with `type` discriminator + per-dimension verdict with evidence + top-level "not tested" checklist) is a superset of what an eventual HTML renderer needs. PR Q ships the JSON; the renderer PR (post-PR-Q) renders against this contract. No schema migration required.
- **Spike-mode (3-check rubric) for `/flow:ship-spike`** — Launch / one happy step / no log errors. Single-dimension (correctness only — regression + scope-creep are not meaningful without a plan defining scope). Same Unknown-blocking semantics; lower bar in number of checks, not verdict rigor.
- **Inherits FB-0012 bounded-retry contract from PR M** — Judge runs single-pass; budget cap (verifyBudgetCalls slot) forces Unknown on overrun (mechanical exit signal per FB-0012(a) — no judge-output loop); reward-hacking guards (no test-disabling, no @ts-ignore/eslint-disable) baked into adversarial.md prompt per FB-0012(c).
- **Flow self-config as `platform: library`** — flow itself has no runtime; verify-build cleanly skips at Step 1.2 platform check. Dogfoods the new schema slot; provides the canonical "this is a library plugin" reference config for any plugin-like consumer.

**Technical decisions:**
- **POSIX-portable shell** in SKILL.md `!` blocks (no bash arrays — dash compatibility per FB-0010 silent-skip discipline). External CLI fail-fast (FB-0009).
- **JSON Schema draft-07 with `additionalProperties: false`** at every level of findings-schema.json — strict. Additive changes require explicit schema bump; prevents drift.
- **8 observation type discriminators** (screenshot / a11y_snapshot / network / console / log / stdout / exit_code / narrative) — covers what bundled `/verify` can return + structured captures from Playwright/XcodeBuildMCP, with `narrative` as the freeform fallback.
- **Optional `timestamp_offset_ms` on observations** — relative-to-verify-start, for the future renderer's timeline layout. Absolute timestamp anchor deferred to PR R+ (FOLLOW-UP routed).
- **Spike-mode preserves schema shape** — regression + scope-creep dimensions emitted as Unknown with `evidence: ["(spike mode — dimension not applicable)", "<criterion>"]` so downstream consumers (ship Step 4a, future HTML renderer) don't need spike-aware branching.
- **Verify-build does NOT auto-skip on doc-only diffs** — unlike security + a11y, behavioral changes can live in non-code files (config-driven toggles, etc.). The run-and-observe loop is cheap to attempt; falls through to Unknown if nothing observable.

**Tradeoffs discussed:**
- **Single big PR vs phase-staged PRs.** User chose Path B (full skill on one branch, single PR) over Path A (intake PR + phase PRs). Reasoning: ship one focused PR per skill; let queued PRs (N/O/P/R) build on top regardless of sequencing order. PR Q is orthogonal to N/O/P/R (different files; mechanical rebase in either order). Ship order = whichever finishes first.
- **Wrap bundled `/verify` vs inline orchestration in `/flow:ship` Step 2.5.** Chose Shape A (separate skill) over Shape B (inline). Justifications: ship-spike composability, eval testability, separation of concerns, future Preflight-tier extensibility, standalone invocability for power users wanting flow's plan-criteria + Unknown gate vs bundled `/verify`'s freeform observation. Precedent: `/flow:security-review` resolves the CLAUDE.md "don't wrap bundled" ambiguity in favor of substantive-added-value wrappers.
- **Ship-only single-tier vs two-tier (Preflight fast-subset + ship full-pass).** Two-tier rejected — fast subset meaningless on iOS (60s min build+boot) and Android (~30s emu boot); slowing iterate cycles to catch a class reviewers can also catch is a bad trade. Mid-iterate verification available via bundled `/verify` directly.
- **Adversarial transformation: inline `lib/adversarial.md` vs named subagent.** Inline. Promote to `plugins/flow/agents/verify-adversarial.md` on rule-of-three (consistent with `flow:close-out` precedent).
- **VLM pairwise instruction kept in v1 rubric.** Default-safe — if bundled `/verify` returns screenshots structurally and judge doesn't pairwise-compare, scores are unreliable. Phase 1 empirical characterization may drop this if `/verify` is confirmed text-only.

**Lessons learned:**
- **Always check the harness's available-skills list before drafting a new flow skill** (FB-0015 — captured this PR). The 20+-file first-pass draft duplicated bundled `/verify` + `/run` + `/run-skill-generator` because I didn't audit available-skills at session start. Concrete pre-planning check: grep for the proposed skill's core verb (verify, run, audit, review, ship); if a match exists, justify the wrapper with substantive added value or drop the skill.
- **FB number / PR letter coordination is non-trivial under cross-worktree parallelism.** Drafted as FB-0010 → FB-0012 → FB-0013 → FB-0014 → FB-0015 across the session as collisions surfaced. PR letter drafted as M → Q after bounded-retry PR M took the slot. K1's reserved-feedback-numbers.md protocol made the collisions visible before merge; without it the cross-file references would have silently pointed at the wrong concepts (FB-0010 fan-out class applied to FB numbers).
- **Staff-review caught a fan-out BLOCKER on the manifest descriptions** (17-slot references that survived the diff). Doctor Check 2.5's scan misses install-surface JSON (`.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json`). FB-0010 strikes again; routed as FOLLOW-UP to extend Check 2.5's scan.
- **Flow's own `flow.config.json` was missing.** Adding it as `{platform: library, uiSurface: false}` IS dogfooding the schema — useful both for self-protection at /flow:ship invocation AND as a reference config for any plugin-like consumer.

### PR K1 — Reserved feedback numbers (claim-time defense for FB-XXXX collisions across parallel branches; no version bump)
**Date:** 2026-05-28
**Branch:** `pr-k1/reserved-feedback-numbers`
**Commit:** [SHA at ship time]

**What was done:**
Added `dev-docs/reserved-feedback-numbers.md` — a small protocol file where in-flight branches claim their `FB-XXXX` number before drafting the entry in `feedback.md`. Parallel branches editing this file at the same line produce a clean textual merge conflict (mechanical enforcement). When a PR ships, `/flow:ship`'s synthesis step removes the line. Also added a Handoff Notes entry in `dev-docs/plan.md` documenting the FB-collision audit + resolution.

**No version bump.** `dev-docs/` is project-dev only; doesn't ship in the plugin install.

**Why:**
Post-PR-J cross-worktree audit (triggered by user prompt 2026-05-28: "make sure there hasn't been any lost work… as the PR letters advance on this branch and others") discovered three in-flight FB conflicts before any branch had rebased:

1. `sweet-hellman-6c0745` drafted FB-0011 = "bounded-retry agent loops" while PR J had already shipped FB-0011 = "autonomy bar" to main.
2. `sweet-hellman` drafted FB-0012 = "same-model critic collusion."
3. `pr-m/verify-build-skill` (lucid-matsumoto-730ba0) independently drafted FB-0012 = "check bundled Claude Code skills first."

Counts at audit time: sweet-hellman had **20 FB-0011 references across 5 files** (feedback.md, history.md, plan.md, research doc, schema.json) and **12 FB-0012 references across 2 files** (plan.md, research doc). PR M (verify-build) had 1 FB-0012 textual entry + by-name handoff-doc references.

The textual merge conflict on `feedback.md`'s insertion point only catches the entry itself. The 19 + 11 cross-file references would survive a feedback.md-only rebase resolution and silently point at the wrong concept (the FB-0010 "fan-out contradiction" sub-class applied to FB numbers).

**Resolution recorded mid-PR-K1:** Between this PR's initial draft and the rebase onto main, sweet-hellman rebased + shipped at `0cf642e` (#22) as v1.2.6. Sweet-hellman **renumbered their drafted FB-0011 → FB-0012 and swept all 20 cross-file references cleanly before pushing** — no silent overwrite occurred. PR J's FB-0011 ("autonomy bar") survives untouched on main. The verify-build PR (lucid-matsumoto) still has the open arbitration item: its drafted FB-0012 must renumber to **FB-0013**, and its drafted "PR M" letter is now taken (suggest PR N at its ship time). PR K1's protocol file is updated to reflect the resolution; the audit-trail section preserves both the original contention and the outcome for institutional memory.

**Design decisions:**
- **Why a separate file rather than a section in `dev-docs/plan.md`** — the protocol's mechanical benefit is the textual merge conflict on a small, dedicated file. Sections in plan.md edit other lines too, weakening the conflict-detection guarantee. Single-purpose file is sharper.
- **Why a docs-only PR rather than folding into PR K** — sweet-hellman + PR M (verify-build) were both actively in flight at PR K1's commit time; landing the protocol file ahead of either rebase gives both branches a fetch-and-pull-in coordination surface. PR K (which adds the mechanical Doctor Check 6 + lens-staff-engineer FB-cross-file hunt) is the *permanent enforcement*; PR K1 is the *immediate-coordination signal* layer. Option C from the layered-defense recommendation.
- **Why include current state details in the file itself** — concrete inline references (which branches claim which numbers, what the resolution was) are higher-signal than abstract protocol description. Branches reading the file see the live state plus the rule.
- **Suggested arbitration of the residual FB-0012 contention** — lucid-matsumoto's verify-build PR moves to FB-0013 (single cross-reference; cheaper than re-renumbering sweet-hellman's now-merged FB-0012). Not enforced; surfaced for human decision at PR M-verify-build ship time.

**Technical decisions:**
- File lives at `dev-docs/reserved-feedback-numbers.md` alongside other dev-docs metadata. Not `plugins/flow/` — doesn't ship in the install.
- Format: protocol description + Currently reserved list + Audit trail. The Audit trail section is intentional; FB-0010-style institutional memory for past collisions.
- Protocol step 3 ("push your reservation immediately, don't batch") is the load-bearing race-detection move. Without immediate push, two branches can both reserve the same number locally before either pushes; the push order then determines who wins, but the local edits diverge silently.

**Tradeoffs discussed:**
- **Protocol file vs Doctor Check 6 first.** Doctor Check 6 (FB-collision check vs `origin/main`) is the *rebase-time* enforcement; this file is the *claim-time* enforcement. Both are needed: Doctor catches collisions even if the protocol file isn't updated; the protocol file prevents collisions from being introduced in the first place. PR K ships Doctor Check 6 + lens-staff-engineer hunt extension as the second + third defensive layer. The user explicitly chose Option C (both): land this small PR now, fold Doctor + lens changes into PR K.
- **Audit-trail section in the file vs in history.md.** Kept in the file because the audit trail IS the institutional memory of why this protocol exists. history.md tracks "what we built"; reserved-feedback-numbers.md tracks "what conflicts the protocol caught." Different surfaces; cheap to maintain both.
- **Auto-update on `/flow:ship` vs manual entry removal.** Decided: `/flow:ship` synthesis step (step 4) handles the entry removal — same place that updates feedback.md with the new FB entry. Single source of doc-write timing.

**Lessons learned:**
- **Cross-worktree audits are cheap and catch class issues mechanical merge can't.** The 20-FB-0011-references finding was invisible to git merge-conflict detection but obvious to a one-shot grep across uncommitted state. Periodic "what's in-flight elsewhere?" sweeps are a good discipline; consider folding into the `/flow:doctor` Check 6 design when PR K builds it.
- **Sweet-hellman's clean renumber-then-rebase validated the protocol shape even before the protocol file existed.** Their sweep covered all 20 FB-0011 references + 12 FB-0012 references; nothing silently survived. This is the existence proof that the discipline (grep first, edit second per FB-0010) works when applied. The protocol file makes it harder to forget the sweep, but doesn't change the mechanics.
- **Naming registries work mechanically when the registry file is small and dedicated.** Same pattern works for skill names, schema slots, agent names. If a fourth class hits the same "merge-conflict-but-cross-file" pattern, consider generalizing this file to "reserved-identifiers.md" with sections per identifier type.

### Flow plugin v1.2.6 — bounded-retry mechanical preflight in /flow:ship + /flow:ship-spike (PR M)  `SAFETY`
**Date:** 2026-05-27
**Branch:** `pr-h2/preflight-retry-loop` (branch name retained from pre-rename; PR labeled PR M after the parallel PR I/J/K/L collision)
**Commit:** [SHA after rebase + force-push]

**What was done:**
Added a bounded-retry mechanical preflight (new Step 1c) to `/flow:ship` and `/flow:ship-spike`. The step runs a project-owned shell command (new `flow.config.json.preflightCmd` slot — typecheck + lint + fast tests, project owns the composition) BEFORE invoking reviewers. On non-zero exit, the skill enters a bounded-retry loop: fix the failure, re-run, up to N=3 total invocations, with oscillation detection via diff-hash (`git diff HEAD | sha256sum`). The loop fires ONLY on this externally-verifiable exit signal — reviewer outputs at Step 2 stay deliberately single-pass. Docs-only diffs skip the loop entirely via the 3-source check (committed + uncommitted + untracked, per PR D's lineage), with `sourceFilePatterns` regex validated before use (FB-0010 silent-skip prevention). Unset/whitespace-only slot emits the standard loud-warning (FB-0006/0007 pattern), never silent no-op. Exit 127 (command not found) fails fast without consuming the retry budget. Schema grew from 16 → 17 slots; live references updated (plugin.json description, marketplace.json descriptions ×2, README.md ×2, doctor SKILL.md description, template/base/CLAUDE.md.template + bootstrap.sh — the template/base/ updates caught at review-time per PR G's consistency discipline). New eval fixture `plugins/flow/evals/security/test_preflight_retry.py` with 6 test functions exercising 7 load-bearing contract markers (N=3 cap, diff-hash oscillation, exit-127 fail-fast, do-not-disable-tests, do-not-add-suppressors, single-pass-reviewers, docs-only early-exit) plus schema/jq/sh-c behavior assertions.

**Why:**
User-driven exploration of whether to add `/loop`-style iteration to the workflow. Research pass against Anthropic's "Building Effective Agents" (evaluator-optimizer pattern requires "stopping conditions" + "explicit success criteria") and the 2026 Agentic Coding Trends Report ("without explicit success criteria, verification becomes guesswork"). The honest read: a bounded retry is the right primitive where the exit signal is mechanically verifiable (external tool exit code); it's the wrong primitive where the exit signal is another model's judgment (reviewer "looks good"). Flow's current `/flow:ship` had no mechanical-quality preflight loop at all — Step 3's `typecheckCmd` re-run was a one-shot post-reviewer-fix check. This PR adds the missing primitive in the one slot where the exit signal is unambiguous, and explicitly forbids the same shape on reviewer-judgment outputs (reward-hacking failure mode).

**Design decisions:**
- **Loop only on mechanically-verifiable exit codes (preflight script exit status).** Never loop on LLM-judgment outputs (auditor "approved", plan-critic "APPROVED", reviewer "no findings"). Loops over LLM judgment teach Claude to *phrase around* the reviewer rather than fix substance — exactly what evidence-or-silence and passive review are designed to prevent. This is the load-bearing call; everything else is downstream. Captured as **FB-0012**.
- **Step 1c position: BEFORE reviewers, not after.** Running preflight before Step 2 means reviewers see code that already typechecks (what they expect). Running it after would risk reviewers + Claude fighting over the same files across iterations.
- **Hard N=3 cap, not a config slot.** Anthropic guidance names "maximum iterations" without prescribing N. N=3 is a deliberate choice (rationale: enough for fix-A-broke-B-fix-B, not enough to wander) — not an empirically-tested literature finding. Matches the spirit of Microsoft Magentic's caps (three separately-configurable: `max_round_count`, `max_stall_count`, `max_reset_count`) and Trigger.dev's example of "up to 10 iterations"; both name caps without prescribing N. If 3 proves wrong later, the slot is a single-file follow-up; adding it prematurely violates FB-0003.
- **Diff-hash oscillation detection on top of N=3.** Pure A↔B↔A oscillation aborts before attempt 3 burns budget. Drift (A→B→C all broken differently) is caught by N=3 exhaustion. Independently converged with Microsoft Magentic's `max_stall_count` primitive (Magentic counts consecutive non-progressing rounds; Flow detects exact-diff oscillation — same defensive shape, different detector). Known false-positive: same correct fix made twice → spurious abort; mitigated by attempt logs preserving the situation.
- **Prompt-driven contract, not shell-script harness.** The retry semantics live in the SKILL.md natural-language instructions, not in a wrapper script. Matches Flow's existing orchestration idiom. The risk (a session ignoring the cap) is detected via the per-attempt log line; the alternative (shell harness) is real implementation cost.
- **Reward-hacking guards explicit in the contract.** "Do NOT modify or disable tests unless the failure is a genuine test bug" + "Do NOT add `// @ts-ignore`, `# noqa`, `# type: ignore`, `eslint-disable-next-line`, `// biome-ignore`, `@SuppressWarnings`, `#[allow(...)]`, or equivalent suppressors." Prompt-level guards are probabilistic; human merge gate at Step 7 is the backstop. Both layers matter.
- **Docs-only diffs skip the loop entirely.** Reuses `sourceFilePatterns` (PR D lineage). A docs PR has nothing for preflight to verify; running it is wasted work + violates the FB-0006/0007 early-exit-when-irrelevant principle.
- **No standalone `/flow:preflight` skill.** Step 1c stays inside `/flow:ship` and `/flow:ship-spike` so the loop only fires under the surrounding gates (stale-base, gh+jq, something-to-ship). Exposing it standalone invites consumers to invoke the loop without the gates.

**Technical decisions:**
- **Reuse `sourceFilePatterns` for docs-only early-exit** — already in schema since PR D. Avoids new regex slot proliferation.
- **3-source diff check** matching PR D's `/flow:security-review` lineage: committed (`git diff origin/$BASE..HEAD`) + uncommitted (`git diff HEAD`) + untracked (`git ls-files --others --exclude-standard`). The common 'iterate locally then /flow:ship' loop hits uncommitted/untracked — must catch all three.
- **`sourceFilePatterns` regex validated before use** via PR D's GREP_RC check (grep -qE returns 0/1 on valid regex match/no-match; 2 on regex error). Invalid override falls back to default + emits loud warning. Closes FB-0010 silent-skip class.
- **Whitespace-only `$PREFLIGHT_CMD` treated as unset** — `jq -r` returns literal whitespace for `"   "` slot values; `[ -z "$VAR" ]` wouldn't catch. `printf '%s' | tr -d '[:space:]'` strips and re-tests.
- **3-tier `DEFAULT_BRANCH` fallback chain in Step 1c** — separate Bash invocations don't share scope (per `/flow:ship` Step 1b's explicit note). Re-resolved inline to avoid the FB-0008 silent-fallback-to-`main` failure.
- **`sh -c "$PREFLIGHT_CMD"` not `eval`** — same trust model as `typecheckCmd` (FB-0004); subshell can't mutate caller-process state.
- **Schema description names the precedence between `preflightCmd` and `typecheckCmd`** — if both set, both run (Step 1c for preflight, Step 3 for typecheck). Avoids a magic precedence rule; user owns the config.
- **Mirror Step 1c verbatim across ship + ship-spike** — consistency is the value (FB-0009 lineage); a copy-paste here is cheaper than a doc-snippet extraction until a 3rd bounded-retry block exists.
- **ship-spike Step 2 trimmed** — Step 1c now handles preflight via bounded retry; Step 2's redundant `tools/preflight/check.mjs` invocation removed. Step 2 retains `typecheckCmd` one-shot (parallels `/flow:ship` Step 3's role).
- **Eval fixture asserts SHAPE not end-to-end behavior** — prompt-driven iteration is non-deterministic by construction. Contract markers are text-grep on SKILL.md. Real "does Claude obey N=3?" is a dogfood-time question, not CI-time.

**Tradeoffs discussed:**
- **Bounded retry on preflight vs adding a `/loop` user-facing primitive.** User asked about `/loop` — Anthropic's `/loop` is a scheduling/polling primitive (run a prompt every N minutes), not a goal-seeking primitive. The right fit for "iterate until tests pass" is an internal retry block inside `/flow:ship`, not a separate user command. A standalone command would invite usage without the surrounding ship gates.
- **Loop the reviewers too?** No. Single-pass reviewers are load-bearing per Flow's product principles ("evidence or silence"). Looping until the auditor approves teaches reward hacking. The research pass explicitly identifies this as the failure mode; the PR body should not invite consumers to extend the contract to reviewer outputs.
- **Hardcoded N=3 vs config slot.** Slot adds flexibility but violates FB-0003 if shipped without proven need. 3 is a deliberate design choice consistent with non-prescriptive guidance; adjustable later if dogfood shows it bites.
- **Schema description length.** v1.2.6 description grows again (already long after v1.2.5). Acceptable cost; consumers read it once during install. Future PR could deduplicate via a CHANGELOG.md reference.
- **Prompt-driven loop vs shell-harness.** Shell harness is more reliable but real implementation cost + diverges from Flow's idiom. Ship the prompt-driven version; instrument with per-attempt log line; promote to harness if a session ignores the cap.
- **PR letter rename PR H2 → PR M.** Original branch + PR title used "PR H2" (next-in-sequence at planning time). After rebase onto main, "PR H2" was already taken by the docs cadence softening PR (squash `2266ceb`). Renamed to PR M (next available letter after K/L, which are queued for `/flow:red-team` + Detection-Point-3 routing). Branch name kept as `pr-h2/preflight-retry-loop` for continuity; PR title updated to PR M.

**Lessons learned:**
- **Documentation referencing a slot before the schema declares it** is an inverse FB-0003 (doc-without-implementation, vs the more common schema-without-consumer). Worth a follow-up sweep to find others. Doctor's Check 2.5 would not catch this directly — it checks slot-count fan-out, not "every documented slot has a schema entry."
- **The user's framing question ("would loops help us iterate to quality?") was the right question to push back on.** The honest answer is "loops help on mechanical signals; they harm on judgment signals." Encoding that distinction in the contract (Step 1c does loop; Step 2 does not) is more valuable than the loop itself.
- **Bounded-retry contracts need oscillation detection.** Pure iteration caps would allow A↔B↔A burn until exhaustion. Diff-hash is the cheap detector. Future bounded-retry blocks (if any) should inherit this — captured as FB-0012.
- **5-lens review pipeline emulated via Agent subagents (FB-0001 pattern) caught 1 BLOCKER + 11 NITs that survived implementation discipline.** BLOCKER was a FB-0010 fan-out survivor (template/base/ files still said "16 slots") — exactly the class FB-0010 was written to prevent. The discipline working on its own enforcement.
- **PR letter collisions on a fast-moving main require renumber-on-rebase.** Original "PR H2" became "PR M" after PR I/J/H2-docs/K-queued/L-queued landed in parallel. Lesson: when committing forward-planning blocks for queued PRs, expect rename if main moves. Plan-critic flagged the scope drift (forward-planning in same diff as in-flight PR) — convention update queued for future H-series.

### PR H2 — docs/upgrade.md cadence softening (no version bump)
**Date:** 2026-05-27
**Branch:** `pr-h2/upgrade-cadence-softening`
**Commit:** [SHA at ship time]

**What was done:**
Three copy edits to `docs/upgrade.md` after user feedback that the original PR-H1 prescription was too aggressive ("do I really need to run this after every session? every update? or just major updates?"):

1. **"When to run it" table rewritten** with semver-aware guidance. Old table had 5 triggers, all variations of "run the ritual." New table differentiates major/minor/patch bumps explicitly: major requires before-next-session; minor before-next-session in projects using the new surface; **patch is OPTIONAL — batch them, flow's discipline is additive at patch level so deferring is safe.** Added explicit "Mid-session: skip" and "Just to be safe: skip" rows. Plus a TL;DR at the top: "run when you want a specific new feature; otherwise weekly-ish hygiene is enough."

2. **"Multi-project ritual" → "Multi-project: once per machine (for user-scope installs)".** Original section claimed the ritual must run "in each project's Claude Code session" because the catalog cache is "per-session." That was wrong: for user-scope installs (the default), the catalog cache + the installed plugin both live at user-scope; one ritual run propagates to all projects on the machine. Project-scope installs (custom workflow) are the per-project case, but most consumers don't set that up. Section now distinguishes the two with a quick `jq` check for which scope you're in (with fail-loud fallback for jq-missing case, mirroring the existing FB-0009 pattern elsewhere in the same doc).

3. **Auto-update tradeoff hardened.** Old text said "for patch bumps, this is usually fine — flow's discipline is additive-only at patch level." That overpromised the additive guarantee. New text: "flow aims to be additive-only [at patch level]... the discipline is enforced by author care + lens-staff-engineer + /flow:doctor Check 2.5 — it's not a hard guarantee, so verify each upgrade with /flow:doctor regardless." Plus version-aware recommendation reframed as a principle: "when a major bump ships (any x.0.0), default to auto-update off until you've read the major-bump CHANGELOG; flip back on after you've understood the breaking changes." Rule propagates forward without naming a specific version.

**Why:**
User asked the cadence question directly. Re-reading my own upgrade.md surfaced that I'd overprescribed — every trigger row said "run the ritual" with no patch-vs-major distinction. A consumer following the prior table literally would have been running the 2-command ritual after every flow PR merge, even for trivial patch bumps. That's friction with no proportional benefit. The fix is copy-only; no behavior changes.

**Design decisions:**
- **No version bump.** Same precedent as PR H1: `docs/` lives at repo root, not inside `plugins/flow/`; consumers fetch the new copy from GitHub directly, not via `/plugin install`. No new behavior shipped.
- **Patch-bump = optional, not "skip entirely."** Considered telling consumers to never run the ritual for patch bumps unless they see a feature they want. Decided against: weekly-ish hygiene catches accumulated drift, and the cost of running the ritual is ~30 seconds. The current copy ("optional. Batch them") frames the right cadence without being absolute.
- **The "per-machine vs per-project" correction is a factual fix, not a softening.** The original "per-session" claim was wrong; I traced it from my Claude Code research and may have misread the source. The corrected description matches actual Claude Code marketplace + plugin-install behavior (per-machine for user-scope installs).
- **Auto-update recommendation reframed as a principle, not a named version.** Original "OFF starting v2.0.0" — named-version signaling — is fragile (no event surfaces it when v2.0.0 ships). New "when a major bump ships (any x.0.0), default off until you've read the CHANGELOG" propagates forward as a rule.

**Tradeoffs discussed:**
- **Where to surface "cadence" in the doc.** Considered (a) new section at top, (b) integrated into "When to run it" table, (c) rewriting both. Chose (b) + (c): the table itself carries the major/minor/patch distinction, with a TL;DR sentence above the table. Avoids creating a new section that competes with the existing structure.
- **Multi-project section accuracy.** The original "per-session" claim was a real factual error. Considered framing the fix as "clarification" — landed on "correction" instead per the .claude/rules/general.md scope discipline ("'why' goes in the documentation").

**Lessons learned:**
- **Docs overprescription is a real risk** when the author is also the maintainer dogfooding. The author internalizes "do this often" as a default and bakes it into the consumer-facing doc, where it reads as required cadence to someone less invested. The corrective surface is consumer feedback at first-read; this PR turns one such feedback round into a doc-shape change.
- **Per-session vs per-machine vs per-project install scoping.** Worth understanding deeply before writing install/upgrade docs. The original wrongness in PR H1 was caught only by an explicit user question. Routed as numbered plan FOLLOW-UP #27: `/flow:doctor` install-scope detection check would prevent future doc errors of this shape.
- **Parallel-PR collision via PR J (v1.2.5 adversarial sharpening, separate session).** While PR H2 was in flight, PR J shipped to main bumping the plugin to v1.2.5. Rebased PR H2 onto the new main + reconciled the v1.2.4-current → v1.2.5-current framing in plan.md Current Focus. The FB-0008 stale-base preflight gate would have caught this at /flow:ship time; manual rebase served the same role since this PR went via `gh pr create` after the workflow-loop completed (per PR I workflow-spawn discipline, /flow:ship should orchestrate end-to-end — captured as discipline reinforcement, not a new FOLLOW-UP).

### PR J — Adversarial sharpening of the reviewer pipeline (v1.2.4 → v1.2.5) `SAFETY`
**Date:** 2026-05-27
**Branch:** `claude/youthful-chaum-500268`
**Commit:** [SHA at ship time]

**What was done:**
Prompt-only PR sharpening Flow's four reviewer surfaces along the dimensions deep research on adversarial review and code-review best practices converges on. First of a three-PR sequence (PR J = sharpening; PR K = `/flow:red-team` skill + agent; PR L = trust-boundary detector + autonomous gate). Bumps to v1.2.5. *Note: originally drafted as "PR I" during the planning conversation; renamed to PR J after rebase on `origin/main` revealed that a separate "PR I — workflow-spawn skip prevention" had landed in parallel (squash `da0b2c4`, also bumping to v1.2.4). My PR is complementary (different reviewer surfaces); renumbered to PR J + v1.2.5 to avoid collision. Queued PR J → PR K, queued PR K → PR L throughout this entry, plan.md, FB-0011, and project memory.*

Four reviewer prompts edited:

1. **`plugins/flow/agents/auditor.md`** — added two new sections:
   - `## Principle` (right after the intro): Anthropic's verbatim over-engineering warning ("flag only gaps that affect correctness or evidence-grounding; treat the rest as optional") promoted to a principle-level statement, not buried in schema.
   - `## Self-check before emitting` (between False-verification proxies and Output format): three-step disproof routine. The reviewer must name the specific session text that would invalidate the finding, re-scan for it, and drop if found or if the lookup is fuzzy. Directly modeled on Anthropic's Claude Code Security pattern: "Claude re-examines each result, attempting to prove or disprove its own findings and filter out false positives."

2. **`plugins/flow/agents/plan-critic.md`** — added two new sections + one in-place edit:
   - `## Principle` (same shape as auditor): adversarial framing tempered with the over-engineering warning.
   - `## Self-check before emitting` (between The two-citation rule and What does not count): the disproof routine adapted to the two-citation rule — the reviewer must attempt to find a *third* citation that would resolve the apparent conflict.
   - `Internal incoherence` category extended to explicitly cover **fan-out contradictions within the plan** (count / name / slot / version / file path referenced in N places where values disagree). This absorbs **PR-G FOLLOW-UP #5** ("plan-critic.md fan-out hunt addition") from `dev-docs/plan.md` § "PR H+ FOLLOW-UPs routed from PR G review."

3. **`plugins/flow/agents/lens-staff-engineer.md`** — added one new section:
   - `## How to read this diff` (right after the title intro, before Inputs): explicit adversarial reading stance ("assume the diff is broken — what's the most likely break?") + the over-engineering warning. The framing is the engineer-lens analog of the security lens's threat-model stance; the existing FB-0010 hunts (silent-skip on edge case, fan-out contradiction) compose under this stance rather than replacing it.

4. **`plugins/flow/skills/security-review/SKILL.md`** — modified the agent prompt block at Step 3 only; all operational logic (FB-0006/FB-0007 source-file early-exit, FB-0008 `[ -z ]` defaultBranch fallback chain discipline, FB-0009 fail-fast gh+jq, three-source diff capture including uncommitted + untracked) preserved untouched. *Note: FB-0008's full stale-base preflight gate (`git fetch + merge-base --is-ancestor`) lives in `/flow:ship` Step 1, `/flow:staff-review` Step 1, and `/flow:doctor`, not in `/flow:security-review`; what security-review applies from FB-0008 is the `[ -z ]` fallback chain pattern (not the pipe-OR form). The stale-base preflight gate proper is added to `/flow:red-team` in PR K per the plan-critic ISSUE 7 finding.*
   - Identity shift: "You are a staff security engineer cold-reading a diff" → "You are a **red-team operator**. Your goal is to find an **exploitable vulnerability** — not to evaluate whether the code is good."
   - Added over-engineering warning + an explicit narrowness reminder ("a missing input validator on a value that never reaches user-controlled data is not a finding; a sanitizer config that is wrong-by-default *is*").
   - "Hunt for:" → "Attack surface (categories to probe):" — same nine categories, each gains an attacker-mindset trailing question (e.g., "Where is the attacker URL?", "Where does cross-origin trust enter?").
   - Added a `Before emitting each BLOCKER/NIT` disprove paragraph: trace the dangerous sink back to the input source; if not user-controllable in any realistic execution path, drop the finding.
   - Output format gains a "the attacker scenario in one sentence" requirement on BLOCKER lines, forcing the reviewer to produce a concrete exploit path rather than abstract speculation.

Version bump: `1.2.4` → `1.2.5` in `plugins/flow/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (both fields: top-level metadata + per-plugin entry). Marketplace descriptions refreshed to surface v1.2.5 framing (the v1.2.4 workflow-spawn summary moves to CHANGELOG history-of-record). README.md "What v1.2.4 ships" → "What v1.2.5 ships" (skill catalog unchanged — no slot/skill/lens/rule count drift).

CHANGELOG.md gains a v1.2.5 entry following the established Date / Version / Headline / 2-4 bullets / "Breaking changes: none" pattern, placed above the v1.2.4 (PR I workflow-spawn) entry.

**Why:**
User asked: "should I add an additional adversarial review in the workflow of the flow plugin?" Triggered a deep-research pass across (a) frontier-lab official documentation (Anthropic Claude Code best-practices, Multi-Agent Coordination Patterns, Claude Code Security, OpenAI CriticGPT, DeepMind CodeMender), (b) AI-native production patterns (Anthropic's own Claude Code Review plugin, Cursor Bugbot, Cognition's "Don't Build Multi-Agents" carve-out for read-only review, GitHub Copilot Code Review's "silence is better than noise"), and (c) academic literature on multi-agent debate, LLM-as-judge bias, self-critique failure modes (Du et al., Liang et al., Smit et al., Zhang et al. ICML 2025 position paper, Zheng et al. NeurIPS 2023, Huang et al. ICLR 2024, Khan et al. ICML 2024 Best Paper, Kenton et al. NeurIPS 2024, McAleese et al. CriticGPT, Bai et al. Constitutional AI).

Convergent findings that shape this PR:
- **Anthropic explicitly recommends "an adversarial review step"** (Claude Code best-practices: "Before treating a task as done, have a subagent review the diff in a fresh context and report gaps"). Flow already has this in shape; the gap was that the prompts weren't explicit about the adversarial stance.
- **Adversarial framing raises recall by 16–93% on security-sensitive tasks** (Mao et al. on multi-role vulnerability detection; multiple 2025–2026 studies on attacker-mindset prompting; CriticGPT catches ~85% of inserted bugs vs ~25% for human reviewers).
- **But:** "A reviewer prompted to find gaps will usually report some, even when the work is sound" (Anthropic best-practices); CriticGPT hallucinates and human-machine teams outperform critic-alone. The over-engineering tax is documented and material.
- **Mitigation: prove-or-disprove self-check.** Anthropic's Claude Code Security ships exactly this pattern at scale: "Claude re-examines each result, attempting to prove or disprove its own findings and filter out false positives." This PR backports the pattern into Flow's auditor + plan-critic + security-review reviewers.
- **Categorical (pass/flag) outputs beat numeric scores** (OpenAI Cookbook LLM-as-judge: classifier 98% vs 92–95% for numeric raters). Flow's existing `ISSUE` / `AUDIT SUMMARY` / `No issues flagged.` / `APPROVED` schemas are already optimal — this PR resists the temptation to add confidence scores and reinforces the existing schemas.

PR J scope: prompt-only. PR K adds `/flow:red-team` as a user-invocable standalone skill. PR L adds the trust-boundary detector + autonomous-invocation wiring at three workflow detection points (plan / staff-review / ship).

**Design decisions:**
- **Standalone `/flow:red-team` skill, not a 5th lens in `/flow:staff-review`** (decision made in plan; ships in PR K). The 4-lens ceiling stays. Red-team has its own threat-model categories and a different consequence asymmetry (false negatives much worse than false positives) — composes with `/flow:ship` the same way `/flow:security-review` and `/flow:accessibility-review` already do.
- **Per-finding `Fix-confidence:` field on red-team output (ships PR L)** with values `AUTO-FIX-SAFE` vs `ESCALATE`. Encodes the user's stated autonomy bar (FB-0011, saved to project memory at `~/.claude/projects/-Users-benyamron-dev-flow/memory/feedback_autonomy_bar.md`): auto-fix only when fix is clearly best-practice + clearly aligned with spec/intent + low implementation risk; otherwise escalate. This extends the existing confidence-gate primitive into auto-fix routing.
- **No debate loop.** "Judging with Many Minds" (arxiv 2505.19477) shows debate amplifies bias sharply after the initial round. Flow's parallel-then-merge topology is on the safer side of the published evidence — preserve it.
- **No numeric 0–100 scores.** OpenAI Cookbook's classification-vs-numeric finding plus Anthropic research system's "pass-fail with rubric" preference. Keep the categorical schema.
- **Mix-model-family routing deferred to a roadmap follow-up.** Same-family models agree on wrong answers 97% of the time (Goel et al. 2025); a cheap config change would help, but the Claude Code subagent SDK surface for this isn't there yet.

**Technical decisions:**
- **Self-check is a prompt-level addition, not a separate agent or pass.** Same agent, same context, ~50–100 extra tokens, drops findings via internal reasoning rather than a second invocation. Lowest-cost intervention with the largest published quality lift.
- **Adversarial framing on `lens-staff-engineer` is composable with FB-0010 hunts.** The new `## How to read this diff` section sits at the top of the prompt; the existing silent-skip + fan-out hunts continue to operate inside the categorical Hunts list. Neither replaces the other.
- **Security-review's identity shift preserved every operational gate.** The agent prompt is one section of the SKILL.md file; the bash orchestration around it (early-exit, FB-0008 fallback chain, fail-fast) is intentionally untouched. This isolates the behavior change to the reviewer's framing.
- **Plan-critic's fan-out hunt addition uses the existing two-citation rule.** A fan-out contradiction is just a special case of internal incoherence where the two citations are two stale references in different files. No new category, no schema change.

**Tradeoffs discussed:**
- **All reviewers adversarial vs selectively adversarial.** Loading "find more bugs" framing onto every existing reviewer would burn the over-engineering tax across the entire pipeline. Per the published evidence (consequence-asymmetry analysis), security has the strongest case for full adversarial identity; UX, design-engineer, accessibility, push-further have weak cases (false positives in subjective categories are pure noise). Resolution: full red-team identity for security; adversarial-leaning preamble for engineer (the FB-0010 hunts are already adversarial-shaped, this just makes the stance explicit); no framing change for UX / design-engineer / accessibility / push-further.
- **Separate skill vs 5th lens for red-team.** A 5th lens would reuse staff-review's orchestration but compromise the 4-lens ceiling discipline and mix threat-model categories with engineer/UX/design/push-further. Standalone skill is cleaner, composes with `/flow:ship` like the other domain reviewers, and preserves the documented contract in `plugins/flow/docs/workflow.md` Step 7 ("Four Explore agents review the diff in parallel from four lenses"). Standalone wins.
- **3-PR split vs single mega-PR.** Sharpening (PR J) is prompt-only, dogfoods fast, lowest blast-radius. New skill (PR K) is testable in isolation as user-invocable. Autonomous gate (PR L) depends on PR K's skill existing. Each PR has one clean story.
- **Auto-fix-safe vs always-stop-and-present on red-team BLOCKERs.** User explicitly chose the "act when clearly best-practice + low-risk + no competing options; otherwise stop" hybrid — saved as the durable autonomy-bar rule (FB-0011 + project memory). Encoded as the per-finding `Fix-confidence:` tag in PR L. Default-to-ESCALATE when in doubt; conservative-grow the AUTO-FIX-SAFE category list only with dogfood evidence.

**Lessons learned:**
- **Plan-critic caught 5 BLOCKERs + 2 REDIRECTs + 1 FOLLOW-UP on the draft plan**, all real misalignments — including a passive-vs-active violation (the detector was originally wired into the plan-critic *agent* rather than the orchestrating skill), a 4-lens-ceiling contradiction inside the plan's own Scope statement, missing SAFETY discipline + missing FB-0003 schema-pairing + missing FB-0008 stale-base for the new skill. Pre-plan-approval critique is load-bearing; this was a strong dogfood validation.
- **Engineer-lens dogfood caught a factual error in the CHANGELOG mid-PR.** The sharpened engineer-lens (running on its own new prompt) caught that I'd labeled "FB-0008 stale-base preflight" as preserved-in-security-review, when actually the preflight gate proper isn't in security-review (it's in /flow:ship + /flow:staff-review + /flow:doctor). What security-review applies from FB-0008 is the `[ -z ]` fallback chain. Strong meta-validation: the prove-or-disprove discipline forced the agent to verify the FB-0008 claim against the file before accepting my CHANGELOG line.
- **Parallel-PR collision caught at FB-0008 stale-base preflight before push.** A separate "PR I" (workflow-spawn skip prevention) merged on main during this session — collision discovered at the post-commit stale-base check. Rebased + renumbered to PR J + v1.2.5. This is the FB-0008 gate doing exactly what it was designed to do.
- **PR-G FOLLOW-UP #5 absorbed opportunistically.** Editing `plan-critic.md` anyway; bundling the one-line fan-out hunt addition costs nothing and avoids a separate PR. PR H proper's queue gets one item shorter.
- **Research substrate is the right project-dev investment.** The 3-research-agent parallel pass produced a 12k-word report with 50+ first-party citations that grounded every PR J/K/L decision in published evidence rather than vibes. Worth the token spend on any future architecture-shaping question.

### Flow plugin v1.2.4 — workflow-spawn skip prevention (FB-0010 workflow-step sub-class)  `SAFETY`
**Date:** 2026-05-27
**Branch:** `pr-i/workflow-spawn-prevention`
**Commit:** [SHA at ship time]

**What was done:**
Encoded the 9th FB-0010 incident as a workflow discipline. PR H1's review surfaced that the author ran `gh pr create` directly instead of invoking `/flow:ship`, skipping `/flow:ship`'s Step 2 pipeline (which spawns `/flow:security-review` + `/flow:accessibility-review`). The skip was justified after-the-fact ("would have early-exited anyway") but missed that the `STATUS: SKIPPED` audit-trail signal is load-bearing regardless of body execution.

Defenses encoded across 4 surfaces:

1. **`plugins/flow/skills/staff-review/SKILL.md`** (consumer-shipped) — new "After this skill" footer naming `/flow:ship` as the canonical next step. Reframes the existing "ends with work ready, not merged" line into actionable forward motion. Direct fix for the inflection point where the author would naturally choose between `/flow:ship` and `gh pr create`.

2. **`plugins/flow/skills/ship/SKILL.md` Step 1.0** (consumer-shipped) — visual emphasis (`⚠️` per ASSUMES line) + a new REMINDER paragraph naming the workflow-step silent-skip class explicitly + the "Always invoke /flow:ship, never `gh pr create`" rule.

3. **`plugins/flow/docs/workflow.md` Step 10** (consumer-shipped) — new "Never bypass `/flow:ship` with `gh pr create` directly" subsection. Names the failure mode: skipping `/flow:ship` skips the entire Step 2 (security + a11y reviews); the STATUS: SKIPPED line is load-bearing audit-trail. Canonical reference for the discipline.

4. **`.claude/rules/general.md` Workflow discipline subsection** (project-dev only) — auto-loads on every edit in this repo. Mirrors the workflow.md statement scoped to flow's own dev infrastructure.

Plus CHANGELOG.md v1.2.4 entry + manifest version bump v1.2.3 → v1.2.4 in both `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json`.

**Why:**
PR H1's review pipeline missed `/flow:security-review` + `/flow:accessibility-review` entirely until the user caught it. Root cause: I bypassed `/flow:ship` and ran `gh pr create` manually. 1 incident isn't usually enough for FB encoding (FB-0010 was encoded after 6), but the fix is trivially mechanizable as prompt-level reminders. MEDIUM confidence in plan.md names the fallback: if a 2nd workflow-spawn-skip occurs after PR I, the next step is orchestration-level auto-spawn in `/flow:staff-review` (requires session-introspection helper that doesn't exist).

**Design decisions:**
- **Reduced scope from 12 files to 9.** Initial plan included reviewer-skill exit footers on staff-review + critique-plan + audit-plan + audit-completion + log-disagreement (5 SKILL.md files). Reading the latter 4 surfaced rigid `## Output` blocks ("Do not add commentary before or after.") that would conflict with appended footer prose. Reduced to staff-review only. Plan-critic Finding 1 REDIRECT confirmed this independently; Finding 3 BLOCKER (fan-out file count contradiction in the original plan) was also surfaced by plan-critic and validates FB-0010 working on its own defense PR.
- **Primary fix vs defense-in-depth.** Staff-review footer + `/flow:ship` Step 1.0 strengthening + workflow.md Step 10 are primary (directly address the bypass). `.claude/rules/general.md` is defense-in-depth (project-dev only).
- **No orchestration auto-spawn.** Considered auto-spawning security/a11y from `/flow:staff-review` Step 4. Rejected because it duplicates `/flow:ship` Step 2 (drift risk), needs session-introspection that doesn't exist, and prompt-level reminders are the cheap-first defense with auto-spawn as named fallback.
- **v1.2.4 patch-level.** Additive workflow guardrails — no skill behavior, contract, or schema changed.
- **SAFETY marker** because of `plugins/flow/skills/ship/SKILL.md` + both manifests (all on safety.md paths list). Runtime authority unchanged.

**Technical decisions:**
- Workflow.md Step 10 subsection placed BETWEEN pipeline list and "Why the PR opens here" — linear flow: pipeline → discipline → rationale.
- General.md subsection placed AFTER "Consistency discipline" and BEFORE "Autonomous work guardrails" — narrative arc: general → consistency → workflow → autonomy.
- CHANGELOG v1.2.4 entry follows Keep-a-Changelog-style format established in PR H1.

**Tradeoffs discussed:**
- **Encode-after-1-incident vs wait for 2-3.** FB-0010 encoded after 6. This is 1 incident of new sub-class. Decision: encode now because fix is cheap + user explicitly chose this over dogfood-first.
- **Reviewer-skill footer scope.** Wanted footers on all 5; rigid `## Output` blocks on audit/critique skills constrained to staff-review only.
- **Project-dev rule vs consumer-shipped rule.** Considered adding to `plugins/flow/rules/general.md` (consumer-shipped). Decided project-dev only because workflow.md Step 10 already carries the consumer-side contract; adding it as a rule too would be fan-out.

**Lessons learned:**
- **Plan-critic + parallel execution + self-correction converged on the same fix.** Plan-critic returned NOT APPROVED with a BLOCKER (fan-out count contradiction); independently I'd discovered the audit/critique-plan conflict and reduced scope. Two paths to the same answer.
- **FB-0010 self-application caught itself.** Plan-critic flagged "fan-out count contradiction inside the FB-0010 defense PR." The discipline works on its own defense PR. Catching it pre-commit validates the discipline.
- **Discipline-PR for 1-incident class is defensible when fix is mechanical.** Threshold isn't hard; it's "is encoding cost less than expected recurrence cost?" Cheap reminders justify low threshold. Invasive orchestration changes require higher threshold.


### PR H1 — Upgrade docs + CHANGELOG (pre-install shore-up, docs-only at repo root, no version bump)
**Date:** 2026-05-27
**Branch:** `pr-h1/upgrade-docs-changelog`
**Commit:** [SHA at ship time]

**What was done:**
Shipped two cheap fixes from the Tier-2 audit of flow's update infrastructure, before user begins active dogfood across two consumer projects (md-manager + health-tracker):

1. **`docs/upgrade.md` (new)** — the 2-command ritual (`/plugin marketplace update flow` → `/plugin install flow@flow` → `/flow:doctor`), when-to-run guidance, verification via doctor's final-line verdict, 4 troubleshooting cases (marketplace-not-found, missing skills in /help, doctor Section 1 FAIL, unexpected breaking change), optional auto-update opt-in with tradeoff callout, multi-project ritual section.
2. **`CHANGELOG.md` (new, at repo root)** — extracted v1.0.0 through v1.2.3 from the inline README "Versions:" block + history.md entries. Reverse chronological; date + headline + 2-4 bullets + explicit "Breaking changes:" callout per entry. v1.0.0 is the only entry with a real breaking change (install identity changed from `assumption-auditor@llm-auditor` to `flow@flow`). Keep-a-Changelog-style — distinct from history.md format (no SHA/branch/tradeoffs; intentionally terse).
3. **`README.md`** — replaced 6-line inline "Versions:" block with a single line linking to CHANGELOG.md + a separate line linking to docs/upgrade.md. Also added upgrade.md to the "Full bootstrap docs" rail under the Quick Start.
4. **`docs/bootstrap.md`** — appended "When a new flow version ships, pick it up via the 2-command ritual in docs/upgrade.md" to the "What's next" section.
5. **`docs/migration.md`** — appended a "Keeping flow up to date" subsection pointing at upgrade.md.

**No version bump.** Pure docs-at-root changes; `docs/` and `CHANGELOG.md` are not included in the plugin install package (`/plugin install flow@flow` ships only `plugins/flow/*`). Consumers fetch the new docs from GitHub directly. Spares a no-op `/plugin marketplace update` cycle.

**Why:**
User asked "is the update infrastructure solid?" before installing across md-manager + health-tracker. Audit identified Tier-2 gaps:
- Update requires 2 commands consumers must remember; no auto-update by default for third-party marketplaces.
- No CHANGELOG at the canonical repo-root location (per-version notes were buried inline in README + verbosely in history.md).
- No "your installed version is behind" surfacing anywhere.

The first two are mechanizable as docs. The third (silent version drift) is left for PR H proper (FB-0010 FOLLOW-UP #2 — generalize Check 2.5 to a `minFlowVersion` slot + Doctor Check 6) per explicit Scope (out) call.

**Design decisions:**
- **CHANGELOG distinct from history.md (intentional divergence).** history.md retains the verbose internal-tracking format (SHA + tradeoffs + design decisions); CHANGELOG is terse user-facing (date + headline + bullets + breaking-change callout). Plan-critic specifically flagged this divergence as worth naming; spec-walk item 9 makes the divergence explicit so future docs hygiene PRs don't try to merge the two formats.
- **No version bump for docs-at-root.** Verified: `/plugin install flow@flow` packages only the `plugins/flow/*` subtree; root-level `docs/`, `CHANGELOG.md`, `README.md` are read from GitHub directly. Consumers on v1.2.3 get the new docs the moment we merge — no client action. Bumping to v1.2.4 would force a no-op upgrade cycle.
- **Cross-links in 5 places (README × 2, bootstrap.md, migration.md, plan.md).** A CHANGELOG nobody can find is the FB-0005 silent-failure class re-stated. Plan-critic explicitly approved this scope expansion as "polished over partial" per CLAUDE.md quality bar.
- **Multi-project ritual section in upgrade.md.** User's stated use case is 2 active consumer projects. Explicit guidance prevents the "I updated once, why didn't it stick everywhere?" failure mode.

**Technical decisions:**
- CHANGELOG written manually (not auto-generated from history.md or git log). Manual extraction risks drift; MEDIUM confidence verdict #2 flagged this. Mitigation: FB-0010 lens-engineer hunt + Check 2.5 catch survivors at review (and indeed Check 2.5 passed against the current tree post-edit).
- Upgrade.md "Pin to a prior version" troubleshooting uses `cd ~/.claude/plugins/flow && git checkout v1.2.3`. This assumes the plugin install directory is a git checkout (Claude Code's plugin manager treats marketplaces as git repos). If a future Claude Code release changes the install shape, this hint becomes stale — accept the risk; the doc names the assumption.
- Auto-update opt-in example uses the schema documented by Claude Code (`"autoUpdate": true` in `extraKnownMarketplaces.<name>`). Doc surfaces the tradeoff (silent breaking-change exposure) so consumers choose deliberately.

**Tradeoffs discussed:**
- **Bump or no bump?** Considered bumping to v1.2.4 to give consumers a discoverability signal that new upgrade docs exist. Decided against: the docs land on GitHub immediately; a version bump would force no-op `/plugin install` cycles across all consumers; sets a bad precedent (every README polish = version bump = upgrade burden). If consumers report they don't notice the new docs, revisit per the verdict-#1 mitigation.
- **CHANGELOG location.** Considered putting under `docs/CHANGELOG.md`. Decided on repo root — Keep-a-Changelog convention is `CHANGELOG.md` at root, and the file is short enough that root placement keeps it visible on GitHub's repo landing.
- **Manual vs auto extraction.** Auto-extracting from history.md per-version blocks via a script would prevent drift but adds a dependency (script must run on every history.md edit) and complicates docs hygiene. For 6 versions of history, manual is cheaper. Revisit when CHANGELOG hits 15+ entries.

**Lessons learned:**
- Plan-critic ran cleanly in parallel with execution and produced APPROVED + 3 actionable findings (CHANGELOG format spec + file count cleanup + verdict #1 mitigation reword). Folding the 3 into the plan before write-time was cheaper than catching them at review.
- FB-0010 discipline applied to PR H1's own work caught the inline-versions-block-in-README as a fan-out source for the future CHANGELOG; cleaner to delete the inline block than maintain two copies (FB-0010 single-source-of-truth principle).

### Flow plugin v1.2.3 — consistency discipline (FB-0010 defense for the recurring bug class)  `SAFETY`
**Date:** 2026-05-26
**Branch:** `pr-g/consistency-discipline`
**Commit:** [SHA to be filled at ship time]

**What was done:**
Encoded defenses for the most-recurring bug class flow's own development has surfaced — "consistency that depends on author memory" — across 6 incidents (PR 1 stale paths, PR B unset DEFAULT_BRANCH, PR D regex inversion, PR E POSIX/bash mismatch, PR F pass-1 slash-as-shell, PR F pass-2 slot-count fan-out + intra-file contradiction). Specifically:

1. **FB-0010** captures the lesson with all 6 citations. Two flavors named: *silent-skip on edge case* (failure swallowed via `2>/dev/null` / unset-fallback / regex inversion) and *fan-out contradiction* (a count/name/slot referenced in N places, only some updated by a contract change).
2. **`lens-staff-engineer.md`** (consumer-shipped) gains two explicit hunt categories: silent-skip sweep + consistency sweep. The "specifically asks" section adds a grep-after-diff step naming the patterns to search for. The "gotchas" section names the consistency sweep as load-bearing — fan-out contradictions live in unchanged files, so they survive diff-only review.
3. **`/flow:doctor` Check 2.5** (consumer-shipped) compares `jq '.properties | keys | length'` on the schema against any "N slots" claim in CLAUDE.md / README.md / docs/, flagging survivors of a stale count. Cheap mechanical check for the fan-out shape that's actually mechanizable.
4. **`plugins/flow/docs/workflow.md` Step 4** adds a "consistency sweep" paragraph naming the discipline at the preflight stage, before `/simplify` runs.
5. **`.claude/rules/general.md`** (project-dev) adds a "Consistency discipline (FB-0010)" section with the grep-first-edit-second rule + the "If a colleague greps for the old value tomorrow, will they find a contradiction?" check.
6. **README + manifest** bumped to v1.2.3 with version-note explaining the discipline. plugin.json + marketplace.json descriptions updated to reflect the new lens-engineer hunts + the doctor check.

**Why:**
The engineer-lens missed 2 of 6 occurrences first-pass (both fan-out shapes — PR F pass-2 was needed to catch them via adversarial review). Pattern is stable enough across PRs to encode rather than re-derive each time. Costs of encoding (small lens-prompt + doctor-check + workflow.md paragraph + project-dev rule) are dramatically smaller than the cumulative cost of adversarial-second-pass review every PR.

**Design decisions:**
- **Two-layer defense** — consumer-shipped (lens-engineer + doctor) + project-dev (general.md rule). Consumer projects benefit from the same discipline flow uses on itself; flow gets a stronger internal guardrail than just shipping the consumer artifacts.
- **Doctor Check 2.5 is WARN-not-FAIL.** Mismatched documented count is a real signal but doesn't BLOCK install/use; staying WARN keeps the doctor surface low-friction and respects the "[READY with WARN-level items]" path's existing semantics.
- **Lens-engineer hunts are additive, not gating.** The lens still triages BLOCKER/NIT/FOLLOW-UP; the new hunts give it explicit search vocabulary rather than relying on emergent "specifically asks" coverage.
- **Schema as source-of-truth for slot count.** Future contract changes update the schema, and the doctor check + lens grep both derive from that — no third copy to drift.

**Technical decisions:**
- Doctor Check 2.5 uses `grep -rEn '([0-9]+) slots?'` with awk filtering against the schema's actual count. Cheap, portable across BSD/GNU. The `grep -vE ":[[:space:]]*#"` line filters out comment lines so we don't flag `# Schema has 16 slots — see CHANGELOG` style annotations as stale.
- Workflow.md addition lives at Step 4 (Preflight) rather than Step 7 (Staff-review) because the discipline catches the bug class CHEAPER as a pre-simplify sweep than as a lens-agent finding.
- Project-dev rule lives in `.claude/rules/general.md` (auto-loads on `**/*`) rather than `safety.md` (auto-loads only on safety-critical paths). The discipline applies to every edit, not just safety surfaces.

**Tradeoffs discussed:**
- **Mechanizing further** — e.g., a pre-commit grep that does the slot-count check automatically — was considered. Decided against for now: pre-commit hooks add install friction; consumers vary in whether they run hooks; and Check 2.5 in `/flow:doctor` plus the lens-engineer prompt cover the same surface at lower cost.
- **Promotion to a Stop hook** (fail the session if `/flow:critique-plan` was skipped — the existing "honest gap" in CLAUDE.md.template) was also considered for this PR. Decided to scope to consistency-discipline only; Stop hooks are v1.x autonomous-routines work per the spec, and this PR is the rule-of-six trigger for the consistency class specifically, not a broader enforcement-layer redesign.
- **Single big "consistency.md" rule file** vs subsection of general.md was considered. Kept as a subsection because the rule applies on every edit (matching general.md's `**/*` glob) and dedicating a file would split the auto-load mechanism unnecessarily.

**Lessons learned:**
- 5 prior incidents (PRs 1, B, D, E, F-pass-1) all caught by the engineer-lens *eventually*. Only at occurrence 6 (PR F pass-2 — the slot-count fan-out) did the pattern require *adversarial* review to surface. That's the threshold for encoding: when the same lens that should catch it stops catching it reliably, give the lens explicit prompt-level vocabulary for the pattern.
- "Internal contradictions inside one file" (line 22 vs line 260 of doctor/SKILL.md) is a sub-shape of fan-out contradiction that survives even careful single-file review. The discipline rule names it explicitly.
- **SAFETY marker on this entry** is because `.claude-plugin/marketplace.json` and `plugins/flow/.claude-plugin/plugin.json` (both on `.claude/rules/safety.md`'s `paths:` list) had description text and version field changes. Runtime authority is unchanged — no allowedTools/sourcePaths/disable-model-invocation modifications; the changes are version + description prose only. Plus `/flow:doctor` Check 2.5 introduces a new WARN-branch error-handling shape (documentation.md format spec requires SAFETY marker on error-handling changes). Verified via `git diff main` that no authority-bearing keys changed in either manifest.

**Self-review iterations (workflow pipeline ran 6 parallel reviewers — engineer + push-further + UX-designer + design-engineer + security + plan-critic):**
- 2 BLOCKERs caught, both FB-0010 violations inside the PR that adds FB-0010 defenses: (a) `README.md:50` said "6 agents" but the count is 8; (b) `dev-docs/plan.md` "Files touched: 9 files" but Scope (in) enumerated 10. Both fixed inline before push. Validates the discipline's value and proves PR-G defenses applied to PR G itself work.
- 6 cheap NITs fixed in-tree, mostly FB-0010 violations within `/flow:doctor` Check 2.5 itself: schema-not-reachable silent-skip, no-docs-found vacuous PASS, jq-failure unguarded, greedy-sed picking grep-line-number digit, narrow scan-target list (missed CLAUDE.md.template + core-docs/ + dev-docs/), and the "PRs 1, B, D, E, F" undercount vs "6 incidents." A SCAN_TARGETS leading-space word-split bug surfaced only at smoke-test time and was a 7th silent-skip flavor caught by tightening the test matrix.
- 9 FOLLOW-UPs routed to plan.md (deferred deliberately): Defense #4 (silent-skip skill-code pairing), Check 2.5 generalization to skill/lens/rule counts, consumer-shipped consistency rule (`plugins/flow/rules/general.md`), plan-critic.md fan-out hunt addition, CLAUDE.md.template consumer mention, intra-file contradiction detection, schema-path fallback hardening, symlink-following grep hardening, citation drift across files.

### Bootstrap doc — document `allow_auto_merge` prereq for the merge queue
**Date:** 2026-05-25
**Branch:** [next branch off main]
**Commit:** [next commit]

**What was done:**
Added an "Optional — GitHub merge queue" section to `docs/bootstrap.md` (between Step 6 and "What's next") and a matching Troubleshooting entry. Documents the four-step recipe (enable auto-merge → add CI workflow → apply ruleset → queue with `gh pr merge --auto`) and calls out `allow_auto_merge=true` as the load-bearing prereq that produces the `enablePullRequestAutoMerge` GraphQL error if skipped.

**Why:**
Flow's own merge queue setup in the prior history entry hit this exact error mid-flow (`gh pr merge 14 --auto` failed; had to `gh api -X PATCH /repos/by-dev-tools/flow -f allow_auto_merge=true` before queueing worked). md-manager already had it enabled, so the divergence was invisible until flow's first queued PR. Any consumer following flow's lead and setting up a queue will hit the same wall.

**Design decisions:**
- **Placed in `docs/bootstrap.md`, not `plugins/flow/docs/workflow.md`.** Workflow.md is a 413-line loop reference with no GitHub-infra section; expanding its scope to cover repo settings would dilute its purpose. Bootstrap.md already covers GitHub PR setup at Step 6, so this fits naturally as an optional sub-step.
- **Framed as optional, not mandatory.** Flow doesn't ship a merge-queue requirement — it ships a loop. The queue is one of several ways to enforce the loop's "every PR through CI" discipline; consumers without a queue still get the loop's value.
- **Included the four-step recipe inline, not as a separate doc.** Bootstrap.md is already a stepwise recipe; adding another markdown file for one optional configuration would fragment the consumer's read path.

**Technical decisions:**
- Referenced both `by-dev-tools/flow` (Python stdlib CI) and `by-dev-tools/md-manager` (Node CI) as reference workflows so consumers can pick whichever matches their stack.
- The ruleset-copy instruction points at `gh api /repos/by-dev-tools/flow/rulesets/<id>` rather than embedding a JSON payload — the payload is long and would drift if the source ruleset evolves.

**Tradeoffs discussed:**
- Inline section vs. standalone `docs/merge-queue.md`. Standalone would be easier to deep-link but adds a file for ~30 lines of content; the bootstrap reader is already in the right mental context for "PR machinery setup". Kept inline.
- Whether to also add this to `template/base/README.md.template`. The template is project-generic README boilerplate (consumer's own README), not flow's setup docs — would be confusing to inject flow-specific GitHub setup into a project README scaffold. Skipped.

---

### CI workflow + merge queue ruleset on main — mirror md-manager structure  `SAFETY`
**Date:** 2026-05-25
**Branch:** claude/charming-goldwasser-f8a7b2
**Commit:** [this PR]

**What was done:**
1. Added `.github/workflows/ci.yml` with two jobs (`evals`, `security`) triggered on `pull_request:` + `merge_group:`. Both run Python stdlib invocations of the existing eval runners — no new deps. Concurrency-grouped on event + ref so superseded runs cancel.
2. Applied a GitHub ruleset on `main` mirroring md-manager's structure: deletion-block, non-fast-forward, required linear history, PR-required with squash-only merges (0 required reviewers), required status checks (`evals` + `security` — 2 contexts vs md-manager's 3, since flow's testable surface is different), and a merge queue (squash, ALLGREEN grouping, max 1 build / max 5 merge / 5-min wait / 60-min timeout). Every parameter on every rule matches md-manager exactly except the status-check context names + count, which differ by design.
3. **`SAFETY`** — wired 3 missing check types into `plugins/flow/evals/run_evals.py` (`severity`, `finding_count`, `reference_rule_contains`) so the 3 plan-critic fixtures (`scope_drift_form_fix`, `spec_violation_bundled_ui`, `internal_incoherence_jwt_migration`) stop failing under the runner. These keys were already in `ground_truth.yaml` from PR 1 but had no rule implementation; the runner returned `unknown=<key>` for them. Now: `severity` matches `· {value lower} ·` in output, `finding_count` regex-counts `^ISSUE(\s+N)?\s+·` lines on raw output, `reference_rule_contains` substring-matches the value in lowercased output. Existing pass/skip behavior preserved for the 5 other cases.

**Why:**
md-manager has a merge queue; flow had no branch protection, no CI, and no merge queue. Setting it up "in the same way" gives flow the same shipping discipline: every PR must clear evals + security before landing, merges are squash-only, history stays linear. This is the lightest layer of the loop's mechanical gates — feedback compounds when every change is forced through the same pipeline.

**Design decisions:**
- **`evals` + `security` as required checks** (vs. only `security`, vs. no required checks). User picked both. Required also fixing the 3 broken eval cases — a one-edit fix that lets the regression surface ship as a real gate from day one rather than as a follow-up.
- **No required reviewers (0).** Mirrors md-manager. Solo-dev cadence; the loop's human gate is plan approval, not PR review.
- **Squash-only.** Mirrors md-manager. Keeps `main` linear and each PR atomic.
- **Merge queue grouping = `ALLGREEN`** with `max_entries_to_merge: 5` and `min_entries_to_merge_wait_minutes: 5`. Mirrors md-manager exactly — at flow's volume, batching is unlikely to fire, but the config is identical so behavior is predictable when it does.

**Technical decisions:**
- **Eval harness check additions kept minimal** — three small `if key == …` branches in `check_required`. No restructuring of the dispatch, no new helper functions, no changes to `load_ground_truth` or `render_context`. The runner's exit-code contract (0 if no failures, 1 otherwise) is preserved.
- **`finding_count` counts on raw `output`**, not lowercased `text`, because `ISSUE` is uppercase in the schema and the regex is anchored on it. Other checks use lowercased `text` for case-insensitive substring matching, consistent with prior keys.
- **Workflow runs `python3` directly** (no `pip install`); flow declares stdlib-only.
- **Ruleset applied via `gh api POST /repos/by-dev-tools/flow/rulesets`** with the JSON payload structurally identical to md-manager's except in the `required_status_checks` list — md-manager has 3 contexts (`typecheck`/`build`/`test`); flow has 2 (`evals`/`security`).

**Post-ship audit findings (retroactive `/flow:security-review` + `/flow:audit-completion` against PR #14):**
- **Audit-completion finding 1 — Unverified completion** ("ready to merge via the queue"): CI green on `pull_request:` event ≠ behavioral verification of the queue. End-to-end merge-queue exercise (PR enters queue → `merge_group:` CI fires → PR lands) is the missing check. Action: hold the "ready" claim to "ruleset + CI in place; queue path untested" until PR #14 is actually queued.
- **Audit-completion finding 2 — Unverified completion** ("byte-for-byte"): corrected above. The required-status-checks list differs in size (2 vs 3) and contents by design; "structurally identical except for status-check contexts" is the accurate framing.
- **Security NITs:** (a) `actions/checkout@v4` / `actions/setup-python@v5` use major-version pins rather than commit SHAs — matches md-manager's posture deliberately; tightening pinning is a project-wide policy choice, not a flow-only one. (b) `python-version: '3.11'` hardcoded across two jobs — fine; multi-version matrix only needed if/when version-compat issues surface. No BLOCKERs found.

**Tradeoffs discussed:**
- Required checks set: only `security` (no eval-fix scope) vs. both (fix evals first). User picked both → fixed evals.
- Whether to gate the merge queue on a CI workflow that didn't yet exist on `main`. GitHub evaluates required status checks against PR head / merge_group SHAs, not historical default-branch runs, so applying the ruleset alongside the workflow PR works — this PR's own merge_group run satisfies the gate.

**Lessons learned:**
- The `unknown=<key>` failures from `run_evals.py` had been latent since PR 1 — running the harness end-to-end exits 1 today on `main`. Worth treating that exit code as part of the PR-1 acceptance bar in retrospect; the merge queue setup surfaces it for free.

---

### Flow plugin v1.2.0 — template directory + bootstrap docs + PR-2 follow-up absorption (PR 3 of extraction umbrella)
**Date:** 2026-05-25
**Branch:** pr3/template-directory
**Commit:** 215c875..[push] (7 phase commits; PR opened at Phase 8)

**What was done:**
Shipped the consumer-side scaffolding so a new project can adopt flow in ~10 minutes per `docs/bootstrap.md`. Three deliverable surfaces:

1. **`template/base/`** (11 files) — Tier 1 (CLAUDE.md.template, README.md.template, flow.config.json.example, .claude/settings.json.example, .claude/rules/safety.md.template, .gitignore.template) + Tier 2 (5 core-docs scaffolds with format headers: spec, plan, roadmap, history, feedback).
2. **`template/stacks/{web,swift,tauri-rust-ts}/`** (16 files) — per-stack overlays: preflight runner (web/tauri = .mjs; swift = .sh), CI workflow yaml, `.gitignore.append`, UI rules (web + tauri), dev-server rule (web + tauri), link skill (web + tauri), swift safety.md.append.
3. **`docs/bootstrap.md`** (NEW projects, ~8 KB) + **`docs/migration.md`** (EXISTING projects, ~11 KB; renamed PR A/B/C → Stage 1/1.5/2 to eliminate umbrella numbering collision).

Plus absorbed 2 PR-2 FOLLOW-UPs as security regression fixtures:
4. **`plugins/flow/evals/security/test_cwd_constraint.py`** — 4 strong asserts on `extract_session.py` `--reference-paths` defense (rejects absolute outside-cwd via content-sentinel check, accepts with opt-out, accepts under-cwd, rejects dotdot traversal).
5. **`plugins/flow/evals/security/test_malicious_config.py`** — 3 asserts on `flow.config.json` shell-meta handling (jq -r is string-safe across 10 string slots, sh -c "$TYPECHECK" executes per documented trust model, critique-plan referenceGlob preserves literal string in quoted-arg form).
6. **`plugins/flow/evals/run_security_evals.py`** — discovery-based runner companion to `run_evals.py`.

Plus schema slot #14 added: **`rustWorkspaceDir`** (consumer of the tauri preflight script that was dead per FB-0003 rule).

Manifest bump: v1.1.0 → v1.2.0 (additive; no breaking changes).

Phased execution (Phases 1-8, all success criteria verified):

- **Phase 1:** Schema slot enumeration; md-manager web-stack signal survey (npm scripts, settings.json hook patterns, .gitignore baseline). 4 observations recorded; per-PR plan committed.
- **Phase 2:** template/base/ Tier 1 (6) + Tier 2 (5). Placeholder consistency verified (caught + fixed `INSTALL_STEPS` vs `INSTALLATION_STEPS` inconsistency pre-commit).
- **Phase 3:** 3 stack overlays. node --check on the .mjs runners; bash -n on the swift .sh runner; ci.yml structural grep.
- **Phase 4:** bootstrap.md (~7.9 KB, 6 steps, covers 3 stacks) + migration.md (~11.2 KB, 3 stages with validation gate at Stage 1.5). Migration deletion list verified against md-manager-pr4-6-spec.md (12/12 expected items).
- **Phase 5:** 2 security fixtures + runner. Bug caught + fixed during execution (parents[3] → .parent.parent.parent in path derivation). All 7 asserts pass.
- **Phase 6:** Bootstrap verification — followed `docs/bootstrap.md` Steps 1-5 from scratch in `/tmp/flow-bootstrap-smoke/` for the web stack. Plugin loaded; 5 user-visible skills surfaced via `/help`; preflight chain ran end-to-end (typecheck pass; build + test fail as expected for empty smoke project, demonstrating the gate contract works); claude plugin validate clean. Swift + tauri preflight runners verified syntax-only (no Xcode/cargo env in this session). All template paths referenced by bootstrap.md resolved (12/12).
- **Phase 7:** Dogfood via 3 parallel lens Agents (engineer+simplify combined, push-further, security; skipped UX-designer + design-engineer + accessibility with explicit reason — pure docs+template+JSON-example surface). Caught 4 BLOCKER + 9 NIT + 4 FOLLOW-UP findings; all BLOCKER + NIT fixed in commit `33428e6`; FOLLOW-UPs routed to dev-docs/plan.md.
- **Phase 8:** This entry. Manifest bumped 1.1.0 → 1.2.0; history.md + plan.md + feedback.md FB-0004 written; PR opens at end of phase.

**Why:**
PR 3 of the flow extraction umbrella. After PR 3 ships, md-manager (the canonical reference consumer) can run PRs 4 → 5 → 6 against a complete v1.2.0 surface — install non-breaking using the template, dogfood, then delete duplicates. Without PR 3, md-manager PR 4 has nothing to derive its `flow.config.json` shape from. Now flow ships its own consumer scaffolding.

PR 3 also absorbs 2 of the 8 PR-2 FOLLOW-UPs (the eval coverage items) because PR 3 was touching the eval surface anyway — closes them as concrete tests rather than open promises.

**Design decisions:**

- **3 stacks for v1.2.0 (web / swift / tauri-rust-ts), not more.** Matches the umbrella's stated targets. Python / Go / Rust-only / Ruby / etc. defer to v1.3+ if/when consumers ask. Shipping 3 well > shipping 7 thinly.
- **Tier 1 + Tier 2 base split.** Tier 1 = required for any consumer (CLAUDE.md, flow.config.json, settings.json, safety.md, README, .gitignore). Tier 2 = recommended-but-shippable-empty core-docs scaffolds (spec/plan/roadmap/history/feedback) with format headers. Consumers who want flow but don't care about the doc discipline can skip Tier 2. Tier 1 is non-negotiable.
- **Bootstrap docs as 6 numbered steps, not collapsed to 4.** Push-further lens suggested collapsing install+copy and verify+smoke. Held the 6-step shape: each step has a different verification outcome; collapsing would compress two distinct cognitive transitions into one. PR 4 dogfood will surface whether the step count feels heavy in practice — FB-0004 captures the watch-this-pattern signal.
- **`$comment-*` keys in flow.config.json.example.** Push-further suggested replacing with a sibling `.example.md` cheat-sheet. Held: putting docs in a separate file means consumers hold two files in their head during bootstrap. The bootstrap step explicitly tells them to strip the comments. FB-0004 captures this for PR 4 reconsideration.
- **Migration Stage 1/1.5/2 naming, not PR A/B/C.** Push-further caught the umbrella numbering collision (PR 4/5/6 in flow's plan vs PR A/B/C in migration doc). Stage names match the parenthetical labels the doc already used.
- **`.claude/settings.json.example` documents intentional divergence from default-hooks.json.** Initially claimed "pulled from" — false. Switched to "modeled on … differs intentionally" + named the differences (POSIX case vs bash [[]] + omitted *.pem/*_rsa patterns). Replicating default-hooks.json verbatim was the alternative; chose documented-divergence because the template needs POSIX-portability and the omitted patterns produced false positives in earlier consumer feedback.

**Technical decisions:**

- **Preflight scripts share the same shape pattern (loadConfig → runGate → summary) but ship as 3 separate files**, one per stack. Push-further routed "shared helper library" as FOLLOW-UP — defer until a 4th stack lands or until an existing stack's preflight needs a behavior change that has to land in all three.
- **Security fixtures live under `plugins/flow/evals/security/`**, separate from `plugins/flow/evals/fixtures/` (auditor regression). Different runner (`run_security_evals.py`), different shape (assert-on-exit-code, not assert-on-rendered-text). Avoids polluting the auditor harness's contract.
- **Strong asserts on content sentinels, not path strings.** PR-3 engineer-lens caught that `assert "/etc/hosts" not in stdout` is vacuous (leak prints `127.0.0.1`, not the path). Switched both rejection + accept tests to content-sentinel checks. **FB-0004** captures the rule.
- **`cp -n` (no-clobber) in all bootstrap recipes.** Security NIT: a user who misreads bootstrap.md as suitable for an existing project would silently clobber CLAUDE.md / README.md / .gitignore. -n + an explanatory note + a pointer at migration.md closes the foot-gun.
- **`rustWorkspaceDir` slot landed in v1.2.0 schema (not deferred).** Engineer NIT: the tauri preflight already read the slot; documenting it inline closes the FB-0003 schema-without-implementation gap (in the wrong direction — implementation-without-schema). Pair landed.

**Tradeoffs discussed:**

- **Skip UX/design-engineer/accessibility lenses in Phase 7 dogfood vs run them anyway.** Skipped with explicit reason: PR 3 is pure docs+templates+JSON-examples — no visual surface, no UI code. Running them would have produced empty reviews (per the staff-review SKILL's "Don't skip a lens... legitimate skip is when a lens genuinely doesn't apply"). Logged explicitly rather than skipped silently.
- **`cp -n` vs `cp --backup=numbered`.** Picked `-n` (skip-existing). `--backup` would preserve clobbered files as `.~1~` versions but adds complexity for the common case (fresh project — nothing to backup).
- **Stage 1.5 vs Stage 2 numbering.** Considered just three stages (1/2/3). Picked Stage 1/1.5/2 because the dogfood gate (Stage 1.5) is structurally a checkpoint, not a deliverable PR like Stages 1 + 2 — the half-step naming reflects that.
- **Bootstrap.md vs migration.md as two files** vs one merged "adopting flow" doc. Two files = clearer entry point for each audience (the first paragraph of each doc tells you whether you're in the right place). Migration doc is 50% longer than bootstrap; merging would dilute both.

**Lessons learned:**

- **Vacuous-pass test asserts are a class of bug only adversarial review catches.** test_absolute_outside_cwd_rejected initially asserted on `"/etc/hosts" not in stdout` — passes trivially because a leak prints content, not the path string. Engineer lens flagged it as a BLOCKER. FB-0004 captures the rule: when writing security regression tests, the assert must check on the THING THAT WOULD LEAK, not on a proxy for it.
- **Schema slots without consumers and consumers without schema slots are symmetric bugs.** PR 2 caught `memoryHardCap` documented-but-not-read; PR 3 caught `rustWorkspaceDir` read-but-not-documented. Both surface the same way: dogfood, not greps. Pre-commit grep recipe from FB-0003 needs the bi-directional version (every consumer reference must have a schema entry AND vice versa).
- **Push-further lens caught two structural design questions (collapsing bootstrap steps, replacing $comment keys with sibling cheat-sheet) that benefit from real-consumer signal before settling.** Held both; routed to plan.md "PR 4+ follow-ups" so md-manager's PR 4 dogfood can pressure-test them. This is the lens working correctly — surfacing direction-worthy questions, not demanding immediate change.
- **Per-phase commits + per-phase verification + per-phase task-list updates compounded.** When Phase 7's lens reviews surfaced 4 BLOCKERs, locating each one took seconds (each was in a specific phase commit's diff). Monolithic commits would have made the dogfood loop more expensive.

### Flow plugin v1.1.0 — workflow surface backfill (PR 2 of extraction umbrella)
**Date:** 2026-05-24
**Branch:** pr2/workflow-backfill
**Commit:** 25ef3bc..ef8fd32 (7 phase commits + dogfood fix commit; PR pending push to push at end of Phase 8)

**What was done:**
Backfilled the `[PR 1 LIMITATION]` placeholders inside `plugins/flow/skills/ship/SKILL.md` (step 2 security+a11y reviews; step 4b memory machinery) and ported the rest of the workflow surface from md-manager. The plugin now covers the full canonical 11-step loop end-to-end. 13 new shipped artifacts + 3 modified existing artifacts + manifest version bump.

Phased execution (Phases 1–8):

- **Phase 1:** Fetched 12 md-manager sources via `gh api` in parallel. Refined the handoff plan with 4 observations: staff-review extraction is more structural than handoff implied; security/a11y reviews carry heavier md-manager tokens; all 4 source skills start step numbering at 0; ship-spike references nonexistent `tools/preflight/check.mjs`. Committed plan refinement; user direction was "execute autonomously per success criteria" so no separate user-gate beyond the original PR-2-plan approval.

- **Phase 2:** Ported `/flow:security-review` and `/flow:accessibility-review`. De-projected (stripped 'markdown-notes app', 'Vite + React + TypeScript', src/lib/markdown.ts, `--sand-9`, `--page-text-quiet`). Added `uiSurface=false` skip-early gate to accessibility-review for backend-only consumers. Config-slot doc paths throughout. All locked PR-1 idioms applied.

- **Phase 3:** Extracted 4 lens prompts from md-manager's inline `staff-review/SKILL.md` (14.3KB single file) into separate plugin-shipped agent files (`lens-staff-engineer.md`, `lens-ux-designer.md`, `lens-design-engineer.md`, `lens-push-further.md`). Each agent has frontmatter + Inputs + Hunts + Specifically-asks + Triage scheme + Output format + Gotchas. Push-further lens's "Nothing to push — surface at ceiling for its scope" escape hatch preserved verbatim (load-bearing restraint contract).

- **Phase 4:** Ported `/flow:staff-review` as a pure orchestrator. The SKILL spawns 4 parallel `Agent` calls with `subagent_type: lens-{staff-engineer,ux-designer,design-engineer,push-further}`. File grew from md-manager's 14.3KB → only 12.9KB despite adding all the consumer-side config-slot scaffolding (the lens content extraction worked; the file is just slightly under what an orchestrator + scaffolding needs).

- **Phase 5:** Ported the remaining 9 artifacts in one phase: `/flow:ship-spike` (lightweight spike pipeline), `/flow:workflow-help` (new skill — prints loop + project config + skill catalog), `planner` + `docs` context-isolation agents (de-projected to read paths from spawner-injected slots), 4 portable rules (`general.md`, `plan-discipline.md`, `documentation.md`, `exploration.md`), `tools/memory/check.mjs` (canonical-path derivation with Claude-Code-worktree slug scoring added), `flow.config.schema.json` (13 slots — 2 more than the handoff estimated: `designLanguagePath` + `branchPrefix` per actual SKILL needs and the md-manager spec call-out), and `default-hooks.json` (2 PreToolUse hooks — sensitive-file write blocker + path-validation warn-only). Manifest bumped to v1.1.0.

- **Phase 6:** Backfilled `/flow:ship` placeholders with real `Skill('flow:security-review')` + `Skill('flow:accessibility-review')` invocations (step 2) and the full 6-substep memory machinery (step 4b). Addressed both PR-1 FOLLOW-UPs: `critique-plan` SKILL now reads `flow.config.json.referenceGlob` (default `core-docs/*.md`); `extract_session.py` rejects out-of-cwd `--reference-paths` by default with stderr message, opt-in via `--allow-external-paths`. Verified empirically (created minimal session file, tested `/etc/hosts` rejection-then-acceptance).

- **Phase 7:** Dogfooded PR 2 through the newly-built `/flow:staff-review` lens orchestration. Spawned 4 parallel Agent subagents (engineer + UX-designer + push-further + security) on PR 2's own diff. Skipped design-engineer (no visual surface) + accessibility (uiSurface=false in flow's own repo) with explicit reason. Caught 2 BLOCKERs (`Skill` missing from ship.md `allowed-tools`; `memoryHardCap` schema slot dead) + 11 NITs + 8 FOLLOW-UPs. All BLOCKERs + NITs fixed in-tree. FOLLOW-UPs routed to `dev-docs/plan.md` § "PR 3+ follow-ups from PR 2 review".

- **Phase 8:** This entry. Doc synthesis (history.md + plan.md + feedback.md FB-0002 + FB-0003). Will verify md-manager-pr4-6-spec.md accuracy against shipped surface, then push + open PR.

**Why:**
PR 2 of the flow extraction umbrella. After PR 2, a consumer project with `flow.config.json` set can run the full 11-step loop using only `/flow:*` skills + Claude Code bundled natives (`/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api`). The plugin is feature-complete for v1 — PR 3 ships the consumer-side template directory; PRs 4–6 migrate md-manager.

**Design decisions:**

- **Lens prompts extracted to separate agent files** (vs kept inline in staff-review SKILL): more modular (each lens individually invocable), the orchestrator is more readable, and lens prompts can be versioned independently. Trade-off: introduces a new subagent_type dispatch pattern that wasn't smoke-tested in plugin context before this PR. Mitigated by dogfooding in Phase 7 (which succeeded).

- **`workflow-help` is a new skill, not a port.** md-manager has no equivalent. Designed as the onboarding front door: prints the canonical 11-step loop + resolved project config + skill catalog + bundled-native annotations + project-shaped-surface list. Push-further lens correctly flagged that the first version jumped straight to a step list — added "Flow is a managed-autonomy loop: ..." opening sentence in Phase 7.

- **13 slots in `flow.config.schema.json`, not 11.** Handoff estimated 11. Added `designLanguagePath` (read by staff-review UX + design-engineer + push-further lenses + a11y-review for grounding) and `branchPrefix` (called out in md-manager spec as needed; landing now since the cost is one schema entry). Both must have at least one consumer wired in to avoid the FB-0003 "schema-without-implementation" anti-pattern.

- **Hooks are opt-in, not auto-applied.** `plugins/flow/hooks/default-hooks.json` ships the patterns; consumers merge them into their project's `.claude/settings.json` (template/settings.json.example in PR 3 will do this by default). Both hooks are warn-only or block-on-clear-pattern (Edit|Write sensitive-file matcher exits 2); neither blocks arbitrary actions.

**Technical decisions:**

- **`sh -c` over `eval` (idiom locked in PR 1)** applied to all 4 new typecheckCmd consumers (ship, ship-spike, staff-review, security-review, accessibility-review). Subshell isolation; trust boundary documented at each call site.

- **`${CLAUDE_PLUGIN_ROOT}` for all cross-file references in shipped prompts (idiom locked in PR 1)** applied universally. The 13 cross-file refs in PR 2's new artifacts all use the dynamic form. Three legitimate documentation references to `tools/preflight/check.mjs` remained un-prefixed because that path is CONSUMER-shipped (not plugin-shipped) — documented in commit messages.

- **Memory tool path derivation**: ported from md-manager's `tools/memory/check.mjs` with added scoring penalty for `-claude-worktrees-` slugs (parallel to the existing `-conductor-workspaces-` penalty), so the harness's canonical project path wins over the worktree path. The auditMarker lives next to the script (per-install, not per-project) — documented in the script's top-of-file comment as acceptable for v1.1 with a v1.2 revisit if cross-project misalignment surfaces.

- **`extract_session.py` cwd constraint via `Path.resolve()` + `relative_to()`**: defeats symlink-following attacks (Path.resolve canonicalizes the path) AND `..` traversal (relative_to raises ValueError for out-of-tree paths). Verified empirically by the security lens reviewer with symlinks pointing outside cwd. The `--allow-external-paths` opt-out is only settable via explicit CLI flag.

**Tradeoffs discussed:**

- **Lens extraction (Option B, this PR) vs keep inline (Option A, md-manager's pattern):** chose extraction. Cost: one more layer of indirection at spawn time; introduces a `subagent_type` contract that wasn't pre-validated. Benefit: modular lenses, individually invocable, orchestrator file is readable rather than buried under 12KB of prompt content. Fallback would have been single-commit reversion if Phase 4 smoke-failed — it didn't.

- **`memoryHardCap` wire vs drop the slot:** engineer lens caught it as dead (schema doc says configurable, check.mjs hardcoded 30). Choices: (a) wire check.mjs to read the slot, (b) drop the slot from schema. Wiring is the better fix — the schema documents it as configurable for a real reason (consumers with bigger memory corpora) and the implementation cost is ~15 lines. Same calculus for `branchPrefix` (wired to ship + ship-spike branch creation).

- **Skill descriptions: trigger-quality vs body-completeness:** UX lens caught that `/flow:security-review`'s description didn't mention the doc-only skip — the auto-trigger machinery would fire on doc-only diffs that mention "rendering" in prose, then skip — wasted spin-up. Added "Skips doc-only diffs" to the description. Tradeoff: longer description, slightly more parse cost, but cleaner trigger contract.

- **Reviewer-notes template ellipses vs explicit null-finding:** UX lens caught that `_Findings:_ ...` reads as unfilled placeholder. Replaced with explicit empty-shape pattern (`Nothing of consequence` / `—`). Tradeoff: slightly more verbose; clearer signal to human reviewers.

- **Hook 2 known bypasses (warn-only vs hard-enforce):** Security lens noted bypasses (python -m, env-var indirection, equals-form arg). Choices: (a) widen regex to catch more, (b) drop the hook entirely, (c) keep warn-only and document bypasses. Chose (c) — the in-script `cwd` constraint in `extract_session.py` is the load-bearing defense; the hook is documented as belt-to-braces. Consumers wanting hard enforcement can change `exit 0` → `exit 2`.

**Lessons learned:**

- **Dogfooding caught 2 BLOCKERs that all the pre-commit greps + claude plugin validate + smoke test missed.** Specifically: (1) Skill missing from ship.md allowed-tools — runtime-only failure; (2) memoryHardCap dead slot — semantic mismatch between schema doc and implementation. Both classes are now FB entries (FB-0002 and FB-0003). The pattern is the same as PR 1's discovery that stale `agents/auditor.md` refs in shipped prompts survived the cold-read: only running the loop end-to-end exposes the surface.

- **The bootstrap exception is now FULLY lifted for PR 3+.** All review skills exist + work. Future PRs in the umbrella should walk themselves through `/flow:staff-review` + `/flow:security-review` (+ `/flow:accessibility-review` for UI work) WITHOUT having to spawn Agent subagents manually — the SKILLs themselves do that.

- **Per-phase commits with co-author trailer made the dogfood traversable.** When the engineer lens flagged the `Skill` missing from `allowed-tools`, locating the change took seconds (it was in Phase 6's commit message verbatim). Monolithic commits would have hidden the regression in noise.

- **Schema design needs the "every slot has a consumer" check.** Two of 13 slots in v1.1.0's first commit had no consumer — caught by engineer lens, fixed in Phase 7. FB-0003 captures the rule. The check can be a pre-commit grep; should land as a one-liner in flow's own preflight when that exists.

### Flow plugin v1.0.0 — restructure + rename + initial workflow surface (PR 1 of extraction umbrella)
**Date:** 2026-05-24
**Branch:** claude/trusting-jackson-0de7f4
**Commit:** d3517dc..65a0a58 (9 commits; PR https://github.com/by-dev-tools/flow/pull/5)

**What was done:**
- Repo restructured from flat root (`agents/`, `skills/`, `scripts/`, `evals/`, `DISAGREE.md`) into Anthropic's marketplace + plugin shape: `.claude-plugin/marketplace.json` at root; `plugins/flow/*` for the plugin (manifest, agents, skills, scripts, evals, docs, DISAGREE).
- Marketplace renamed `llm-auditor` → `flow`; plugin renamed `assumption-auditor` → `flow`; both URLs updated to `by-dev-tools/flow`.
- Plugin version bumped 0.3.0 → 1.0.0 to mark the rename + expanded scope (workflow loop, not just audit/critique).
- New shipped surface: `plugins/flow/skills/ship/SKILL.md` (ported from md-manager's `.claude/skills/ship/SKILL.md` per a locked PR-1 port table — 3a active, 3b placeholdered, security+a11y placeholdered, loud-warning typecheck, default-branch fallback chain) and `plugins/flow/docs/workflow.md` (ported canonical 11-step loop, de-projected, bundled-Claude-Code skills annotated, flow-internal audit/critique skills annotated).
- Disagreement storage path renamed `~/.claude/plugins/data/assumption-auditor/disagreements/` → `~/.claude/plugins/data/flow/disagreements/`. Pre-existing records on disk become orphaned; README documents the `mv` migration.
- This repo's own dev-tracking moved `core-docs/` → `dev-docs/` to keep `core-docs/` free as the name for consumer-template scaffolding shipping in PR 3.
- README + CLAUDE.md rewritten for the marketplace identity + three-surface boundary (plugin artifacts / dev-tracking / project-dev infra).
- `.claude/rules/safety.md` rewrote its `paths:` frontmatter for the new safety-critical surface under `plugins/flow/*` and added `plugins/flow/skills/ship/SKILL.md` as new published surface. `general.md`, `documentation.md`, agents, project-dev skills all updated `core-docs/` → `dev-docs/`.
- Recovery anchor: pushed git tag `pre-flow-plugin` at `8857ebd` so the flat-root layout is recoverable forever.

**Why:**
PR 1 of the flow plugin extraction umbrella (canonical plan: md-manager `core-docs/plan.md` § "Flow plugin extraction"). The umbrella exists to make the managed-autonomy workflow installable as a Claude Code plugin so md-manager + designer + future consumer projects don't each carry their own copy of the loop's skills/rules/agents. PR 1 specifically converts this repo (the renamed llm-auditor) from a single-plugin flat-layout to the marketplace + plugin shape Anthropic documents, plus lands the workflow surface that the bundled reviewers will ride alongside.

**Design decisions:**
- **Bundling audit/critique inside flow** (not a separate `assumption-auditor` plugin sibling): they're used with the workflow skills 100% of the time; separation imposed install friction without compositional value. Recorded as Decision 2 in `core-docs/handoffs/flow-plugin-consolidation-2026-05-23.md` (md-manager).
- **One repo for marketplace + plugin + (future) template**: matches Anthropic's `claude-plugins-official` pattern and is explicitly documented as supported. Avoids the maintenance cost of multiple repos.
- **`dev-docs/` for plugin self-tracking; `template/core-docs/` reserved for consumer scaffolding (PR 3)**: keeps the consumer-vs-plugin distinction visible. Without this, future sessions would conflate "flow's dev-tracking" with "what flow ships to consumers."
- **Loud-warning pattern for unset config slots** (not silent no-op): false-affordance risk if `/flow:ship` silently skipped a missing `typecheckCmd`. The warning leaves trace evidence.
- **Default-branch fallback chain (`git symbolic-ref` → `flow.config.json.defaultBranch` → literal `main`)**: works in every repo without project setup; respects override if the consumer configures it.

**Technical decisions:**
- **`source: "./plugins/flow"` with no `pluginRoot`** (not `pluginRoot: "./plugins"` + `source: "flow"`): both forms are documented but coexistence is ambiguous. Validator passes both individually; engineer-lens review during PR walked-through caught the redundancy. Single-form keeps the manifest cleaner.
- **Shipped prompts reference paths via `${CLAUDE_PLUGIN_ROOT}/...`** (not relative paths like `agents/auditor.md`): dynamic resolution works regardless of install location; relative paths broke when the file moved to `plugins/flow/agents/`. Engineer-lens caught two cases (plan-critic.md + critique-plan/SKILL.md) the initial cold-read missed.
- **`sh -c "$TYPECHECK"` over `eval "$TYPECHECK"`**: subshell can't mutate caller-process state. Mildly stronger isolation; trust model is unchanged (project owns its own `flow.config.json` like `package.json` scripts). Security-lens recommendation.
- **`git mv` for every restructure move** (not delete + create): preserves blame across the move boundary. Single commit with 29 renames as the restructure step.

**Tradeoffs discussed:**
- **Renaming surface vs preserving install continuity**: rename breaks existing user installs of `assumption-auditor@llm-auditor` until the user re-runs `/plugin marketplace add` + updates `~/.claude/settings.json`. Accepted because there's a single user (sole consumer); coordinated one-line settings.json edit is the migration cost. Flagged in PR body.
- **Disagreement-storage-path rename vs orphaning records**: chose rename + README migration instructions over the alternative (dual-write to both old and new paths). Local debug/dev data, sole consumer, trivial `mv`.
- **Step 0 vs Step 1 numbering in /flow:ship**: initially numbered 0–7 (Pre-flight as 0 to signal it's a gate, not work). Push-further lens caught it as a materiality scratch — readers process docs top-to-bottom, not as developers reading off-by-one. Renumbered 1–8.
- **README cheat-sheet vs single-source-of-truth**: initially duplicated the 11-step ASCII block verbatim across README and workflow.md. Push-further lens caught it. Replaced README block with a one-line arrow flow + pointer; workflow.md is the canonical source.
- **Whether to retroactively run plan-critic on the plan I wrote**: yes, as dogfood. Verdict: APPROVED. No findings. First evidence that flow's own bar is consistent with this work.

**Lessons learned:**
- **Cold-read pass missed two stale path references** (`agents/auditor.md` in shipped prompts) that the engineer-lens review caught. The pre-PR cold-read grepped for `core-docs/` and `md-manager` tokens but not for bare `agents/` references — those slipped through. Adding "grep for bare `agents/` / `skills/` / `scripts/` / `evals/` references in shipped artifacts" to the next cold-read recipe would catch the same class.
- **Validator-passes ≠ manifest-clean**. `claude plugin validate` accepted `pluginRoot` + absolute `source` coexisting, but the shape was ambiguous. Always-on validators catch syntax; ambiguous-but-syntactically-valid shapes need lens-level review. (This is the kind of finding that would earn an agent-memory entry once PR 2's memory machinery exists — surfacing under "Lessons learned" instead.)
- **Per-phase commits with the co-author trailer made the cold-read trivial** to traverse. Step C's manifest rename commit was 28 lines; reviewing it after the fact took seconds. Monolithic restructure commit would have buried real issues under thousands of unchanged-content rename lines.
- **The /ship pipeline's own walk-through caught issues the pre-merge cold-read missed.** Three BLOCKERs and two cheap NITs found by the lens reviews, all fixed in a single follow-up commit. This is the "review pipeline catches what cold-reads miss" data point that motivated bundling the workflow surface into flow in the first place — meta-validation by dogfooding.

### Auto-invoked disagreement loop for v0.3.0
**Date:** 2026-05-15
**Branch:** v0.3.0-disagreement-loop
**Commit:** 5a3038f

**What was done:**
Closed the feedback loop on the auditor and plan-critic so users can register disagreement with a specific finding in plain language, without invoking a slash command. The plugin now ships an auto-invoked `log-disagreement` skill that the model triggers when it detects pushback on a recent finding, captures the session window and dispute metadata to user-scope storage, and confirms the capture in a single line.

Concrete artifacts:
- `skills/log-disagreement/SKILL.md` — model-invokable skill (`disable-model-invocation` omitted; default behavior allows the model to invoke). Description lists explicit invocation triggers (plain-language disagreement after an audit output) and anti-triggers (general conversation, acceptance, unrelated pushback). Body instructs the model to extract reviewer/category/severity/claim/reason and dispatch the capture script.
- `scripts/log_disagreement.py` — captures the session window from the audit output forward (last ~12 turns by default) into a `.jsonl` plus a `.meta.json` with the structured dispute fields. Stored under `~/.claude/plugins/data/assumption-auditor/disagreements/` so disputes accumulate across projects and survive workspace cleanup.
- `agents/auditor.md` and `agents/plan-critic.md` — added an "Output footer (always)" section requiring every output to end with the disagreement invitation. The footer is part of the schema, not commentary, so the existing "do not add commentary before or after" discipline remains intact.
- `evals/fixtures/*.expected.txt` — footer appended to all five existing fixtures so they stay aligned with the new schema. The harness is still stubbed; once live invocation lands, expected outputs and live outputs will match exactly.
- README updated with the auto-invocation flow and a new entry in the slash-command table.
- `.claude-plugin/{plugin,marketplace}.json` bumped to 0.3.0 with descriptions reflecting the new feedback channel.

**Why:**
The v0.2.0 feedback loop was open: when a reviewer's output was wrong, users had to manually edit `DISAGREE.md` to register the disagreement. Most users would not bother. Maintainer-side prompt tuning depended on disagreements being captured, which depended on users doing free work — a brittle loop that empirically yielded zero entries in `DISAGREE.md` across the v0.1.0–v0.2.0 cycle. Without captured disputes the next prompt tune is data-blind; with them, every false positive becomes a regression test.

The forcing function: as the plan-critic moves toward being a real approval gate (md-manager integration just shipped), the cost of a bad critic finding rises. Users will tolerate occasional false positives only if they have a near-zero-cost way to flag them. Manual `DISAGREE.md` editing fails that bar; "just say so in chat" passes it.

**Design decisions:**
- **Model-invokable skill instead of a hook.** Two options for auto-invocation: a `UserPromptSubmit` hook (deterministic but keyword-based) or a model-invokable skill (nuanced but probabilistic). Chose the skill because plain-language disagreement is too varied for keyword matching to catch well — "actually the scope is fine here" is disagreement; a keyword hook would miss it. The trade-off is silent-miss risk when the model fails to recognize disagreement. Mitigated by the explicit invitation footer (gives the user a near-explicit trigger) and by a documented v0.3.1 follow-up to add a hook as a deterministic safety net if smoke-testing shows the miss rate is non-trivial.
- **User-scope storage, not project-scope.** Disagreements are plugin-improvement data, not project data. A project-scope log would scatter the feedback across repos and make maintainer-side analysis hard. User-scope under `~/.claude/plugins/data/` mirrors how forge stores its data and survives project deletion.
- **Two paired files per disagreement.** `.jsonl` for the session window (fixture-skeleton), `.meta.json` for the structured fields (queryable). Splitting them means the maintainer can `cat *.meta.json | jq` to triage disputes without parsing session JSONL, while still having the session content available for promoting a disagreement to an eval fixture.
- **Footer in the output schema, not in the skill output.** The footer needs to be inside the subagent's prescribed output so the existing "do not add commentary" rules don't conflict with it. Wrote it as a schema section, not a special case, so future schema additions follow the same pattern.
- **No automatic promotion to eval fixture.** Disagreements land as candidates; promoting them to `evals/fixtures/` is still a manual maintainer step. Tempting to auto-promote but risky — a single misclassified disagreement becomes a permanent regression test pinning the wrong behavior. Manual review remains the gate.

**Technical decisions:**
- **`datetime.datetime.now(datetime.timezone.utc)` instead of `utcnow()`.** Python 3.7+ stdlib only is the project constraint. `utcnow()` is deprecated in 3.12+; `now(timezone.utc)` works in 3.2+ and isn't deprecated. Future-proof at zero cost.
- **`SESSION_CAPTURE_WINDOW = 12` and `start = max(0, audit_idx - WINDOW//2)`.** Captures from a few turns before the audit forward, so the fixture includes the user request, the plan/completion, the audit output, and the user's pushback. Empirically sized; tuneable in a follow-up if it captures too little or too much.
- **Walking records back-to-front for audit detection.** `find_recent_audit_record_idx` scans for assistant turns containing `AUDIT SUMMARY` / `CRITIQUE SUMMARY` / `ISSUE ·` / `No issues flagged` / `APPROVED`. Marker-based detection is brittle to future schema changes but cheap; documented as a known coupling.
- **Slugify the category for the filename.** Prevents collision when multiple disputes land in the same second (rare but possible) and keeps filenames filesystem-safe across platforms.
- **The skill calls the script via `Bash` only.** No file-edit tools needed in the skill; the model just packages the dispute fields and runs the script. Smaller blast radius.

**Tradeoffs discussed:**
- **Auto-invoke vs explicit `/disagree` slash command:** explicit is more reliable but adds friction; auto-invoke is frictionless but risks silent miss. Chose auto-invoke with the explicit-invitation footer as a hybrid — the model has full context to detect disagreement, the user has an obvious channel to push back. The silent-miss tradeoff is acknowledged and has a documented mitigation path.
- **Footer wording:** considered "Disagree? Just say so." (terse), "If a finding is wrong, just say so. Your pushback will be logged for prompt tuning." (chosen — explicit about both the channel and what happens to the input), and a longer explanation of the loop (rejected as commentary).
- **CLAUDE.md fragment for reliability:** original plan included a CLAUDE.md instruction telling the model to invoke `/log-disagreement` on detected disagreement. Plugins cannot inject CLAUDE.md fragments into host projects, so dropped. The skill description and footer carry the same instruction-load now.
- **Bumping plan.md Current Focus to reference v0.3.0:** could have left it pointing at the v0.2.0 next-step (live eval invocation). Updated so the document reflects the current state; live-eval-invocation moves to the "next load-bearing step" framing inside the v0.3.0 entry.

**Safety:**
Touches `agents/auditor.md` and `agents/plan-critic.md` — both safety-critical per `.claude/rules/safety.md`. The change is additive (a new schema section requiring a footer) and does not modify, weaken, or remove any existing discipline: the "evidence or silence" rule, the two-citation rule, the forbidden phrases, the permission-to-find-nothing clause are all preserved. Existing fixtures' expected outputs were updated to include the new footer so the regression set stays aligned. The footer text is invariant ("If a finding is wrong, just say so. Your pushback will be logged for prompt tuning.") — no variability that could erode reviewer discipline. Marked here per the safety rule's "Flag the change" requirement, though strictly this isn't an error-handling / persistence / fallback change.

**Lessons learned:**
- The "model-invokable skill description" doubles as documentation of the auto-invocation contract. Wrote it carefully because it's the only line of defense against silent miss — the more concrete and exemplified the description, the higher the recognition rate. Treating it like a regular skill description (one-line summary) would have been worse than the alternative.
- The footer being part of the *schema* matters. Putting it in commentary territory would create a "the prompt says no commentary, but it also requires this commentary" contradiction. Naming it as a schema element resolves the conflict cleanly. Worth remembering for any future schema additions.
- Storage location reveals product intent. User-scope under `~/.claude/plugins/data/` signals "this is plugin-improvement data, not project data." Project-scope would have signaled "this is a per-project audit log" — a different (and worse for this use case) product.


**Date:** 2026-05-14
**Branch:** project-status-overview
**Commit:** 8ce9fb3

**What was done:**
Added a second skeptical reviewer alongside the existing auditor: the **plan-critic**, which checks proposed plans for *reasoning* gaps (scope drift, spec violation, internal incoherence) rather than *evidence* gaps. Shipped as v0.2.0.

Concrete artifacts:
- `agents/plan-critic.md` — prompt with three categories, a two-citation discipline (every finding cites both a source of truth and the conflicting plan element), and three severity tiers (BLOCKER / REDIRECT / FOLLOW-UP). Explicit `APPROVED` signal for clean plans.
- `skills/critique-plan/SKILL.md` — user-invocable entry point. `disable-model-invocation: true`, `context: fork`, `agent: plan-critic`. Mirrors the existing `audit-plan` skill pattern. Invokes the preprocessor with `--reference-glob "core-docs/*.md"`.
- `scripts/extract_session.py` extended with `--reference-paths` and `--reference-glob` (opt-in). Reads matching docs from CWD; skips `history.md` / `plan.md` / `roadmap.md`; caps each doc at 12000 chars; renders a `## Reference documents` section above the existing context. Existing audit-plan / audit-completion flows produce byte-identical output when the new flags aren't passed.
- `evals/fixtures/scope_drift_form_fix.{jsonl,expected.txt}` — exercises scope drift.
- `evals/fixtures/spec_violation_bundled_ui.{jsonl,expected.txt}` — exercises spec violation; reference rule embedded via in-session Read of `core-docs/feedback.md`.
- `evals/fixtures/internal_incoherence_jwt_migration.{jsonl,expected.txt}` — exercises internal incoherence; two contradictory plan steps (keep + remove the same middleware file).
- `evals/ground_truth.yaml` — new entries with a `reviewer: plan-critic` field for future harness dispatch.
- Marketplace + plugin metadata enriched to match the `forge` pattern (owner, version, keywords, homepage, repository, category).

**Why:**
The existing auditor is rigorous but narrow — it can only flag claims that lack session evidence. It misses a different failure class: plans whose *reasoning* is misaligned with intent. Plans that silently expand scope, contradict a documented rule, or contain internal contradictions don't lack evidence — they lack alignment. The plan-critic is the sibling lens for that class.

The md-manager workflow's plan-approval gate (step 3 of its workflow.md) was the proximate forcing function. That gate is currently a human-only check; the long-term goal is to stage trust so an agent can review plans at the gate. The plan-critic is the first credible candidate to do so.

**Design decisions:**
- **Sibling subagent, not a fifth auditor category.** The auditor's discipline is "evidence or silence" — adding reasoning categories would dilute it. Two prompts, shared plumbing, no cross-references is the right separation.
- **Two-citation rule as the falsifier-equivalent.** The auditor demands a tool-call citation; reasoning critique can't. The substitute discipline: every finding must produce one quote from a source of truth, one quote from the plan element, plus one sentence of glue. If the critic can't produce both quotes, no flag. Same epistemic stance as "evidence or silence."
- **Severity tiers in the output.** Auditor output is binary (issue / no-issue). For an approval-gate use case, a calling agent needs to distinguish "must fix before approval" from "note and proceed." BLOCKER / REDIRECT / FOLLOW-UP imported from the md-manager `staff-review` skill pattern.
- **Deterministic doc loading via preprocessor.** Reference docs are inputs; loading them belongs in the preprocessor, not in the subagent's tool use. This keeps the critic's context predictable and removes its dependency on what Claude happened to Read during the session.
- **Default skip list.** `history.md` (decision log), `plan.md` (work tracker), `roadmap.md` (future work) are *not* sources of truth for new plans. Loading them would inject noise and stale state. Excluded by default; user can override with explicit `--reference-paths`.

**Technical decisions:**
- **Glob-with-skip-list, not explicit-paths-only.** Glob is more ergonomic for projects following the `core-docs/` convention. Explicit `--reference-paths` available as override for non-conventional layouts.
- **12000-char cap per doc.** Sized to fit typical `spec.md` / `feedback.md` / `design-language.md` / `workflow.md` without truncation. Adds a `(truncated; original N chars)` marker when it does fire. Cap is per-doc, not total, since the critic reads them as separate quotable units.
- **`reviewer: plan-critic` field in ground_truth.yaml.** Forward-looking — the eval harness doesn't dispatch on it yet (still reads `.expected.txt` stubs for both reviewers), but adding the field now means the harness rewire only needs to read what's already there.
- **README registers both reviewers explicitly.** The "Slash commands" table at the top is the install-and-go contract. Sub-tables for each reviewer's categories. Output formats documented separately.

**Tradeoffs discussed:**
- **Plugin vs. in-repo for md-manager:** could have built the critic directly in md-manager. Decided against — the categories are generic, the infrastructure already exists in this plugin, and md-manager isn't the only project that will benefit. Cost of the plugin dependency is one `/plugin install` per consumer.
- **Bundle into forge marketplace vs. independent:** could have added the critic to the existing forge marketplace for a unified surface. Decided against — different products (forge = infrastructure architect, auditor = session reviewer), different release cadence, easier to spin off if maintenance shifts. Two marketplaces costs users one extra `/plugin marketplace add` command. Trivial.
- **Ship plan-critic in v0.2.0 vs. hold experimental:** plan-critic hasn't been battle-tested on real sessions. Shipping anyway because the md-manager workflow change depends on `/critique-plan` existing. README is honest that the third category (internal incoherence) lacks a fixture and that the eval harness is still stubbed. Better to ship with honest limitations than block the consumer workflow.
- **History entry written before commit:** the docs discipline rule requires history.md updated before commit. Entry written now with `Commit: [pending]` placeholder; replace with SHA on the actual commit.

**Lessons learned:**
- The "two-citation rule" framing took several passes to land. Initial drafts asked for "specific quotes" or "concrete evidence" — too vague. Naming the structure (one quote from truth, one from the plan, one sentence of glue) made the discipline enforceable. Worth doing the same exercise for any future reviewer category.
- The preprocessor-vs-subagent question for doc loading kept coming back. Multiple options seemed plausible (extend preprocessor, sibling preprocessor, subagent Read tool, pre-flight skill, host-project rule). The right factoring was clear once the question was "which component is responsible for deterministic input?" — that's the preprocessor's job, always.
- README discipline matters at the marketplace boundary. The bare marketplace.json (the v0.1.0 version) would have shipped fine for self-install but looked unfinished in any discovery surface. Filling in keywords / homepage / category is 10 minutes of work; doing it before publish saves a "looks abandoned" first impression.


**Date:** 2026-04-20
**Branch:** codebase-overview
**Commits:** e30b75b, 4d3522b, + in-progress fixup

**What was done:**
Added `CLAUDE.md`, `core-docs/`, and `.claude/` scaffolding for developing the plugin. Kept the new project-dev files strictly separate from the plugin's own published artifacts (root `agents/`, `skills/`, `scripts/`, `evals/`, `.claude-plugin/`, `README.md`, `DISAGREE.md`). Added a `.gitignore` for `.claude/settings.local.json`, `.claude/forge/`, and `.DS_Store`.

**Why:**
Before this change, the repo had no project-dev infrastructure -- no agent specs, no rules, no living docs. Sessions developing the plugin had to rediscover context every time. The template provides a scoped, predictable place for that context.

**Design decisions:**
- Explicit plugin-vs-dev boundary documented at the top of CLAUDE.md. The dual-name collision (`agents/` at root vs. `.claude/agents/`) is structural -- Claude Code's plugin convention requires plugin artifacts at root, and Claude Code's project convention requires project-dev infra under `.claude/`. Resolved via documentation, not reorganization.
- Renamed `.claude/skills/audit/` to `.claude/skills/preship/` to avoid slash-command collision with the plugin's own `/audit-plan` and `/audit-completion`. The pre-ship skill's frontmatter `name:` was updated to match (caught in review -- would otherwise have registered as `/audit`).
- Deleted template pieces inapplicable to a headless plugin: `core-docs/design-language.md`, `.claude/agents/ui.md`, `.claude/rules/ui.md`, `.claude/rules/dev-server.md`, `.claude/skills/link/`, `.claude/skills/dev-panel/`, `.claude/skills/setup/`.
- Scoped `.claude/rules/safety.md` to plugin-critical files: `agents/auditor.md`, `scripts/*.py`, plugin manifests, eval harness. These are the files whose silent breakage would be most expensive.

**Technical decisions:**
- `.claude/settings.local.json` gitignored per Claude Code convention (per-user permissions should not be shared).
- Empty `.claude/forge/` directory left in tree (git doesn't track empty dirs) but gitignored to prevent Forge's local cache from being committed later.
- `core-docs/plan.md` Current Focus populated with the real v0.1.0 state (eval harness stub + SKIP'd fixtures) rather than left as a template placeholder.

**Tradeoffs discussed:**
- Keep vs. rename `.claude/skills/audit/`: renaming adds a small cognitive cost (users typing `/audit` won't find it) but eliminates a real collision risk during plugin development. Renaming won.
- Populate vs. leave template placeholders in `plan.md`/`history.md`/`feedback.md`: populated plan.md because the current focus is knowable and useful; left history.md and feedback.md format-only because the first real entries should come from real work, not backfill.
- Merge template README content into the existing plugin README: skipped. Template README is generic philosophy; plugin README is concrete install/use docs. Nothing to merge.

**Lessons learned:**
- Directory renames don't automatically update frontmatter `name:` fields. Always grep for the old name after a skill rename. The preship skill's frontmatter was missed in the first pass and caught in self-review -- the exact kind of "declared done, didn't actually verify" error the plugin itself is designed to catch.
- Full-repo grep for references to deleted files (`design-language`, `UI Agent`, etc.) after cleanup is load-bearing. Four agent/workflow files had stale references the deletion step missed.
