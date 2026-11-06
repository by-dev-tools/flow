# Mobile option 4 — touch support for the gate-1 annotation layer

**Status: PAUSED 2026-11-06 by Ben — not abandoned.** Round 3 is in review; Ben gave informal
feedback ("fine, still needs some work, good start") but has not approved gate 1, and the worker's
own round-4 candidate list (below) has not been built. Ben's direction: stop here, document, and
archive the workspace — do not start round 4 or any new work until this is explicitly picked back
up.

## Origin

Same dispatch as `2026-10-03-mobile-options-1-3-dispatch.md`: Ben, 2026-10-03 — *"I'd like all 5 of
those ranked options."* Options 1–3 went to the `mobile-opts` worker (that doc); **option 4 — touch
support for the click-to-pin annotation layer — went to a separate worker (`touch`)**, dispatched
informally rather than written to disk at the time. This doc exists so that gap doesn't also become
a "cited authority with no artifact" problem for whoever resumes it.

### Outcome (as understood from the worker's own framing, not a written plan)

Gate 1's click-to-pin annotation layer — the mechanism a human uses to comment on a prototype or a
verify-build report before approving it — should work on a touch device, not only with a mouse.
**Still gate 1: no feature branch, no plan written, no approval inferred at any point in this
workstream.** This is prototype-first design exploration living entirely on an orphan branch,
exactly as intended — nothing here was ever meant to merge until a plan exists.

## Where the work lives

- **Branch:** `proto/touch-gate1` (orphan, never merged, explicitly `Not for merge. Delete once gate
  1 closes.` per its own commit messages).
- **Commits**, oldest first:
  - `7aee85c` — gate-1 touch prototype, pinned for durable serving
  - `aa77652` — revision 2: Ben's five points + a wide-table case
  - `129a59f` — revision 3: sheet-sized buttons, the editor becomes a sheet
  - `4654413` — round-3 hand-off frames (phone 390×844, desktop 1280×900), captured from the
    committed `prototype.html` (sha256 `880f2c42…`) after the live preview link proved unreliable
    (see below)
- **Artifacts for round 3:** `gate1-phone-390x844.png`, `gate1-desktop-1280x900.png`, committed at
  `4654413` alongside `prototype.html`. Raw links (repo is public, confirmed 200 unauthenticated):
  - `https://raw.githubusercontent.com/by-dev-tools/flow/46544130161f57b0a3d0b5e63bf177af7001ba2e/gate1-phone-390x844.png`
  - `https://raw.githubusercontent.com/by-dev-tools/flow/46544130161f57b0a3d0b5e63bf177af7001ba2e/gate1-desktop-1280x900.png`

### Why screenshots instead of a live link

The live prototype preview repeatedly 502'd — both the orchestrator's own relay server and, measured
independently, the worker's own official preview link died identically whenever the serving
workspace slept between messages. This is a genuine Conductor platform constraint (sleeping
workspaces stop serving), not a flow bug. Round 3 switched to committed, verified PNGs instead —
durable, no dependency on anything staying awake. If a future round needs a live interactive
prototype again, expect the same 502 pattern and plan around it rather than re-discovering it.

## Status as of 2026-11-06

Ben's feedback on round 3, verbatim: *"the touch prototype is fine. it still needs some work, but
it's a good start."* No specifics given. Rather than guess, the orchestrator asked the worker to
propose candidate refinements from its own design judgment. The worker's reply (verbatim, condensed
— full version in the session transcript if needed) proposed three, ranked by priority, **none
built**:

1. **You can see what you pinned, but can't adjust it — only delete and re-aim.** Measured: 70 of 80
   commentable elements are under the 44px touch-target floor (verdict dots 9×9, "need" chip 43×23,
   inline code 132×18). Proposed fix: wider/narrower controls in the editor sheet reusing the
   existing `walkDepth` logic, post-commit so it fits the existing flash-then-confirm rhythm.
   Moderate cost — touches the targeting code.
2. **While writing a comment, nothing on screen says what it's about.** The highlight flash is gone
   by 700ms (measured) while the editor can stay open indefinitely; the persistent descriptor at the
   top of the sheet is 105 characters, redundant, and clipped (497px of text in a 364px box).
   Proposed fix: keep the outline drawn for as long as the editor is open (`drawHL` already supports
   this), and cut the descriptor to its non-redundant half. Small cost — "the one I'd expect to feel
   biggest per line changed."
3. **The 44px rule stops at the edge of the sheet.** Pins on the page itself are 22×22 (measured),
   half the floor applied to every control inside a sheet. Proposed fix: a transparent padded hit
   box around the same visible 22px dot — tappable area grows, nothing visually changes. Small cost,
   contained to one rule.

The worker also flagged two things NOT to re-raise (checked and ruled out: pin badges don't overlap
at five comments on a dense page; "Copy all" output is already good — grouped, numbered, records
viewport), and two alternate readings of "needs work" worth naming if the above misses the mark: the
demo content/report page itself rather than the commenting mechanism, or something only verifiable
on a real device (dictation into the comment field, on-screen-keyboard behavior — neither
reproducible in this environment).

## For whoever picks this back up

1. Read Ben's feedback above and the three candidates — confirm with him which (if any) is what he
   meant before building anything. The worker explicitly declined to guess; don't guess on its
   behalf either.
2. The worker's own workspace (`Mobile option 4 (annotation layer on touch)`) was archived
   2026-11-06 once this doc was written — there is no live chat to resume. Start fresh, pointed at
   `proto/touch-gate1` and this doc.
3. Expect the live-preview-link 502 if you reach for it; the screenshot-and-commit pattern from round
   3 is the known-working alternative.
4. Still gate 1 throughout — no plan, no feature branch, no merge, until Ben approves what's on
   `proto/touch-gate1`.
