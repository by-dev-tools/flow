# D1 §9.3 spike — is an auto-written technical plan good enough to anchor the machine gate?

**Date:** 2026-09-16 · **Mode:** spike (finding is the deliverable, no shipped code) · **Branch:** `conductor/spike-93-auto-plan-quality`
**Gates:** `dev-docs/handoffs/d1-prototype-first-gate.md` §9.3 — a LOW-confidence assumption rated an **automatic human gate**; Phase 3 (auto-write + machine-gate the technical plan) does not get built until this clears.
**Evidence:** `dev-docs/research/2026-09-16-d1-auto-plan-quality-spike/design-brief.md`, `.../auto-plan.md` — the exact artifacts this finding is based on, committed unmodified so the reasoning below can be checked against them, not just trusted.

## Verdict: MIXED

The auto-plan's individual criteria are **genuine** — not vacuous, testable against a live artifact. The auto-write step's **coverage** is **hollow** — it under-declared roughly as many real behaviors as it declared. The gap between those two results, on the same plan, is itself the finding: a mechanically clean plan (0 vacuous criteria) is not the same thing as a complete plan, and the three-reviewer pre-execution gate the handoff currently specifies (`auditor` + `plan-critic` + push-further, reading the plan + brief only) did not catch the completeness gap on this run.

**This is n=1.** One prototype, one auto-plan, one pass of each reviewer. It is not a statistical claim about auto-plan quality in general — it is a demonstration that the failure mode §9.3 worried about is real and reproducible, on a real, heavily-reviewed artifact, using the actual shipped checking machinery. That is what a spike is for; it is not evidence the failure mode is rare or common.

## Method

**Prototype chosen:** `plugins/flow/skills/verify-build/lib/annotation-layer.html` — the click-to-pin annotation overlay. This is the handoff's own named "reference case" (§3 step 4: "the six-round annotation-layer rebuild is the reference case"), a real artifact that went through genuine iterative human review (FB-0076, six rounds) and shipped with a real staff-review pass (PR #49, v1.7.0). Using it means the spike's ground truth (what a real reviewer actually flagged when this shipped) is independently checkable in `git log`, not invented for the spike.

**What I built, in character as the D1 Step-6 agent:**
1. A **design brief** (`design-brief.md`) — the six FB-0081 fields, reconstructed to stand in for D1 Step 2 (no such artifact exists pre-Phase-2; the trigger, prototype phase, and gate 1 aren't built yet). Deliberately included one field ("pushes past the literal request: accessibility parity — screen-reader announcements, keyboard operability") to give the plan-critic pass a real "user's stated request" to check scope drift against, mirroring what would exist by the time Step 6 runs in the real loop.
2. A **13-item Spec-walk technical plan** (`auto-plan.md`), written by reading the prototype's own header-comment design notes and its function inventory (mode toggle, pin placement/anchor resolution, comment CRUD, clipboard export + fallback, accessibility live region, dark mode), in the same house Spec-walk style used elsewhere in `dev-docs/plan.md` (pin-marker `→ verify:` suffix per FB-0068's convention).

**Path taken for the machine gate — checked, not assumed, and this is a methodological result in its own right, not a caveat:**

