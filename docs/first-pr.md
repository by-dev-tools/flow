# Your first PR through the flow loop

A concrete, step-by-step walkthrough. **Read this once before opening your first real PR** in a flow-enabled project — it grounds the canonical 11-step loop in actual commands you type.

**Prerequisites:** you've run `bash bootstrap.sh --stack <your-stack>` and `/flow:doctor` returns clean.

**The change we'll make as an example:** add a single sentence to your project's `core-docs/spec.md` under § "Vision" (or wherever feels right). Concrete enough to walk through every step; small enough to ship in 30 minutes; touches a doc that the auto-loading `documentation.md` rule cares about, so you'll see real rule + skill activity along the way.

Once you've walked the loop once, you have the muscle memory for any subsequent PR.

---

## Step 1 — Clarify

In your project's Claude Code session, tell Claude:

> "I want to add a sentence to `core-docs/spec.md` under Vision: '_<your-actual-vision-text>_'. Walk me through the flow loop on it."

Claude reads `core-docs/spec.md` (and likely `core-docs/plan.md` + `core-docs/feedback.md`) to understand context. Auto-loading rules fire on the path matches: `general.md` always; `documentation.md` because you mentioned `spec.md`.

**What you should see:** Claude reads the source-of-truth docs and either asks 2-4 clarifying questions OR (if autonomous) lists assumptions to confirm.

---

## Step 2 — Plan (load-bearing human gate)

Claude writes a plan into `core-docs/plan.md` under "Active Work Items". The auto-loading `plan-discipline.md` rule (paths: `**/plan.md`) injects the required-fields contract: mode, goal, scope in/out, spec-walk checkboxes, confidence verdict per load-bearing assumption.

For a one-sentence-to-spec change the plan is small but the SHAPE is the same:

```markdown
### Add vision sentence to spec.md

**Mode:** feature (could argue tiny — see § Confidence verdicts)
**Goal:** Sharpen spec.md § Vision with one concrete sentence about <X>.
**Scope (in):** Single sentence added to core-docs/spec.md § Vision.
**Scope (out):** Anything that changes feature table, open questions, principles.

**Spec-walk:**
- [ ] sentence added to spec.md § Vision
- [ ] no other content modified
- [ ] /flow:critique-plan returns APPROVED before execution

**Confidence verdicts:**

**Assumption:** Sentence text is the user's stated intent verbatim, not a paraphrase.
**Confidence:** HIGH
**Why:** Quoted directly from user message.
**If it flips:** Revise to user's preferred wording. Single-commit edit.

**Risks:** none material.

**Files touched:** core-docs/spec.md (1 line added).
```

### Run `/flow:critique-plan`

```
/flow:critique-plan
```

The plan-critic agent reads the plan + your reference docs (whatever `flow.config.json.referenceGlob` resolves to — default `core-docs/*.md` excluding history/plan/roadmap). Returns either `APPROVED` or a `CRITIQUE SUMMARY` with BLOCKER / REDIRECT / FOLLOW-UP findings.

For this trivial example you'll likely see `APPROVED`. **Don't skip this step even though it's docs-only** — see `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` Step 2 "Run on EVERY plan, including docs-only ones" qualifier. The discipline matters; skips compound.

### Human gate

You approve, redirect, or revise. Claude does NOT execute until you say "approved" (or equivalent).

**The point of this gate:** the plan encodes scope and risk. Catching a bad plan here is cheap. Catching it after execution is expensive.

---

## Step 3 — Execute

After your "approved":

```
Edit core-docs/spec.md (add the sentence)
```

Auto-loading `documentation.md` rule fires (matches `**/spec.md`) and reminds Claude of the format contract for spec.md.

Claude checks off the spec-walk boxes as the change lands.

---

## Step 4 — Preflight (mechanical gate)

If your project has a `tools/preflight/check.{mjs,sh}` (bootstrap.sh ships one per stack):

```sh
node tools/preflight/check.mjs
# or, for swift: bash tools/preflight/check.sh
```

