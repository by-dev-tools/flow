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

## Round two — the rigor gate's re-review, and the finding that mattered most

The rebase moved source after the first staff-review, so the rigor gate reported `source-drift` and
prescribed its auto-resolution: re-run all four lenses on the final tree. That re-run earned its
cost twice over.

**BLOCKER — the circularity fix was applied at one of the two sites that decide the verdict.**
`visual-significance.py` reads the change-set twice: once for `asset_hits` (what the report *names*)
and once for `new_files` (what sets `content_changed`, which *decides*). The exclusion went into the
first and not the second. So a captured frame still flipped a pure-refactor verdict from `false` to
`true` — **and the result was worse than before the exclusion existed**, because the filter had
already removed that path from `visual_signals`, so the verdict flipped with nothing in the report
naming the file that flipped it.

Measured on the shipped script, two change-sets differing by exactly one row:

```
R100  src/old.css → src/new.css                              → false
R100  src/old.css → src/new.css
A     dev-docs/pr-frames/feat-a/prototype-phone.png          → true   ← flow's own frame
```

Worth sitting with: the previous commit's history entry and roadmap row both asserted the circle was
closed. It was not, and **the eval I wrote to pin it could not tell** — `circular/exclusion-is-applied`
asserted the literal `"not FLOW_CAPTURED_FRAMES.search(p)" in src`, which is satisfied by the filter
appearing at one site. That is `general.md` item 4's own corollary — *pin the decision, not a string
that currently implies it* — committed inside the test written to honour it.

The replacement drives the shipped script and compares the **verdict** across those three
change-sets, so it needs no list of sites and cannot go stale as sites are added. It is
mutation-sensitive: reverting the second-site fix turns it red, where the literal pin stayed green.
It also leads with a known-positive (`instrument-can-say-true`), because two `false` assertions prove
nothing from an instrument that can only say `false`.

**A sixth unearned green, in the sidecar.** `capture()` unlinks the previous run's *frame* before
writing — with a comment calling a stale frame "the wrong-frame class the whole engine is built to
refuse" — but merged the *sidecar*. Merge-not-clobber is right across labels and wrong across
iterations of one: re-capturing a page that had since lost its `<title>` left the previous run's
description attached to this run's frames. Driven, not reasoned about:

```
iter1  title "Activity feed — empty state"  → sidecar {"prototype": {"title": "Activity feed — empty state"}}
iter2  title removed                        → frames: fresh.  sidecar: UNCHANGED
```

The engine's own note was false while it happened — it said the frames "carry no description" while a
description sat in the file and would be used. The label is now dropped when its source is, exactly
as the frame is.

**And the chat alt was the half I did not fix.** Two lenses, independently: the PR-body alt was given
the sidecar's title; the chat alt — on the surface where a non-seeing reader has *less* context, not
more — still read `Prototype — first screen at phone width (390×844)`, with `frames.json` sitting
unread in the same directory the capture had just written it to. My own eval pinned that defective
string by name. It now reads the sidecar from the working tree, which is correct precisely *because*
the chat frame is uncommitted by construction — the `git show` pinning on the sibling exists only
because a PR body is a projection of the commit, and a chat message is not.

Five smaller ones, each verified before fixing: the `branch_for_dir` note — the one defence against
the two-meanings-of-`--branch` collision this PR deliberately accepted — was sitting in a **dead
string expression** below the real docstring, invisible to `help()`; `/flow:doctor` printed a
confident `[PASS] chatImagePath unset` for a state nobody measured (an empty engine report pipes
through `jq` with exit 0); `warn_if_not_ignored` went fully silent on its own "could not measure"
tristate at the one shipped call site; a comment claimed all three adapters agree on a `warnings`
key that two of them do not have; and `vendor/scan-covered-every-target` asserted
`scanned == len(targets)`, a tautology that passes if you empty the list — `general.md` item 3 inside
the harness built to catch item 3.

One deletion: a private `r"(\d+) slots"` sweep I had added here was a **fourth** copy of a shape
`doctor/lib/slot_count_scan.py` documents escaping three ways, guarding a contract
`run_merge_status_evals.py` already covers over a strict superset of the same files. Removed rather
than fixed — one contract, one scanner.

