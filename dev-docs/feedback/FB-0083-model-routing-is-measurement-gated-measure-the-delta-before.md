### FB-0083: Model routing is measurement-gated — measure the delta before swapping any subagent off Opus
**Date:** 2026-07-08
**Source:** user direction

**What was said:** Asked how aggressive the first model-routing PR should be, the user declined to pick a routing map and instead asked for a way to *measure* the difference (output quality + token usage) between a delegated model and a baseline — "inclined to be more conservative and stay on Opus and try Sonnet for some things, not moving immediately to Haiku," plus interest in "some sort of randomized or programmatic way to compare a delegated model to Sonnet as I work to get more samples."

**Synthesized rule:** Do not route any subagent off the default (Opus) on the strength of a benchmark or a cost argument. Build the measurement first: per-subagent token attribution, an offline Opus-vs-Sonnet A/B over the reviewer fixtures (finding-overlap + FP-rate + token cost), and a randomized/shadow sampler that accumulates paired samples over real use. Opus stays the default; Sonnet is the only challenger; Haiku is not on the table yet. `plan-critic` + the lens agents stay on Opus regardless until data clears the bar (FB-0013 same-model critic collusion). Every routing decision cites measured data, never a swap on faith. This is PR P's auditor-only, measurement-first discipline generalized to the whole subagent fleet (roadmap § Next "M — Model-measurement harness").

**Applies to:** model selection, subagent orchestration, roadmap item M, PR P
