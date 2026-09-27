# 2026-09-27 — S0 option (c): the rule-skills are model-invoked, and the measurement refused the premise

**PR:** #TBD · **Version:** v1.51.0 · **Feedback:** FB-0122 · **Roadmap:** S0 (resolved), S2 + config-driven-`paths:` (retired)

## What was asked, and what the measurement said instead

Ben chose option **(c)** at the S0 human gate: stop trying to make the four rule-skills path-activate, let
Claude load them by judgment from their descriptions. The premise handed down with it was that the
descriptions were *actively suppressing* the only mechanism left — all four ended with "Not user-invocable
— path-activated only." — so rewriting them should turn the feature on.

**The code change is right and shipped. The premise did not survive contact with the measurement.**

## The doc verification (all confirmed, two corrections to the brief)

- **`paths:` on a `SKILL.md` is a real, documented field.** It *limits* an activation the `description`
  otherwise earns: *"Glob patterns that **limit** when this skill is activated… Uses the same **format** as
  path-specific rules"* — format, not semantics. The read-trigger semantics we assumed belong to
  `.claude/rules/*.md`. Two mechanisms, one field name. **Nothing to report upstream; option (a) was moot.**
- **A plugin cannot ship rules at all** — `rules/` is not in the standard layout, and the same page says
  *"To include instructions that load into Claude's context, put them in a skill."* The docs endorse (c)'s
  mechanism rather than merely lacking an alternative.
