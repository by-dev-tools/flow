## 2026-09-27 — Fix 11 stale version claims from #158's title, find a second independent instance on #84, add a mechanical check (FB-0123)

**Branch:** `conductor/version-provenance-check` · **SHA:** [this commit] · **Mode:** docs hygiene
(dev-docs + dev-side CI only — no plugin artifact touched)

**What was done.** `plugins/flow/.claude-plugin/plugin.json` is v1.50.0 on `main`. #158 (D1 Phase
2) shipped as v1.48.0, but its PR title (never corrected after two other PRs landed first and
took v1.45.0/v1.47.0 while it sat at review) still read v1.46.0. Swept `dev-docs/` with
`git grep -nE 'v1\.4[5-9]\.[0-9]|v1\.5[0-9]\.[0-9]'` — **112 raw matches repo-wide, 85 in
dev-docs** — and checked every survivor against `plugin.json`'s history at each PR's merge
commit rather than against any PR title. Found **9 wrong claims in `dev-docs/roadmap.md`** (lines
142, 165, 197, 201, 216, 217, 224, 234, 244 — three more than the five the dispatching orchestrator
had already spotted by hand) and **2 in `dev-docs/handoffs/d1-prototype-first-gate.md`** (lines
133, 187), all saying v1.46.0 for work that shipped as v1.48.0. Fixed all 11 to v1.48.0; left five
genuinely-historical v1.46.0 mentions in `plan.md`/`roadmap.md:18` untouched (they narrate the
re-sweep process that produced the wrong claim in the first place, and are correct as history).

**A second, independent instance of the identical class, found while building the ground-truth
map from git history rather than from the human's list:** #84 opened as "v1.22.0" and shipped as
v1.24.0; `roadmap.md`'s D1 table (`(v1.22.0, #84)`) had copied the stale title number. Fixed to
v1.24.0. Same shape, unrelated PR, five months apart — two occurrences is what justified the FB
entry over a one-off fix.

