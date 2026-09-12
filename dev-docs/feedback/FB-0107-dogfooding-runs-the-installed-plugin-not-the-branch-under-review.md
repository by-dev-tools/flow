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