- **`/flow:critique-plan` was not invoked as a skill.** This checkout's `plugins/flow/.claude-plugin/plugin.json` is v1.43.0; the *installed* marketplace copy (what Claude Code actually resolves for a `/flow:*` skill call, per FB-0107) is pinned at v1.29.0. `dev-docs/history/2026-09-13-dogfood-version-provenance.md` already measured, in this exact repo, that 1.29.0's `extract_session.py` does not comma-split `referenceGlob`, so a `/flow:critique-plan` run here resolves **zero** reference documents — a clean `APPROVED` from that path would be indistinguishable from a reviewer that never read a single project rule. I confirmed the same file-level fact again before relying on it (diffed `extract_session.py`'s `ref_globs = [...]` comma-split logic between the installed 1.29.0 copy and this checkout). Given that, I spawned `flow:plan-critic` **directly** via the Agent tool — fresh context, pointed at the brief, the plan, the prototype, and the reference docs myself — rather than let a broken skill produce a false-clean signal.
- **`/flow:audit-coverage` was not invoked as a skill either, for a different and more precise reason than I first wrote in the chat summary of this spike.** Its `SKILL.md` builds its evidence block from a live `git diff` (`skills/audit-coverage/SKILL.md:90`), and there is no diff yet at the point in the D1 loop this plan simulates (Step 6, before Execute). **The corrected framing (caught on review): this is not "a fourth reviewer that structurally can't run pre-execution" — it's an existing reviewer whose *judgment* is diff-agnostic and whose *input* is diff-shaped.** Its own instructions state the judgment plainly: "for each user-perceptible behavior change [...], check whether any declared criterion would cause someone to test it" (`SKILL.md:130`), and explicitly separate that from criterion quality ("`SKILL.md:129`: you check declared-vs-built completeness only, not criterion quality — that's `/flow:verify-build`'s axis"). That framing transfers to a source tree with one substitution: feed it the approved prototype's source as "what was actually built" instead of a diff. So I spawned a fresh `flow:auditor` and handed it `audit-coverage`'s own task framing verbatim, with the prototype's full source in place of the diff. This is best read as **a second input mode for the existing, already-tuned reviewer**, not new judgment invented for this spike.
- **Live dry-read, not just static reasoning.** Built a minimal host page, injected the real prototype fragment before `</body>`, loaded it in headless Chrome (`google-chrome --headless=new --dump-dom`), and confirmed the DOM reflects real script execution matching a plan claim (`aria-checked="true"`, the fab glyph showing the empty-state mark) rather than static markup. This grounds the "criteria are genuinely testable" claim in an actual observation, not an assumption that a client-only HTML artifact must obviously be scriptable.

## Result 1 — vacuity: 0/13, deterministic, reproducible

```
python3 plugins/flow/skills/verify-build/lib/extract-criteria.py \
  dev-docs/research/2026-09-16-d1-auto-plan-quality-spike/auto-plan.md \
  | python3 plugins/flow/skills/verify-build/lib/criterion-specificity.py
# → {"total": 13, "vacuous": [], "specific_count": 13}
```

Every declared criterion names an observable predicate (#148's shipped heuristic, `criterion-specificity.py`). No criterion reads like "Rate limiting works correctly." On the narrow axis this checker exists to police — is the criterion's own claim falsifiable — the auto-plan is clean.

## Result 2 — coverage: 10 undeclared real behaviors, against 13-14 declared

Spawned `flow:auditor` with `audit-coverage`'s own task framing (see Method), the prototype's full source as the "diff," and the plan's Spec-walk as "declared criteria." Ten `Undeclared change` findings came back, each naming a specific function/control in the prototype with no covering criterion:

| # | Undeclared behavior | Evidence in `annotation-layer.html` |
|---|---|---|
| 1 | Keyboard-only interaction path (Tab + Enter, Shift+Arrow walk to elements Tab can't reach) | `walkStep`/`walkDepth`/`focusWalkTarget` (~469-511), `focusin` handler (~1146-1154); code comments cite WCAG 2.1.1 explicitly |
| 2 | Bulk delete-all (`#an-wipe`, two-step arm/disarm) | ~978-992 |
| 3 | Single-comment delete (row button + editor's Delete) | ~835-849, ~927-931 |
| 4 | A second, independently-persisted hover-outline preference (`snapPreview`) with its own compensating flash-on-commit behavior | ~392-394, ~634-662, ~966-976 |
| 5 | Show/hide-all-pins toggle | ~324-328, ~959-962 |
| 6 | Opening/closing the comment list panel itself (distinct from the single-pin editor) | ~937-940, ~942-946 |
| 7 | Per-row copy button (distinct single-note format from the batch "Copy notes" export the plan does cover) | ~819-833, `oneNoteBlock()` ~1044-1046 |
| 8 | Storage-quota-exceeded warning path (localStorage write failure → one-time user-visible warning) | `save()` ~396-406 |
| 9 | Escape key's four-branch priority state machine (editor → copy sheet → panel → mode-off) | ~1093-1106 |
| 10 | Discard-on-empty-close (an untouched blank comment must not persist as a stray pin) | ~683, `dropEmpty()` ~920-923 |

Finding #1 (keyboard-only interaction) was also caught independently by the `flow:plan-critic` pass below, via a completely different route (the brief's own text, not the code) — the same real gap surfaced twice, by two different mechanisms, which is stronger evidence than either alone.

**The juxtaposition is the finding.** 0/13 vacuous and 10 undeclared, on the same plan, from the same auto-write pass. A criterion-quality checker (`criterion-specificity.py`) and a criterion-completeness checker (the `audit-coverage`-framed pass) are answering genuinely different questions, and a plan can score perfectly on the first while failing badly on the second. Anyone reading only the vacuity number would conclude the plan is solid; anyone reading only the coverage count would conclude it's unusable. Both are true simultaneously, about different axes.

## Result 3 — `flow:plan-critic` (direct spawn): 2 BLOCKERs

1. **Internal incoherence.** The plan's own preamble names the real approved-prototype path (`plugins/flow/skills/verify-build/lib/annotation-layer.html`); its Files-touched section then names an unrelated, disconnected new path (`overlay/annotation-layer.html`) with no "moved from / promoted from" language. An auto-write that drifts from the artifact it claims to be anchored to defeats the entire premise D1 Step 6 exists for (§3 step 6: "against a design that survived contact").
2. **Scope drift (contraction).** The brief named keyboard operability as one of two explicit accessibility-parity asks pushing past the literal request. The plan implemented only the other half (screen-reader live-region announcements) and silently dropped keyboard entirely — no Scope (out) line names it as a deliberate cut. This is the same real gap as coverage finding #1, caught by a different reviewer via a different citation path (brief text vs. code).

## Result 4 — `flow:auditor` claim-check (direct spawn): 2 findings the mechanical checkers structurally cannot catch

1. **A criterion that tests a component outside the plan's own declared evidence.** "An unreadable/corrupt overlay file degrades to the read-only report rather than crashing the renderer" is a claim about the *renderer* (the thing that injects the overlay before `</body>`) — a component the plan's own Scope (out) excludes ("the renderer that decides when to inject... assumed to already produce the HTML page"). The plan never reads or cites renderer code; it just asserts the guarantee holds and offers a one-line manual check. `criterion-specificity.py` cannot catch this — the claim itself is concrete (it has a subject, a condition, an outcome), so it reads as non-vacuous. Only an LLM check that cross-references the criterion against the plan's own Scope sections caught it.
2. **A verify-method that's vague relative to its siblings.** "A modifier-click... passes the click through... → verify: manual check" names no target action, unlike every sibling criterion's verify step (which all name a concrete action: "drag-select a paragraph, confirm no editor opens"; "remove the anchored element, confirm the pin still lists... as lost"). `walk-pin-lint.py` would not catch this either — it only checks that *a* pin marker is present (`→`/`verify:`/etc.), not the quality of what follows the marker. This is a real, load-bearing gap between what the two mechanical checkers police (claim concreteness; marker presence) and what actually makes a criterion checkable (a named target action for the verify step) — closing it is not covered by either shipped engine today.

## What's thin, for whoever designs Phase 3

The three-reviewer pre-execution gate as scoped in the handoff (§3 step 6, §5) — `auditor` + `plan-critic` + push-further, reading the plan and the brief — has **no mechanism that reads the approved prototype's own code for behavioral completeness.** `plan-critic` caught one of the ten real gaps, and only because this particular brief happened to name the missing capability explicitly in its "pushes past the literal request" field — that is a property of this brief's wording, not a guarantee the mechanism provides by design. `auditor` does not check completeness at all (it checks whether stated claims are backed by evidence). The pass that actually caught 10 of the 12 real gaps found across all instruments was a coverage-style read of the prototype's *source*, and that judgment already exists, already tuned, in `/flow:audit-coverage` — it is just fed a diff today, and there is no diff at Step 6.

Two ways to close this, neither of which is mine to pick (routed to the orchestrator/Ben — see Decision below):

- **(a) Feed `audit-coverage` the approved prototype's source as an alternate input mode**, alongside its existing diff mode, at the pre-execution machine gate. This is cheaper than "add a fourth reviewer with new judgment to maintain" — the judgment half is exactly what this spike did by hand, and it worked. It is an input-mode addition to an existing, already-tuned reviewer, not new prompt-engineering surface to drift out of sync.
- **(b) Accept that real coverage-hole detection only happens post-execution**, via the existing `/flow:audit-coverage` running against the actual diff once Execute produces one, and design Step 6's machine gate to be explicitly a form/coherence check (is this internally consistent, does it match the brief) rather than a completeness check — with the cost of a late-discovered coverage gap priced in as a known, accepted residual rather than assumed away.

## Side note: the handoff disagrees with itself on what this spike gates

Not this spike's to fix, but worth recording so it isn't silently smoothed over: `dev-docs/handoffs/d1-prototype-first-gate.md` §0 ("Resolve or escalate both before Phase 2") and §8 ("Do not start Phase 2 until §9.3's spike resolves") say this spike gates **Phase 2**; §9.3's own verdict text says "this is an automatic human gate... do not build **Phase 3** until the spike clears." Those disagree — a fan-out contradiction inside one document. Per the orchestrator's direction on this run, Phase 2 (being built in parallel by Track B) is **not** blocked by this spike; only Phase 3 is. This doc does not edit the handoff to resolve the contradiction — out of scope per the dispatching brief.

## Bottom line for §9.3

Confidence stays where the handoff put it: **do not build Phase 3 assuming the current three-reviewer plan gate closes the completeness hole FB-0080 was about.** On this one real, heavily-reviewed prototype, using the actual shipped checking machinery, it didn't — not because the checking machinery is bad, but because the piece that would have caught most of the real gaps (`audit-coverage`'s judgment) isn't in the loop at the point the plan gets machine-gated. That's a design question for whoever builds Phase 3, not a verdict that D1 should be abandoned — the criterion-quality axis (vacuity, live testability) held up fine on this run.

## Reproduce this

```bash
# vacuity check (deterministic)
python3 plugins/flow/skills/verify-build/lib/extract-criteria.py \
  dev-docs/research/2026-09-16-d1-auto-plan-quality-spike/auto-plan.md \
  | python3 plugins/flow/skills/verify-build/lib/criterion-specificity.py

# confirm the installed-vs-checkout version gap that routed plan-critic off the skill path
cat ~/.claude/plugins/cache/flow/flow/1.29.0/.claude-plugin/plugin.json | grep version   # 1.29.0
cat plugins/flow/.claude-plugin/plugin.json | grep version                              # 1.43.0 (or later)
diff <(grep -A2 'ref_globs' ~/.claude/plugins/cache/flow/flow/1.29.0/scripts/extract_session.py) \
     <(grep -A2 'ref_globs' plugins/flow/scripts/extract_session.py)

# live dry-read (headless Chrome; confirms the prototype is a real, scriptable app)
python3 - <<'PY'
proto = open("plugins/flow/skills/verify-build/lib/annotation-layer.html").read()
open("/tmp/dry-read-host.html", "w").write(
    f'<!doctype html><html><body><h1 id="h1">Report</h1>{proto}</body></html>'
)
PY
google-chrome --headless=new --disable-gpu --no-sandbox --virtual-time-budget=2000 \
  --dump-dom file:///tmp/dry-read-host.html | grep -o 'id="an-mode"[^>]*aria-checked="[a-z]*"'
```

The `flow:plan-critic` / `flow:auditor` direct-spawn passes are not mechanically reproducible from a script (they're fresh-context Agent-tool invocations) — the prompts used are described in full in the Method section above and can be re-issued verbatim against `design-brief.md` / `auto-plan.md` / the prototype file.
