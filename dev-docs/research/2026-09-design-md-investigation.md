# Agentic design guidance in public — Vercel's `design.md`, the wider survey, and what flow should (and shouldn't) do

**Date:** 2026-09-03
**Status:** research / direction-setting. **Spike — no plugin artifacts changed by this doc.** Deliverable is the finding + a recommendation; §6 routes items to `roadmap.md`. Nothing here is approved scope.
**Question researched (original):** what is Vercel's `design.md`, and what should flow learn from it?
**Question researched (extended, user direction 2026-09-03):** widen to a survey of how leading AI/product companies build in public on *agentic design quality* — how agents produce high-quality design/craft output, and how that improves from human feedback.
**Companion docs:** `ai-workflow-landscape-2026-07.md` (competitor frameworks, reflection, visual feedback), `anthropic-canon-alignment-2026-08.md` (Anthropic canon), `service-agnostic-2026-07.md` (AGENTS.md / skills / packaging), `dev-docs/handoffs/d1-prototype-first-gate.md` (the prototype-first gate this interacts with).

**Provenance / confidence.** All primary sources below were fetched live from this workspace on 2026-09-03 and quoted from the fetched text, not from memory or from search summaries. The four consumer repos were read via `gh api` at HEAD. Where a claim is a search-result summary rather than fetched primary text, it says so. Two claims are flagged as *my inference*, not vendor-measured.

> **Environment correction to a prior doc.** `anthropic-canon-alignment-2026-08.md` records that `anthropic.com` is *"egress-blocked from the flow CI/dev environment"* and that its quotes are therefore unverified against source. **That is no longer true in this environment:** `www.anthropic.com`, `code.claude.com` and `docs.claude.com` all return `200` here. The Anthropic quotes in §2.2 below are fetched primary text. Worth re-verifying that doc's load-bearing quotes on a future pass — cheap now.

---

## 0. What is already covered, and what is genuinely new

Mandatory delta statement, per the brief.

| Already in flow's research corpus | Where | Treatment here |
|---|---|---|
| Anthropic canon: context engineering, "Building Effective Agents", the attention-budget finding | `anthropic-canon-alignment-2026-08.md` | Not re-explained. §2.2 adds only the *skill-authoring + eval-driven-development* page, which that doc does not cover. |
| gstack / Superpowers / GSD / Spec Kit / Kiro; reflection & self-improvement literature; OpenAI Self-Evolving Agents cookbook; the visual-feedback landscape (Agentation, Tweag) | `ai-workflow-landscape-2026-07.md` §2, §5, §6 | Not re-explained. The OpenAI cookbook **re-confirms** what §5 already recorded (LLM-as-judge + human review + iterative prompt refinement) and adds nothing on the design axis — one line, moving on. |
| AGENTS.md as a *portability standard*: governance, inertness, no spec, Claude Code doesn't read it, `.agents/skills/` convergence | `service-agnostic-2026-07.md` §3.1–3.3 | Not re-explained. §2.3 covers a **different** question that doc never asks: AGENTS.md vs skills as a *loading mechanism*, and Vercel's measured eval on exactly that. |
| Codex / Cursor packaging + hook semantics | `service-agnostic-2026-07.md` §4 | Not touched. |

**Genuinely new in this doc:**

1. **Three Vercel artifacts, not one.** `design.md` is the third of a published trilogy; the *second* (`product-design`, June 2026) is far more relevant to flow because it governs agents working **inside a codebase** — which is what every flow consumer is. Nothing in flow's corpus mentions it. (§1)
2. **A measured Vercel result that cuts against skill-shaped packaging** — and sits in tension with Vercel's own other two posts. (§2.3)
3. **First-hand evidence on whether the four consumer repos' design-language docs are actually working**, including two drift checks with opposite outcomes. (§3)
4. **The flow-level-mechanism vs repo-level-content split, argued from that evidence** rather than from principle. (§4)
5. **Three verified gaps in flow's own `designLanguagePath` plumbing** that nobody has written down. (§3.4)
6. A **"nothing found"** result for several named vendors on this axis. Reported as a result, not omitted. (§2.6)

---

## 1. What Vercel actually does — mechanisms, verified

Vercel has published **three** related pieces. Treating `design.md` alone gives a distorted picture.

