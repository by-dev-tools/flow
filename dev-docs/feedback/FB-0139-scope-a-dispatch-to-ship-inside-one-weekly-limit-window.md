# FB-0139 — Scope a dispatch to ship inside one weekly-limit window, not to span one

- **Date:** 2026-10-31
- **Source type:** user direction, ahead of a planned change (orchestrator seat).

- **What was said:** Ben, ahead of moving the account to a lower usage tier: *"let's focus on
  intelligent and strategic chunking of work so that we can actually ship it and keep making
  incremental progress, rather than always be hitting limits as soon as we start big, large
  projects that end up not getting shipped."* He paired it with an explicit non-concern: 5-hour
  rate-limit stalls are cheap to resume and not worth engineering around; the risk is a weekly
  limit hitting mid-feature, after which the branch sits unshipped for the rest of the window.

- **Why this doesn't contradict FB "tokens matter, lost time doesn't"** (`token-not-time`,
  recorded earlier in the same program): that entry is about *token spend* — don't ration model
  choice to save capacity, stalls from a 5-hour limit are an accepted cost. This entry is about
  *shipping cadence* — the failure it targets isn't the limit itself, it's a feature that never
  reaches a mergeable state before one. The two entries bound the same practice from different
  sides: don't economize on quality to save tokens, and don't let scope drift into something that
  can't land before the account's slowest-resetting ceiling.

- **Synthesized rule:** when scoping a dispatch, prefer a shape where the worker can realistically
  reach plan → build → PR inside roughly one weekly-limit window over a multi-week feature that
  stays unshipped the whole time it's in flight. A large feature still gets built — split it into
  sequential PRs that each stand alone and ship, the way this program's own mobile-review work
  already did (hand-off honesty + PR images as one PR, the preview-link adapter as a second, the
  touch-profile annotation layer as a third), rather than one branch accumulating everything before
  opening a PR.

- **How to apply:** at dispatch time, name the shippable unit in the brief's Outcome line, not just
  the overall goal. If a request is naturally larger than that, say so when writing the plan and
  propose the split rather than silently building the whole thing on one branch. This is a
  dispatch-shaping habit, not new infrastructure — don't build a scheduling system to enforce it.
