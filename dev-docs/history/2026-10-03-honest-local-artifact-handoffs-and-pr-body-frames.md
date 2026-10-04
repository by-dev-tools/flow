## 2026-10-03 — A hand-off that names a local file says so plainly, and the committed frames render in the PR

**Branch:** `conductor/mobile-options-1-3-hand-off-pr-images-preview-url` · **Version:** v1.59.0 · **Roadmap:** D7 · **No new FB**

Mobile options **3 + 2** from `dev-docs/research/2026-10-mobile-workflow.md` § 8 (merged as #175, point-in-time — not edited here). Ben was reviewing from a phone. A gate that hands over a sandbox-local path has not asked anyone to look at anything, and a merge gate that asks a human to look at a picture, then links them to an HTML file's *source*, has not asked them to look at anything either.

Option 1 (`conductor preview set`) is **PR B, held** on Ben's measured answers to research § 6 Q1–Q5. Options 4 and 5 are dispatched to other workers.

### What shipped

One stdlib engine, `plugins/flow/skills/ship/lib/artifact-handoff.py`, with two renderers and a self-test:

- **`local-line`** — the honest sentence for an *uncommitted local* artifact (the verify-build walkthrough; a gate-1 prototype). It states where the file can and cannot be opened and **names no client**.
- **`frames`** — the `## Before / after` PR-body section: a projection of the **commit**, not of the session. It reads the committed `visualHistoryPath` record, requires the newest entry's branch to equal this PR's, and emits a row only for a frame tracked at HEAD.

Four prose call sites in `ship`, `ship-spike` and `prototype` now call it instead of composing strings by hand.

### Why an engine and not four string edits

The research doc costs both options as "a string change", and for option 3 alone that is right. Option 2 is not: it needs repo-visibility resolution, SHA pinning, a committed-asset check, a branch match, and a recon-only fallback. **A hand-composed image URL that is subtly wrong renders in the PR body as a broken image**, which is worse than today's honest absence, and nothing in the pipeline would catch it. A template string can only be pinned by a grep — the FB-0010 "consistency depends on author memory" class this repo keeps paying for.

### The two measurements that decided the design

Taken as a **pair**, because an instrument that can only return one answer is not an instrument (`.claude/rules/general.md` Consistency item 4):

| Probe | Result |
|---|---|
| unauthenticated `raw.githubusercontent.com` fetch of a **public** blob (`by-dev-tools/flow` @ `06c0eeb`, `README.md`) | `http=200`, 11,699 bytes |
| the same shape for a **private** blob (`byamron/health-tracker` @ `c809384`, a committed `.png`) | `http=404`, 14 bytes |

So inline images are a **public-repo-only** mechanism. Flow is public; a `uiSurface:true` consumer in a private repo is the exact population option 2 is for. Hence: inline `<img>` **only** for a confirmed-public repo, `/blob/` links — openable by any authorised viewer on any client — in every other case, **including when `gh` cannot tell us**. One inference step past the measurement is labelled as such: GitHub's markdown image fetch is unauthenticated, so that 404 surfaces to the reviewer as a broken image.

### Tradeoffs

- **Fail closed on visibility.** A wrongly-private verdict costs a missing inline image and a still-useful link. A wrongly-public verdict costs a broken image *and* a hand-off that claims something false — the exact defect option 3 removes, reintroduced by option 2. The alternative (always embed, accept broken images on private repos) was offered at the gate and declined.
- **The branch match is the load-bearing half, not the frame extraction.** On a ship where §5c legitimately skipped, the newest entry belongs to a **previous** PR; embedding its frames would show the reviewer a different change's before/after while labelling it this one's. That is worse than no images, and it is the default behaviour if the branch is not checked.
- **URLs pin to the PR-open SHA, not the branch.** A branch URL 404s the moment the branch is deleted at merge — exactly when someone reads the PR back as history. Residual, stated: further commits leave the body's frames pinned to the earlier SHA, and `/flow:land` does not re-render merged bodies. That is correct for a merge-gate record.
- **The hand-off names no client.** Research § 6 Q1/Q2 — whether the iOS app opens a session-produced HTML file, and what a tapped `file://` does there — are open and unanswered. "iOS cannot open this" would be the unverified-completion claim `/flow:audit-completion` exists to catch, *and* wrong in the Mac-app-with-Sync-files case. Stating the artifact's own property is true on every client and survives whatever the answers turn out to be.
- **Decision 7 was REVERSED at the gate.** The plan excluded `/flow:ship-spike` on the dispatch's write scope. The orchestrator who set that scope widened it: ship-spike is a second hand-off surface for the same two artifacts, and leaving it would ship a contradiction between them (Consistency item 2).

### What flow cannot dogfood, and what stands in for it

All four entries in this repo's own `dev-docs/visual-history.html` are inline CSS/SVG reconstructions, so `visual-history-assets/` does not exist here and **every flow ship takes the no-frames branch**. The frame branch is therefore driven against a temp git repo. `--selftest` was proven **mutation-sensitive** before being trusted: neuter the committed-asset check and it goes red, naming the break.

### Scope addition: the stale `uiSurface:false` self-claim

Flow has been `uiSurface: true` since v1.24.0. Two **shipped** sites still said otherwise: `schema/flow.config.schema.json` (`visualHistoryPath`'s description) and `ship/SKILL.md` §5c's FB-0016 note — doubly stale, since it also called the §5c entry shape unvalidated while the roadmap has recorded it VALIDATED for releases. A repo-wide grep found no third *live* site; the survivors are point-in-time records (`CHANGELOG.md`, `dev-docs/handoffs/*`, the merged research doc) and are deliberately untouched, as are the many correct references to `uiSurface:false` as a **consumer** state. The pin is paired: each absence sits beside the corrected claim, plus an assertion that the live `flow.config.json` still backs it — so the opposite drift fails too.

### What the reviewers found, because the disciplines are the transferable part

`/simplify` (4 lenses) and `/flow:staff-review` (4 lenses) between them found **three defects in my own work that CI was green over**, and each is an instance of a rule already written down here:

1. **A three-line render pasted into a markdown table cell.** The walkthrough hand-off was routed into the `## Flow run` table, which Decision 5 had itself rejected as "the single worst place to render" this material. "Paste its stdout verbatim" was unfollowable at that one site. Now a standalone block in both skills, pinned by a check that no `artifact-handoff.py local-line` call sits on a table row.
2. **A measurement that could only return one answer — in my own eval harness.** The coherence case guarded on `flow:test-plan-provenance`, which is `pr-coherence.py`'s *subcommand* name, not its marker (`flow:test-plan-rendered`). The guard never matched, no stamp was written, and **both arms ran unstamped** — the arm the case was shaped to exercise never ran. A sixth spelling of a five-site contract. The fixture is now produced by driving the real `render-test-plan.py`, and an instrument-validation check asserts it passes provenance *before* the with/without comparison is read.
3. **The mutation test passing for the wrong reason.** Hoisting the escaper gave the engine a sibling import, so the mutant written to a bare temp dir died on `import md_safe` — exiting non-zero *without running*. "Non-zero" could no longer distinguish "the mutation was caught" from "the mutant never started". Fixed with `PYTHONPATH`, plus a `mutant-actually-ran` check ahead of the verdict.

Also found and fixed: `code_span(inline(x))` double-processed, so a reader would have seen `` `frames/\[a\]_b` `` — the two neutralizing strategies do not compose, because inside a code span a backslash is literal. `md_safe.one_line` (contain) is now split from `inline` (escape), with the engine's use of each pinned in both directions. And the shared escaper itself was a reuse miss the lens named: a private copy passed `<`, the HTML-comment opener, so **one PR body carried two escaping policies** — now one definition in `md_safe.py`, two readers.

### Residuals, recorded rather than discovered later

Named in the roadmap D7 entry: `verify-build/SKILL.md:534/536` is deliberately untouched (machine-readable, and PR B's surface); the SHA-pinning behaviour above; flow's inability to dogfood the frame branch; and the deeper fix for the `vh-entry` markup contract — a shared contract module in the `manifest_contract.py` shape, which needs the writer in its write scope. In the meantime a round-trip eval drives the **real writer** and asserts the reader parses what it emits, validated by mutating the writer's attribute order and watching CI go red.

### Pre-existing red CI, found and fixed

This plan's own Spec-walk had five criteria naming no verification artifact. `run_autoplan_evals.py` grades the ACTIVE plan block and is CI-wired, so the plan commit was already failing. Each criterion now names its pin.

### Late arrival: Ben's measured iPhone results (2026-10-04)

They landed mid-ship and changed one thing in this PR, confirmed another, and unblocked PR B.

**Changed here.** A page served without a charset *header* leaves the browser guessing, and Safari on
iOS falls back to Latin-1 — measured, a `✓` rendered as `âœ“`. `python3 -m http.server` sends no such
header, and that is exactly what `.claude/launch.json` serves `.flow` with. The audit came back
asymmetric: `render-report.py` and `visual-history-skeleton.html` already declared UTF-8, but the
**prototype is authored by the agent and nothing required it** — and `/flow:prototype` Step 8 injects
the annotation layer, whose UI is full of non-ASCII glyphs, into precisely that file. So the one
page a human is asked to *approve* was the one with no guarantee. Now required by the skill, and
pinned — including an assertion that the annotation layer is still a **fragment**, since it inherits
its host's charset and a future reader must not "fix" it by giving it a second `<head>`.

**Confirmed here.** A `raw.githubusercontent.com` image link works from the iOS client — independent
confirmation of option 2's mechanism from the very client that motivated it.

**A finding that looks like it contradicts this PR, and does not.** *"Never put a path you expect
someone to tap inside a code span"* — iOS renders a code span as monospace text, not a link. This PR
puts the local path in a code span **deliberately**: that path is one nobody can tap from the page,
so monospace is the honest signal for exactly that property. The rule bites where a path IS meant to
be opened, which is PR B's surface. Every pointer this PR emits that a reader *should* follow is a
real markdown link, never a code span.

**Unblocked PR B, with a caveat that shapes it.** The preview URL works on iOS — but a preview's
backend dies when the serving workspace sleeps while the URL registration survives, so a live-looking
link can be dead. PR B must treat the preview as a convenience and always pair it with a
process-independent route. The strongest such route is also new information: a markdown image
pointing at a file inside the workspace **renders inline in the iOS chat**, with no server and no
public repo. Recorded in roadmap D7 so PR B is planned against measurements rather than assumptions.
