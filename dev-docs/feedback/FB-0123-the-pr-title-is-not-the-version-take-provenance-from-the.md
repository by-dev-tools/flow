# FB-0123 — The PR title is not the version; take provenance from the artifact, not the prose that describes it

- **Date:** 2026-09-27
- **Source type:** user correction (orchestrator, relayed from Ben — a version claim told to Ben
  was wrong, sourced from a PR title rather than the manifest; a second worker's dispatch then
  inherited the same wrong number from the roadmap and had to correct it)

- **What was said:** `plugins/flow/.claude-plugin/plugin.json` is the fact about which version a
  PR shipped under. A PR's *title* is written when the PR opens and is never mechanically
  re-synced — #158 opened as "v1.46.0", two other PRs (#157, #159) landed first and claimed
  v1.45.0/v1.47.0 while #158 sat at review, so #158 actually merged at **v1.48.0** with a title
  still reading v1.46.0. Nine dev-docs sites in `roadmap.md` plus two in
  `dev-docs/handoffs/d1-prototype-first-gate.md` copied the stale title number instead of reading
  the manifest — one file contradicting itself eleven lines apart (`roadmap.md:11` correctly said
  v1.48.0; ten lines later the same file said v1.46.0 for the identical PR). Cost, recorded
  because it's the justification: the orchestrator told Ben the wrong version reading #158's
  title, and by a second worker's count this is the **third** time the number has been off by a
  release or two in this program.

  Independently, this rule's own construction found a **second, unrelated instance of the
  identical class**: #84 opened as "v1.22.0" and shipped as **v1.24.0**; `roadmap.md`'s D1
  roadmap table copied the stale v1.22.0. Two separate PRs, two separate sessions, same failure
  shape — a title read as a fact instead of a claim.

- **Synthesized rule:** **take a version claim from the artifact that defines it, never from
  prose that describes it.** A PR title, a chat message, a prior roadmap line, or a squash-merge
  commit subject (which GitHub derives FROM the title, so it inherits the same staleness — #158's
  merge commit subject *also* reads "v1.46.0", immutably, because it's what the title said at
  merge time) are all **descriptions**, not the fact. `plugins/flow/.claude-plugin/plugin.json`
  at a commit is the only place "what version did this ship under" is authoritative. This is the
  same shape as `.claude/rules/general.md` item 4's corollary "pin a claim at the layer where it
  is claimed" — one layer further out: that corollary is about a criterion verified at the wrong
  *code* layer; this is about a claim sourced from the wrong *provenance* layer. Both fail the
  same way — a green-looking claim that never touched the thing it claims to be about.

- **Applies to:** any dev-docs prose (`roadmap.md`, `plan.md`'s living "Current Focus",
  `dev-docs/handoffs/*.md`) that cites `vX.Y.Z (#NNN — ...)`. Mechanized in
  `dev-docs/check-version-provenance.py` (new dev-side CI job `version-provenance`,
  `.github/workflows/ci.yml`): derives a PR→version ground-truth map from the full git history of
  `plugin.json`, flags any dev-docs claim that contradicts it, and refuses to pass on zero
  pairings found (`.claude/rules/general.md` item 3 — a negative check must be paired with the
  positive that the claims it protects are still present, so the check cannot go green by every
  claim being deleted). Not applied to `dev-docs/history/*.md` or `plan.md`'s retained
  shipped-PR blocks — those are point-in-time records kept **as the record**, and a since-
  corrected claim re-told inside one while narrating how the correction happened (see
  `plan.md`'s own "one known stale survivor, deliberately not edited" note) is intentional, not
  drift. Related: [[FB-0107]] (a gate reporting on the wrong artifact is worse than no gate,
  because it manufactures the belief that the check happened — this is that same shape applied
  to a roadmap claim instead of a ship gate).
