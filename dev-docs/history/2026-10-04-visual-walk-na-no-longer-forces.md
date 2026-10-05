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

- 55-row accept/reject table on the predicate; four paired end-to-end cases (N/A + zero assertions
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

**The staff-review pass found the guard was still wrong — a third time — and two lenses
found it independently.**

`/flow:ship`'s rigor gate reported `missing`, not stale: the security commits had landed after
the earlier review, so the final tree had never been staff-reviewed. Re-running it was the
prescribed auto-resolution and it was not a formality.

The design-engineer and push-further lenses separately reported that `_UNDENIAL_RE` **does not
contain the word `deferred`** — the word whose dictionary definition *is* the class the guard is
named after. Measured: `N/A — deferred`, `N/A — next PR`, `N/A — punted`, `N/A — awaiting design`,
`N/A — blocked on the design review`, `N/A — in progress`, `N/A — see Figma`,
`N/A — mockups attached` all SUPPRESSED, which is the direction that ships an unseen UI with a
green report. `N/A — deferred to later` was caught only because `later` happened to sit in the
sentence — delete that one word and the identical sentence suppressed. That is v2's failure
verbatim, one vocabulary over.

**Why my own eval could not see it, which is the part worth carrying.** Every reject row in the
table hit a marker the list already contained. So the table had only ever been validated against
its own vocabulary — item 4, an instrument never run against a known positive from *outside* the
set it was built from. And the comment three lines above the regex faults v2 for exactly this
("pinned the three shapes its author happened to write, not the class"). I wrote that sentence
and then reproduced it one abstraction level up, in the same function. The 22 new reject rows
share no token with the pre-fix regex, which is the only kind of row that could have caught it.

The structural reading came from push-further and is now the roadmap entry: three leaks in three
versions is what a **blacklist on the dangerous polarity** looks like. Suppression is the
expensive direction, and the guard implements it as a deny-list, so every phrasing nobody
enumerated defaults to suppress. The fix — require the tail to be positively denial-*shaped* — is
filed with its one measured casualty, deliberately not taken here. Adding tokens treats symptoms;
the entry exists to stop the next person adding more and calling the class closed.

**Four more findings, each a different shape of the same disease:**

1. **My criterion claimed a pairing that did not exist** (staff-engineer). "The removal is SCOPED
   to the `declared_na` branch" was asserted to be paired with "the two inherited branches still
   forward theirs" — and nothing asserted it. Deleting **both** surviving passthroughs left 76/76,
   200/200 and the security test green. Item 3, inside the criterion written to invoke item 3.
   Now pinned by `8k`, red on both halves under the deletion.
2. **§5a's own data source contradicted §5a's prose** (staff-engineer). `extract-visual-states.py`
   emitted "§5a should capture the primary/launch state only" on a declared N/A — and §5a is
   agent-executed from exactly that JSON. The prose said skip; the data said capture. Fixed with
   an opt-in `empty_warning_na` so `extract-criteria.py` is untouched, and paired three ways.
3. **A rejected near-miss was silent** (UX). `N/A for this PR` and `N/A — TBD` produced output
   byte-identical to a bare block, so an author who wrote a denial read back "plan declares a
   Visual-walk block" and then got a demand for a walkthrough they cannot produce — FB-0132's
   symptom intact on every near-miss spelling, and the FB-0082 absent-vs-no collapse. The verdict
   was right; the silence was the defect. New `na_near_miss` returns a *category*, never the
   heading text, and returns None for headings with no denial intent so it cannot accuse
   `native rendering is unchanged` of a failed denial.
4. **The published convention was wider than the predicate** (staff-engineer). `plan-discipline`
   promised any separator-followed denial counts, while `N/A — no frames needed` and
   `N/A — nothing to capture` keep forcing: an artifact noun reads as "these exist somewhere"
   even when negated. Documented explicitly rather than patched, because loosening the regex moves
   toward suppression. The 14 examples are now pinned **both** against the predicate and against
   their own continued presence in the shipped file, so rewording the doc cannot leave the test
   checking strings nobody ships.

**And one I caught by mutating my own new test.** Making `na_near_miss` always return None — the
exact pre-fix silence — reddened 9 checks in the parser suite and left the visual-significance
suite at **76/76**. The classifier was pinned; the thing an author actually sees was not. The claim
is "the author is told", and that claim is made in `visual_signals`. Case `8l` pins it at that
layer, and reddens 6 checks under the same mutation. That is the third time this release that a
test sat one layer below the claim it was written for.

**One process slip worth recording, because it is the FB-0131 lesson in a new disguise.** I ran
`tools/eval-sweep.sh && git commit && git push` as one compound command. The sweep printed
`1 of 43 harnesses RED` — and the push went through anyway, because `&&` chains on the *exit code
of the last command*, and I had put the gate at the front of a chain rather than in front of a
decision. v1.57.0's lesson was "read the exit code, not the last line of output"; this is the same
mistake one layer out — I read the exit code and then wrote a command that ignored it. The failure
was two of this round's own new criteria naming bare check labels, which Arm A's pin lint does not
count as a verification artifact (`→ 8h-…` instead of `→ run_visual_significance_evals.py checks
8h-…`). Fixed by repinning the criteria, not by loosening the lint. **A gate belongs in its own
invocation, with the next step conditioned on what it said.**

**A third audit-coverage round, and the gap it names about my own criteria is the useful part.**
Both forcing-arm warnings asserted "this change is therefore treated as visually significant" —
and override detection runs *before* Gate 1, so on a `uiSurface:false` project that sentence sat in
the same JSON as `visual_significant: false` and `override SUPPRESSED by uiSurface=false`. The
signal list contradicted itself. What made it invisible is declared in the criterion that fixes it:
**none of the 25 criteria exercised `uiSurface:false` at all**, so no declared behaviour sent anyone
to the one configuration where the claim is false. The clause now reuses this file's own fail-closed
wording from 60 lines up rather than a second phrasing, and is paired across the config axis in both
branches.

Worth noting how the first attempt failed: I defined the shared clause *between* two arms of the
`if/elif` chain, which silently converted `elif declared_na` into a separate `if` — so an
`all_demoted` block would have evaluated both. Caught by reading the chain back (`grep -nE '^ +(if|elif) '`)
rather than by a test, because no test covers "these branches are mutually exclusive". Hoisted above
the chain, where `uis` is already in scope.

**Round four found a false suppression reachable by moving one word.** The parenthetical strip —
`**Visual-walk** *(UI only)*: N/A`, pre-existing and correct for its purpose — ran *before* the
un-denial search, so a deferral written inside the parenthetical was deleted before it could be
searched for. `**Visual-walk (TBD):** N/A` suppressed the override **silently**: no near-miss
warning, and not a demoted qualifier either, so no path reported it. Five spellings measured, all
suppressing. This is the fourth distinct leak in the same guard, and the third in this release —
which is itself the strongest argument for the polarity inversion already filed, since each one has
been a different way for unenumerated input to reach "suppress" by default.

The fix separates the two tails: the denial token anchors on the stripped tail (that strip is why
the token is findable at all), while the un-denial searches the full one. Paired three ways,
because "reject every parenthetical" would satisfy the obvious two assertions by breaking the
feature the strip exists for.

**The re-review the stale rigor marker forced was worth it, and the two lenses converged.**
`/flow:audit-skips` reported `staff-review: SHOULD-RE-RUN` — the marker predated three commits of
real logic. Re-running all four lenses on the final tree found, among other things, that the
near-miss warning I had just added to *end* a silence was **asserting something false**: its
`redirects` explanation said "it also points at visual artifacts kept ELSEWHERE" for
`N/A — no screenshots in this change`, which is the opposite of what the author wrote — and is one
of the three phrasings `plan-discipline` itself flags as the counter-intuitive ones people reach
for. Before this release the near miss was silent, which was worse but at least not *wrong*; naming
a category without naming the mechanism traded silence for a false imputation on the likeliest
spelling. That is the same defect as the outcome clause two commits earlier, which is twice in one
release that a signal I added to improve honesty asserted a falsehood.

**Both the UX and push-further lenses independently flagged the same consumer-facing overclaim**,
which is the strongest signal in the pass: `plan-discipline` closed with "so a near miss is never
silent." Measured by two lenses separately, one pass each: **22 of 29** hand-written denial
phrasings suppress *silently* — `postponed`, `waiting on design`, `tracked in #200`,
`storybook covers it`, and nine lemma-siblings of words already in the lists (`waiting on` vs the
listed `awaiting`; `forthcoming` vs `coming`; `second pass` vs `next pass`). The universal was true
only over the marker vocabulary, in the one artifact that ships to consumers and shapes their
authoring. It is now scoped to what a word list can do, and says plainly that it is a word list and
not an understanding.

**I did not add those tokens, and that was the harder call.** It is the fifth vocabulary round; the
file's own comment forbids it, both lenses recommended against it, and a fifth round buys another
release of false confidence. The measured leak set is filed instead, together with the instrument
that would have caught it — a held-out-vocabulary corpus asserted in the **leak** direction, which
goes red the moment the polarity inversion lands and forces re-classification rather than silent
carry. Push-further's observation is the one to keep: relative to the *current* regex the 39-row
reject table now has **zero** rows drawn from outside its own vocabulary, so it is back in exactly
the state its own comment diagnoses for v2 and v3. Hence FB-0136.

**Also found: a markdown bug I introduced.** The convention body sat at column 0 inside numbered
item 8, which terminates an ordered list in CommonMark — so the body rendered detached from its own
number while four places pointed readers at "field 8". Hoisted to its own section (field 8 keeps its
number, because the spike/tiny overrides key on field numbers), taking it from 66% of the skill to
9%. All four pointers re-aimed.

**The staff-engineer lens returned no blocker and verified far more than it flagged** — chain
integrity after my botched first attempt, exact mutation counts (10 and 2, not "about"), the
fan-out sweep, and branch exclusivity brute-forced over **736 shapes with 0 divergences**. Its
most useful observation is a property I had not noticed: because a false rejection requires the
token to match *and* an un-denial to be found, every new false rejection the parenthetical fix can
produce is also **explained** — never the silent shape. That is the right invariant and it was
luck, not design, so it is now asserted.

Its three real findings were all the same lesson pointed at me:

1. **A silent fail-open in a `sensitivePaths` gate.** With `walk_extract` unimportable, a plan
   declaring `**Visual-walk:**` with an assertion returned `false`, exit 0, **zero signals** — "I
   could not look" rendered identically to "I looked and found nothing". Item 1 verbatim. The
   asymmetry was self-documenting: the `file_patterns` import *five lines below* already captures
   its exception and fails CLOSED, with a comment giving this exact reason. Nobody noticed because
   both are `# pragma: no cover` defensive blocks. Made loud here; fail-closed filed, because it
   changes the verdict a broken install produces.
2. **The round-4 fix was pinned one layer below its claim** — 10 parser checks against a changelog
   sentence making a *gate* claim; reverting it left the composed suite at 102/102. The `8l` block
   I wrote two rounds earlier exists to apply exactly that corollary, and I did not apply it to the
   next round's fix. Third time this release.
3. **"These branches are mutually exclusive" was an invariant nothing asserted** — and my botched
   first attempt at the `uiSurface` fix had already broken it once, caught by reading the chain
   back rather than by a test. Now asserted at the parser layer over every pinned row × 8
   qualifiers, paired with a corpus-size check so a reorder fails loudly rather than going vacuous.

**A process error of mine it also caught, worth recording.** I began applying the other three
lenses' fixes while this one was still reading, so the tree moved under it mid-review — and it was
running `cp`-based mutation experiments in that same tree. It flagged this itself, said it could
not *prove* it had clobbered nothing, and hashed its backups against HEAD to bound the risk. I
verified afterwards that all seven of my edits survived and that the three engine files parse, and
the suite is green — but the correct sequencing is to collect all four lens reports *before*
editing, and I will not get a second warning that clearly.

**Verification (final):** 344/344 `run_walk_extract_evals.py` · 110/110
`run_visual_significance_evals.py` · 8/8 `test_plan_text_not_quoted.py` · 6/6 security test files ·
43/43 harnesses green **by exit code** (1m17s measured). Six mutations run on the new surface,
each red on the assertion meant to catch it and no other: restoring the warnings passthrough
(8h + the composed security test), re-keying the count on the warning total (8j only), deleting
both inherited passthroughs (8k only), silencing `na_near_miss` (8l + the parser rows), and making
the outcome clause unconditional again (8n's two `uiSurface:false` arms only), and reverting the
un-denial search to the stripped tail (10 checks, all in the parenthetical test).
