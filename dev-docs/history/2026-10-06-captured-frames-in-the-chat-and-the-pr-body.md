# Captured frames in the chat message and in the PR description (v1.65.0)

**PR:** TBD · **Branch:** `conductor/chat-and-pr-screenshots` · **Date:** 2026-10-06, rebased and shipped 2026-10-31
**Spec:** roadmap **D7** § Next "Inline chat images as the always-available route for still frames",
which this closes. No new FB.

## What

A reviewer is asked to *look* at two things flow produces: the gate-1 prototype and the merge-gate
walkthrough. v1.59.0 made the hand-off honest about where they live; v1.60.0 made them optionally
reachable at a URL. Both still require the reader to go somewhere, and both can fail: the preview
URL stops serving when its workspace sleeps (measured), the PR-body image needs the repo to be
public (measured, 200 public / 404 private), and the local path is unreachable by construction.

This ships the third route and the only one with no such dependency — a **still frame**:

- the gate-1 chat message carries **one** captured phone-width frame, inline;
- the PR body's `## Before / after` section carries **both** frames, committed per-PR.

New `plugins/flow/lib/capture_frames.py` (engine + `captureBackend` adapter), two schema slots
(`captureBackend`, `chatImagePath`, 38 → 40), `frames --source captures` and `local-line
--chat-image` on `artifact-handoff.py`, `/flow:ship` §5d, `/flow:doctor` Check 2.14, and
`evals/run_capture_frames_evals.py` wired into CI.

## Why these decisions, and what the alternatives were

### Measured before designed — five probes, each of which changed the design

| Probe | Result | What it decided |
|---|---|---|
| `google-chrome --version` | 151.0.7922.169 | capture is possible with no new Python dependency |
| `--headless --screenshot={out} --window-size=w,h` | real PNGs, **exactly** 390×844 / 1280×900 | the two widths and the flag set |
| the same against a served `http://127.0.0.1:…` URL | real PNG | one capture path would serve both — **and was then deliberately not used**, see below |
| stderr on every run | `Failed to connect to the bus`, **exit 0** | success is the artifact, never the exit stream |
| raw URL at a **squash-discarded** PR-branch SHA | **http 200** | committed per-PR frames survive a squash-merge |

The last one is the enabling fact for the PR-body half and it was not obvious: this repo
squash-merges, so a PR branch's tip is not an ancestor of `main`. Paired three ways so the result
means something — `main`'s SHA returns 200 (the mechanism works at all) and an all-zeros SHA returns
404 (it is not simply always 200). It is why `/flow:land` does **not** prune `pr-frames/` after
merge: the images in a merged PR body keep working whether or not the files remain on `main`, so
pruning would be routine cleanup rather than a correctness requirement, at the cost of a post-merge
commit per PR.

### Success is the ARTIFACT, never the exit stream

The measurement that shaped the engine. Every real headless run writes dbus noise to stderr and
still exits 0 with a correct PNG. A reader that treats stderr as failure discards every working
capture; a reader that treats exit 0 as success accepts a truncated file. So `capture()` reads the
PNG magic bytes **and** the IHDR dimensions, and consults the exit code only to make a reason
specific once the artifact has already failed. The dimension check is what separates "captured the
page at this width" from "captured something" — without it a backend that ignores `{width}` produces
two byte-different frames labelled 390×844 and 1280×900 that are in fact one viewport.

That is also why all four placeholders are **required** rather than optional: a template that cannot
be told a size would pass validation and then produce exactly that pair of true-looking captions
over one measurement.

### A page with no UTF-8 declaration is refused, not warned about

Ben measured that a page served without a charset renders `✓` as `âœ“`. A screenshot of a garbled
page is strictly worse than no screenshot: it is a picture that lies, published into the one message
the human is guaranteed to read, and nothing downstream can tell it from a correct one. v1.60.0
already requires `<meta charset="utf-8">` in the agent-authored prototype and asserts both renderers
emit it, so this refusal should be unreachable in practice — which is exactly why it has to be loud.