- **`user-invocable: false` stays; `disable-model-invocation` must not be set** (its row reads "Description
  not in context", which would forbid the only working path).
- Two corrections to the brief: § "Writing effective descriptions" lives on the **platform** best-practices
  page, not `code.claude.com/docs/en/skills`, and it carries a **1,024-char hard cap on `description`** —
  a different limit from the 1,536-char *combined* `description`+`when_to_use` listing truncation. Both
  bind. And the docs provide **`when_to_use`** as a separate field for trigger phrases, which the brief did
  not name; all four now use it.

## The numbers

43 interpretable sessions, 0 discarded at final count, on scrubbed neutral bases with no `CLAUDE.md`,
`AGENTS.md`, or `.claude/` beyond the probe skills. Counts are "fired / n", where *fired* = a `Skill`
tool_use for that rule **during the task turn**. Every session carried its own known-positive and any
session failing it was discarded rather than counted as a zero.

<!-- RESULTS_TABLE -->

**Arms.** **a** = today's (pre-v1.51.0) descriptions + `paths:`, project scope. **b** = the v1.51.0
descriptions, no `paths:`, project scope. **cold** = the real v1.50.0 plugin installed, **plugin scope, old
descriptions**. **c** = the real v1.51.0 plugin installed, **plugin scope, new descriptions**. **d** = a
deliberately *neutral* description + `paths:`, project scope — isolates the field from the description.

## What that means, in the order the evidence forces

**1. The suppressant sentence was not decisive.** Arm a fired `plan-discipline` 2/3 and `documentation`
1/3 *with* "path-activated only" in the description. The sentence we identified as the blocker was not
blocking. That was the core premise of the brief and of my own plan, and it is wrong.

**2. Arm b is not reliably better than arm a on the model the main series used.** On sonnet, `plan-discipline`
went 2/3 → 3/3 and `documentation` went 1/3 → 0/3. At n=3 neither movement is distinguishable from noise,
and **I am not going to call that an improvement.**

**3. The name does the work, not the description.** Arm d — a deliberately vague description ("Notes about
writing a plan document") plus a restrictive glob — still fired `plan-discipline` and `documentation`. When
the skill's *name* matches the task ("write a plan" → `plan-discipline`), naming dominates and the
description barely registers. Those cells measure naming quality, not description quality. The
discriminating cells are `general` and `exploration`, where the name does not match the task surface — and
those are where everything reads zero on sonnet.

**4. Plugin scope and project scope are NOT equivalent, and only plugin scope matters.** This is the
finding that matters most, and it is the one the orchestrator's insistence on arm c bought. Project-scope
`plan-discipline` fires 3/3; plugin-scope `flow:plan-discipline` fired **0** in every measured session. The
plugin was live and invocable in those sessions — `flow:workflow-help` worked in the same transcripts, which
is precisely why that control exists. The plausible mechanism: at plugin scope the skill is namespaced and
competes with 26 sibling flow skills across ~5,669 always-on description tokens; at project scope there are
five skills and one obviously matches. **The plan cited E1's probe 3 as establishing project ≡ plugin
equivalence. That was for `paths:` — a different mechanism — and it does not transfer.**

**5. The model matters more than the description.** On **opus-5, the default Conductor model for the claude
agent**, arm b fired 3 of 4 rules where sonnet fired 1. The main 36-session series ran on sonnet — a
**non-default** model. Per the orchestrator's own standing instruction ("if they diverge, that divergence is
a more important finding than the headline"), this outranks the headline.

## So did (c) work?

**As a code change: yes, and it was worth shipping on its own merits.** `paths:` genuinely could only gate
the trigger; the descriptions genuinely were worse than the docs' own guidance; the doctor check genuinely
reported `[PASS]` over a claim it never checked; `plugin-provenance.py` genuinely would have broken. All of
that is true independent of the invocation rate.

**As a fix for the advertised feature: not demonstrated, and on the evidence here, not likely at plugin
scope.** I am not going to describe this as working because the PR's own thesis wanted it to. The shipped
docs now say the four *raise the floor rather than acting as a gate*, which is what the numbers support.

## Three instrument defects, because each one nearly produced a flattering answer

1. **Scoring the whole session instead of the task turn.** Turn 2 *asks* which rules were consulted; a model
   can satisfy that by invoking one right then. First run showed every arm firing — including the arm built
   to return zero. That "all arms fire" result is the tell, not the finding. Fixed by segmenting at the
   second `userMessage` and scoring only before it.
2. **Counting limit-truncated sessions as negatives.** 19 of the first 28 sessions hit the account limit
   mid-run. Their empty results are *absence of evidence*, and counting them would have manufactured a clean
   `0/N` for arm a — exactly the error the known-positive exists to catch. All 19 were discarded and re-run.
   The known-positive is what made them *detectable*: no control sentinel, no interpretation.
3. **A re-run that silently lost to the thing it replaced.** `sorted(glob("results-*.tsv"))` puts
   `results-a-rerun.tsv` *before* `results-a-sonnet.tsv`, so the truncated original overwrote its own
   replacement and all 19 stayed discarded. Found because the discard count did not fall after a successful
   re-run — the number that should have moved, didn't.

And one arm-validity defect: **arm c's first build installed 1.50.0 from `main`, not this branch**, because
the scrub ran before the plugin copy. It would have measured the old descriptions and been labelled the new
ones. Caught by asserting the arm's validity **by content** (`paths:` absent, `when_to_use` present) rather
than by version string — the FB-0107 dogfooding trap, one layer out.

## The code

- **Four rule-skills** — rewritten `description` + new `when_to_use`, `paths:` removed, `user-invocable:
  false` kept, no `disable-model-invocation`. Bodies no longer narrate their own path-activation.
- **`plugin-provenance.py`** — `_is_rule_skill()` keyed on `paths:`; removing it would have reclassified all
  four as command skills and printed *"a model asked to run one would wrongly conclude it does not exist"*,
  which that function's own docstring calls "something simply untrue of it". Re-based on `user-invocable:
  false`. **CI could not have caught this**: the eval pinned a *synthetic* `a-rule` fixture carrying
  `paths:`, so it kept passing after the real files stopped having the shape. Now asserted over the four
  **real** files plus a real command skill — both halves, so neither hardwired `True` nor hardwired `False`
  passes. Found by `/flow:critique-plan`, not by me. It is item 4's corollary — *pin a claim at the layer
  where it is claimed* — and per Ben's instruction it is filed as an example under that corollary rather
  than as a new rule.
- **`/flow:doctor` Check 3.2** — asserts registration (labelled as such) plus the frontmatter contract, each
  negative paired with a positive so deleting a skill fails rather than passes. Verified by mutation: five
  distinct violations each produce a `FAIL`, including deletion.
- **New `[UNCHECKED]` marker** — outside the verdict arithmetic, printed inline as `[READY] (N unchecked)`.
  Every such line must name the mechanism that would make it checkable, and that clause is its own deletion
  criterion. Its prose now also tells the reader not to read a green line as "the rules governed this run".
- **Nine false claims corrected**, including **`template/base/CLAUDE.md.template`**, which still pointed at
  `${CLAUDE_PLUGIN_ROOT}/rules/` — the directory Phase 00 deleted in v1.33.0. `bootstrap.sh` copies that
  file into every consumer repo, so it is **write-once**: a wrong line there stays wrong forever in every
  project that already adopted flow.
- **Two fan-out survivors the eval suite caught**, both after I believed the sweep was complete: doctor's
  awk frontmatter parser tripped #165's new argument-placeholder lint (awk's field variable is spelled like
  a host placeholder — rewritten in sed, because the lint should stay strict rather than learn an
  exception), and `run_doc_slot_resolution_evals.py` asserted FB-0102's coverage requirement *through the
  retired globs*. Re-pointed at the body text that carries the requirement, not deleted. **The lesson: I
  grepped prose for path-activation claims and never grepped eval assertions for the same contract.**

## Tradeoffs

- **Retiring S2 and config-driven-`paths:` rather than keeping them "just in case."** With no globs there is
  nothing to widen. Kept struck-through, because §5.3's measurement (3 of 4 consumer repos matched zero
  files) is the standing argument against ever re-introducing a hardcoded source-root glob.
- **`[UNCHECKED]` outside the verdict arithmetic, not inside it.** Inside, every consumer sits permanently
  below `[READY]` over an item nobody can clear — which then argues for retiring `[READY]`. Buried
  entirely, the signal is lost. Inline count keeps both.
- **Reporting a null result rather than tuning until it passed.** Ben's instruction was explicit and it was
  the right call: a description reverse-engineered to satisfy my own instrument would be the instrument
  measuring itself.
- **Not re-opening (c).** The change stands on its own merits; whether to reach for the `SessionStart` hook
  is a separate decision, recorded on the roadmap with the layer caveats attached.

## Open, and routed rather than fixed

- **The decisive experiment is now a different one**: plugin scope × default model × a rule whose name does
  *not* match the task. That cell is the only one that describes a real consumer on the hard case.
- **`general` cannot be restored to "always" by any description.** The `SessionStart` hook is the only
  mechanism that could, and it buys **delivery**, not **compliance** — the third turn of the same screw
  (registration → activation → delivery → compliance, each looking like the guarantee beneath it).
- **`tools/rule-activation/`** ships the rig with all three instrument defects documented, so the next seat
  inherits the corrected version rather than rediscovering it.
