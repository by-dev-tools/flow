## 2026-09-26 — Hand-harvest the lesson-contribution queue; `flowRepoPath` was unset, so the drain was disabled, not empty

**Branch:** `conductor/contribute-drain-flowrepopath-fb-0118-0121` · **SHA:** [this commit] · **Mode:**
docs-only (orchestrator closeout task 2 of 2, run separately from #161 — different review shape)

**What was done (user-facing: none — dev-side config + feedback corpus only).**

1. **Set `flow.config.json.flowRepoPath` to `/home/vercel-sandbox/flow`.** It was unset, and per its
   own schema ("Unset disables the contribute drain") that meant `/flow:contribute` had never once been
   runnable in this repo — not silently broken, but silently *off*, indistinguishable from "checked and
   found nothing" to anyone who didn't read the guard condition. Re-ran the run-from-checkout guard after
   setting it: `pwd -P` matches `flowRepoPath` exactly, and `contribution_store.py list` still returns
   `[]` — confirmed the queue is genuinely empty now that the drain can run, not disabled.
2. **Hand-wrote five FB entries (FB-0118 through FB-0121, plus this history entry for the fifth)** —
   the lessons that were sitting in this program's transcripts, uncaptured, because the automated Step 4c
   → `/flow:contribute` path was never reachable end-to-end (harvest enqueues to user-scope storage
   regardless of `flowRepoPath`; the *drain* is what was gated). Same shape as [[FB-0111]], the first time
   this exact failure happened.
3. **Did not implement any of the three promotion candidates** (FB-0118, FB-0119, FB-0120 each name a
   specific shipped-surface edit). Each is its own review shape — bundling three prompt/rule edits into
   a lessons-harvest PR is the fan-out risk `.claude/rules/general.md` § Consistency item 2 exists to
   prevent. Filed as named candidates for a future PR to pick up.

**Why.** The orchestrator dispatched this as a closeout task believing `/flow:contribute` would simply
find nothing. It found nothing — but for the wrong reason: the mechanism was off, not empty. Setting
`flowRepoPath` and re-checking is what turns "disabled" and "empty" into distinguishable states, which
is the actual finding worth recording.

**The fourth lesson (recorded here only — already fully stated in [[FB-0115]], no new FB number
needed).** [[FB-0115]]'s own "Two corollaries the execution added" already carries it verbatim: *"A
drop-rule that names only the headline metric will delete the wrong things."* The rule that PR ran
under — "if a change does not move recall, drop it" — deleted a validated instrument (a deterministic
hunk inventory) whose recall contribution was 0 **because it worked**: it found the missed behaviors and
a downstream matcher dismissed them, relocating the bottleneck rather than hiding it. A headline metric
cannot see that relocation; only the enumeration-vs-match split (also from FB-0115) makes it visible. No
promotion candidate here — the corollary already lives in the FB entry that is its natural home, and
duplicating it into a sixth file would itself be the fan-out FB-0010 warns about.

**Meta-finding — this is the second time, not the first.** [[FB-0111]] hand-harvested four lessons under
the identical circumstance seven business days ago (2026-09-16): a pre-archive check found the queue
directory and watermark both absent, proving Step 4c had never executed, and the lessons were rescued
from a chat transcript one archive away from deletion. That incident's root cause was different from this
one — an operator skip of ship Steps 3-5, not a config slot — but the *symptom* is identical both times:
an automated pipeline that is supposed to compound quality across sessions produced **zero** automated
contributions across this program's entire run, in two separate ways, and neither was caught by anything
except a human-initiated audit. Twice is a pattern, not a coincidence. Whatever the specific fix in each
case, the loop's own **observability** is the standing defect: silent-off and silent-empty read
identically, and nothing in `/flow:ship`'s Step 4c nudge or `/flow:contribute`'s guard currently
distinguishes them for anyone who isn't manually checking `flowRepoPath` and the watermark file. Not
fixed in this PR (docs-only scope); named here so it isn't lost a third time.

**Design decisions.**
- **flowRepoPath is a machine-local value baked into a repo-shared config file, and that tension is
  flagged in `flow.config.json` itself (a `$comment-flowRepoPath` block), not silently resolved.** The
  value set here (`/home/vercel-sandbox/flow`) is correct for this Conductor cloud-sandbox convention but
  will be wrong on any local clone (e.g. a Mac dev checkout) until that machine sets its own. No env-var
  override exists today; noted as a possible future fix, not built here (out of scope for a docs-only
  closeout task).
- **Five lessons stated as candidates, not applied.** Every one of FB-0118/0119/0120 names an exact
  target file and edit; none is executed in this PR. This mirrors FB-0111's own precedent exactly — the
  hand-harvest's job is to preserve the lesson before it's lost, not to also ship the fix under a
  different gate's cover.

**Tradeoffs discussed.**
- Considered writing all three promotions directly into this PR to close the loop fully. Rejected: the
  human explicitly separated this from #161 for review-shape reasons, and stacking three shipped-surface
  prompt/rule edits behind a "just draining the queue" PR title is exactly the kind of scope-creep this
  repo's Scope discipline rule forbids ("do what was asked... new scope discovered mid-execution: surface
  to the user, don't silently absorb").

**Lessons learned.**
- An "unset ⇒ disabled" config slot with no consumer-visible signal at drain time is a silent-skip in the
  FB-0010 sense, even though its own doctor check (2.8) correctly reports it as `[PASS]` — PASS is the
  right verdict for a *consumer* project where flow-contribution is optional, but flow's own repo is the
  one place the slot is not optional, and doctor has no way to know that distinction from the slot value
  alone.
- See [[FB-0118]], [[FB-0119]], [[FB-0120]], [[FB-0121]] for the individually-synthesized rules; see the
  meta-finding above for the standing observability gap this PR does not close.