Four further findings went to roadmap § Next as items 5–8 (the record pointer the captures arm
retires, multi-label interleaving and cross-label staleness, the exclusion being broader than the
writer's path, and working-tree enumeration deciding which source ships).

## The security review found the exclusion was a gate bypass

`/flow:security-review` traced every sink in the diff and disproved the obvious ones — a crafted page
`<title>` cannot break out of `![…](…)` because `md_safe.inline()` escapes at the render site; the
`captureBackend` template never reaches a shell; `branch_slug` is a positive filter that returns `""`
rather than traversing. Then it found the one that mattered, in the fix from the previous round.

`FLOW_CAPTURED_FRAMES` matched a bare `pr-frames/` path segment **anywhere**. So a contributor who
names a directory `pr-frames/` in their own PR — `src/assets/pr-frames/hero.png`, a path they choose
freely — silently suppressed the visual gate for a genuinely changed UI asset. Measured on the
shipped script: the same single-file add reads `false` under `src/assets/pr-frames/hero.png` and
`true` under `src/assets/frames/hero.png`.

And the suppressed run explained itself with *"diff touches no UI or asset files … a file outside
those patterns is NOT examined for a render delta"* — **false** for a diff that touched exactly one
asset file. The exclusion dropped those paths into the not-matched floor, so the verdict changed and
the report denied the files existed.

Two halves, both shipped. The pattern now requires the shape the engine actually writes —
`pr-frames/<branch-slug>/<label>-<frame>.png`, two path segments deep, where a contributor's
directory is one — and the frame *names* are deliberately not spelled there, which would have been a
third copy of the `FRAMES` table. Separately, an exclusion now **names what it excluded**: an
exclusion a report will not name is indistinguishable from a pattern that never matched.

The third option the reviewer offered — matching the directory `frames_dir()` computes at runtime —
was rejected for the same reason the literal was chosen over an import in the first place: this file
is a `sensitivePaths` gate, and #183 shipped precisely because its one existing cross-module import
could fail silently and void a whole gate. Trading a narrow miss for a wider blind spot is the wrong
direction. That decision is on the PR as a question rather than absorbed, because the reviewer
flagged it `[decision-required]` and it is not mine to close.

Three impostor paths are now pinned, alongside the positive that flow's own frames stay excluded and
that a suppression names its files.

**One more, same class, one layer up:** `/flow:ship` §5d interpolated `$PLAN_A` unquoted, so
`planPath` was an argv injector — `"dev-docs/plan.md --files-from /dev/null"` word-splits and forces
an empty change-set, a second route to the same suppressed verdict. No shell execution, and five
pre-existing sites carry the identical shape, but FB-0108's point is that a per-site quoting
convention is the thing that keeps re-arriving. The site this PR adds uses `set --` instead; the five
others are a roadmap item, not this PR's scope.

## Coverage, declared — and what three successive audits kept finding

`/flow:audit-coverage` ran three times and the plan grew **14 → 24 criteria**. That is not a sign
the audit was noisy; every finding was a behaviour a review round had *added* after the plan was
approved, which is precisely the under-declaration the gate exists to catch. The agent drafted each
criterion; the human declared them. Declaring one's own coverage is grading one's own homework.

**Run 1 (full diff, truncated)** — six findings, all declared: the frame exclusion, §5d's capture
decision, the sidecar alt text, `--source auto`'s fall-through, the dock-sentence/`prototype.html`
pair, and the verify-build boundary.

**Run 2 (scoped to the two files run 1 could not read)** — commissioned by the human rather than
accepted as "probably fine", and it earned its cost. 36 behaviours inventoried from the unread
remainder, **one undeclared**: the chat directory's git-ignore tristate. Both halves of that
behaviour were themselves review-round fixes — the note was unreachable because its only shipped
call site swallowed stderr, and the predicate went silent on its own "could not measure" — so it is
the changed-late-and-never-declared shape exactly. It was also genuinely **unpinned**: the functions
appeared in the selftest's text but carried no assertion, which a grep for the names would have
reported as covered. Written, then declared.

**Run 3 (full diff again, with 21 criteria)** — three more, and one is the sharpest of the lot:

> **§5d has a fifth path nobody had enumerated: no plan doc.** It warns and then computes visual
> significance *from the diff alone*, so a plan declaring `Visual-walk: N/A` cannot suppress
> capture — the exact suppression #183 shipped — reachable through a misconfigured `planPath`
> rather than through the plan.

The criterion I had declared enumerated exactly four arms, and all four presupposed the plan
resolved. The behaviour kept is warn-and-continue, because §5c and §7b do the same thing with the
same verdict and making §5d uniquely refuse would put three readers of one value into two minds;
the residual is bounded in the cheap direction (over-capture commits ~20 KB nobody asked for, it
never skips a gate). The point is that it is now *declared* rather than *unnoticed*.

The other two were the chat-side alt text — my criterion was PR-body-scoped and its pairing asserts
the *opposite* source, so the chat path had no criterion at all — and `/flow:doctor`'s fourth
outcome, where an unreadable engine report was being reported as "the slot is unset" because an
empty string pipes through `jq` with exit 0. Same could-not-measure collapse as the tristate one
layer below it.

**The honest residual:** run 3 was *also* truncated — this diff is simply larger than a 60 KB
evidence cap. Run 2 closed the biggest unread slice by hand. What remains unaudited is smaller and
overlapping, and three four-lens rounds plus a security pass read those files end to end. Recorded
rather than rounded off.

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