**Honest note on the limits of that check.** The verification capture on this host rendered the em
dash and `×` correctly while `✓` came out blank — a missing *font glyph*, not an encoding failure.
The charset predicate cannot see that, and nothing here claims it can.

### The target is a local file, and the `{url}` the engine derives — not one a caller composes

The third probe showed a served URL captures fine, so an obvious generalisation was available. It
was dropped on purpose: the UTF-8 precondition is only checkable on bytes flow can read, and a flag
letting a caller pass a URL instead would exist solely to let them skip that precondition. Nothing
in flow needs it.

### `frames --source captures` as a flag, not a second subcommand

The two sources share every downstream rule — tracked-at-the-named-sha, the public/private embed
policy, the sha pin, the markdown escaping — and one surface is what keeps them from drifting. The
cost is real and was raised at the gate: `--branch` now carries **two meanings**. On `record` it is
a value *matched* against the newest entry's recorded branch; on `captures` it is the *source of a
directory name*. They are bound to different parameters inside (`branch_to_match` /
`branch_for_dir`), with a one-line comment at each read point, so the collision is visible where it
is used rather than only in the head of whoever wrote it.

### Committed under `pr-frames/<branch-slug>/`, not in the curated record

`/flow:ship` §5c calls `visual-history-assets/` *curated, not a per-PR dump* and enforces a hard skip
it describes in its own text as a mechanical floor against exactly that failure mode (FB-0042).
Writing every PR's screenshots there would defeat the one rule that keeps it readable.

The per-PR directory also *is* the own-PR guard, and it is a stronger one than the record source
has. There, a previous PR's frames are excluded by **comparing** a recorded branch against this one
— a comparison that has already been wrong once in this file's history (two empty strings compared
equal). Here another PR's frames are not reachable at all: nothing outside this slug's directory is
ever listed. A branch that slugs to nothing (a detached HEAD reads as an empty branch name) refuses
rather than falling back to a shared directory.

Cost, stated rather than engineered around: **~20 KB per visual PR**, permanently — ~1 MB/year at
fifty such PRs.

### One image in the chat, both in the PR body

The ~100-word gate-1 budget exists because *"the messages I come to are too long and I don't really
read them and I just end up approving anyway."* Markdown image syntax costs no prose words, but D7's
own note is blunt that an image is not free attention, so two frames in a chat message is a scroll —
the thing being fixed. `--chat-image` is accepted **only** for `--kind prototype`, and that is a
structural guard rather than a convenience: the frame is a local, uncommitted file, so the same
syntax in a PR body is a broken image, which is the defect the rest of the engine exists to refuse.

### `chatImagePath` is a slot, and flow's own value is **not** `.context/`

The brief said to write chat images to `.context/`. That is a **host** convention, ignored only
through `.git/info/exclude` — local to a single clone and shared with nobody — so a flow consumer
would have neither the directory nor the ignore rule. Hardcoding it in a plugin artifact is exactly
the project-specific-token mistake `previewBackend` exists to avoid (FB-0085).

Flow's own config therefore sets `.flow/chat-frames`, not `.context/`: `.flow/` is in the
**committed** `.gitignore`, so the ignore travels with the repo and the dogfooded configuration is
correct for anyone who clones it. The engine also prints a note when the configured directory is not
git-ignored, and `/flow:doctor` Check 2.14 reports the same thing at setup — these frames are for
the chat message, not the repo, and "not fatal and invisible" is how a repo accumulates screenshots
nobody chose to keep.

### `/flow:ship` chooses its frame source by the adapter's EXIT CODE

Not by grepping a render for image syntax. An exit code is a signal the engine's author maintains
against their own output; a grep is one more thing to keep correct
(`.claude/rules/general.md` item 4, exit-code corollary). A project with no capture adapter keeps
v1.60.0's behaviour exactly — the record source is still the default and still shipped.

### `verify-build` captures nothing, and says why

