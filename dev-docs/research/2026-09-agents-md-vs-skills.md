# AGENTS.md vs skill-shaped packaging — what Vercel measured, what anyone else measured, and what it means for flow

**Date:** 2026-09-03
**Status:** research / direction-setting. **Spike — no plugin artifacts changed (`plugins/flow/**` untouched).** Deliverable is the finding + a recommendation. §7 routes items to `roadmap.md`; nothing in §6 is approved scope. **Experiments E1–E3 were approved by the human and executed 2026-09-03 — results in §5; they changed the recommendation.** **Point-in-time:** the Vercel post is dated 2026-01-27 and models have shipped since; re-check §1's figure before citing it in 2027.
**Question researched:** flow ships 22 skills and 10 agents; its entire delivery mechanism is skill-shaped. Vercel published an eval saying a passive AGENTS.md beats skills. Is flow's architecture wrong?
**Short answer:** No — and the headline that prompted the question does not survive reading the post's own evidence. The real finding underneath it is about *loading mechanism*, it has since been measured at ~200× Vercel's published run count by someone else, and it points the other way for flow's shape.
**But the experiments the question triggered found something bigger than the question:** flow's four path-activated rule-skills **have not loaded for any consumer since Phase 00 shipped** (§5.1), and `exploration`'s globs miss three of the four consumer repos (§5.3). Packaging needs no change; loading does. See §6.
**Companion docs:** `2026-09-design-md-investigation.md` (the trigger; §2.3 there is the claim this doc tests), `service-agnostic-2026-07.md` (AGENTS.md as a *portability* standard), `anthropic-canon-alignment-2026-08.md` (attention budget → roadmap item AB), `ai-workflow-landscape-2026-07.md` (competitor frameworks).

**Provenance.** Every primary source below was fetched live from this workspace on 2026-09-03 and quoted from the fetched bytes. The Vercel results figure was downloaded and read as an image, not inferred from the surrounding prose. Repo facts were measured with `tools/harness_audit/harness_audit.py --surfaces` and `git grep` at HEAD (`b4b4257`). Claims resting on a search summary rather than fetched primary text say so inline. `anthropic.com` / `platform.claude.com` / `code.claude.com` are reachable from here (the stale egress caveat is being corrected separately), so all Anthropic material below is fetched first-party text.

---

## 0. What was already known, and what is new

Mandatory delta statement.

| Already in flow's corpus | Where | Treatment here |
|---|---|---|
| AGENTS.md as a *portability* standard — governance, inertness, no spec, Claude Code doesn't read it | `service-agnostic-2026-07.md` §3.1–3.3 | Not re-explained. This doc asks a different question: AGENTS.md vs skills as a **loading mechanism**. |
| Vercel's eval exists; 56% invocation; skill scored at baseline; scope limit = framework APIs not design | `2026-09-design-md-investigation.md` §2.3 | **Extended, and partly corrected.** That doc took the reported table at face value — correctly, for its purpose. This doc reads the post's own results figure and finds the figure and the tables disagree. |
| Attention budget / context rot; flow's harness weight is unaudited | `anthropic-canon-alignment-2026-08.md` §3 → roadmap **AB** | Not re-explained. §3.4 resolves the apparent conflict between AB and FB-0085/Phase 00, and §4.5 hands AB one measured correction to its own inventory. |
| Anthropic skill-authoring + eval-driven-development page | `2026-09-design-md-investigation.md` §2.2 | Not re-explained. §2.4 adds only what that doc doesn't cover: Anthropic's **allocation** guidance (which mechanism for which content) and the fact that none of it is measured. |

**Genuinely new here:**

1. **Vercel's published results figure contradicts Vercel's published results tables**, in the same post, under the caption presenting it as the result. n = 11 tasks, one run each — and in the figure the skill arm *beats* baseline (§1.2). This is the single most decision-relevant fact in the doc and nobody in flow's corpus had looked at the image.
2. **The winning arm was a `CLAUDE.md`**, not an AGENTS.md — confirmed in the figure's column header and in the shipped codemod source (§1.3).
3. **A much larger measured result exists and runs the other way**: SkillsBench (arXiv, 87 tasks × 18 model–harness configs × 3 trials = 9,396 trajectories) measures curated skills at **+16.6 pp** over a no-skills baseline, with per-harness invocation rates spanning **46.4%–99.2%** (§2.1). Nothing in flow's corpus cites it.
4. **Nobody has replicated Vercel's actual comparison.** SkillsBench has no passive-context arm; Vercel's own open-source harness has no skill arm (§2.2). The comparison exists in exactly one place, at n=11.
5. **A mechanism taxonomy grounded in fetched Claude Code docs** that dissolves the FB-0085-vs-AB "tension" the brief names: they are not in conflict, because `paths:` activation is a third loading mode that is neither of the two things being compared (§3).
6. **Flow's always-loaded metadata is 18,053 chars — 2.25× the entire payload of Vercel's winning configuration — and carries no guidance** (§4.4). That is a real cost finding, arrived at from the opposite direction to the headline.
7. **A measured correction to AB Step 1's own surface inventory**: `harness_audit.py` counts an 85,176-char file as always-loaded that nothing loads (§4.5) — a live bug in merged code (#136), independently confirmed by E1's hook log.
8. **Three experiments actually run** (§5), two of which returned defects: `paths:` frontmatter on a `SKILL.md` does not activate the skill at any scope (E1, measured three ways with positive controls); `exploration`'s globs match zero files in 3 of 4 consumer repos (E3); `log-disagreement`'s capture rate is not measurable from this workspace and is reported as inconclusive rather than estimated (E2).

---

## 1. What Vercel actually measured

Source: [`AGENTS.md outperforms skills in our agent evals`](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals), Jude Gao, 2026-01-27. Full page text and both content images fetched.

### 1.1 The reported result

The task domain is stated clearly and is narrow: Next.js 16 APIs *"that aren't in current model training data"* — `connection()`, `'use cache'`, `cacheLife()`/`cacheTag()`, `forbidden()`/`unauthorized()`, `proxy.ts`, async `cookies()`/`headers()`, `after()`/`updateTag()`/`refresh()`. Verbatim on the suite: *"We hardened the eval suite by removing test leakage, resolving contradictions, and shifting to behavior-based assertions… Every configuration was judged against the same tests, with retries to rule out model variance."*

The reported tables:

| Configuration | Pass rate | vs baseline | Build | Lint | Test |
|---|---|---|---|---|---|
| Baseline (no docs) | 53% | — | 84% | 95% | 63% |
| Skill (default behavior) | 53% | +0 pp | 84% | 89% | **58%** |
| Skill with explicit instructions | 79% | +26 pp | 95% | 100% | 84% |
| AGENTS.md docs index (8 KB) | 100% | +47 pp | 100% | 100% | 100% |

And the diagnosis: *"In 56% of eval cases, the skill was never invoked. The agent had access to the documentation but didn't use it."*

**What is not stated anywhere in the post:** the number of eval cases, the number of retries, which model(s), which harness, how "pass rate" is computed from Build/Lint/Test, or the skill's `name`/`description`. Every one of those is load-bearing for the conclusion.

### 1.2 The post's own results figure contradicts the tables

