## 2026-10-04 — An explicit `**Visual-walk:** N/A` no longer forces `visual_significant` TRUE
**Branch:** conductor/fix-visual-walk-na-forces-significance · **SHA:** 9beb5c4…HEAD · **v1.62.0** · **FB-0132**

**What was done:**

`visual-significance.py`'s Visual-walk override no longer keys on `block_count >= 1`. A new
`heading_declares_na()` plus a shared `declared_na` field in `walk_extract.py` distinguish a block
that *declares there is no visual surface* from one that merely exists; `visual-significance.py` and
`/flow:verify-build` §5a both read that one field. `plan-discipline` publishes the authoring
convention for the first time. Causes 2 and 3 of the original report are recorded, not fixed.

**Why:**

The override read the *presence* of a heading and never its contents, so
`**Visual-walk:** N/A — no UI in this change` set `visual_significant: true` and `/flow:ship` §7a then
demanded a rendered walkthrough and a visual-history entry for a diff with no UI — artifacts that
cannot be produced. Omitting the block entirely gave the right verdict. The predicate rewarded
careless authoring and punished careful authoring, which is the finding in one sentence.

**Tradeoffs and decisions:**

- **Rejected the roadmap's option (a) — "treat any zero-assertion block as non-forcing" — and
  recorded why, so nobody simplifies back to it.** Its premise is that a block with no checkboxes
  declares nothing to capture; `verify-build/SKILL.md` §5a says the opposite verbatim ("0 assertions
  in a present block → capture the primary/launch state only"). Taking (a) literally would have
  retired a documented behaviour by reinterpreting it rather than by deciding to remove it. The error
  polarity settles it independently: a false *force* costs a waivable manifest entry, a false
  *non-force* ships a UI surface with zero frames and a green gate.
- **Rejected option (b) — a new `**Visual surface:** none` field — because reading the denial the
  author already writes gets (b)'s "declared, not inferred" virtue without a second spelling of the
  same fact**, and without leaving every existing `N/A` heading still forcing.
- **A bare 0-assertion block deliberately still forces**, and that is pinned in the failing direction
  so a later "simplification" cannot land silently. Confidence on this stayed **MEDIUM** and the
  measurement sharpened rather than resolved it: the bare-empty shape has **zero instances** in
  `plan.md`'s entire history, so §5a's contract documents an intent no author has exercised in either
  direction. The decision is therefore inert today; it matters on the day someone writes one, and that
  first instance is the evidence for revisiting.
- **The §5a half was wired on the orchestrator's call**, reusing the same field rather than a second
  matcher — the two surfaces are documented as keying on one lifecycle predicate, and leaving them
  split is the FB-0085 shape.

**The guard took three versions, and the sequence is the useful part:**

1. `(?![A-Za-z0-9])` — accepts whitespace, so `None yet, will fill in` matched and would have
   **suppressed**. Caught by `/simplify`'s altitude lens, which also named the gap in my reasoning: I
   had argued the match "fails safe" because a *miss* keeps forcing, which is true and says nothing
   about a *false match* — and a false match in a suppression predicate is the dangerous direction.
2. Require a separator. **Shipped believing it fixed the class; it only moved the boundary.** A
   deferral is spelled with separators too, so `None, will fill in later`,
   `N/A - to be filled in at Step 8`, `NA: pending the prototype`, `None (TBD)` and
   `none. TODO before the gate` all still matched. `None yet, will fill in` was rejected only because
   the word `yet` happened to sit between `None` and the comma. Caught by `/flow:staff-review`.
3. Reject on the **un-denial** itself. A deferral says *when*; a redirection (`N/A, see the prototype
   for frames`) says *elsewhere*; both assert a visual surface exists. Deliberately not keyed on the
   word "visual", since `N/A — nothing visual` is a genuine denial.

**The lesson I'd carry forward over the regex:** an accept/reject table pins the shapes its author
thought of, not the class. Mine had 22 rows and still admitted five deferral spellings. What found
them was a reviewer asked specifically to *find a shape the table misses* — a different instruction
from "review this".

**Verification:**

- 28-row accept/reject table on the predicate; four paired end-to-end cases (N/A + zero assertions
  doesn't force · N/A + assertions still forces · bare empty still forces · an N/A declaration cannot
  mask a real render delta).
- Nine mutations red, each on the assertion meant to catch it — including reverting to option (a),
  dropping the zero-assertion guard, removing the `^` anchor, and removing the trailing boundary.
- 137/137 `run_walk_extract_evals.py` · 62/62 `run_visual_significance_evals.py` · 43/43 harnesses
  green **by exit code** (`tools/eval-sweep.sh`, not a last-line grep — see FB-0131).

**Recorded, not fixed (per the dispatch):**

Cause 2 (the N/A line sat above #171's own `Spec-walk`, so `co_located` read `true` for a different
PR's section) against `walk_extract.py`'s KNOWN-LIMITATION 2 and the per-PR boundary-marker roadmap
entry. Cause 3 (nothing demoted the merged blocks) in the field manual's § 2a. Both with the observed
version, per § 9. In both cases the N/A fix **narrowed** the blast radius without closing the
limitation: a retained block carrying real *assertions* still leaks them.

Two further findings routed to roadmap § Next rather than fixed: the identical presence-not-content
defect on **Spec-walk** in `skip-audit-checks.py:783` (where `**Spec-walk:** N/A` makes a truthful "no
Spec-walk" skip read as a lie, while omitting the heading returns LEGITIMATE — and `declared_na` now
arrives at that call site unread), and `**Mode:**`'s parser misreading `**Mode** — tiny` as `other`,
a positive wrong claim reachable by copying `plan-discipline`'s own field-list formatting.