The plan's file table put a capture in §5a. It does not belong there and the skill now says so
explicitly. §5a's whole discipline is *reach the state, assert it via the a11y tree, then capture*;
`captureBackend` has no drive primitive and no a11y tree, so using it there would turn "capture the
state you confirmed you reached" into "screenshot whatever is on screen", which §5a step 1c forbids
in those words. The rendered report is handed to the capture engine at `/flow:ship` §5d instead,
after judging is already done. The boundary note is paired with its own positive in the evals, or
deleting the note would turn the "verify-build does not capture" assertion green.

**And nothing here certifies anything.** FB-0066 forbids an implementer self-certifying shipped
visual work from frames it read itself. These frames are evidence *for the human's eye*, at a gate
they were already attending.

## Tradeoffs

- **A third `*Backend` adapter, and the hint parameters the v1.60.0 review flagged.**
  `render_template`'s two trailing `*_hint` arguments were an honest trade for two adapters and that
  review said they would stop being one at a third. This is that third. Routed to roadmap § Next
  deliberately rather than fixed here: the fix is a refactor of a function three shipped adapters
  call, and bundling it with a feature PR would make the feature's diff unreviewable for the one
  reason the refactor exists.
- **Binary files in git, forever** — ~20 KB per visual PR. Stated and accepted; see above.
- **Flow cannot fully dogfood this PR.** This change is `Surface: non-visual`, so
  `visual_significant` is false and §5d correctly captures nothing on its own ship. The engine was
  verified against the real browser by hand (two frames, exact dimensions, inspected) and the
  behavioural load sits in `run_capture_frames_evals.py` — the same position `previewBackend` was in
  and for the same reason: `platform: library` means `/flow:verify-build` self-skips here.

## What the staff-review caught, and why one of it was a shipping defect

Four lenses ran in parallel against the committed diff. Three of the four independently found the
same BLOCKER, which is worth stating because it is the strongest signal the pass produced.

**BLOCKER — a configured capture adapter silently retired the curated visual-history source.**
`/flow:ship` §7b chose its frame source from whether the adapter *validates* (`capture_frames.py
check` exits 0 on a well-formed template), which says nothing about whether §5d actually captured
anything. Every §5d skip — not visually significant, no prototype and no walkthrough, a refused
page, a detached HEAD — still reached §7b with `SRC=captures`, so a consumer who set the slot *and*
had a curated record with committed frames got "No frames to show" in place of their images. §5d's
own operator message promised the opposite in the same diff: *"the Before/after section falls back
to the visual-history record."* That fallback did not exist.

Reproduced before fixing, against one repo holding a real curated entry. The fix puts the
fall-through **in the engine** (`render_frames_auto`) rather than in two shell blocks that would
each have to remember it, and keeps `--source captures` strict so the mode is still testable on its
own. Both skills now pass `auto`. Pinned by `test_auto_never_retires_the_record`, which also asserts
at the *composed* layer that the shipped call sites pass `auto` and not `captures` — the engine
being right while the shell is wrong is the layer-mismatch class `general.md` item 4 names.

Also worth recording: the changelog's "Breaking changes: none" was true only for the unset default.
It is now true generally, which is what it should have said.

**The still photographed flow's own chrome.** Both capture targets were
`prototype.presented.html` — the prototype *plus* flow's click-to-pin dock, which is exactly why
§8's hand-off has to carry the sentence "The small floating comment dock is flow's, not the design."
That sentence is a caption apologising for the picture. In the live page the dock earns its pixels
because it is clickable; in a still it is furniture on the one image a phone reader sees before they
approve, and they cannot tell it from a floating affordance the design itself proposes. Both call
sites now capture `prototype.html` — which is also the file `approve` hashes, i.e. literally the
thing being approved.

