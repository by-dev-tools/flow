# FB-0139 — Scope a dispatch to one shippable PR, named as the brief's Outcome

- **Date:** 2026-10-31, corrected same day
- **Source type:** user direction, ahead of a planned change (orchestrator seat); self-corrected by
  the user the same day, before the PR carrying the first version of this entry had merged.

- **What was said:** Ben, ahead of moving the account to a lower usage tier: *"let's focus on
  intelligent and strategic chunking of work so that we can actually ship it and keep making
  incremental progress, rather than always be hitting limits as soon as we start big, large
  projects that end up not getting shipped."* He paired it with an explicit non-concern: 5-hour
  rate-limit stalls are cheap to resume and not worth engineering around; the risk named was a
  weekly limit hitting mid-feature, after which the branch sits unshipped for the rest of the
  window.

- **The correction, same day:** *"I'm not convinced that you can actually identify and predict how
  much you can get done within Claude's weekly limit, so I'm not sure if that's a good guiding
  principle of the work. The concept of chunking to keep shipping consistently is still a good
  workflow to follow though. Can we base it around something we can actually measure and predict
  accurately?"* He's right — the orchestrator has no visibility into weekly-limit consumption, so
  "scope this to fit inside one window" was a rule resting on a number nobody can see. The original
  entry built the right instinct on the wrong instrument.

- **Why this doesn't contradict FB `token-not-time`** (recorded earlier in the same program): that
  entry is about *token spend* — don't ration model choice to save capacity, stalls from a 5-hour
  limit are an accepted cost. This entry is about *shipping cadence* — the failure it targets is a
  feature that never reaches a mergeable state, not the limit itself. Unchanged by the correction.

- **Synthesized rule (corrected):** scope each dispatch to exactly one shippable PR, named in the
  brief's Outcome line — not to a time or token budget, which the orchestrator cannot measure in
  advance. This is auditable *after* the fact (did the dispatch produce the one PR it named, or did
  scope grow and need a split?) without requiring any prediction *before* it. A large feature still
  gets built — split it into sequential PRs that each stand alone and ship, the way this program's
  own mobile-review work already did (hand-off honesty + PR images as one PR, the preview-link
  adapter as a second, the touch-profile annotation layer as a third) — and `general.md`'s existing
  "surface new scope, don't silently absorb it" rule is the mechanism for keeping a dispatch from
  growing past what it named.

- **How to apply:** at dispatch time, name the one shippable outcome in the brief's Outcome line,
  not just the overall goal. If a worker reports mid-flight that real scope exists beyond what was
  asked, that is the rule working — route it to a follow-up dispatch rather than fold it in. Don't
  justify a split by estimating how much time or usage it would take; justify it by whether the
  piece being split off is a complete, shippable unit on its own.