**Added `dev-docs/check-version-provenance.py`, wired into `.github/workflows/ci.yml` as a new
`version-provenance` job** (dev-side lane, not a shipped `/flow:*` surface — same three-surface
boundary as `dev-docs/check-index.py`'s `dev-docs` job). Builds a PR→version ground-truth map by
walking the full git history of `plugin.json` (extracting each commit's `(#NNN)` squash-merge
suffix and the version the file held at that commit), then scans `roadmap.md`, `handoffs/*.md`,
and `plan.md`'s living "Current Focus" prefix (everything before the first `## PR —` heading) for
`vX.Y.Z (#NNN ...)`-shaped claims and flags any that contradict the ground truth. Two assertions
per `.claude/rules/general.md` item 3: the negative (no contradiction) is paired with a positive
(at least 5 pairings must be found), so the check cannot go green by every version claim being
deleted from the corpus. A `--selftest` mode (item 4 — never trust a check that has only ever
returned clean) pins the pairing engine against five synthetic fixtures, including the exact
shapes that produced false positives while building this: a dense "Recently shipped" list line,
an incidental cross-reference to a different PR mentioned inside a long descriptive paragraph, an
unbalanced-paren code span, and an external `repo#NNN` citation.

**Why.** The orchestrator told Ben the wrong version reading #158's title, and a second worker's
dispatch inherited the same wrong number from `roadmap.md` and had to self-correct — by that
worker's count, the third time in this program the number has been off by a release or two. A
one-time grep-and-fix closes the found instances; it does nothing about the next PR whose title
goes stale on a rebase. The mechanical check is what makes the fix durable rather than a one-time
cleanup that silently rots the same way `roadmap.md:11` already had eleven lines away from its
own correct line.

**Design decisions.**
- **PR-number-attached claims only, not every version mention.** `.claude/rules/general.md`
  item 3 requires a paired positive, and "every `vX.Y.Z` in dev-docs" would make the positive
  vacuous (thousands of unrelated mentions). Scoping to claims that name a specific PR is also
  the only scope this check *can* verify — a bare "v1.49.0 added X" with no PR number is a
  description, not a checkable claim. This deliberately means the check does **not** catch
  phase-name-keyed claims like "Phase 2 shipped (v1.46.0 — ...)" that never wrote `#158` on the
  same line (9 of the 11 fixed instances were exactly this shape) — those still need a human
  sweep. The orchestrator's own framing ("a version claim ATTACHED TO A PR NUMBER") already
  scoped the mechanical half this narrowly; the wider sweep is what a human grep is for.
- **Scan scope excludes `dev-docs/history/*.md` and `plan.md`'s retained shipped-PR blocks.**
  Both are point-in-time records kept as the record (per `CLAUDE.md`'s own "history/ — not
  maintained" framing); a since-corrected claim re-told inside one, narrating how the correction
  happened, is intentional (see `plan.md`'s own "one known stale survivor, deliberately not
  edited" note at the v1.48.0 re-sweep). The first draft scanned the whole corpus and produced
  dozens of false positives from exactly this shape — narrating a PAST wrong claim as part of
  explaining a correction is not the same defect as a PRESENT wrong claim nobody has noticed.
- **Paren-span matching, not distance/nearest-token heuristics.** Three heuristics were tried
  and discarded, each defeated by a different real shape in this corpus: nearest-by-absolute-
  distance mispaired PRs with the NEXT list item's version on dense "vA (...; #N). vB (...; #M)."
  lines; nearest-preceding-only then broke the reverse "(#N, vX)" order; bidirectional-nearest
  reintroduced the first failure on a different line shape. The version that held: find each
  `vX.Y.Z(`'s own matching close-paren by depth-counting (capped at 1500 chars so a genuinely
  unbalanced paren elsewhere in the prose can't create a runaway span — measured: one did,
  swallowing 147,927 chars and six unrelated PR numbers before the cap was added), then pair a
  span with only the FIRST PR number near its own open paren — every other PR mentioned deeper in
  a long paragraph's prose is an incidental cross-reference (e.g. a v1.49.0 entry citing "#159's
  recorded 0-of-5" while describing a different, earlier PR's history), not a new claim.
  A small supplementary regex catches the one shape the span engine structurally can't
  ("(v1.22.0, #84)" — paren opens before the version, not after) — the exact shape the #84 bug
  itself took, so it earned its own explicit pattern rather than a generalization risking the
  same false-positive class the span engine was hardened against.
- **`fetch-depth: 0` on a new, separate CI job rather than editing the existing `dev-docs`
  job's checkout.** The ground-truth walk needs full history; the existing `dev-docs index`
  check does not, and its job name is referenced by name in `dev-docs/README.md` and is a likely
  branch-protection required-check — widening its checkout as a side effect of an unrelated
  check risked a name/identity change neither reviewable nor revertible from this branch. A new
  job (`version-provenance`) is strictly additive.

**Tradeoffs discussed.**
- Considered scanning `dev-docs/history/*.md` too, since a wrong number there is still wrong.
  Rejected: those entries are declared not-maintained by design, and the false-positive rate from
  "correctly narrating a past mistake" vastly outweighs catching the rare case where a history
  entry itself has a live, never-corrected error (none were found in this sweep).
- Considered a distance-only heuristic (rejected three times, see Design decisions) before
  landing on span matching — recorded so a future maintainer doesn't re-try the same three
  discarded shapes from scratch.

**Lessons learned.** See [[FB-0123]] for the synthesized rule. Also: **a check should print its
own construction history as evidence it was adversarially validated**, not just what it currently
asserts — the `--selftest` fixtures direct-quote the exact false positives found while building
this (dense list line, incidental cross-reference, unbalanced paren, external `repo#NNN`), so a
future edit to the pairing engine is guarded against regressing into a shape already proven wrong
once.