**The alt text named the frame and said nothing about the page.** `"prototype at phone width,
390×844"` was the entire text alternative for a reader at the merge gate who cannot see the image,
in the one section that exists to be looked at — and the sibling record path's own selftest pins
`"blank gray panel with no call to action"`, so the project's bar was already higher. The renderer
cannot read the HTML (it is ephemeral, and the renderer is deliberately a projection of the commit),
so `capture` now writes a small `frames.json` beside the frames carrying the page's `<title>`, and
the renderer reads it back with `git show <sha>:<path>` like everything else. The projection
discipline is unchanged and asserted: `alt/reads-the-commit-not-the-worktree` deletes the sidecar
from the working tree and requires the render to be byte-identical.

**A capture is one screenful, and nothing said so.** Captions and alts now read "first screen at
phone width — 390×844". The viewport-clipping itself is deliberate and correct — the fold is a real
design fact and a full-page capture of a long prototype is unreadable at PR-body width — but it has
to be said out loud, which is the same standard the UTF-8 refusal applies one notch louder.

**The per-PR directory was composed twice.** A shell literal `pr-frames/$SLUG` in `/flow:ship` and a
Python constant in the renderer: the one contract both halves must agree on, duplicated in the one
file whose own comment says two copies "agree today and diverge the first time one is tidied — and
the divergence would be SILENT." It would have been exactly that: the reader's "committed no
captured frames" line is indistinguishable from a correct skip. There is now a `frames-dir` verb,
the shell calls it, and `test_frames_dir_is_composed_once` pins the CLI the shell actually invokes
rather than only the Python function underneath it.

**Six smaller ones, all real:** `chat-dir`'s reasons were thrown away by `2>/dev/null` at its only
shipped call site, so `warn_if_not_ignored`'s message could never reach a human — the silent-skip
class, in the diff that adds it; the skill re-derived `<label>-<frame>.png` instead of reading the
path the engine prints; `git check-ignore` returning 128 (outside a repo, corrupt index) was read as
"not ignored", a confident claim about something nobody measured, so the predicate is now a tristate
and `/flow:doctor` **calls** it rather than re-implementing it; `/flow:doctor` WARNed on
PR-body-frames-without-a-chat-image, which is a supported configuration the engine's own message
calls correct — a warning that fires on a correct setup is how people learn to ignore warnings; the
wrong-size refusal blamed the template for a device-pixel-ratio capture, sending a retina-capturing
author to inspect a placeholder that was in fact correct; and the surfaced command error was
likely to be `Failed to connect to the bus`, the one line this module documents as present on every
successful run.

**And one comment that claimed a property the code did not have.** `FRAMES`'s header said the chat
message takes the first entry "by construction rather than by a caller remembering which index to
slice" — while the caller passes the literal `--only phone`. Reorder the table and the chat frame
does not follow. The comment now says what is true and names where the contract actually lives.

Four findings were routed to roadmap § Next rather than fixed: retina/DPR capture, dark mode never
being photographed, the two frames rendering at very different scale when stacked, and
`## Before / after` being the wrong heading for an after-only set (the string is pinned at ~8 sites,
so a per-source heading is a genuine fan-out). `validate()`'s triplication across the three adapters
joined the existing `render_template` hint-parameter item, since both are the same refactor.

## What the rebase surfaced, 21 days later

This branch was held at the ship gate while #183 and #184 landed. Rebasing onto a `main` that had
moved two releases produced two findings, neither of which a clean replay would have.

**The version had to move, and the courtesy that was extended could not be honoured.** #184
deliberately re-claimed itself `1.63.0 → 1.64.0` so this branch could keep the number it claimed
first. But #184 merged first, so 1.63.0 became a *backwards* version: shipping it would leave every
consumer already on 1.64.0 unable to update. Re-swept to **1.65.0**, and 1.63.0 is now a permanently
skipped number — a reserved-then-overtaken claim. The reservation was the right instinct and the
wrong mechanism; version numbers cannot be reserved across a merge queue, only taken at merge.

**Two concurrent branches each swept the same five sites, and both were individually right.** #184
added `ciWaitSeconds` and swept the slot-count fan-out 38 → 39. This branch added `captureBackend` +
`chatImagePath` and swept the same five sites 38 → 40. Every one of those five files conflicted at
rebase, and *taking either side* would have shipped a wrong number — the merged schema holds **41**.
Resolved against the schema file itself rather than against either side of the conflict.
`run_merge_status_evals.py`'s slot-count check is what forced the question at rebase instead of
after merge; its comment now records why neither branch's number survived.

