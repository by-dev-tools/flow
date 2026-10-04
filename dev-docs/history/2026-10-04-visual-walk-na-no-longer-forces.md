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
- Harness totals as of this section: 137 / 62. Both grew after the security review below added
  rows; the authoritative final counts are in that section, not here.

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

**The security review's BLOCKER: the fix routed the happy path onto a prompt-injection carrier.**

The new `declared_na` branch was written the way its two neighbours already were — append the
decision signal, then forward `blk["warnings"]`. `/flow:security-review` rejected it, and the
argument is the part worth keeping, because the diff looked like it was *following* local precedent:

Pre-diff, a plan declaring `**Visual-walk:** N/A` took the `block_count >= 1` arm, which forwards no
warnings. The passthrough existed only on `co_located is False` and `all_demoted` — both **abnormal**
plan states, where the warning text *is* the operator's remedy ("move the block under the active
heading"). So copying the pattern onto a *terminal correct* reading routed the **happy path** through
a warnings passthrough for the first time. "It matches the neighbouring branches" was true and was
not the same as "it is safe here"; the neighbours earn the quote and this branch does not.

Two carriers, both measured on my own diff before the fix:

- the malformed-checkbox warning interpolates `line.rstrip()[:80]` with **no `!r` escaping**, once
  per bad line with **no cap** — N crafted `- []` lines yield N attacker-chosen 80-char strings;
- the multi-block warning interpolates `{first_heading!r}` **untruncated** — 424 characters from a
  three-times-repeated payload, with `declared_na=True` and `co_located=True`.

Both land in `visual_signals` → `skip-audit-checks.py`'s stdout → the forked **skip-auditor's**
prompt: the gate that adjudicates whether review stages were legitimately skipped. The same sink the
line-number fix earlier in this entry exists to close; I closed the direct quote and opened an
indirect one two lines below it.

Removed rather than sanitised. The one warning carrying a live remedy on this path — "a later block
holds your real assertions and only the first was read" — is now a **count**, keyed on
`block_count > 1`. Not on `len(warnings)`: `declared_na` requires `not items`, so the
empty-assertions warning fires on **every clean N/A forever** (measured: a spotless
`**Visual-walk:** N/A — no UI surface` carries exactly 1 warning), and that warning's own advice
("capture the primary/launch state only") is wrong here because §5a skips. A permanent, misleading
`[WARN]` on the happy path is the same mistake as v1.57.0's permanent-⚠️ hedge, two releases apart.

**The NIT I declined, and why that needed measuring rather than agreeing.** The review proposed
widening `_UNDENIAL_RE` with `add(ed|ing)\b`, `after\b`, `step \d` and `#\d`. Measured first: the
first three reject **four legitimate denials** — `N/A — no UI added`, `nothing added to any rendered
surface`, `no visual change after the refactor`, and `prose change to ship Step 2a` (a real flow PR
shape). "No UI added" is the most natural phrasing of a true N/A, so the widening would have
re-broken this release's own bug on the commonest wording. It would also have bought nothing: three
of the NIT's four motivating deferrals were **already** rejected via `frames`, `prototype` and
`will `. Those four phrasings are now **accept rows** in the eval table, so the next person to
"tighten the guard" sees red instead of silently reverting the fix.

The one genuine gap it found — `N/A — covered by #456`, matched by no shipped token — is pinned as a
known limitation in the *accept* direction and routed to roadmap § Next, not closed. `#\d` cannot
separate "this PR has UI and the walk is over there" (reject) from "the UI landed in #120, so this PR
has none" (accept), and choosing which of a missed walk or a forced walk on a non-visual PR is worse
is a plan-gate judgment, not a parser's.

**The leak eval is pinned at the composed layer, and validates itself by default.**
`evals/security/test_plan_text_not_quoted.py` asserts over the real `skip-audit-checks.py` **stdout**
— where the claim is actually made — rather than over `visual-significance.py` in isolation, per
§ Consistency discipline item 4's "pin a claim at the layer where it is CLAIMED". It mirrors both lib
dirs (the engine resolves its helper as a sibling path, so an in-place mutation would be invisible to
a mutant engine run), patches the passthrough back in, and reports **INCONCLUSIVE** unless both
carriers leak through the mutant. That ran `--selftest`-gated for about a minute before I moved it to
on-by-default: it costs 0.18s, and an instrument validated only when someone remembers a flag is the
author-memory consistency this repo keeps getting bitten by.

It earned that guard immediately. The first version reported a clean pass with a **malformed config**
— `uiFilePatterns` as a list where the engine `re.compile()`s a string — so the engine exited 1 and
the payload was absent from its *empty* stdout, for entirely the wrong reason. The
`::arm-reached` assertion is what turned that into a failure instead of a green tick.

**Two paired assertions agreed with a mutant, and the pairing is what hid it.** The count line is
keyed on `block_count > 1`, and I wrote the comment explaining why `len(warnings)` would be wrong
*before* writing the tests — then the tests failed to catch exactly that. Re-keying the count on
`len(blk["warnings"])` left both new cases green: the clean-N/A case carries 1 warning, so `1 > 1` is
false and no line appears; the two-block case carries exactly 2 warnings, so the **wrong key printed
the right number by coincidence**. Two assertions, both passing, both agreeing with a mutant — the
"pin the DECISION, not a string that currently implies it" corollary, where the string was a numeral.

What separated them is one shape neither case covered: **one** Visual-walk block with **two** parser
warnings (an N/A heading followed by two malformed `- []` lines). Correct code stays silent; the
mutant announces "2 Visual-walk blocks are present" about a plan that has one. That is case 8j, and
it is red under the mutation and green without it. The transferable bit is that the mutation was run
at all — I had the reasoning written down in a comment and still would have shipped a suite that
could not tell the two keys apart, because the numbers coincided on the inputs I happened to pick.

**Verification (final):** 143/143 `run_walk_extract_evals.py` · 73/73
`run_visual_significance_evals.py` · 6/6 security test files · 43/43 harnesses green **by exit code**.
Mutations run on the new surface: restoring the passthrough (red on 8h and on the composed-layer
security test), and re-keying the count on the warning total (red on 8j only).
