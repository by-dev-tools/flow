# FB-0107 — Dogfooding runs the *installed* plugin, not the branch that changes it

- **Date:** 2026-09-12
- **Source type:** review feedback (surfaced independently by two workspaces during pre-archive checks)
- **What was said:** Two workers preparing to be archived reported the same underlying fact from
  opposite directions. One found that #147's queue flush (`cmd_flush`, shipped v1.39.0) only fired
  because it invoked the code from its own working tree — the *installed* plugin in the cloud
  workspace is pinned at **1.29.0** and contains no flush code at all. The other found its queue
  simply empty, because the Step 4c harvest that fills it also does not exist in 1.29.0.

- **Synthesized rule:** **This repo's self-review executes the installed plugin, not the branch
  under review — so a skill change is systematically *not* exercised by the PR that ships it.**
  When `/flow:ship` runs from a flow branch, the `/flow:*` skills it invokes resolve to the
  installed marketplace version. The diff sitting in the working tree is inert. Dogfooding is
  therefore testing the *previous* release on every flow PR, which is close to the opposite of what
  everyone involved believed it was doing.

  Three consequences worth separating, because they have different fixes:

  1. **A skill fix cannot validate itself.** Any PR whose entire payload is a change to `/flow:*`
     behaviour ships with zero execution evidence for that behaviour, no matter how thorough its
     Spec-walk looks. The ship pipeline running green is evidence about the installed version.
  2. **The staleness is unbounded and invisible.** Nothing pins, checks, or reports the installed
     version at ship time. 1.29.0 against a `main` at 1.41.0 is a twelve-release gap that no gate
     noticed, and the gap will keep widening silently because nothing is watching it.
  3. **The failure is confidence-inverting, like FB-0105.** The pipeline reports success. A
     reviewer reads "flush fired, queue drained" and concludes the mechanism works. What actually
     happened is that a *different, older* mechanism ran. A gate that reports on the wrong artifact
     is worse than a missing gate, because it manufactures the belief that the check happened.

  This is the fourth member of the FB-0085 class (shipped, believed effective, never loading),
  after the rules-as-skills `paths:` bug, the hooks declaration, and `exploration`'s globs. The
  class is now large enough that "does this actually load/run in the environment it targets?"
  belongs in the ship checklist as a standing question, not as something rediscovered per incident.

  **Immediate operational consequence, already in force:** pre-archive checks must **export the
  contribution queue manually** and must not treat a clean flush report as evidence of durability —
  in most workspaces the flush code was never present to run.

- **Applies to:** `/flow:ship` + `/flow:ship-spike` (which version did the reviewers run?);
  `/flow:doctor` (the natural home for an installed-vs-repo version check, alongside the Check 3.2
  "registered vs activates" upgrade already routed as S0); the dogfooding claim in `CLAUDE.md` and
  `dev-docs/workflow.md`; canonical §4.6 archive safety.

---

## Measured correction (v1.43.0) — the axis is *which executor resolved the path*, and "inert" was wrong

The entry above says *"The diff sitting in the working tree is inert."* **That is not accurate, and
the truth is more awkward than uniform staleness.** Measured while building the provenance reporter:

> **Everything Claude Code resolves comes from the INSTALLED tree. Everything the Bash tool resolves
> comes from the WORKING TREE.**

`CLAUDE_PLUGIN_ROOT` is empirically **unset** in Bash-tool calls (four places in this repo already
asserted this) and **set** in `!`-preprocessor blocks. So the same `${CLAUDE_PLUGIN_ROOT}/…` string
names different files depending on who expands it:

| Surface | Resolved by | Source |
|---|---|---|
| SKILL.md prose, agent prompts | Claude Code's registries | **installed — stale** |
| Scripts in `!`-preprocessor blocks | Claude Code's expander (`CPR` set) | **installed — stale** |
| Helper libs in fenced Bash blocks (32 of 144 ref sites carry the fallback) | Bash tool (`CPR` unset) | **working tree — fresh** |
| Bare `${CPR}/…` executables in fenced blocks (the other 112) | Bash tool | **hard failure**, not staleness |
| Skills/agents absent from the installed tree | not registered | **neither — no tool exists** |

Three consequences the original entry did not have:

1. **One run draws from two versions,** so a single "plugin version" line would be **wrong**, not
   merely ambiguous — it would report the installed version and imply the fresh engines never ran.
   Hence four labelled rows.
2. **A *modified* script can be silently overridden while a *new* one hard-fails.** In a `!`-block
   `CPR` is set, so the installed copy wins even for a script this branch changed; and
   `audit-plan`/`critique-plan` carry no fallback, so a script a branch *adds* fails outright there.
3. **v1.4x engines are being driven by 1.29.0 prose** — a contract-mismatch surface, not just old
   code running.

**This was measured by FB-0107's own PR, at its own plan gate.** The `/flow:critique-plan` run
auditing that plan reported resolving **zero** reference documents. Cause, verified in both copies:
`flow.config.json.referenceGlob` is the comma-joined `dev-docs/*.md,dev-docs/feedback/*.md`; the
checkout's `extract_session.py` comma-splits it and 1.29.0's does not — so zero matches is the
1.29.0 signature specifically. The reviewer was structurally unable to cite a project rule. It said
so, loaded the docs by hand, and returned 7 real findings anyway. **Had it instead returned a clean
`APPROVED`, the plan would have carried a confident pass from a reviewer that never read the rules**
— the confidence-inverting shape this entry names, occurring inside the PR that documents it.

**Why the fix is a report and not "always run from the working tree."** That reads as the obvious
answer and it is wrong as a blanket rule. Comparing against an installed tree is the *only* way to
observe a packaging/loading bug — this branch found **5 skills and 1 agent** that exist in the
checkout and are not registered at all, which is unobservable by construction if you bypass
installation. It would also make `/flow:ship` grade its own homework, and a branch that breaks ship
could not ship itself. A *stable* reviewer is partly a feature. So: make the version explicit and
visible; do not force a resolution order.

**Also corrected:** "the natural home for an installed-vs-repo version check" is not only
`/flow:doctor`. The check belongs where the *claim* is made — the PR body — because that is where a
reviewer forms the belief that a gate ran.