The post presents one image under *"We ran the hardened eval suite across all four configurations"*, captioned *"Eval results across all four configurations. AGENTS.md (third column) achieved 100% across Build, Lint, and Test."* That image ([direct link](https://assets.vercel.com/image/upload/contentful/image/e5382hct74si/5klujg5rHUkECCKEGbllHN/b6cf879ce5a9aa4b88e1c275e460e32f/CleanShot_2026-01-21_at_11.19.58_2x.png), downloaded and read here) is four side-by-side terminal panes. It shows:

- **11 eval tasks**, named: `agent-000-app-router-migration-simple`, `agent-021`…`agent-030`.
- **`run-1` only** — one run per task per arm; no visible retries.
- Each pane's own `Overall (B/L/T)` line:

| Column header in the figure | Overall (B/L/T) | As percentages |
|---|---|---|
| Baseline | 9/11/9 | 82% / 100% / 82% |
| SKILL | **10/11/10** | **91% / 100% / 91%** |
| **Claude.md** | 11/11/11 | 100% / 100% / 100% |
| SKILL w/ Nudge | 11/11/10 | 100% / 100% / 91% |

Three things follow, and they matter in descending order:

1. **In the post's own figure, the plain skill arm beats baseline on every axis** (10/11 vs 9/11 build, 10/11 vs 9/11 test). The tables say it tied on pass rate and lost on tests (58% vs 63%). The prior spike quoted that 58-vs-63 as the sharpest edge of the finding — *"an unused skill in the environment may introduce noise or distraction."* The figure the post published as its result does not show that. **The post never reconciles the two.**
2. **n = 11, single run.** Counting tasks where all three of Build/Lint/Test pass: baseline fails something on 3 of 11 (`agent-000` test, `agent-022` build+test, `agent-029` build) = **8/11 = 73%**, not the 53% in the table. The figure and the tables cannot both describe the same run. Whichever run the tables describe, **the only sample size Vercel published anywhere is 11**, and the gaps in the figure are 1–2 tasks wide.
3. This is independently corroborated. A commenter on the [Hacker News thread](https://news.ycombinator.com/item?id=46809708) read the same screenshots as *"29/33 baseline, 31/33 skills, 32/33 skills + use skill prompt, 33/33 agent.md"* — which is exactly the B+L+T sums of the four panes above (9+11+9=29, 10+11+10=31, 11+11+11=33, 11+11+10=32). Two independent readings of the image agree. The reply on that thread states the consequence plainly: *"29/33 vs 33/33 is the kind of gap that could easily be noise with that sample size."*

For scale: **SkillsBench runs 9,396 scored trajectories** (§2.1). Vercel's published figure shows 44.

### 1.3 The winning artifact is a CLAUDE.md, and the comparison is not like-for-like

The figure's third column is headed **`Claude.md`**, not AGENTS.md. This is not a screenshot mislabel: the shipped codemod ([`vercel/next.js#88961`](https://github.com/vercel/next.js/pull/88961), `packages/next-codemod/lib/agents-md.ts`, read via `gh api`) names its functions `generateClaudeMdIndex` and `injectIntoClaudeMd`, and defaults with `const targetFile = outputFile || 'CLAUDE.md'`. The harness pane header reads `Eval | Claude Code`. **For a Claude Code shop, the winning artifact in this experiment is literally a CLAUDE.md** — which is worth stating precisely because `service-agnostic-2026-07.md` §3.1 already established that Claude Code does not read AGENTS.md at all.

Beyond the name, the two arms differ in **at least three ways simultaneously**, only one of which is the loading mechanism:

- **Loading.** Skill = model decides to invoke. CLAUDE.md = present every turn. This is the variable the post claims to isolate.
- **Content shape.** The winning arm is an **index**, not the docs: *"Not the full documentation, just an index that tells the agent where to find specific doc files."* The agent still retrieves — it reads files out of `.next-docs/`. So the contrast is not passive-vs-active retrieval; it is **who decides to start retrieving.** The skill arm's content shape is never shown.
- **An extra instruction only one arm received.** The winning arm carries `IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any Next.js tasks.` — confirmed present in the codemod source. Nothing says the skill arm had it. The post's own §"Explicit instructions helped" demonstrates that instruction wording alone moves this suite by 26 pp. An uncontrolled instruction difference in a 26-pp-sensitive suite is a confound, not a footnote.

The post's own §"Explicit instructions" section is in fact a **fourth** uncontrolled variable and the authors say so: same skill, same docs, *"You MUST invoke the skill"* → *"Misses project context"*; *"Explore project first, then invoke skill"* → *"Better results."* Their conclusion — *"If small wording tweaks produce large behavioral swings, the approach feels brittle"* — is a fair reading. It is also a reading that applies to the winning arm, whose own single instruction line was never ablated.

### 1.4 What "56% never invoked" can and cannot tell us

The brief asks the right question: a 56% invocation rate could mean the skill was bad, the description was bad, or models under-invoke generally. **The post cannot distinguish these, because it never publishes the skill.** Neither does the open-source harness (§2.2). The skill's `name`/`description` — which both OpenAI and Anthropic identify as *the* determinant of triggering (§2.3, §2.4) — are unavailable, so the most likely single-cause explanation is also the one that cannot be checked.

We do, however, now have a distribution to place 56% against. SkillsBench measures task-specific skill invocation rate across 18 model–harness configurations at n=261 trials each: **46.4% to 99.2%** (§2.1). 56% sits in the bottom quartile of a range that spans more than 2×. That is consistent with *"this skill, in this harness"* and does not support *"skills under-invoke"* as a general law.

### 1.5 What the post actually concludes — and it is narrower than its title

Verbatim, and worth quoting in full because it is routinely dropped when the post is cited:

> "Skills aren't useless. The AGENTS.md approach provides broad, horizontal improvements to how agents work with Next.js across all tasks. **Skills work better for vertical, action-specific workflows that users explicitly trigger**, like 'upgrade my Next.js version,' 'migrate to the App Router,' or applying framework best practices. The two approaches complement each other.
>
> That said, **for general framework knowledge**, passive context currently outperforms on-demand retrieval."

Both scoping clauses are load-bearing. The claim is about *general framework knowledge* reaching an agent that must decide to go looking for it. It explicitly carves out *vertical, action-specific workflows that users explicitly trigger* — which is a fair one-line description of `/flow:ship`, `/flow:doctor`, `/flow:land`, `/flow:contribute`.

**Verdict on Q1.** The headline result is real in the sense that Vercel ran it and reported it honestly, and the mechanism they identify (removing the invocation decision) is sound and independently corroborated. But as evidence it is **weak**: n=11 single-run in the only figure published, a figure that contradicts the tables it accompanies, at least three uncontrolled variables between arms, and the losing artifact withheld. It is a useful hypothesis generator. It is not a result that should move an architecture.

---

## 2. What else has been published — measured vs asserted

### 2.1 MEASURED, and much larger: SkillsBench

[`SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks`](https://arxiv.org/abs/2602.12670), arXiv 2602.12670v4 (v1 2026-02-13, v4 2026-06-14), 77 authors, plus the [1.1 release note](https://www.skillsbench.ai/blogs/skillsbench-1-1) (2026-06-16). Abstract fetched from arXiv; full PDF downloaded and read (`pdftotext`, 3,098 lines) for the tables below.

Design: **87 tasks across 8 domains, paired no-Skills vs curated-Skills conditions, 18 model–harness configurations (Claude Code, Codex, Gemini CLI, OpenHands), 3 trials per task — 9,396 scored trajectories.**

- **Headline: curated skills raise mean pass rate from 33.9% to 50.5% (+16.6 pp, 25.5% normalized gain), with per-configuration gains from +4.1 to +25.7 pp.** Every one of the 18 configurations improved.
- **Invocation rate is measured per configuration and varies enormously** (Table 14, n=261 trials each): Codex+GPT-5.5 **99.2%**, OpenHands+GPT-5.5 92.0%, … **Claude Code + Opus 4.7 68.2%**, … OpenHands+Gemini 3.1 Flash Lite **46.4%**.
- **Finding 4, verbatim: *"Skill discovery is usually not the bottleneck."*** And the caution alongside it: *"High Skill Invocation Rate does not guarantee high resolution, so the remaining failures often occur after task-Skill access."*
- **Finding 3, verbatim: *"Harness choice materially changes how the same model uses Skills."*** With the discussion's sharper version: *"Some harnesses reliably retrieve and use Skills, while others acknowledge Skills content but proceed without invoking it. This motivates evaluating Skills under multiple harnesses rather than treating 'with Skills' as a single condition."*
- **Finding 6 — the one flow should feel:** *"Compact, focused Skills outperform exhaustive ones."* Measured: tasks paired with **1 skill gain +18.0 pp, 2–3 skills +19.0 pp, ≥4 skills only +10.1 pp** — *"suggesting excess content creates overhead or conflicting guidance."* And on length: *"compact and standard-length Skills (+19.0 and +21.5 pp) outperform detailed (+14.5 pp) and comprehensive documentation (+0.7 pp); focused procedural guidance beats exhaustive prose."*
- **Bad skills actively hurt.** Self-generated skills (agent authors packs with Anthropic's `skill-creator`, then solves with only those) land **below** the no-skills baseline on all three dedicated-harness configurations: −8.1 pp (Claude Code + Opus 4.7), −11.3 pp (Codex), −11.5 pp (Gemini CLI), while curated skills add +18.2 to +24.8 pp on the same configurations. Attributed to *"generated packs the solver never discovers, creator-side authoring that displaces solver work, and confidently wrong pack content."*
- **Skills cost tokens rather than saving them, in this harness.** Table 15, Claude Code + Opus 4.7: mean 4,332 K tokens/trial no-Skills → **6,425 K with skills**; $5.21 → $6.74. (Marked *"session-JSONL-derived and approximate."* Direction is consistent across most rows but not all — OpenHands + Claude Opus 4.7 goes the other way, 1,771 K → 1,094 K.)
- Stated caveats: 13 of 87 tasks show negative skill lift in aggregate; some failed runs still recorded invocations; one leaderboard submission lacks a no-Skills ablation.

**This is the strongest measured evidence in the whole survey, and its direction is: well-curated skills help substantially; badly-curated skills hurt; invocation is not usually the limiting factor; and the harness matters more than the packaging debate implies.**

### 2.2 The comparison nobody has replicated — reported as a result

**SkillsBench has no passive-context arm.** Grepped the full PDF: zero occurrences of `AGENTS.md`, zero of `CLAUDE.md`, zero of "passive context" or "always-on". It measures skills-vs-nothing, not skills-vs-AGENTS.md.

**Vercel's own open-source harness has no skill arm.** [`vercel/next-evals-oss`](https://github.com/vercel/next-evals-oss) (pushed 2026-08-31, read via `gh api`) publishes ~55 experiment files, every one of them a `<model>.ts` / `<model>--agents-md.ts` **pair**. There is no skills condition and no skill definition anywhere in the tree. The current fixture set (`vercel/next.js@canary:evals/evals`) is **28 evals**, and [nextjs.org/evals](https://nextjs.org/evals) now reports *"Success Rate is pass@4: an eval passes if any of four attempts passes"* — i.e. Vercel's own live methodology has since moved to 4 attempts, while the January post's figure shows `run-1`.

So: **the AGENTS.md-vs-skills comparison exists in exactly one published experiment, at n=11, and the losing arm is not reproducible from any public artifact.** That is worth saying plainly before anyone treats it as settled.

### 2.3 ASSERTED, not measured: OpenAI

[`Evaluating agent skills`](https://developers.openai.com/blog/eval-skills), Dominik Kundel & Gabriel Chua — the post Vercel links as its *"known limitation"* citation. It contains **no numbers, no tasks, no models, no results**. It is prescriptive methodology, and on this question it says two useful things:

> "The name and description matter more than they might seem. They're the primary signals Codex uses to decide **whether** to invoke the skill at all, and **when** to inject the rest of SKILL.md into the agent's context. **If these are vague or overloaded, the skill won't trigger reliably.**"

> "Because skill invocation depends so much on the `name` and `description` in SKILL.md, the first thing to check is whether the skill triggers when you expect it to… This is where you surface the misses: cases where the skill doesn't trigger at all, **triggers too eagerly**, or runs but deviates from the intended steps."

Its concrete prescription is a `should_trigger` column in the eval CSV — **trigger reliability tested separately from guidance quality**, with deliberate `should_trigger=false` rows to catch over-eager matching. That is the right discipline and neither Vercel nor flow does it. Note it is the *inverse* framing of Vercel's finding: OpenAI treats a low trigger rate as a **defect in the author's description**, not a property of skills.

### 2.4 ASSERTED, not measured: Anthropic — but it does answer the allocation question

Three first-party pages, all fetched. **None contains a single measured number about skills vs always-on context.** What they do contain is an explicit allocation rule, which is the first-party answer to the mechanism question:

From [Extend Claude Code](https://code.claude.com/docs/en/features-overview), the "CLAUDE.md vs Rules vs Skills" comparison, verbatim:

| Aspect | CLAUDE.md | `.claude/rules/` | Skill |
|---|---|---|---|
| **Loads** | Every session | Every session, or when matching files are opened | On demand, when invoked or relevant |
| **Scope** | Whole project | Can be scoped to file paths | Task-specific |
| **Best for** | Core conventions and build commands | Language-specific or directory-specific guidelines | Reference material, repeatable workflows |

And the honest admission on the failure mode Vercel measured:

> "**How Claude chooses skills:** Claude matches your task against skill descriptions to decide which are relevant. **If descriptions are vague or overlap, Claude may load the wrong skill or miss one that would help.**"

> "Every feature you add consumes some of Claude's context. Too much can fill up your context window, **but it can also add noise that makes Claude less effective; skills may not trigger correctly**, or Claude may lose track of your conventions."

From [Skills](https://code.claude.com/docs/en/skills): *"Create a skill when… a section of CLAUDE.md has grown into a procedure rather than a fact. Unlike CLAUDE.md content, a skill's body loads only when it's used, so long reference material costs almost nothing until you need it."* And the context-lifecycle table:

| Frontmatter | You can invoke | Claude can invoke | When loaded into context |
|---|---|---|---|
| (default) | Yes | Yes | **Description always in context**, full skill loads when invoked |
| `disable-model-invocation: true` | Yes | No | **Description not in context**, full skill loads when you invoke |
| `user-invocable: false` | No | Yes | **Description always in context**, full skill loads when invoked |

From [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices): *"The context window is a public good."* · *"Keep SKILL.md body under 500 lines for optimal performance."* · *"The 'name' and 'description' in your Skill's metadata are particularly critical."* · and the caveat the prior spike already surfaced: *"There is not currently a built-in way to run these evaluations. Users can create their own evaluation system."*

**Anthropic's guidance and Vercel's finding do not conflict.** Anthropic already says: facts every session → CLAUDE.md; path-scoped guidelines → rules; reference material and repeatable workflows → skills. Vercel put general framework knowledge in a skill, which Anthropic's own table routes to CLAUDE.md, and found it did better in CLAUDE.md.

### 2.5 Nothing published — reported as a result

- **Cursor, GitHub Copilot** — both have rules conventions, neither has published any measured comparison of rules vs skills, or any invocation-rate measurement. *(Search-summary basis; not exhaustive.)*
- **The AGENTS.md project itself** — `service-agnostic-2026-07.md` §3.1 already established there is no spec, no validator, and near-zero maintainer activity. There is correspondingly no eval.
- **No independent replication of Vercel's comparison exists.** The discussion of it is entirely practitioner commentary (§2.6).

### 2.6 Practitioner reports — anecdote, but consistent and worth logging

The [HN thread](https://news.ycombinator.com/item?id=46809708) is the largest public scrutiny of the post. Two themes recur, both relevant:

- **Invocation is unreliable in practice, at a rate people notice.** *"The agents I'm using (Gemini CLI, Opencode, Claude) all seem to have trouble activating skills on their own unless explicitly prompted"* (`sally_glance`). *"About 5-10% of the time, it will not use the skill… I miss deterministic bugs"* (`joebates`). Counter-report: *"I have a couple skills invoked with specific commands… and they have never failed to activate"* (`JamesSwift`), and *"Sounds like they've been using skills incorrectly… You need to make sure your skill descriptions are well defined"* (`smcleod`).
- **The comparison is widely read as category-confused.** *"This is exactly how I thought skills work. The short descriptions are given to the model up-front and then it can request the full documentation as it wants. With skills this is called progressive disclosure. Maybe they used more effective short descriptions in the AGENTS.md than they did in their skills?"* (`EnPissant`). *"Their AGENTS.md approach tells the AI where to find instructions for performing a task. That's a Skill"* (`thorum`).

Anecdote, flagged as such. The signal worth keeping is that the *skeptical* reading — bad description, not bad mechanism — was the most common one among people running these systems daily, and it is the same reading OpenAI's post prescribes testing for.

---

## 3. The mechanism question: when does passive beat invocable?

This is the useful part, and it is answerable from fetched documentation plus the two measured studies.

### 3.1 There are not two loading mechanisms in Claude Code. There are four.

The whole "AGENTS.md vs skills" framing collapses two independent axes — **who decides** and **when it is paid for** — into one. Separated, using the frontmatter reference and memory docs fetched above:

| Mode | Trigger | Deterministic? | Always-loaded cost | Invoked cost |
|---|---|---|---|---|
| **A. CLAUDE.md / unscoped rule** | Session start | Yes | Full body, every request | — |
| **B. Path-scoped rule / skill with `paths:`** | *"Path-scoped rules trigger when Claude **reads** files matching the pattern, not on every tool use"* | **Yes, on file read** | Description only | Full body |
| **C. Model-invoked skill** (default, or `user-invocable: false`) | Claude matches task ↔ description | **No** | Description (≤1,536 chars incl. `when_to_use`) | Full body |
| **D. User-invoked skill** (`disable-model-invocation: true`) | Human types `/name` | Yes (human decides) | **Zero** | Full body |

Mode B is the one the framing has no room for, and it is exactly what flow's four rule-skills use. Verbatim from the frontmatter reference: `paths` = *"Glob patterns that limit when this skill is activated… When set, Claude loads the skill automatically only when working with files matching the patterns. Uses the same format as path-specific rules."*

**Vercel compared A against C.** Their result is a statement about A-vs-C, in one harness, on one content type, at n=11. It says nothing about B or D, and both of those are where most of flow lives.

### 3.2 When passive (A) wins

Three conditions, all present in Vercel's setup:

1. **The content is needed on most turns.** General framework knowledge for a Next.js task qualifies. A deployment checklist does not.
2. **The agent would have to *know it doesn't know* to go get it.** This is the real mechanism, and it is stronger than "the agent forgot to invoke." Outdated training data is invisible from the inside: the model has a confident wrong answer and no signal to retrieve. Vercel's own fix is not the file, it is the sentence in it — `Prefer retrieval-led reasoning over pre-training-led reasoning`. Stripe converges on the same move from a different direction: [`docs.stripe.com/llms.txt`](https://docs.stripe.com/llms.txt)'s first line is *"When installing Stripe packages, always check the npm registry for the latest version rather than relying on memorized version numbers."* (Noted in the prior spike; not re-derived.)
3. **It fits the budget.** 8 KB. Anthropic's guidance is *"target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."*

### 3.3 When invocable (C/D) wins

1. **Side effects.** Anthropic, verbatim: *"Use `disable-model-invocation: true` for skills with side effects. This saves context and ensures only you trigger them."* And: *"You don't want Claude deciding to deploy because your code looks ready."* This is not a performance argument — it is a control argument, and no eval result can override it.
2. **Bodies too large for the budget.** Flow's Class B total is **478,587 chars ≈ 120 K tokens** across 22 skills (`harness_audit.py --surfaces`). `ship/SKILL.md` alone is 137,729 chars ≈ 34 K tokens. Making that passive is not a design choice, it is arithmetic.
3. **Mutually exclusive procedures.** SkillsBench Finding 6: ≥4 skills on one task gains only +10.1 pp vs +19.0 pp for 2–3. Merging `/flow:ship`, `/flow:ship-spike`, `/flow:land` and `/flow:post-merge` into one always-loaded document would put four contradictory procedures in front of the model on every turn.
4. **The user knows when.** Vercel's own carve-out: *"vertical, action-specific workflows that users explicitly trigger."*

### 3.4 The FB-0085 / AB "tension" — it is not one

The brief flags Phase 00 (rules → path-activated skills, because rules were never loading) and roadmap AB (auditing always-loaded token cost) as pulling in opposite directions. Reading the Phase 00 history entry and the AB roadmap entry against the docs above, **they do not conflict**, for a reason worth writing down:

- **Phase 00 was not a passive-vs-invocable decision at all.** The bug was that `plugins/flow/rules/*.md` *"is not a Claude Code plugin component — no loader call site joins a plugin root"* (FB-0085, verified against the decompiled installed CLI at v2.1.237). The files were in a directory nothing reads. The fix moved them to a directory something reads. Loading went from **0%** to *something*; no trade was made against token cost, because the prior cost was zero and so was the prior benefit.
- **The mode Phase 00 landed on is B, not A.** `paths:` activation is *conditional* always-on: full body only when a matching file is read. That is precisely the shape AB wants — Anthropic's own framing: *"Rules with `paths` frontmatter only load when Claude works with matching files, saving context."*
- **AB's target is A and the description aggregate**, not B. AB Step 1's inventory explicitly separates always-loaded from invoked-per-use and says the two *"must never be summed together."*

So the correct statement is: Phase 00 moved four surfaces from *never loading* into *mode B*; AB audits *mode A* and the always-loaded description aggregate. They meet at exactly one place — §4.4's finding that flow's description aggregate is large — and there they agree.

**One real gap Phase 00 left — and E1 found it is far worse than this section originally suspected.** The draft's concern was timing: a mode-B surface loads on first matching Read, not at session start, so a turn that plans before reading anything would miss it. That concern is real but moot. **E1 measured the actual behavior: mode B does not work for skills at all.** `paths:` fires for `.claude/rules/*.md` and not for `SKILL.md`, at either project or plugin scope, so flow's four rule-skills have never loaded for any consumer. See §5.1 — that finding supersedes this paragraph and is the top recommendation in §6a.

---

## 4. Relevance to flow, per surface

Counts measured at HEAD: **22 skills, 10 agents** (the brief's 21/9 is one release stale; `review-brief` and `lens-experience` shipped in #137).

### 4.1 Flow's four surface classes are not one thing

| Class | Members | Loading mode (§3.1) | Does the Vercel finding apply? |
|---|---|---|---|
| **1. User-invoked commands** (12) | `ship`, `ship-spike`, `doctor`, `land`, `post-merge`, `contribute`, `workflow-help`, `staff-review`, `review-brief`, `audit-plan`, `critique-plan`, `audit-completion` | C (except `post-merge`, which is D) | **No.** This is the case Vercel's conclusion explicitly carves out: *"vertical, action-specific workflows that users explicitly trigger."* The trigger is typed by the human (or, for `/flow:ship` alone, gated on an explicit readiness predicate) — not left to ambient relevance-matching, which is the thing Vercel measured failing. |
| **2. Skill-invoked gates** (6, of which `land` is also class 1) | `verify-build` (7 call sites), `audit-skips` (2), `land` (2), `security-review`, `accessibility-review`, `audit-coverage` | C, but reached via `Skill()` from another skill's body | **No.** The call is written into `/flow:ship`'s body as an instruction, not left to ambient relevance-matching. This is the same "remove the decision point" move Vercel recommends — flow already made it. |
| **3. Path-activated rules** (4) | `general`, `plan-discipline`, `documentation`, `exploration` | **B** | **Not directly.** These are already the deterministic-loading shape. The relevant question here is coverage, not invocation (§3.4). |
| **4. Genuinely model-invoked** (1) | `log-disagreement` (fires on detecting user disagreement with a finding) | C, with no human or programmatic trigger | **Yes — this one, and only this one.** |

Distinct membership: 12 + 5 (class 2 minus `land`) + 4 + 1 = 22. Class 1 is labelled *user-invoked* rather than *human-only* because 11 of the 12 are model-invocable in principle — but each one names its human trigger phrases in its own description (*"ship it"*, *"is flow set up right?"*, *"land #N"*), and `/flow:ship`'s auto-invocation is gated on an explicit readiness predicate rather than on ambient relevance-matching. The distinction that matters for Vercel's finding is whether a *decision point* exists that can silently fail, and for these it does not: the trigger is either typed or predicated.

**So the answer to Q4 is: of 22 skills, the AGENTS.md finding lands squarely on one.** Flow's architecture is overwhelmingly modes B and D-in-spirit (human- or caller-triggered), which is the regime both Vercel and Anthropic route *to* skills.

### 4.2 `log-disagreement` is the one genuine exposure, and it is untested

`log-disagreement` is the only flow skill whose firing depends entirely on the model noticing an ambient condition. Its description is unusually good by OpenAI/Anthropic criteria — 976 chars, three numbered preconditions, six literal trigger phrasings (*"no, finding 2 is wrong"*, *"false positive"*, *"that's not a scope drift"*), and an explicit negative case (*"Do NOT invoke for general project questions, acceptance…"*). That is closer to OpenAI's `should_trigger`/`should_trigger=false` discipline than anything else in the repo.

**Its trigger rate is still not measured** — E2 (§5.2) verified the write path works and found 1 captured record against 41 harvest-queue lessons in the one drain on record, but could not establish a denominator and is reported inconclusive. The whole feedback pipeline — `~/.claude/plugins/data/flow/disagreements/` → `/flow:contribute` → prompt tuning — sits downstream of it. If it fires at Claude Code's SkillsBench rate (68.2%), roughly a third of disagreements are silently lost, and the loss is invisible: an unfired capture leaves no artifact. This is the FB-0010 silent-skip class applied to a skill trigger. §5b names the cheap test.

### 4.3 The four rule-skills' coverage is also unmeasured

**Superseded by E1 (§5.1) — now measured, and the answer is that they never load.** What follows was the pre-experiment framing; it is kept because its second question survives. Same FB-0085 discipline: `paths:` activation is documented, but flow had never watched it fire. `general` (`**/*`), `plan-discipline` (`**/plan.md`), `documentation` (5 doc names), `exploration` (`src|app|lib|packages/**`). Two open questions with real consequences: does a plan-writing turn that Reads nothing load `general`? and does `exploration`'s hardcoded source-root list match a Swift/iOS consumer's layout (`health-tracker`, `ripe`, `music-app` are all Swift — none has `src/`, `app/`, `lib/`, or `packages/`)? The second was checked (E3, §5.3): **0 matching files in health-tracker, ripe, and music-app; 0 in flow's own repo.** The first is moot — nothing activates.

### 4.4 The real cost finding — and it is the opposite of the headline

Measured with `tools/harness_audit/harness_audit.py --surfaces`, and independently priced by `claude plugin details flow@flow`, which reports **~4,645 always-on tokens** for v1.36.0 — up from **~4,122** at v1.29.0, **+13% across seven releases**. The char-based estimate below (~4,500) and the first-party token count agree closely, so the growth curve is real and cheap to re-measure:

| Surface | Chars | ≈ tokens |
|---|---|---|
| 22 plugin skill `description:` fields | 14,249 | ~3,600 |
| 10 plugin agent `description:` fields | 3,804 | ~950 |
| **Always-loaded metadata a consumer pays every session** | **18,053** | **~4,645 (measured — see below)** |
| Vercel's entire winning AGENTS.md payload, for comparison | 8,192 | ~2,000 |

**Flow's always-loaded surface is 2.25× Vercel's winning configuration and contains no guidance — only "here is what exists."** Only one skill (`post-merge`) sets `disable-model-invocation: true`, so 21 of 22 descriptions are in context on every request of every session in every consumer project.

Two individual entries are worth naming: `ship` at 1,453 chars and `doctor` at 1,229. `ship`'s description embeds the entire auto-invocation predicate — every spec-walk checkbox, the BLOCKER condition, the confidence-verdict condition, FB-0011's four escalation triggers. That is a *procedure* living in an *index*, paid on every turn of every session whether or not anyone ships anything. It is also within 6% of the 1,536-char truncation limit, which means it is one edit away from silently losing its tail.

This is a live, measured instance of exactly what AB exists to find. It arrives via the AGENTS.md question but is independent of how that question resolves.

### 4.5 A correction AB Step 1 should take

`tools/harness_audit/harness_audit.py:157` hardcodes `plugins/flow/docs/workflow.md` (85,176 chars, 619 lines) into the always-loaded list. **Nothing loads it.** It is not a `CLAUDE.md`, it is not under `.claude/rules/`, and flow's own `CLAUDE.md` contains no `@`-import of it (`grep -n '^@\|@plugins' CLAUDE.md` → empty). For consumers it is a plugin doc file, read on demand by `/flow:workflow-help` and by skills that cite it. It is a Class B surface counted as Class A, and it is **64% of the reported 132,788-char Class A total** — so AB's headline always-loaded number is roughly 3× too high.

Reported here rather than fixed: this is a spike, and the fix belongs to whoever picks up AB Step 1b (it may also want a `[WARN]`-on-unverified-classification, since a hardcoded list is exactly the FB-0010 fan-out shape).

---

## 5. E1–E3: run, with results

Approved and executed 2026-09-03, after the §6 recommendation was drafted. All three were read-only or scratch-only; the repo carries no artifact from any of them. **Two returned hard results; one is inconclusive and says so.**

### 5.1 E1 — flow's four path-activated rule-skills do not activate. At all.

**Method.** Three fresh, authenticated Claude Code sessions (v2.1.257) started in this workspace via `conductor session create`, each instrumented three independent ways:

1. **The `InstructionsLoaded` hook** (`load_reason` ∈ `session_start` / `path_glob_match` / …), registered via a gitignored `.claude/settings.local.json`, appending raw JSON to a scratch log.
2. **Transcript content search** for each rule-skill's distinctive first heading.
3. **Agent self-report** — the probe was asked to state, as JSON, which `flow:*` skills it could see and whether specific rule documents were in its context.

**Preconditions verified before trusting anything.** The plugin cached in this workspace was **v1.29.0 — a pre-Phase-00 build with a dead `rules/` directory and zero `paths:` skills**, so the first in-session attempt was thrown out as confounded. It was uninstalled and reinstalled from the working tree to **v1.36.0**, and probe 2 confirmed the plugin was live by listing **21 `flow:*` skills**, including all four rule-skills by name.

**Positive controls fired correctly in every session**, which is what makes the negative trustworthy:

| Surface | Mechanism | Result |
|---|---|---|
| `CLAUDE.md` | unscoped | ✅ `session_start` |
| `.claude/rules/general.md` | unscoped rule | ✅ `session_start` (agent also self-reported it in context) |
| `.claude/rules/documentation.md` | rule, `paths: dev-docs/**` | ✅ `path_glob_match` on Reading `dev-docs/plan.md` |
| `.claude/rules/safety.md` | rule, `paths:` incl. `plugins/flow/scripts/log_disagreement.py` | ✅ `path_glob_match` on Reading exactly that file |

**And the result:**

| Surface | Glob | Probe Read a matching file? | Activated? |
|---|---|---|---|
| `flow:general` | `**/*` | yes (every file) | ❌ **no** |
| `flow:plan-discipline` | `**/plan.md` | yes — `dev-docs/plan.md` | ❌ **no** |
| `flow:documentation` | `**/history.md`, `**/plan.md`, … | yes — both | ❌ **no** |
| `flow:exploration` | `src|app|lib|packages/**` | n/a — flow's repo has none (see 5.3) | not testable here |

Zero hook events. Zero transcript occurrences. Probe 2 self-reported `plan_discipline_rule_in_context: false` and `documentation_rule_in_context: false` immediately after Reading `dev-docs/plan.md`.

**Probe 3 isolates the cause.** A throwaway **project-scoped** skill (`.claude/skills/e1-probe-rule/SKILL.md`, `user-invocable: false`, `paths: ["**/roadmap.md"]`, containing a unique marker string) also **did not activate** when the probe Read `dev-docs/roadmap.md` — while `.claude/rules/documentation.md` fired on the same Read, in the same session. So this is **not** a plugin-scope problem and not a glob-syntax problem.

> **Finding: `paths:` frontmatter on a `SKILL.md` does not activate the skill. Path-scoped activation works for `.claude/rules/*.md` and does not work for skills — at either project or plugin scope — in Claude Code v2.1.257.**
>
> `paths` is a documented SKILL.md frontmatter field (*"Glob patterns that limit when this skill is activated… Claude loads the skill automatically only when working with files matching the patterns"*). Observed behavior does not match that description. Whether the field is inert on skills, or activates through a channel all three instruments miss, is not distinguishable from outside — but flow cannot rely on it either way.

**Why this matters more than its size.** This is the **third** instance of the same class in flow, and the second one Phase 00 itself created:

1. `plugins/flow/rules/` — not a plugin component; never loaded (FB-0085, fixed by Phase 00).
2. `hooks/default-hooks.json` — matched no auto-discovery filename (FB-0085, deliberately left opt-in).
3. **The Phase 00 fix itself** — the four rules were moved from a directory nothing reads into a frontmatter field nothing acts on. **The bug it fixed is still open.** Phase 00's own verification checked that the skills were *registered* (`claude plugin details` showed 17→21) — which is true, and is not the same as *activating*.

That is exactly FB-0085's own rule turned back on its own fix: *"a claim that a mechanism works is only as good as the runtime check behind it."* Registration was checked. Activation was not.

**Cost of the finding:** three Sonnet probe sessions, each a single Read-and-reply turn.

**Two incidental confirmations, both first-party:**
- `claude plugin details flow@flow` reports **~4,645 always-on tokens** for the current build (22 skills, 10 agents) and ~4,122 for v1.29.0 (17 + 9). §4.4's independent char-based estimate was ~4,500 — close enough that §4.4's figure can now be replaced with a measured one. Per-skill: `ship` ~370 always-on / **~34k on-invoke**; `doctor` ~310 / ~10.7k; `verify-build` ~230 / ~13.7k.
- Probe 2 listed **21** visible `flow:*` skills, not 22 — `post-merge` was absent, exactly as `disable-model-invocation: true` predicts (*"Description not in context"*). The context-cost table in §2.4 is confirmed behaviorally.

### 5.2 E2 — inconclusive. The write path works; the rate is not measurable from here.

**What was established:**
- **The capture mechanism works end-to-end.** `log_disagreement.py` invoked directly against a scratch `HOME` wrote a well-formed record to `~/.claude/plugins/data/flow/disagreements/`. If the skill fires, the record persists. Any loss is at invocation, not persistence.
- **Volume, from the one drain on record.** history.md's `#119` entry: `/flow:contribute` drained *"41 queued lessons + **1** disagreement record."* The harvest queue (written programmatically by `harvest_lesson.py` at ship Step 4c) out-produced the model-invoked capture path 41 : 1 over the same window.
- **`plugins/flow/DISAGREE.md` has never had an entry.** `git log --follow` shows two commits, both scaffolding. The manual path is unused.

**What could not be established, and why — stated plainly rather than estimated:**
- **There is no denominator.** `log-disagreement`'s trigger is narrow by design: a dispute of a *specific finding* from `/flow:audit-plan`, `/flow:audit-completion`, or `/flow:critique-plan` — not general pushback, not disagreement with `/simplify` or the lenses. The repo record contains no clean count of events meeting that bar. One candidate — *"of the 5 disagreements, self-disproof was correct on 4"* (history.md, dynamic-workflows spike) — turns out to be **method-A-vs-method-B disagreement inside an experiment, not user disputes**, and was discarded rather than used. 1 record over an unknown and plausibly small denominator is not a rate.
- **The real store is machine-local** (`~/.claude/plugins/data/flow/disagreements/`, per `log_disagreement.py:33`) and lives on the user's Mac. This is a fresh cloud workspace; the directory does not exist here. **No local-command tool is exposed in this session** (searched twice), so the user's Mac is not reachable from here — contrary to what the context update suggested might be available. If that tool is available in another seat, E2 becomes a two-command job: count files in the store, count qualifying disputes in recent transcripts.

**One thing E1 does settle for E2:** `log-disagreement` carries **no `paths:` field**, so E1's defect does not touch it. Probe 2 confirmed its description is in context. Its invocation path is intact; only its *rate* is unknown.

### 5.3 E3 — `exploration`'s globs miss three of the four consumer repos

Measured with `gh api …/git/trees/HEAD?recursive=1` against each repo at HEAD. Globs: `src/**`, `app/**`, `lib/**`, `packages/**`.

| Repo | Total files | Files matching | Actual source roots |
|---|---|---|---|
| `byamron/health-tracker` | 515 | **0** | `App/`, `HealthTrackerCore/`, `Widget/` |
| `byamron/ripe` | 98 | **0** | `ripe/`, `design/`, `tools/` |
| `byamron/music-app` | 92 | **0** | `MusicApp/` |
| `byamron/portfolio` | 237 | 56 | `src/` ✅ (also `apps/`, which `app/**` does *not* match) |
| `by-dev-tools/flow` (own repo) | — | **0** | `plugins/`, `tools/`, `dev-docs/` |

Three of four consumer repos are Swift/iOS and have no lowercase `src`/`app`/`lib`/`packages` directory at all. `health-tracker`'s `App/` is capitalized and does not match `app/**`. **flow's own repo cannot trigger its own exploration rule either.**

**Interaction with E1, which matters for the fix:** E1 makes E3 moot *today* — `exploration` would not fire in `portfolio` either, because no skill's `paths:` fires. But E3 says the fix is **two-part**: even after the activation mechanism is corrected, `exploration` still reaches exactly one repo in the fleet. Fixing activation alone would leave it dead in 75% of consumers. This is the already-queued `roadmap.md:912` "config-driven `paths:`" item, now with evidence attached.

---

## 6. Recommendation

**Headline: do not repackage anything — the packaging question is answered. But flow has a live loading bug that the packaging debate was obscuring, and it should be fixed on its own merits.**

The bar for a repackaging proposal, per FB-0088, is deliberately very high: ~91 queued roadmap items and a recent review that found real overbuilding. Nothing in §1–§4 clears it. The evidence that *would* have cleared it — a large, controlled, replicated passive-vs-invocable comparison — does not exist (§2.2), and the one experiment that ran it published a figure contradicting its own tables at n=11.

What §5 changed: the three "unmeasured loading assumptions" flagged in the draft are now measured, and **two of the three were wrong in flow's favor being tested**. That is the value the spike actually produced.

### 6a. DO — fix the E1 defect (this is now the top item, and it is not a packaging change)

**S0. Restore path-activation for the four rule-skills.** They have not loaded for any consumer since Phase 00 shipped (2026-08-27, v1.33.0). Three options, in ascending cost; **pick after reproducing E1 independently**, because option (a) depends on an upstream behavior this spike could only observe from outside:

- **(a) Confirm-and-report upstream.** If `paths:` on `SKILL.md` is meant to work, this is a Claude Code bug and worth a minimal repro issue. Cheap, but flow should not *wait* on it.
- **(b) Ship the four as `.claude/rules/*.md` via the template directory** instead of as plugin skills. This is the mechanism E1 proved works — `paths:`-scoped rules fired correctly in all three probes. Cost: they'd arrive via `bootstrap.sh` scaffolding rather than the plugin install, reintroducing exactly the copy-then-drift problem Phase 00's decision 00d avoided. Real tradeoff, not obviously worth it.
- **(c) Accept model-invocation.** Drop `paths:`, keep `user-invocable: false`, and write descriptions that earn the trigger (OpenAI's and Anthropic's shared advice, §2.3/§2.4). Cheapest, but converts four deterministic surfaces into four ambient ones — the exact regime Vercel measured failing, and the one flow deliberately moved away from.

> ⚠️ **The most likely wrong turn: do not close this by deleting the `paths:` fields.**
> That is the FB-0077 shape named in `.claude/rules/general.md` § Consistency discipline — a prohibition satisfiable by deletion. Removing `paths:` makes every symptom disappear and leaves the four rules loading exactly as often as they do now: never. Whatever option lands **must pair the change with a positive assertion that the four rules actually reach context**, not merely that nothing is misconfigured.

**And `/flow:doctor` Check 3.2 (`skills/doctor/SKILL.md:659`) must be upgraded with it.** It currently verifies *registration* — it greps `claude plugin details` for the four names — while its own prose asserts they *"auto-load on path matches when `flow@flow` is enabled."* E1 measured the second half false. The check passes today over a feature that does not work.

The irony is worth recording, because it is the strongest argument for the paired assertion: **Check 3.2 was written specifically to prevent this class.** Its own comment reads *"FB-0085: this exact gap is why the 4 rules never loaded for any consumer despite always being on disk."* It asks the loader instead of disk — a real improvement — and then stops one step short, because *registered* and *activates* are different questions and only the first one is cheap to ask. A check that verifies the fix's mechanism rather than the fix's effect inherits the bug it was built to catch.

**Deletion criterion (FB-0088):** if the four rule-skills' content is ever folded into `CLAUDE.md`/`AGENTS.md` scaffolding, the activation check goes with them.

### 6b. DO NOT DO — with the reason and the flip condition

Unchanged by §5; `paths:` failing makes the case against passive-conversion *weaker*, not stronger, because the fix is a loading fix, not a packaging one.

| Not doing | Why | What would flip it |
|---|---|---|
| **Convert flow's guidance into a passive AGENTS.md/CLAUDE.md payload** | 478,587 chars of Class B body. Arithmetic, not preference. SkillsBench Finding 6 measures ≥4 concurrent skills at +10.1 pp vs +19.0 pp for 2–3 — collapsing 22 procedures into one always-on document is the measured *bad* direction. | A controlled replication with n in the hundreds showing a passive-vs-invocable gap on **procedural** content (all published evidence is on **factual** content). |
| **Convert user-invoked commands (`ship`, `doctor`, `land`) to passive** | Anthropic, verbatim: *"You don't want Claude deciding to deploy because your code looks ready."* Flow's thesis is two load-bearing human gates. | Never. A product principle, not an empirical question. |
| **Blanket `disable-model-invocation: true` to reclaim the ~4,645 tokens** | Breaks composition — `/flow:doctor` Check 1.4 (FB-0074) exists because *"the call is rejected at runtime and the composition degrades to its fallback on every run, silently."* 6 skills are `Skill()` targets; `ship` has a designed auto-invocation predicate; `log-disagreement` is model-invoked by design. | Nothing blanket. A per-skill case for a specific non-composed skill is fine — see 6c. |
| **A trigger-tuning program over all 22 descriptions** | 21 of 22 have a human or programmatic trigger; their descriptions are `/`-menu copy, not trigger surface. | E2's rate, if it is ever measured and comes back low — then tune `log-disagreement` alone. |
| **Build a skill-invocation eval harness** | Anthropic: *"There is not currently a built-in way to run these evaluations."* SkillsBench cost 9,396 trajectories. Flow's fleet is four repos. | E2 finds a real miss rate **and** a second flow surface depends on ambient invocation. Today exactly one does. |

### 6c. DO — the two small fixes, both now better-evidenced

**S1. Hoist `/flow:ship`'s auto-invocation predicate out of `description:` into the body.** Measured: the predicate is **1,004 of the description's 1,495 chars**, and `claude plugin details` prices `ship` at ~370 always-on tokens — the largest single always-on component in the plugin. It is a procedure needed *while shipping*, paid on every turn of every session, sitting 5.4% below the 1,536-char truncation cliff. Keep trigger phrases + a one-line pointer.
⚠️ Pair the removal with the positive assertion that the predicate is present in the body — do not satisfy this by deleting it.
**Still human-gated:** it edits `ship`'s frontmatter, which is gate machinery. Not taken here.

**S2. Fix `exploration`'s globs (E3), together with whatever S0 lands.** Not worth a PR on its own — it is dead either way until S0 fixes activation. Cheapest shape is the already-queued config-driven `paths:` item (`roadmap.md:912`), or an added `**/*.swift` / capitalized-root pattern.

### 6d. Worth considering later, not now

**Adopt OpenAI's `should_trigger` discipline for `log-disagreement` only** — prompts that should fire it plus deliberate near-misses that should not. It is flow's only surface where trigger reliability is load-bearing, and `plugins/flow/evals/` already exists as its home. **Do not size this until E2 has a denominator.**

---

## 7. Routing to `roadmap.md`

Proposed; nothing added by this doc.

**§ Now — new top item**
- **S0 — the four rule-skills have not loaded for any consumer since v1.33.0 (E1, §5.1).** A shipped, advertised feature that does not fire, plus a `/flow:doctor` check that is green over it. Third instance of the FB-0085 class and the second created by Phase 00 itself. Needs an option decision (a/b/c in §6a) at a human gate. Deletion criterion stated.

**§ Next**
- **S2 — `exploration`'s globs reach 1 of 4 consumer repos (E3, §5.3).** Bundle with S0; merges with the queued `roadmap.md:912` config-driven `paths:` item, which now has evidence.

**§ Exploration**
- **E2 — `log-disagreement` capture rate, unresolved (§5.2).** *Surfaces when:* a seat with access to the user's machine is available, or the next `/flow:contribute` drain runs. *Question:* how many qualifying disputes produced a record? *Bar:* needs a denominator; 1-record-vs-41-lessons is suggestive, not a rate. *Do not tune the description before measuring.*
- **S1 — hoist `/flow:ship`'s auto-invocation predicate out of `description:`.** *Surfaces when:* `ship/SKILL.md` frontmatter is next edited. Gate machinery; human-gated.

**⚠️ Feeds roadmap item AB — a live bug in already-merged code (#136), recorded here so it is not lost**
- **`tools/harness_audit/harness_audit.py:157` hardcodes `plugins/flow/docs/workflow.md` (85,176 chars, 619 lines) into the always-loaded surface list. Nothing loads that file.** It is not a `CLAUDE.md`, not under `.claude/rules/`, and flow's own `CLAUDE.md` contains no `@`-import of it (`grep -n '^@\|@plugins' CLAUDE.md` → empty). E1's hook log independently confirms it: across three fresh sessions, the only `session_start` loads were `CLAUDE.md` and `.claude/rules/general.md` — `workflow.md` never appeared. It is a Class B surface counted as Class A, and it is **64% of the reported 132,788-char Class A total, so AB Step 1's headline always-loaded figure is ~3× too high.** Deliberately **not fixed here** (spike; and it belongs with AB Step 1b's other deferred cadence fixes). **AB Step 3 must not inherit this misclassification** when it builds the real token-count report.
- **AB gains a measured baseline:** `claude plugin details` reports **~4,645 always-on tokens** for v1.36.0 (was ~4,122 at v1.29.0 — **+13% across 7 releases**). That is a real growth curve, first-party, and cheaper to re-run than anything AB Step 3 proposes to build. **AB Step 3 may already be mostly solved by a shipped CLI command** — check before building.
- **AB gains an external calibration point:** SkillsBench Finding 6 measures the cost of surface count directly (≥4 skills: +10.1 pp vs 2–3 skills: +19.0 pp) — closer to an empirical answer to *"does this surface earn its token cost?"* than the qualitative context-rot framing AB currently rests on.

**Corrections to a prior doc (not fixed here — this is a spike)**
- `2026-09-design-md-investigation.md` §2.3 and §7 state the skill arm scored *"at baseline"* and *"slightly below baseline on tests (58% vs 63%)"*, sourced from Vercel's tables. Vercel's own results figure shows the skill arm **above** baseline on all three axes (§1.2). The prior doc quoted its source accurately; the source is internally inconsistent. Add a pointer here rather than restating the number.

---

## 8. Bottom line

- **The headline does not survive contact with the post's own evidence.** The figure Vercel publishes as its result shows 11 tasks, one run each, and a skill arm that *beats* baseline — while the tables in the same post say it tied and lost on tests. Both readings of that image (mine and an independent HN reader's) agree; the post never reconciles them. The winning artifact was a `CLAUDE.md`, and it differed from the losing arm in at least three ways at once.
- **The larger measurement runs the other way.** SkillsBench: 9,396 trajectories, curated skills **+16.6 pp**, invocation **46.4–99.2%** by harness, *"Skill discovery is usually not the bottleneck."* Nobody has replicated Vercel's actual comparison — SkillsBench has no passive arm, Vercel's own OSS harness has no skill arm.
- **Correctly scoped, the finding lands on 1 of flow's 22 skills.** Vercel's own conclusion carves out *"vertical, action-specific workflows that users explicitly trigger"* — 12 of flow's skills verbatim. 6 more are reached programmatically. **Flow's packaging needs no change, and this is now the well-evidenced part of the answer.**
- **But the spike found a live bug worth more than the question that prompted it.** flow's four path-activated rule-skills have not loaded for any consumer since Phase 00 shipped in v1.33.0 (2026-08-27) — four releases, with main now at v1.37.0. Measured three ways, in three fresh sessions, with positive controls firing every time, and isolated to the mechanism (`paths:` on a `SKILL.md`) rather than to scope or glob syntax. **Phase 00 fixed a never-loading feature by moving it to a different never-loading mechanism, and verified registration instead of activation** — the precise failure FB-0085 exists to prevent, recurring inside FB-0085's own fix.
- **And a second one:** `exploration`'s globs match 0 files in three of the four consumer repos, and 0 in flow's own. Fixing activation alone would still leave it dead in 75% of the fleet.
- **The real cost problem is the mirror image of the headline.** Flow's always-loaded metadata is **~4,645 tokens, first-party measured** — 2.25× Vercel's entire winning payload, carrying zero guidance — and it has grown 13% in seven releases. That is roadmap item AB's first concrete finding, plus a correction that AB's own inventory over-counts by ~3×.
- **Recommendation: change no packaging; fix the loading.** The three measurements cost three Sonnet turns and some `gh api` calls, and two of the three returned defects. Flow had three documented loading claims it had never watched fire; now it has watched, and one of them was false.