| # | Artifact | Date | Governs | Shape |
|---|---|---|---|---|
| A | [`agents-md-outperforms-skills-in-our-agent-evals`](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) | 2026-01-27 | how framework knowledge reaches the agent | eval report |
| B | [`teaching-agents-product-design-at-vercel`](https://vercel.com/blog/teaching-agents-product-design-at-vercel) | 2026-06-25 | agents editing UI **inside Vercel's repos** | skill + linters + review loop |
| C | [`how-our-agents-build-on-brand-pages-with-design-md`](https://vercel.com/blog/how-our-agents-build-on-brand-pages-with-design-md) | 2026-08-31 | agents making one-off pages **outside** their repos | public file + public CSS + eval loop |

### 1.1 The three-part split (artifact C) — confirmed, with one correction

The brief's pre-read was accurate. Verbatim from the post:

> "design.md supplies guidance that shows agents how to frame the reader's job, structure evidence, and choose a composition. A public stylesheet that defines a bounded, documented vocabulary of classes and tokens. An evaluation loop turns repeated human feedback into better guidance and deterministic checks."

**Correction to the pre-read's framing:** `design.md` was not a first attempt. It is a *rewrite* after a failed port. Verbatim:

> "The naive approach we tried first was to simply port product-design into a public prompt… while the prompt described our visual language just fine, every model reading it interpreted that description differently, generating vastly different pages from the same guidance."

And the diagnosis of *why* — this is the load-bearing sentence of the whole post:

> "Inside our codebases, an agent reads product-design surrounded by real components and shipped examples of the things it describes. But a public prompt includes none of that, leaving every model to rebuild our style from just words alone."

**That is the finding flow should care about most.** `design.md`'s elaborate structure is *compensation for the absence of a codebase*. Flow's consumers all have codebases. So the naive read — "flow should ship a design.md convention" — is copying the wrong artifact. Artifact **B** is the right comparison. (§4 argues this.)

### 1.2 The specimen, read directly

Fetched `https://vercel.com/design.md` — 39,519 bytes, `text/markdown`, 396 lines. It is **skill-shaped**: YAML frontmatter with `name: vercel-brand-guidelines` and a 60-word `description` full of trigger nouns. Structure:

1. Brand context (what tone, what the reader is for)
2. **`## Use this priority order`** — a numbered 1–6 conflict-resolution ladder ("When requirements compete, protect them in this order").
3. Host-integration constraints
4. **Four passes:** frame the reader's job → choose the composition → the visual system → **inspect and revise privately**
5. **`## Reject generated-design reflexes`** — 15 named anti-patterns
6. **`## Use the published CSS API`** — ~150 class names and ~60 token names, no CSS
7. Accessibility + responsive

Five mechanisms worth naming, because they are the reusable part:

- **A conflict-resolution ladder.** Artifact B has the identical move (`## Decision Authority`, a 1–6 list). Two independently authored artifacts, same mechanism — that's a deliberate pattern, not an accident. Almost no design doc in our corpus has one.
- **Falsifiable rule phrasing.** Nearly every rule is written so a reviewer can point at a violation: *"A row whose label, value, or annotation changes the plot width is a layout failure."* Not "rows should feel aligned."
- **Named anti-patterns.** Verbatim rationale: design.md *"names the recurring generated-design patterns that we never want to see, allowing agents to recognize and avoid them far more reliably by giving the patterns names."* **[asserted, not measured]** — no ablation isolates naming.
- **A self-review rubric with a loop condition** — 8 ordered checks, then *"Fix the highest-impact systemic defect, render again, and repeat until no known material visual or usability issue remains."*
- **An explicit escape hatch with a prohibition on guessing:** *"If none fits, use semantic HTML plus a page-owned `vbg-custom-*` or `vbg-viz-*` hook; never inspect the CSS for internal selectors, guess a `vbg-*` class, or extrapolate a name from another primitive."*

### 1.3 The bounded stylesheet — verified, and the context math

`https://vercel.com/geist/vercel-brand.css` returns `200 text/css`, **108,893 bytes**, containing **133 unique `.vbg-*` classes** and **114 unique `--vbg-*` custom properties**. Real, public, and exactly as described.

The claim *"the agent never actually reads the stylesheet… none of the code enters the model's context"* is architecturally true: the CSS is `<link>`ed by the rendered page. **Rough context math** *(my calculation, not Vercel's)*: ~109 KB of CSS is roughly 30k tokens that never load, against a 39.5 KB guidance file of roughly 10k tokens. The split buys back about **three times the guidance file's own size**. Not a rounding error.

Nice detail, and directly relevant to §3: the CSS header pins provenance with **SHA-256 hashes of its two upstream Geist sources**. `byamron/ripe` does exactly the same thing for its bundled font binary. Independent convergence on "pin the artifact you depend on."

### 1.4 The evaluation loop — the measured part, stated honestly

Seven frozen scenarios (usage/performance report, renewal proposal, benchmark report, interactive planning page, build-vs-buy brief, security governance brief, presentation deck). A "scenario" freezes prompt + mock inputs + render settings; a "round" regenerates all seven against the current file, on **Claude Opus 4.8 and Codex with GPT-5.5**. Reviewed in a local harness with full-page renders and **blind A/B**, storing prompt, inputs, model config, design.md version, screenshots, and reviewer feedback per run.

**MEASURED results, with their own caveats quoted:**

| Test | Result | Caveat (Vercel's own words) |
|---|---|---|
| Does the file change output at all? (renewal proposal, same model/prompt/data/viewport, with vs without) | Structural change, not just styling: page led with the recommendation, evidence on one grid, peers on one scale | *"Each version generated once, no rerolls."* n=1 |
| Known-failure counts (3 desktop scenarios × 2 = 6 pages, GPT-5.5, first attempt only) | **39 failures with `design.md` vs 91 without — "57% fewer in this test"** | *"The checks can only catch failures we have already seen and written down, so this test says nothing about whether a page is well designed overall. Six pages is also far too small a sample… every one of them, with or without the file, still had at least one failure serious enough to block shipping."* |
| Total build cost | *"well over 200 runs"* | — |

The honest one-line reading of their own measurement, verbatim: **"once we name a failure and encode it, that failure tends to stay gone."** That is a claim about *regression prevention*, not about design quality. It is exactly the claim an eval-fixture discipline makes.

**The routing rule** — the sharpest mechanism in either post:

> "Judgment changes go into design.md as prose, reusable mechanics go into the stylesheet, and anything that we can check mechanically becomes a deterministic check in code. Problems with the harness itself stay in the harness, and when a single model fails in a way the others don't, we keep it out of the rules until it repeats."

And the falsification rule they hold themselves to:

> "we count how often each kind of complaint shows up in similar work over time. Once we encode a fix, that count should start falling. When it does not, something about the fix is wrong."

### 1.5 Artifact B (`product-design`) — the one that actually maps to flow

This is the in-repo system, and it is closer to flow's shape than `design.md` is. Three parts: *"An agent skill… Linters that enforce clear rules automatically… A review loop that gathers evidence from Slack, Figma, and GitHub, then prepares guideline updates for review."*

Layout, verbatim from the post:

```
.agents/skills/product-design/
├── AGENTS.md          # load order, validation, governance
├── SKILL.md           # runtime workflow
├── references/        # product-judgment, interface-quality, resilience,
│                      # surfaces, copy, rules, glossary, patterns,
│                      # coverage-gaps.md
└── exemplars/pr-{name}.md
tooling/scripts/evals/{fixtures.json, rules-checklist.json, <fixture>/{before,after}}
```

Mechanisms in B with no equivalent in flow, or a partial one:

- **`coverage-gaps.md`** — *"lists areas where we do not have a standard yet."* Explicit negative space. Costs one file.
- **`exemplars/pr-{name}.md`** — *"documents decisions worth repeating from shipped pull requests, along with mistakes to avoid."* Flow's `visual-history.html` is the nearest thing; it records *what shipped*, not *the decision and its counterexample*.
- **Stable rule IDs with canonical sources** — `rule/destructive-names-action`, `Source: copy.md > Actionable; verbs.md`.
- **Request modes** — Shape / Implement / Review / Copy / Harden, resolved *"from the user's verb and artifact before acting."* Flow has `mode: spike | tiny | full`, which is a size axis, not an intent axis.
- **A linter-vs-prose decision tree**, quoted verbatim:
  > "Can code identify the failure without rendering? — No: use agent guidance. — Yes: can the rule avoid likely false positives? — No: use agent guidance. — Yes: does the violation have a concrete fix? — Yes: use a linter. — No: use a warning or agent guidance. Needs product or codebase context: use agent guidance. Establishes a new standard or product policy: require a human decision." *And:* "If a rule cannot stay reliable without many exceptions, move it back to agent guidance."
- **Skill Integrity governance**, verbatim: *"Never promote one screenshot, one shipped file, or one reviewer comment into a universal rule by itself."* and *"Keep deterministic checks mechanical. Keep judgment in prose with its evidence and degree of freedom."*
- **Evidence intake with collection separated from judgment:** *"A collector gathers messages, links, and nearby context without proposing rules. A separate judge groups the evidence, verifies sources, and records open questions… Automation ends with the review packet. A human decides."*
- **Eval design**, and this line is the one to steal: *"We score rule correctness separately from similarity to the shipped result. Shipped code can contain a flaw that the agent should improve instead of reproduce."*

**Convergence with flow, stated plainly.** B's operating contract contains *"Never claim visual verification from code alone."* That is `/flow:verify-build`'s founding thesis (the Potemkin-interface / hallucinated-success class), written independently by a different team. B's evidence-intake loop is structurally `/flow:ship` Step 4c harvest → `contribution_store` queue → `/flow:contribute` drain → human-merged PR. Flow's feedback pipeline is not a novel bet; it is the same bet a serious team made and shipped. **[asserted on both sides — neither Vercel nor flow has measured the loop's effect on quality.]**

---

## 2. The wider survey

### 2.1 Vercel's own adoption protocol (the transferable part)

Both posts end with a "build your own" section. C's, condensed but faithful: (1) pick one repeated artifact with a real reader and real inputs — *"Avoid broad goals such as 'make it on-brand'"*; (2) **save the baseline first** — *"You cannot tell whether new context helped without a before"*; (3) start from your last ten corrections and rewrite each as observable — *"That means writing `Let evidence tables use the full available width` instead of `Make the table feel less cramped`, since only one of those can be checked"*; (4) constrain repeatable mechanics into a stylesheet; (5) run one matched blind comparison; (6) encode the correction *"instead of hand-tuning the generated page."* B's step 1 gives a decision-record template with fields `Scope / Decision / Rationale / Evidence / Exceptions / Bad example / Good example / Assumptions / Open decisions`, and the same warning: *"Avoid starting with broad adjectives like clear, polished, or intuitive. Agents need observable decisions."*

This protocol — not any of their file formats — is the genuinely portable thing.

### 2.2 Anthropic — first-party, fetched

[`docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices`](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices). Nothing here is about *design* output specifically; it is about how guidance should be written and validated, which is the mechanism layer. Verbatim, the parts that bear on this spike:

- **Eval-driven development, in order:** *"Create evaluations BEFORE writing extensive documentation… Identify gaps: Run Claude on representative tasks without a Skill… Create evaluations: Build three scenarios… **Establish baseline: Measure Claude's performance without the Skill**… Iterate: Execute evaluations, compare against baseline, and refine."* This is Vercel's ablation protocol, from the model vendor. **[asserted best practice — the page presents no measurement of its own.]**
- **Degrees of freedom** — the doc's framing for how prescriptive to be: high freedom (prose heuristics) when *"Multiple approaches are valid / Decisions depend on context"*; low freedom (exact scripts) when *"Operations are fragile… Consistency is critical."* Vercel's Skill Integrity section uses the same phrase (*"judgment in prose with its evidence and degree of freedom"*). Two independent uses of one concept.
- **A caveat flow should hear:** *"There is not currently a built-in way to run these evaluations. Users can create their own evaluation system."* The tooling burden falls entirely on the author. This is the single strongest cost argument against flow shipping an eval harness for design guidance.
- **Conciseness as a budget claim:** *"The context window is a public good."* Re-confirms `anthropic-canon-alignment-2026-08.md` §3's attention-budget finding — one line, moving on.

### 2.3 The measured result that cuts against skill-shaped packaging — and a conflict inside Vercel's own corpus

Artifact A, [`AGENTS.md outperforms skills in our agent evals`](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) (2026-01-27), hardened eval suite targeting Next.js 16 APIs absent from training data, *"with retries to rule out model variance"*:

| Configuration | Pass rate | vs baseline | Build / Lint / Test |
|---|---|---|---|
| Baseline (no docs) | 53% | — | 84 / 95 / 63 |
| Skill (default behavior) | **53%** | **+0pp** | 84 / 89 / **58** |
| Skill with explicit instructions | 79% | +26pp | 95 / 100 / 84 |
| AGENTS.md docs index (8 KB) | **100%** | **+47pp** | 100 / 100 / 100 |

The diagnosis: *"In 56% of eval cases, the skill was never invoked. The agent had access to the documentation but didn't use it."* And the fragility finding — same skill, same docs, different trigger wording, different outcome: *"You MUST invoke the skill"* → *"Reads docs first, anchors on doc patterns / Misses project context"*; *"Explore project first, then invoke skill"* → *"Better results."* Their theory: *"No decision point… Consistent availability… No ordering issues."*

**Where the sources conflict, and how it resolves.** Five months later Vercel shipped `product-design` **as a skill**. That looks contradictory and mostly isn't: B ships the exact mitigation A found — an always-present AGENTS.md trigger with firm boundaries — and B cites A's number directly (*"In separate Next.js evals, agents failed to invoke an available skill in 56% of cases. Test the trigger separately from the guidance, because failing to load the skill and failing to follow a rule are different problems."*). C sidesteps invocation entirely: a URL the user hands the agent. A's own conclusion allows both: *"Skills work better for vertical, action-specific workflows that users explicitly trigger… for general framework knowledge, passive context currently outperforms on-demand retrieval."*

**The residual tension is real and should not be smoothed over:** A measured that an *unused* skill was slightly *worse than nothing* on tests (58% vs 63%) — *"an unused skill in the environment may introduce noise or distraction"* — and B/C do not address whether that penalty persists once a trigger is forced.

**Scope limit, stated because it decides how much weight this carries:** A measured **framework-API correctness**, not design quality. Extending it to design guidance is **my inference, not a measured result.** The cheap experiment that would settle it for flow is named in §5.

### 2.4 Stripe — verified first-party, adjacent axis

`https://docs.stripe.com/llms.txt` returns `200 text/markdown`, 90,052 bytes: a machine-readable index where every entry points at a `.md` twin of a docs page (`https://docs.stripe.com/testing.md`, `/api.md`, …). Its **first line** is an anti-stale-training-data instruction: *"When installing Stripe packages, always check the npm registry for the latest version rather than relying on memorized version numbers… Never hardcode an old version number from training data."*

That is the same move as Vercel's *"Prefer retrieval-led reasoning over pre-training-led reasoning."* **Two vendors, independently, on "index + retrieve rather than inline, and tell the model not to trust its priors."** One of them measured it (Vercel, 100% vs 53%). This is the most solid cross-vendor convergence in the survey.

It is also **off-axis for this spike**: both are about *factual currency*, not *taste*. Do not import it as a design finding. (`linear.app/llms.txt` also exists, 10 KB, same convention.)

### 2.5 Linear — published, but about a different problem

[`linear.app/developers/aig`](https://linear.app/developers/aig) — Agent Interaction Guidelines: agent identity badging, using existing UI patterns, instant feedback, transparent internal state, honoring disengagement, human accountability. Presented as a *"living document"*, **[asserted — no measurement, no evals, no user studies cited]**.

This is guidance for **designing products that agents act inside**, not for **agents producing design**. Adjacent, genuinely well-written, and **not on this spike's axis**. The [Linear Method](https://linear.app/method) is the same: excellent prose product doctrine, no agent-facing mechanism. **No transferable finding. Dropping it per the brief's "a finding with no named use case is not a finding."**

### 2.6 Nothing found — reported as a result

Searched and came back empty on the design-quality-for-agents axis:

- **Notion, Google (Gemini), GitHub Copilot instructions, Cursor rules** — everything surfaced is MCP plumbing (Figma MCP server, design-token extraction, "connect your tools") or generic prompt guidance. **No published normative design-quality guidance for agents, and no evals on design output, from any of them.** *(Search-summary basis, not exhaustive; a targeted per-vendor sweep could still turn something up.)*
- **Vercel v0 / AI SDK** — no published evals on *design* output found; `design.md` §"Integrate with the caller's project" treats v0 only as a host stack to preserve.
- **Independent practitioners.** Simon Willison's [agentic-engineering-patterns](https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/) and the `smevals` work are eval-infrastructure, already the same ground as `ai-workflow-landscape-2026-07.md` §5. Nothing design-specific. *(Search-summary basis.)*
- **OpenAI** — the Self-Evolving Agents cookbook is already cited in flow's roadmap #3 and **re-confirms** existing coverage (LLM-as-judge + human review + iterative refinement). Nothing new; nothing design-specific.

**The honest headline: on this axis, Vercel is essentially alone in public.** That is worth knowing before flow treats "the industry is converging on design.md" as a premise. It isn't. One team published three careful posts.

---

## 3. Is design language actually working in the four consumer repos?

This is the crux question and it is answerable with evidence, not opinion. Read at HEAD, 2026-09-03.

### 3.1 First: a correction to the brief

**`byamron/portfolio` is not a flow consumer.** It has no `flow.config.json`. Its `.claude/` contains `forge/` (a separate system), `rules/{animation,technical-context}.md`, and three skills. Its `core-docs/` has no `roadmap.md` or `spec.md`. Also, `tokens.md` lives at the **repo root**, not in `core-docs/`. Anything portfolio shows about design docs is evidence about *the author's practice*, not about *flow's mechanism*. That distinction turns out to matter a lot (§3.3).

### 3.2 Four repos, four different shapes — and the corpus already invented Vercel's two best moves

| Repo | Doc | Lines | Values live… | Judgment layer |
|---|---|---|---|---|
| `health-tracker` | `decisions/design-language.md` + a 9-file `workflow/design-system/` | 836 + ~2k | **both** doc and code | §"Color rules", "one serif per screen", `craft/apple-design-awards.md`, `workflow/design-completion-criteria.md` (4 named gates) |
| `ripe` | `core-docs/design-language.md` | 311 | **inline in the doc**, mirrored in `Tokens.swift` | **11 numbered "Axioms (violate = design bug)"** with provenance |
| `music-app` | `core-docs/design-language.md` | 324 | **only in code** — *"Tokens (see `DesignSystem/Palette.swift`, `Typography.swift`, `Motion.swift`)"* | 6 Axioms + **"Anti-patterns (cut on sight)"** |
| `portfolio` | root `tokens.md` + `core-docs/design-language.md` | 162 + 1,044 | **duplicated across two docs and the CSS** | 5 "Core Principles" |

Two things stand out:

**(a) The corpus independently invented Vercel's two strongest moves.** `ripe`'s section heading is literally *"Axioms (violate = design bug)"* — a falsifiability declaration. `music-app` has *"Anti-patterns (cut on sight): Spinning record, tonearm, wood grain, felt, turntable chrome… Neon accents or the AI-default 'cream paper + terracotta' liner-notes cliché. Raw hex in a view. Linear snap animations."* That is Vercel's *"Reject generated-design reflexes"* section, arrived at independently. The mechanism is already in the corpus; it is just **not codified anywhere flow can teach it to the next repo.**

**(b) The corpus is a natural experiment on Vercel's Part 2.** `music-app` names token *identifiers* and defers *values* to Swift — structurally the design.md/stylesheet split, and drift-proof by construction. `ripe` inlines values. `portfolio` duplicates them three ways.

### 3.3 Drift check — the actual test, and it splits

I compared documented token values against shipped code.

**`ripe` — zero drift.** All 17 checked hex values in `core-docs/design-language.md` match `ripe/DesignSystem/Tokens.swift` exactly (`--ground #FAF8F3`, `--ink #38332B`, `--status-1..4`, `--act-ink #556C3C`, `--neutral-ink-strong #6E6754`, dark-mode values, …). More than matching: the *narrative* survived into the code comments — `Tokens.swift` carries `"#556C3C; Phase 2b had independently reached #576E3E — D2's value wins"`, which is the doc's own reconciliation note. The doc is genuinely the source of truth here.

**`health-tracker` — zero drift.** All 11 checked values are three-way consistent across `decisions/design-language.md` ↔ `workflow/design-system/color-tokens.md` ↔ `UI/Tokens/Color.swift`. And its `feedback.md` carries an explicit precedence rule for exactly this risk: *"On a value conflict between a `decisions/` core doc (esp. `design-language.md`) and a `workflow/design-system/` distillation doc… the decisions/ doc wins and the distillation is reconciled to it — never the reverse."*

**`music-app` — drift impossible by construction**, and its self-declared anti-pattern holds: sweeping every file matched by its own `uiFilePatterns` for raw hex / `Color(red:)` found exactly **one** hit, in `ArtworkColor.swift`, where colour arithmetic is the file's job. Honoured without a linter, n=1 repo.

**`portfolio` — drift found.** `--text-grey` (light) is documented as `hsl(240, 2%, 45%)` in **both** `tokens.md` and `core-docs/design-language.md`; `src/styles/theme.css` ships `hsl(240, 2%, 40%)`. The CSS file's own header reads `Source: tokens.md`. Two docs agree, the code they claim to derive from disagrees, and nothing notices.

The 45%→40% change is almost certainly a deliberate contrast fix (≈4.0:1 → ≈4.9:1 on a light ground). **`ripe` made the identical class of change and wrote it back into the doc**, with the ratio and a ratification date (*"A11y-corrected from the originally locked `#A69D8B` (2.7:1 → 4.9:1 AA); ratified by Ben 2026-07-21"*). Same author, same kind of edit, opposite outcomes. The only variable was whether it got written down — which is precisely the **"consistency that depends on author memory"** failure class `.claude/rules/general.md` § "Consistency discipline (FB-0010)" already names.

**Honest reading of the split.** 3 of 4 repos are clean; the one with drift is the one **not** running flow. That is suggestive, not causal — n=1 each way, and the cleanest repo (`ripe`) is clean because its author wrote ratification notes, not because any tool checked. **The docs are working. Nothing is enforcing them. The evidence does not show that anything needs to.**

Also worth stating: doc↔code consistency is not the same question as *does the doc shape agent output*. On that, the strongest available evidence is indirect but real — `ripe`'s `feedback.md` routes corrections with `**Applies to:** ux, design-language, design deliverables, verification` and `design-language § Dock/Resolution`, and its history cites the doc 17 times; `health-tracker`'s history cites it 35 times. The docs are live participants in the loop, not shelfware.

### 3.4 Three verified gaps in flow's own `designLanguagePath` plumbing

These are defects in flow, found while checking the above. All three verified in-tree:

1. **Nothing scaffolds the doc.** `template/base/core-docs/` ships `plan.md`, `spec.md`, `roadmap.md`, `history.md`, `feedback.md` — and **no `design-language.md`**. A `uiSurface: true` consumer adopting flow gets a slot pointing at a file that does not exist and no template for it.
2. **Nothing checks the doc exists.** `/flow:doctor`'s slot-existence loop is `for slot in planPath specPath roadmapPath historyPath feedbackPath` (`skills/doctor/SKILL.md:229`). `designLanguagePath` is **not in it**, despite doctor's own header promising *"the paths named in slots actually exist on disk."* Meanwhile **15 plugin files** reference the slot (agents `lens-design-engineer`, `lens-ux-designer`, `lens-push-further`, `planner`; skills `staff-review`, `accessibility-review`, `plan-discipline`, `ship`, `verify-build`, `workflow-help`, `doctor`-adjacent schema; plus `docs/workflow.md` and the verify-build schema/example). Three lens agents treat it as their *primary grounding doc* — `lens-design-engineer.md:29` calls it *"your primary source-of-truth"*, `lens-push-further.md:38` says *"uncommon care without grounding is just opinion."*
3. **The slot is a single string; the richest consumer has ten files.** `health-tracker` points `designLanguagePath` at `decisions/design-language.md`, so the lens agents never see `workflow/design-system/{color-tokens,typography,motion,spacing-and-layout,components,accessibility,voice-and-copy}.md`. Its `referenceGlob` is `decisions/*.md`, which doesn't reach them either. The best design corpus in the fleet is ~80% invisible to the reviewers that most need it.

Gap 2 is also an instance of the shape `.claude/rules/general.md` warns about: doctor's header asserts a property that its code does not check for this slot.

### 3.5 Interaction with D1 (prototype-first gate)

**Complementary, not overlapping — and Vercel's evidence supports D1's premise.**

D1 (`dev-docs/handoffs/d1-prototype-first-gate.md`, Phase 0+1 shipped as #137) moves the human's *first* gate from plan text to a prototype, because *"a written plan can't convey feel."* That is an **evaluation-side** change. design.md-style guidance is a **generation-side** change. They meet at exactly one place: the quality of the *first* prototype the human sees.

Vercel independently arrived at both halves. Generation-side: the whole of `design.md`. Evaluation-side, verbatim from artifact B's operating contract: *"Verify the real surface. Source inspection establishes behavior; a rendered interface establishes visual and interaction quality. **Never claim visual verification from code alone.**"* And from C: *"the only way to know whether we were getting closer was to look at the pages coming out."*

So the honest interaction claim: **better generation guidance should reduce prototype iterations, not replace the prototype gate.** No source measures this. If flow ever wants the number, D1 Phase 2+ is the natural place to instrument it (count iterations-to-approval before/after a design-language change) — cheap, because the loop already produces the artifact.

One genuine risk worth flagging to D1: if flow later adds design-guidance machinery *and* D1's brief review *and* the four staff-review lenses, a small UI change passes three separate design-judgment gates. D1's own §9.2 proportionality-collapse question is the right place to resolve that, and it is already deferred to Phase 2.

---

## 4. The flow-level vs repo-level split, argued

The brief calls this the most important output. Here it is, argued from §3's evidence rather than from principle.

**The clean cut is not "judgment vs primitives." It is "shape vs content."**

The tempting cut — Vercel's own — is *judgment in prose (portable-ish) / primitives in a stylesheet (project-specific)*. That cut fails for flow, because **Vercel's judgment prose is not portable either**. Read the specimen: *"Use Geist Sans for prose… Design in monochrome… Avoid em dashes… the Vercel wordmark on the left of the header."* That is Vercel's taste, top to bottom. Meanwhile `ripe`'s judgment layer says *"One curvature family per surface"* and `music-app`'s says *"The artwork is the sacred object."* Both are judgment; both are unportable; and they contradict each other. **Judgment is content.** Any flow artifact that shipped design judgment would violate the project-agnostic quality bar and would be wrong for three of four repos.

So the cut runs elsewhere:

| Layer | Belongs at | Why | Evidence |
|---|---|---|---|
| **What sections a design-language doc has**, and what makes a rule usable by an agent — falsifiable phrasing, named anti-patterns, a conflict-resolution ladder, declared coverage gaps, an explicit "values live here" pointer | **FLOW (mechanism)** | Every repo needs the same *shape*; none can derive it. `ripe` and `music-app` each re-invented half of it independently (§3.2a) — which is the definition of a mechanism that should have been supplied. | §3.2, §1.2 |
| **Where token values live, and the rule that they live in exactly one place** | **FLOW (a one-line convention)** | Purely structural. `music-app`'s pointer form is drift-proof; `portfolio`'s three-way duplication drifted (§3.3). The *policy* is project-agnostic; the *tokens* are not. | §3.3 |
| **That the doc exists, is reachable, and is loaded when design work happens** | **FLOW (plumbing — and this is currently broken)** | 15 plugin files depend on the slot; nothing scaffolds or checks it. Vercel's measured finding is that *loading* is where guidance most often fails (56% non-invocation), not authoring. | §3.4, §2.3 |
| **Every token, axiom, anti-pattern, component convention, brand rule, motion curve** | **REPO (content)** | Unportable by inspection: `ripe` bans all-caps, `health-tracker` mandates mono-uppercase row labels. Both correct, in their own repos. | §3.2 |
| **A bounded primitive vocabulary (Vercel's Part 2)** | **REPO — and mostly already exists** | Every repo already has one: `Tokens.swift`, `Palette.swift`, `theme.css`. Vercel needed a *published* stylesheet only because the agent had no repo. Flow consumers always have the repo. **This part does not transfer.** | §1.1, §3.2 |
| **Deterministic checks on design rules (linters)** | **REPO** | Rules are project-specific, so checks are too. Flow could at most supply the *decision tree* for when a rule earns a linter (§1.5) — one paragraph, not a tool. | §1.5 |
| **The correction→guidance feedback loop** | **FLOW — and it already ships** | `/flow:ship` Step 4c harvest → `contribution_store` → `/flow:contribute` drain → human-merged PR is structurally Vercel's collector/judge/review-packet loop (§1.5). | §1.5 |

**Direct answer to the brief's Part-3 question — real match or superficial?** Real, with one honest asymmetry. Flow's eval-fixture discipline ("prompt changes are code changes," "no new rule without a fixture") is the same discipline as Vercel's "nothing got in any other way" and Anthropic's "create evaluations BEFORE writing." Three independent parties, same rule. But **Vercel closed the loop and flow has not**: Vercel *measures whether the complaint rate falls* after encoding a fix, and treats a flat rate as evidence the fix is wrong. Flow's feedback pipeline enqueues, drains, and merges — and then nothing checks whether the encoded lesson changed anything. That is the same gap `ai-workflow-landscape-2026-07.md` §5 already identified for memory ("nothing measures effectiveness" → roadmap #3). **It is one gap, not two, and it now has external corroboration from two directions.** That is the most valuable single finding in this spike.

**Direct answer on Part 2 (bounded primitives):** the brief asked whether it should exist at flow level. **No.** Not because it's project-specific — the *policy* could be stated project-agnostically — but because the artifact it saves you from (a model inventing typography with no repo to read) does not exist for flow's consumers. The 3×-context-saving argument (§1.3) also doesn't apply: a Swift `Tokens.swift` is already outside the prompt unless someone opens it.

---

## 5. Recommendation

**Headline: build almost nothing. Fix three plumbing defects, add one doc convention, and do one cheap experiment before considering anything larger.**

Flow carries ~91 queued roadmap items and a recent repo-wide review found real overbuilding. This spike found a mechanism worth learning from — but §3 also found that **the design-language docs in the fleet are already working, and nothing is enforcing them.** Machinery aimed at a problem the evidence doesn't show would be exactly the overbuilding pattern.

### 5a. DO — fix the plumbing (small, obviously correct, pays for itself)

**S1. Add `designLanguagePath` to `/flow:doctor`'s slot-existence check.** One token added to the loop at `skills/doctor/SKILL.md:229`, gated on `uiSurface: true`, WARN not FAIL (the slot is legitimately optional). Closes gap §3.4-2, where doctor's header already promises this. **Cost:** ~1 line + a check-count update (grep first — the "N checks" fan-out is the FB-0010 class). **Deletion criterion (FB-0088):** delete if `designLanguagePath` is ever removed from the schema.

**S2. Ship `template/base/core-docs/design-language.md` as a template.** Closes gap §3.4-1. Content = the *shape* only, no taste. See S3.

**S3. Make the template carry the five shape rules the corpus and the survey agree on.** Sections, each with a one-line "why," no project content:
- **Axioms** — falsifiable, numbered, phrased so a violation is pointable (`ripe`'s heading is the model: *"violate = design bug"*).
- **Anti-patterns** — named, so the agent can recognise them by name (`music-app`'s "cut on sight"; Vercel's "Reject generated-design reflexes").
- **Priority order** — how to resolve two rules in conflict. Both Vercel artifacts have one; **no repo in our corpus does.** This is the single biggest missing piece.
- **Tokens: one home, stated.** Either values inline (and the doc is authoritative) or names-only with a pointer to code (`music-app`'s form). Never both. Directly addresses the §3.3 drift.
- **Coverage gaps** — what has no standard yet (Vercel's `coverage-gaps.md`). Cheapest high-value item in the whole survey; costs one heading.
- Plus the authoring rule, stated once: *write corrections as observable decisions.* "Let evidence tables use the full available width," not "make the table feel less cramped."

**Cost:** one template file, ~60–80 lines, plus a `dev-docs/README.md` index row. No skill, no agent, no script, no schema change.
**Deletion criterion:** if two consecutive consumer adoptions ignore the template's headings and write their own structure, the template is wrong — delete or rewrite it, don't defend it.

### 5b. DO — one cheap experiment before anything bigger

**E1. Ablate one design-language doc, once.** Vercel's step 2 and Anthropic's "establish baseline" are the same instruction, and flow has never run it. Pick one repo with a live UI surface (`ripe` is the best candidate — richest axioms, smallest surface), take one real recent UI task, generate the change twice — once with the design-language doc reachable, once without — and score both against the doc's own axioms. n=1, no rerolls, exactly as Vercel's first comparison was.

**What it settles:** whether these docs change agent output at all, which is the premise under *everything* in §5c. Right now that premise is unmeasured in flow, and §2.3's contrary evidence (an unloaded skill scoring *below* baseline) means "obviously it helps" is not safe.
**Cost:** one afternoon, no code.
**Note the honest limit:** it will not settle *quality*, only *change*. Vercel's own 6-page test had the same limit and they said so.

### 5c. DO NOT BUILD (with reasons, and what would change my mind)

| Not building | Why | What would flip it |
|---|---|---|
| **A design-guidance eval harness / fixture suite for design output** | Anthropic: *"There is not currently a built-in way to run these evaluations."* Vercel built a bespoke local app and spent 200+ runs. That is a product, not a feature. Flow's whole fleet is 4 repos. | E1 shows a large effect **and** a second repo independently asks for it. |
| **A token drift-checker (doc ↔ code)** | 3 of 4 repos have zero drift; the one that drifted isn't a flow consumer. Building a checker for one 5%-lightness discrepancy in a non-consumer repo is textbook overbuilding. | Drift appears in a *flow-consumer* repo and causes a real visual defect. Until then S3's "one home" rule is the cheap prevention. |
| **A `/flow:design-review` or `/uncommon-care` skill** | Four lens agents already carry design judgment (`lens-design-engineer`, `lens-ux-designer`, `lens-push-further`, `lens-experience`). D1 adds a brief review. A fifth gate on a small UI change is ceremony. | D1 Phase 2's proportionality work concludes the existing lenses miss a named class. |
| **A public/hosted design.md convention for flow consumers** | The artifact exists to compensate for *having no codebase* (§1.1). Every flow consumer has one. | A consumer starts generating one-off branded artifacts outside its repo. Genuinely plausible for `portfolio`; not for the three iOS apps. |
| **Multi-path `designLanguagePath` (array or glob)** | Real gap (§3.4-3), but a schema change with 15 dependent files, to serve one repo, is not proportionate. `health-tracker` can fix this today by pointing the slot at a short index doc that links the design-system files. | A second repo hits the same limit. |
| **Vercel-style design linters in the plugin** | Rules are project-specific; the checks would be too. | Never at plugin level. Belongs in each repo's `tools/preflight/`. |

### 5d. The one thing worth genuinely considering later (not now)

**Close the loop's measurement half.** §4's asymmetry: flow encodes lessons and never measures whether the complaint recurs. Vercel does — *"Once we encode a fix, that count should start falling. When it does not, something about the fix is wrong."*

This is **the same gap as roadmap #3** (memory-effectiveness instrumentation), reached from a different direction, and it should merge into it rather than become a new item. Flow already has the substrate: FB-XXXX entries are the encoded corrections, and `/flow:contribute`'s queue already dedups and scores confidence. The missing piece is a recurrence count per FB entry, not new machinery.

**Do not schedule it off this spike.** It needs its own sizing against roadmap #3, and §5b's E1 should run first — measuring whether encoded guidance works is premature if we haven't established that guidance changes behaviour at all.

---

## 6. Routing to `roadmap.md`

Proposed; nothing added by this doc.

**§ Next**
- **S1 + S2 + S3 — design-language doc scaffolding + doctor check.** One small PR. Closes three verified defects (§3.4). Deletion criteria stated in §5a.

**§ Exploration**
- **E1 — ablate one design-language doc.** *Surfaces when:* the next substantial UI change lands in `ripe` or `music-app` — the ablation is nearly free if run alongside real work. *Question:* does a design-language doc measurably change agent output, and by how much? *Bar:* n=1, no rerolls, scored against the doc's own axioms; a null result is a publishable outcome and should shrink §5c further.
- **Merge candidate into roadmap #3 — measure whether encoded corrections stop recurring.** *Surfaces when:* roadmap #3 (memory instrumentation) is next sized. Cross-reference §5d; do not size independently.
- **`health-tracker`'s design-system corpus is ~80% invisible to the lens agents** (§3.4-3). *Surfaces when:* a lens finding in `health-tracker` turns out to be ungrounded because the relevant rule lived in `workflow/design-system/`. *Cheap fix first:* an index doc at the slot path; only consider a schema change if a second repo hits it.

**Also worth doing, unrelated to design (found in passing)**
- `dev-docs/design-language.md` and `CLAUDE.md` both state *"flow is `uiSurface: false`"*; `flow.config.json` has said `uiSurface: true` since v1.24.0 with a long comment explaining why. Two stale claims, FB-0010 fan-out class. One-line fix in each; fold into any docs PR.
- `anthropic-canon-alignment-2026-08.md`'s provenance caveat (anthropic.com egress-blocked) is stale in this environment — its quotes can now be verified against source cheaply.

---

## 7. Bottom line

- Vercel's `design.md` is a serious, well-measured artifact whose structure is **compensation for an agent that cannot read a codebase**. Flow's consumers always can. The right thing to study was their *other* post.
- The genuinely transferable material is **the shape of a design-language doc** (falsifiable axioms, named anti-patterns, a conflict-resolution ladder, declared coverage gaps, one home for token values) and **the discipline of writing corrections as observable decisions**. Both are prose conventions. Neither is machinery.
- Two of those five shape rules were **already invented independently** inside our own corpus, by the same author, in two different repos — and never written down anywhere the next repo could inherit them. Supplying that shape is flow's job. Supplying the content never is.
- On the wider survey: **nobody else has published anything substantial on this axis.** Linear published about agents-as-users; Stripe and Vercel converged on retrieval-led docs for *factual currency*, not taste; Anthropic published authoring and eval discipline, not design guidance; Notion, Google, Copilot and Cursor have nothing. Do not plan against an industry consensus that doesn't exist.
- The strongest measured finding in the whole survey is **about loading, not authoring**: an available skill went uninvoked 56% of the time and scored *at* baseline. Flow's exposure to that failure mode is real and it just shipped a mitigation for it (the auto-loading rules + doctor loader check, #135). Extending that measured result from framework APIs to design guidance is **my inference**; §5b names the experiment that would settle it.
- **The docs in the fleet are working. Nothing enforces them. The evidence does not show that anything needs to.** The recommendation is therefore three plumbing fixes, one template, one experiment — and an explicit no to six things.

---

## Sources

**Primary, fetched live 2026-09-03 from this workspace:**
- Vercel — [How our agents build on-brand pages with design.md](https://vercel.com/blog/how-our-agents-build-on-brand-pages-with-design-md) (2026-08-31, John Phamous)
- Vercel — [`https://vercel.com/design.md`](https://vercel.com/design.md) — the specimen, 39,519 B `text/markdown`, 396 lines
- Vercel — [`https://vercel.com/geist/vercel-brand.css`](https://vercel.com/geist/vercel-brand.css) — 108,893 B `text/css`, 133 `.vbg-*` classes, 114 `--vbg-*` tokens
- Vercel — [Teaching agents product design at Vercel](https://vercel.com/blog/teaching-agents-product-design-at-vercel) (2026-06-25, John Phamous)
- Vercel — [AGENTS.md outperforms skills in our agent evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) (2026-01-27, Jude Gao); harness at [nextjs.org/evals](https://nextjs.org/evals)
- Anthropic — [Skill authoring best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)
- Linear — [Agent Interaction Guidelines](https://linear.app/developers/aig) · [Linear Method](https://linear.app/method)
- Stripe — [`https://docs.stripe.com/llms.txt`](https://docs.stripe.com/llms.txt) (90,052 B `text/markdown`) · [docs.stripe.com/agents](https://docs.stripe.com/agents)

**Repo corpus, read at HEAD 2026-09-03 via `gh api`:** `byamron/health-tracker` (`decisions/design-language.md`, `workflow/design-system/color-tokens.md`, `UI/Tokens/Color.swift`, `craft/apple-design-awards.md`, `workflow/design-completion-criteria.md`, `workflow/feedback.md`) · `byamron/ripe` (`core-docs/design-language.md`, `ripe/DesignSystem/Tokens.swift`, `core-docs/{feedback,history}.md`, `tools/preflight/*`) · `byamron/music-app` (`core-docs/design-language.md`, `MusicApp/**`) · `byamron/portfolio` (`tokens.md`, `core-docs/design-language.md`, `src/styles/theme.css`)

**Search-summary basis only (not fetched — flagged inline):** the Notion / Google / Copilot / Cursor "nothing found" sweep; Simon Willison's agentic-engineering-patterns and `smevals`; the OpenAI Self-Evolving Agents cookbook (already covered in `ai-workflow-landscape-2026-07.md` §5).