Typecheck + build + test run. **MUST be green before `/simplify` or `/flow:staff-review` run** — those are judgment-heavy reviews; wasting them on mechanical bugs is anti-pattern.

For a docs-only change, preflight will likely all-pass quickly OR the gate scripts will gracefully skip irrelevant steps (typecheck on a docs change is a no-op).

---

## Step 5 — Commit

Per-phase commits, "why" not "what" in the subject, co-author trailer:

```sh
git add core-docs/spec.md
git commit -m "$(cat <<'EOF'
Sharpen spec.md § Vision with concrete <X> sentence

Why: vision was ambient — readers couldn't ground feature decisions in
a single sentence. Adding one anchors the spec for downstream planning.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

If safety-critical code changed (not the case for this example), include `SAFETY` in the subject.

---

## Step 6 — `/simplify` (bundled Claude Code, NOT a flow skill)

```
/simplify
```

Cold-reads the diff for reuse / clarity / efficiency. For a one-sentence doc change, will return clean. **Run it anyway even on docs-only** — workflow discipline (Step 6 has the "Run on EVERY diff, including docs-only ones" qualifier) + it's literally seconds of cost.

If it finds anything: fix in-tree + re-run preflight + commit.

---

## Step 7 — `/flow:staff-review`

```
/flow:staff-review
```

Four parallel lens agents (engineer / UX-designer / design-engineer / push-further) spawn via `subagent_type: lens-*`. Each reads the diff and returns BLOCKER / NIT / FOLLOW-UP / EXPLORATION findings.

For docs-only diffs: the lens agents recognize the surface and either run substantively OR return "Nothing to push — surface at ceiling for its scope" (push-further) / "skip with reason: no UI surface" (UX + design-engineer).

**Don't skip a lens** because "scope is tight" or "it's just docs." Document the skip-with-reason if a lens truly doesn't apply, OR run it and let it return empty cleanly.

Apply BLOCKER + cheap NIT fixes in-tree. Route FOLLOW-UPs to `core-docs/plan.md` or `core-docs/roadmap.md`.

---

## Step 8 — Present

Claude returns:

- Reviewer notes (findings, what was fixed, what was deferred + where)
- Dev URL via `/link` if UI changed (not applicable here)
- Branch + commit state
- Any MEDIUM-confidence assumptions from the plan that turned out to matter — redirect window

**No PR exists yet.** That's `/flow:ship`'s job in Step 10.

---

## Step 9 — Iterate

You read the reviewer notes + Claude's summary. If you want changes (different wording, different anchor location), say so. Mini-loop: each iteration is a request → clarify → re-execute → re-preflight → re-commit → re-simplify (if non-trivial change) → re-review.

For this one-sentence example, probably no iteration needed.

---

## Step 10 — `/flow:ship`

```
/flow:ship
```

This is the final-pass pipeline. It will:

1. **Step 1.0** — Print workflow-step assumptions (informational; you should see `Step 2 critique-plan ran, Step 6 simplify ran, Step 7 staff-review ran` per the loop you just walked).
2. **Step 1.5** — Verify `gh` + `jq` installed (fail-fast if not).
3. **Step 1a** — Stale-base check. Will exit 1 BLOCKER if branch is behind `origin/<defaultBranch>`. **Fix: `git fetch origin && git rebase origin/<defaultBranch>`.**
4. **Step 1b** — Confirm there's something to ship; classify PR-OPEN vs LOCAL-ONLY.
5. **Step 2** — Sequentially invoke `Skill('flow:security-review')` then `Skill('flow:accessibility-review')`. Both will early-exit cleanly on docs-only (the per-diff source/UI file detection from FB-0006 + FB-0007).
6. **Step 3** — Route any FOLLOW-UPs to plan.md / roadmap.md.
7. **Step 4a** — Synthesize user-feedback entries to `core-docs/feedback.md` (FB-XXXX format). For this example, you probably have no new user-direction entries to capture — skill skips gracefully.
8. **Step 4b** — Failure-pattern memory entry to `~/.claude/projects/<canonical>/memory/feedback_*.md` (if source-diversity bar holds — usually NOT on a trivial change).
9. **Step 5** — Update `core-docs/{history,plan,roadmap,spec}.md` (history gets a new entry; plan's "Current Focus" + "Recently Completed" sweep).
10. **Step 6** — Commit doc updates.
11. **Step 7** — Push with `-u` if branch not tracking; open PR via `gh pr create --base <defaultBranch>` (with `flow.config.json.branchPrefix` honored). Never merges.

**You'll see a PR URL.** Open it. Verify the PR body, the history entry, the plan update.

---

## Step 11 — STOP

**Claude does not merge.** Ever. The user merges. This is the second load-bearing human gate.

You review the PR. CI runs (your project's `.github/workflows/ci.yml` from the bootstrap overlay). When green, you click "Merge when ready" (if your repo uses merge queue) or "Squash and merge" otherwise.

---

## What you should walk away with after one trip through the loop

1. **Muscle memory for the gate sequence.** Plan (gate) → execute → preflight → commit → reviews → ship → merge (gate). The two human gates are non-negotiable; everything between is delegable.
2. **Familiarity with which auto-loading rules fire when.** Edit `plan.md` → `plan-discipline.md` injects. Edit `src/foo.tsx` → `ui.md` + `exploration.md` inject. The rules are the load-bearing enforcement.
3. **A real PR history entry in `core-docs/history.md`** with the per-PR decision log shape (what + why + design decisions + technical decisions + tradeoffs + lessons learned).
4. **A first sense of when the lens agents catch real things.** On a trivial docs change, they won't catch much. On a real product change, the 4-parallel pattern's value compounds.

## Common first-PR pitfalls + fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `/flow:critique-plan` returns "no reference docs loaded" | `flow.config.json.referenceGlob` doesn't match any files on disk | `ls -la $(jq -r '.referenceGlob' flow.config.json)` — confirm the path exists; bootstrap.sh defaults to `core-docs/*.md` |
| `/flow:ship` Step 1a fires BLOCKER on first PR | Branch is stale vs `origin/main` (common immediately after PR-opening another change) | `git fetch origin && git rebase origin/main` then re-run `/flow:ship` |
| `/flow:staff-review` lens agent fails to spawn | `subagent_type: lens-*` resolution failed — likely flow plugin not enabled at project scope OR plugin install incomplete | `/flow:doctor` to confirm install. Re-run `/plugin install flow@flow` if needed. |
| `/flow:ship` Step 4a writes nothing to feedback.md | No new user-feedback to synthesize (correct behavior on trivial PRs) | None — confirm by re-reading the conversation since branch-start; if you DID say something direction-shifting, prompt `/flow:ship` to re-scan |
| Memory entry not written at Step 4b | Source-diversity bar didn't hold (only one finding source — normal on trivial PRs) | None — memory entries earn entries on the SECOND occurrence of a pattern, not the first |
| CI fails on `evals` or `security` job | Project doesn't have these workflows OR scripts they invoke are missing | `bash bootstrap.sh --stack <yours>` ships the stack-specific ci.yml; if you have a custom CI setup, adapt those jobs to your pipeline |

## Next steps after your first PR

- Read `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` end-to-end. The 11-step loop has rationale, gate semantics, spike/tiny modes, and feedback-loop discipline that this walkthrough only touched.
- Configure `core-docs/design-language.md` if your project ships UI. It's load-bearing for `/flow:staff-review`'s UX + design-engineer + push-further lenses.
- Optionally enable the opt-in PreToolUse hooks from `${CLAUDE_PLUGIN_ROOT}/hooks/default-hooks.json` (sensitive-file write blocker + path-validation warn) — merge into your `.claude/settings.json`.
- File any rough edges to flow's `dev-docs/feedback.md` via a follow-up PR in `by-dev-tools/flow`. Real-consumer signal is how the plugin compounds quality.
