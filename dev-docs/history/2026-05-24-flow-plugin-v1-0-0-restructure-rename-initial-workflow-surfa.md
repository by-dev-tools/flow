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