## The §5d trigger did NOT survive its own plan's reading, and that is the point of re-checking

The plan assumed `visual_significance.py`'s verdict would mean what it meant in September. Driven on
post-#183 code against three plan shapes rather than read:

| Plan declares | pre-#183 | post-#183 | §5d |
|---|---|---|---|
| no `Visual-walk` block | false | false | skips |
| **`Visual-walk: N/A`** | **true** (forced) | **false** | **skips** |
| `Visual-walk` + an assertion | true | true | captures |

The middle row is the one that moved, and it moved in this feature's favour: pre-#183, a PR that had
*explicitly declared it has no visual surface* would have had §5d capture two frames, commit ~20 KB
of PNGs, and publish a `## Before / after` section nobody asked for. The gate is correct **because**
#183 landed, not independently of it.

### And running the three arms in sequence found a circular gate this feature was introducing

Arm 3 left its captured frames in the working tree, and arm 2 then read as visually significant —
not via the `Visual-walk` path, but because `visual-significance.py` counts added **asset files**,
and `pr-frames/*.png` are assets. So flow's own captured frames were about to become evidence for
the very verdict that caused them to be captured. The frames exist *because* the answer was true, so
they cannot be why it is true.

`visual-significance.py` now excludes a `pr-frames/` path segment from the asset signal. Scoped to
that segment and **not** to `.png`, because a consumer's own screenshots are real evidence and must
keep signalling — pinned in both directions (`src/img/hero.png`, `assets/pr-frames.png` and
`docs/my-pr-frames-guide.png` all still signal). The exclusion is a literal rather than an import
from `capture_frames.py`, deliberately: that file is a `sensitivePaths` gate whose one existing
cross-module import failing silently is precisely what #183 shipped to fix, and a second such import
would trade a narrow circularity for a wider blind spot. The two definitions are pinned to agree by
`test_captured_frames_are_not_their_own_evidence`, which fails if either moves.

Worth stating plainly: this defect is only reachable because the feature writes committed images
into the repo. Nothing else flow ships does that, so no existing gate had to think about its own
output being read back as input.

## What the harness caught that review would not have

Four defects, all found by running the instruments rather than reading them:

1. **An `ImportError`-only guard around a `parents[3]` lookup.** Computing the path raises
   `IndexError` for a copy of the file at a shallower depth — which is exactly how
   `run_artifact_handoff_evals.py` drives its mutant — so the engine crashed on import and turned
   the **mutation-sensitivity pin** red for a reason unrelated to the mutation.
2. **A known-negative that could not fail.** The first cut's "an uncommitted frame never appears"
   arm named the file `prototype-uncommitted.png`, which the non-frame-file filter excluded *before*
   trackedness was ever consulted. It passed with `git_tracked` mutated to return `True`
   unconditionally. Caught only by running the mutation; re-keyed to a real `-phone` suffix.
3. **A gh-absent arm that measured the wrong absence.** Emptying `PATH` removed `git` too, so no
   frame was tracked and the arm went green on the "nothing is in the commit" branch — it would have
   passed with the visibility gate deleted. `git` is now symlinked in, with a check asserting the
   arm can see it.
4. **Two stale hardcoded counts in sibling harnesses**, plus two slot-count claims my own
   `git grep` pattern missed (`38 schema slots`, `38-slot`) which `run_merge_status_evals.py`'s
   fan-out guard found. Both sibling pins are now **derived** from the directory rather than
   hardcoded: a literal `scanned == 12` made every future shared lib a two-file edit and would go
   red for changes that have nothing to do with the harness asserting it. The `exactly-four-text-
   positions` check also lost the count from its *name* — a number in a check name is a second place
   the contract is written down, and it goes stale without failing anything.
