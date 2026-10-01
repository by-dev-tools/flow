# FB-0125 — A number swept at plan time is stale by ship time; sweep unmerged branches, and sweep again at ship

- **Date:** 2026-09-29
- **Source type:** user correction (orchestrator, at the plan-approval message: *"Two numbers to
  fix before you ship… Take the next free FB and version at ship time, after rebasing, and
  **re-sweep them rather than trusting this message — they will have moved again**."*)

- **What was said:** the version and feedback-ID claims written into a plan are correct when the
  plan is written and wrong when it ships, because concurrent branches claim in the gap. Do not
  trust the plan's claim, and do not trust the dispatch that corrects it either. Re-derive both
  at ship time, after rebasing.

- **Why:** measured on this PR, over one plan gate. At plan time I swept and claimed **FB-0123 /
  v1.51.0**, correctly: FB-0122 was taken by an in-flight branch and v1.51.0 was free. By the time
  the plan was approved, FB-0123 had been taken by #167 and v1.51.0 by S0's branch; the
  orchestrator's own correcting message said *"#166 is v1.52.0 and S0 is taking v1.53.0"* — and by
  ship time `main` was at **v1.52.0** and the free numbers were **FB-0125 / v1.54.0**. Three
  sweeps, three different answers, across roughly two days. The dispatch that told me the numbers
  had moved was itself stale by the time I acted on it, which is exactly why it told me not to
  trust it.

  This is adjacent to [[FB-0123]] and **not the same rule**, and the distinction decides the fix.
  FB-0123 is about a number's *source*: take the version from `plugin.json`, never from a PR title
  or the prose describing it. This is about a number's *freshness*: a claim read from the correct
  source is still wrong if it was read at the wrong time. FB-0123's fix is "read the right file";
  this one's is "read it again, later." A repo doing FB-0123 perfectly still collides here.

- **How to apply:**
  1. **Sweep `main` AND every unmerged remote branch.** `main`'s high-water is the floor, not the
     answer — every collision in this program has been with work that had not merged yet. The
     sweep that actually answers the question is over `git branch -r`:
     ```sh
     for b in $(git branch -r --format='%(refname:short)' | grep -v HEAD); do
       git show "$b:plugins/flow/.claude-plugin/plugin.json" 2>/dev/null \
         | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"])' 2>/dev/null
       git ls-tree --name-only "$b" dev-docs/feedback/ 2>/dev/null | grep -oE 'FB-[0-9]{4}'
     done | sort -uV
     ```
  2. **Claim at ship time, after the rebase — not at plan time.** Writing a number into a plan is
     fine as a working placeholder; treating it as claimed is what breaks. The claim is the pushed
     file, so make the sweep the step immediately before the push.
  3. **Re-sweep even when someone just told you the numbers.** A relayed number has the same
     staleness as a planned one, plus a relay delay. The orchestrator was right to say so about
     its own message.
  4. **Expect a gap and skip into it rather than backfilling.** This PR takes v1.54.0 over a
     `main` at v1.52.0 because S0 holds v1.53.0 unmerged. Stepping over a claimed-but-unmerged
     number is correct; renumbering to close the gap would collide with a branch that already
     wrote the file.

- **Related:** [[FB-0123]] (the number's source, not its freshness), [[FB-0008]] and [[FB-0051]]
  (the stale-base gate — the same "another branch moved under you" class, one layer up),
  [[FB-0010]] (fan-out: one contract value, N files).
