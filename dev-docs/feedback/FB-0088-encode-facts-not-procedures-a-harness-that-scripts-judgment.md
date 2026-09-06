### FB-0088 — Encode facts, not procedures: a harness that scripts judgment becomes a ceiling as models improve

**Date:** 2026-08-23
**Source type:** user direction

**What was said.** While specifying the artifacts for a Conductor-orchestrator design, the user set a standing constraint: *"we need to watch for bloat, especially as it relates to building things that get in the way of or inhibit natural model capabilities as the models get better. This should be as lightweight as possible while still enforcing the workflow, but we need to be careful not to lose functionality because we're building too heavy."*

**Synthesized rule.** When deciding whether a piece of harness earns its place, ask which of two things it encodes. **A fact the model cannot know** — what is in flight, who owns which paths, what the human decided, which version is installed — *compounds* as models improve: a better model does more with an accurate ledger. **A procedure the model could derive** — a triage decision tree, a scripted review order, a wrapper restating what a bundled skill already does — *decays*: it is written against today's model, and every capability gain makes it more ceiling and less floor. Prefer the first; delete the second.

**Corollary (a) — enforce mechanically only what must not drift, and keep that list short.** For flow that is the two human gates and the artifact-existence checks (FB-0062's "a verdict without its artifact is a skip"). Everything else is prose, which a better model handles better than a rule would.

**Corollary (b) — every artifact carries a deletion criterion**, stated when it is created: the condition under which it stops earning its keep. The failure mode is not adding the wrong thing once; it is never removing the right thing later. **FB-0077 is the precedent** — a check outlived the feature it protected and stayed green over its absence for four releases, and nobody had written down when it should have been retired.

**Applies to:** any new `/flow:*` skill, rule, or eval; CLAUDE.md's F11 "never re-implement a bundled skill; compose instead" (this is F11's motivation generalized past bundled skills); `research/2026-08-22-conductor-orchestration.md` §9 "Deliberately not built". Related: FB-0056 (drop a skill whose delta over a bundled one is null), FB-0077 (a check that outlived its feature), FB-0010 (fan-out — a duplicated contract is a procedure encoded twice).
