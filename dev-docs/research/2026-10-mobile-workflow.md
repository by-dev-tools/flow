# Mobile workflow — where a phone hits the limits of the laptop flow (2026-10)

> **Status: LIVING SURVEY.** Commissioned by Ben, 2026-10-03, dispatched by the orchestrator
> seat. Findings only — **no code changed, no decision made**. All claims about shipped flow
> behavior are read from this repo checkout on `main` at commit `a250b66` (v1.55.0), never from
> an installed plugin — this workspace's own installed copy was found at v1.29.0 mid-task and
> updated to 1.55.0 (`claude plugin update flow@flow`), but every citation below still traces to
> the checkout, not the install. Conductor facts are read from Conductor's own CLI (`conductor
> --help`, installed v0.1.0, authenticated) and conductor.build's changelog/docs, dated per
> entry; anything from a third party is labeled **[secondary]**.

## 0. The real shape of the question (Ben, mid-task correction)

The first draft of this brief treated "mobile" as a separate surface. It isn't. **This is one
workflow running in Conductor cloud workspaces, driven sometimes from the Mac app and sometimes
from the iOS app, with the iOS app able to do less.** So the spine of this doc is per—human-gate:
what works from each client, and where the iOS app runs out. Section 5 is new — hand-offs
*between* the two clients — added after the correction, not originally scoped.

## 1. What Conductor's two clients actually are (primary sources)

- **Mac app** (`conductor.build`): full IDE-adjacent surface — terminal panel, Git panel, a
  desktop-only **Browser Preview** pane (`⌘⇧B`, built on "Agentation": render a localhost page
  inside Conductor and click-to-annotate elements, attaching notes to the chat composer)
  ([0.62.0 changelog](https://www.conductor.build/changelog/0.62.0-repo-settings-browser-preview)).
  The sidebar's own warning that it needs "macOS Tahoe or later" plus the macOS-only keyboard
  shortcut confirm this pane has no mobile counterpart.
- **iOS app**, shipped as **Conductor for iOS, v0.90.0, dated 2026-10-02 — yesterday**
  ([changelog](https://www.conductor.build/changelog/0.90.0-conductor-for-ios)). Confirmed
  capabilities, quoted from that entry: *"You can now chat with agents and merge PRs from your
  phone. Works with cloud workspaces."* Plus: a redesigned PR view (branch/review/checks/merge
  status on one card), one-click PR approval, PR-stack navigation, inline video playback with
  scrubbing, "Find in Chat" search over agent thinking/tool calls, settings sync across devices,
  and — released in this same entry — **`.context` file syncing between iOS and Mac for cloud
  workspaces**. The predecessor entry, [0.78.0 "Introducing Conductor Cloud"](https://www.conductor.build/changelog/0.78.0-introducing-conductor-cloud),
  still listed the mobile app as "(coming soon)" — it shipped nine point-releases later, not
  before. Earlier marketing copy and `docs.conductor.build` (an older, unsynced docs tree that
  still says "macOS only") are **stale against the changelog** and should not be trusted over it.
- **What the changelog does not say, and I will not guess**: whether the iOS app can render an
  arbitrary HTML file produced by a session (vs. just diffs/chat/PR metadata), whether a bare or
  `file://` path pasted in chat does anything when tapped, and whether a `conductor preview`
  URL opens correctly in mobile Safari. These become the direct questions in § 6 rather than
  claims.
- **A genuinely new primitive, confirmed by running the CLI itself** (not docs — the tool's own
  `--help`, the strongest primary source available): `conductor preview set --port <port>` shares
  one port per workspace at a stable URL. Its help text states the access model directly:
  *"Viewers sign in with Conductor and need read access to the workspace. The URL stops serving
  while the workspace sleeps … and is deleted when the workspace is archived."* That is: **not
  public**, gated by Conductor auth + workspace ACL, but visible to anyone who already has read
  access to that workspace (a teammate in the same org), and outlives the moment of approval
  until the workspace sleeps or is archived. Nothing in `plugins/flow/` invokes this today
  (`git grep -n 'conductor preview\|http.server\|CONDUCTOR_PORT'` across `plugins/flow/` and
  `dev-docs/` returns nothing outside this file) — it is unused capacity, not a shipped path.

## 2. Area 1 — Gate 1, prototype approval (`/flow:prototype`, D1/FB-0081)

**The artifact.** `prototype/SKILL.md` §§5/8 (read from `main`): the prototype is written to
`$PROTO_DIR/prototype.html` under `.flow/prototypes/<branch-slug>/` — **gitignored**
(`prototype/SKILL.md` §1: `.flow/.gitignore` is `*`). `present` (step 8, invoking
`prototype-gate.py present`) writes a sibling `prototype.presented.html` with the annotation
layer injected, and the hand-off is: *"The `file://` path to the file `present` names… so they
can open it."* This is the complaint Ben named almost verbatim — the plan doc's own roadmap
entry (D1a) independently confirms the artifact "do[es] not survive workspace loss" because it
lives outside git by design; the **durable** half is only the sha256 + quote committed into the
plan doc, never the file itself.

- **Mac app:** if "Sync files" is on, the cloud workspace's files — including gitignored
  `.flow/`, since sync appears to be a filesystem mirror, not a git-aware one — should appear in
  the local mirrored folder, openable via Finder → a real browser. That is still not "open from
  inside Conductor's own chat view"; it is a `file://` URL in *some* browser on the Mac. Whether
  Conductor's Mac app itself makes a pasted `file://` string clickable in-app is unconfirmed —
  candidate question (§6).
- **iOS app:** no changelog or doc evidence of opening an arbitrary local/session file at all.
  The one "file viewing" changelog line found (0.90.0) is explicitly about **local, not cloud,
  workspaces** — "clicking a file path outside the workspace in chat … shows it in Finder" is a
  macOS Finder behavior, not an iOS capability. Treat this gate's visual half as **unconfirmed
  reachable from iOS** rather than assumed broken or assumed fine — direct question in §6.
- **The approval mechanism itself is a different story and already portable.** Approving gate 1
  is typed text — `prototype-gate.py approve --quote-file …` — a session chat action, and
  0.90.0 confirms chat-from-phone works. **The gap is entirely in the LOOKING, not the
  APPROVING.** Ben could in principle type "approved" from his phone having never actually
  seen the prototype, which is worse than the gate `/flow:prototype` exists to replace (an
  approval that wasn't read).

**Annotation layer, touch assessment** (`verify-build/lib/annotation-layer.html`, shared verbatim
by gate 1's `present` injection and the merge-gate walkthrough — same file, same limitations in
both places):

| Behavior | Code | Touch verdict |
|---|---|---|
| Tap to pin a comment | `document.addEventListener("click", …)`, resolves the target via `document.elementFromPoint(e.clientX, e.clientY)` (lines ~691–721) | **Works.** A tap fires a real `click` event; nothing here is mouse-specific. |
| Live hover-outline before you commit | `document.addEventListener("mousemove", …)` (line 664), gated by `snapPreview` which **defaults true** (line 393) | **Silently absent on touch.** `mousemove` never fires from a tap, and the post-commit `flashHL` fallback (line 649) only fires when `snapPreview` is *off* — the default was tuned for a mouse, so a touch reviewer gets no preview before OR after, unless they first find and flip the "Outline elements while hovering" toggle. |
| Interact with the prototype's own links while commenting is on | `⌘/Ctrl/Alt-click` passthrough (`eventIsOurs`, line 436) | **No touch equivalent exists** — there is no modifier-tap gesture. The only route is toggling "Commenting" off first (works on touch, it's a real tap target), but it's an extra, undiscoverable-without-reading-the-hint step every time. |
| Keyboard element-walk (`⇧↑↓` step, `⇧←→` widen/narrow) | `walkStep`/`walkDepth` (lines 469–501); the SKILL.md itself measures this at *"63% of pointer-reachable elements by stepping alone"* | **Fully unavailable without a hardware keyboard** — i.e., unavailable on a phone held normally. Everything directly tappable still works; only the keyboard-reach path (useful for small/overlapping targets) is lost, with no touch substitute offered. |
| Dictation in the note field | plain `<textarea>`, hint text says "dictation works here" | **Plausible, unverified for iOS specifically.** D6 (`research/voice-annotation-pipeline-2026-07.md`) confirmed macOS system dictation works here with zero code; iOS's own keyboard-mic dictation targets the same `<textarea>` primitive, but nobody has run it. |
| Copy-to-clipboard ("Copy all") | `document.execCommand("copy")` with a visible select-and-copy fallback sheet if it fails (`writeClipboard`) | **Degrades safely either way** — `execCommand` is deprecated but still callable from a user gesture on current mobile Safari; the fallback sheet exists for exactly the browsers where it isn't. Not a mobile-specific risk worth a strong finding. |
| Fixed dock position | `#an-dock { position: fixed; right: 20px; bottom: 20px; }`, no `env(safe-area-inset-*)` | **Minor craft nit**, not a break — plausibly sits close to the iOS home-indicator gesture band on some viewports; unmeasured, low stakes. |

Net: the core loop (tap an element, type or dictate, Copy all, paste back) is touch-compatible by
construction. What's lost is the *secondary* affordances tuned for a pointer+keyboard reviewer —
none of them block the gate, all of them make it feel worse on a phone than the ~63%-measured
keyboard path implies it should.

**Relation to filed roadmap items (do not duplicate, just place this finding against them):**
D1d is about *nothing rendering the page before hand-off* — a load-check gap, orthogonal to
reachability; a phone that can't reach the file at all never gets far enough to hit D1d's failure
mode. D1a already accepts the artifact is ephemeral-by-design and defers a durable home "if a
consumer actually asks" — this investigation is evidence a consumer (Ben, from a phone) is
closer to asking than when D1a was written, but D1a's own "revisit if…" condition is about
*durability*, not *reachability*, and this finding is squarely the latter.

## 3. Area 2 — the merge gate: verify-build's walkthrough and `visual-history.html`

**The ephemeral walkthrough is worse than gate 1's artifact, on every device, not just phones.**
`verify-build/SKILL.md` §§5a/Step 10: the rendered report lives at `flow.config.json.verifyReportPath`
(default `.flow/verify-report.html`), explicitly **"ephemeral, not committed… regenerated every
iteration and discarded after merge."** `/flow:ship`'s PR-body template (`ship/SKILL.md` line
~1520, and the explicit instruction at line ~1388) hands this to the human as:

```
Walkthrough (local, uncommitted): <verifyReportPath>
```

That is a **bare filesystem path with no protocol**, not even `file://`. It cannot be opened from
a GitHub PR page — web or mobile, Conductor Mac or iOS — by anyone who is not inside the exact
sandbox that produced it. This is the single clearest instance of Ben's "running them at all"
complaint: it isn't degraded on mobile, it is **unreachable from the review surface on any
client**, and the PR body gives no indication of that until you try.

**The durable half (`visual-history.html`, V3b) is committed but still not "openable."**
`ship/SKILL.md` §5c / `insert-visual-history.py` confirm the distilled before/after frames land as
real committed PNGs under a sibling `visual-history-assets/` directory, referenced from the
committed `visual-history.html` by relative `src`. Two independent problems stack here:

1. GitHub does not render a committed `.html` file — its blob viewer shows source, and
   `raw.githubusercontent.com` deliberately serves raw content as non-executing
   (`text/plain`/`octet-stream`), specifically to prevent exactly this kind of inline execution.
   So even a **laptop** reviewer can't "just open it" from the PR; they must clone/checkout.
2. The committed **PNG frames themselves** are directly viewable by GitHub (and the iOS app's
   file browser, per general GitHub-mobile behavior) — they're just never referenced from
   anywhere a reviewer is actually looking (the PR body only names the `.html` path, never an
   image).

**Annotation layer:** identical file, identical touch profile to §2 above — same shared partial,
injected by `render-report.py` before every rendered report.

**Relation to filed roadmap items:** V3's own entry already calls the ephemeral/durable split
"provisional until a UI-surface cold-run" validates it — flow's own repo is `uiSurface:false` and
self-skips, so this split has literally never been exercised end-to-end outside a toy fixture.
This finding is first-hand evidence from that validation gap, not a new design question. D1d's
"nothing has rendered it" concern (§2) applies here too, compounding with the reachability
problem rather than replacing it.

## 4. Area 3 — reading a PR body, and chat hand-offs, on a phone

**The mechanics are now phone-capable (0.90.0, confirmed):** chat with the session, one-click PR
approval, and merging — all shipped. The content those mechanics surface is a separate question.

**What flow already does well, cite it so it isn't lost:** `/flow:prototype` §8's gate-1 message
carries a hard **~100-word budget** — explicitly because *"the messages I come to are too
long… I just end up approving anyway"* (quoted directly from the roadmap's Designer-signal
track). `manifest-triage.py::render_decisions()` (ship's draft-manifest hand-off) is
decision-first by construction: numbered questions, "what this means" in plain language, a
drafted recommendation up front. Both are real, working instances of what Ben is asking for in
area 2 of his brief — the gap is that **D5 (message budget) is filed as applying to exactly one
message** (roadmap: *"D5 was not acted on beyond a ~100-word budget on that one message"*).
Nothing in `/flow:ship`'s own final hand-off (the `## Flow run` table, the `## Test plan`
section, the Step 8 "Decisions for you" preamble) carries an equivalent budget — it's long by
construction (the `## Flow run` table alone is 14 rows), and nothing trims it for a narrower
screen. **This finding does not replace D5; it is the mobile-specific case for prioritizing it** —
the same unbounded message that's merely annoying on a 27" monitor costs materially more
scroll-and-lose-your-place time on a phone, which is the amplification Ben is naming.

**Field-manual §3's rules are the same complaint from the orchestrator's own operating
experience**, not a separate concern: *"Large text blocks read worse than an agent assumes"* and
*"One message per worker"* (a batched multi-worker message was misread by the wrong worker and
cost a fortnight once) are both about exactly the failure mode that gets worse, not better, on a
small screen with slower scrollback.

## 5. Area 4 — hand-offs *between* the two clients (added after Ben's correction)

This cuts across §§2–4 rather than sitting beside them.

- **Text actions are portable by construction.** Approving gate 1, answering a numbered decision
  list, waiving an entry, merging a PR — all are either plain chat messages or PR actions that
  Conductor's backend treats identically regardless of which client sent them. 0.90.0 confirms
  merge-from-phone works. **So a gate that was started on the Mac can be finished from the
  phone, and vice versa, for the DECISION half.** This is good news and should be stated plainly
  rather than assumed broken.
- **Looking is not portable, because it was never routed through the session at all.** Every
  artifact in §§2–3 is a local file or a `file://` string — neither is a session-level object
  Conductor's API carries between clients; both depend on which filesystem happens to be
  reachable from wherever you're standing. The decision moved between devices cleanly; the
  evidence it's based on did not move at all.
- **`.context/` sync is the sharpest live example, and it is directly relevant to the report you
  are reading.** Per this session's own system instructions, Mac sync of a cloud workspace's
  files is one-directional (cloud → Mac) and an opt-in toggle. 0.90.0 — released the day before
  this investigation — adds `.context` sync for iOS too. This worker was instructed to save
  screenshots under `.context/` and embed them with Markdown image syntax in chat. **Whether that
  embed actually renders as an image for Ben on iOS, versus rendering only because the Mac app
  can resolve a local path, is exactly the kind of claim this document should not guess at** — it
  is Question 3 in §6, not an assumption baked into this report's own delivery.
- **The Browser Preview / Agentation pane has no cross-client story at all** — it is Mac-only by
  its own keyboard shortcut and OS-version gate, so any instruction that tells Ben to "check it in
  Browser Preview" silently fails the moment he's on his phone. Any future flow guidance that
  leans on Conductor's own preview tooling should prefer `conductor preview set`'s **URL**
  (§1) over the Mac-only pane, specifically because a URL is the one artifact shape confirmed to
  cross both clients (it's just a link).
- **One asymmetry worth naming directly:** nothing suggests state is ever *lost* moving between
  clients — both read the same session/PR backend — only that *some artifacts are invisible from
  one of the two*. That's a narrower, more tractable problem than data loss, and worth stating
  that way to avoid over-scoping a fix.

## 6. Open questions for Ben — each answerable in a word

**Status: OPEN, put to Ben 2026-10-03.** Pending — not forgotten; answers land in a later edit
of this doc when the orchestrator brings them back.

1. Can you open an HTML file created in a cloud-workspace session from the iOS app at all (tap a
   path in chat), or only view text/diffs/images?
2. Does a `file://` path or a plain filesystem path pasted in a chat message do anything when you
   tap it on iOS (open in Safari, open in-app, nothing)?
3. When a screenshot is embedded via Markdown image syntax pointing at a `.context/` path in a
   chat reply, does it render as an image for you on the iOS app?
4. Can you open a `conductor preview set` URL directly in mobile Safari (not just inside the
   Conductor app)?
5. On the iOS app's PR view, does a long PR body's markdown table (e.g. a 14-row table) render
   fully, or does it get truncated/collapsed?

**Answered, 2026-10-03 (orchestrator):** *is the `conductor` CLI available and authenticated
inside an ordinary worker's cloud sandbox, not just the orchestrator seat?* **Yes.** The S0
worker created seven workspaces with it from inside its own sandbox, and this investigation
independently ran `conductor preview --help` / `conductor auth whoami` from an ordinary worker
seat (not the orchestrator) to ground §1 — both are live evidence, not inference. This closes
option 1 in §8's remaining open precondition: a flow skill *can* assume the CLI is reachable
from whichever sandbox it runs in, without a capability probe first.

## 7. Further areas beyond Ben's two (named, not investigated to the same depth)

- **Notification pull vs. push.** Nothing found confirms whether reaching a human gate pushes a
  phone notification to Ben or whether he has to know to open the app and check. If it's pull-only,
  every other finding here is moot until he happens to look.
- **Dense tool-call transcripts on a small screen.** A worker session heavy with diffs/test
  output/long bash transcripts presumably renders differently (more collapsed, more truncated) on
  iOS than Mac — unconfirmed, and a plausible second instance of the "reading is harder on
  mobile" theme beyond the two artifacts Ben named.
- **Fleet-level triage from the phone.** Changelog evidence (**[secondary]**, from search
  results rather than a fetched primary page) says *"mobile workspace rows now show the same
  status details as desktop"* — if accurate, this already answers "can Ben triage several
  parallel workspaces from his phone without opening each one" reasonably well; worth confirming
  directly rather than citing the secondary source as settled.
- **Org-visibility creep from `conductor preview set`.** Covered as a cost in §8 option 1, but
  worth naming as its own area: once an artifact is reachable by URL, *anyone with workspace read
  access* can reach it, which is a different and broader audience than "whoever Ben hands the
  link to."

## 8. Ranked options — cost, consumer impact, security; nothing here is decided or built

1. **Serve the ephemeral HTML artifacts (gate-1's presented prototype, the merge-gate walkthrough)
   over a real URL via `conductor preview set`, instead of a bare/`file://` path.**
   Mechanism: `nohup python3 -m http.server <port> --bind 127.0.0.1 --directory <dir> &` then
   `conductor preview set --port <port>`; hand the human `<preview URL>/<file>.html`.
   **Cost:** small — a few lines in `prototype/SKILL.md` §8 and `verify-build`/`ship`'s hand-off
   lines. The CLI's own reachability from an ordinary worker sandbox is now confirmed (§6's
   answered question — not just the orchestrator seat), so no capability probe is needed inside
   Conductor; still fall back to today's `file://`/path string when the CLI or an authenticated
   context is absent (any non-Conductor flow consumer).
   **Consumer impact:** Conductor-specific — a flow consumer not running inside Conductor cloud
   workspaces has no equivalent, so this must stay an optional best-effort branch, never a
   requirement (flow's "project-agnostic by default" principle, `CLAUDE.md`).
   **Security:** confirmed **not public** — gated by Conductor sign-in + workspace read access
   (`conductor preview set --help`, primary) — but reachable by anyone who already has read
   access to that workspace, and the URL persists until the workspace sleeps/archives, not just
   for the moment of approval. Same fix-family as D6's already-measured `file://`-origin failure
   in this exact codebase (served over `http://localhost` to fix a mic-permission bug) — not a
   novel idea here, a second application of one already proven useful.

2. **Embed the committed `visual-history-assets/` frames as real PR-body images
   (`raw.githubusercontent.com` URLs), not just a link to an unrendered `.html` file.**
   **Cost:** small — the PNGs already exist and are committed by PR-open time; this is a
   markdown-string change to the PR-body template / `## Flow run` row, not a new capture path.
   **Consumer impact:** universal, no Conductor dependency — works on any client, any device,
   because it's plain GitHub markdown. Directly answers "running them at all" for the single most
   common case (a before/after still) without needing the interactive walkthrough at all.
   **Security:** none — these are already-committed, already-team-visible assets.
   **Limit:** doesn't cover the interactive walkthrough (annotation layer, open-questions block,
   per-criterion verdict cards) — complements option 1, doesn't replace it.

3. **Make the unreachable hand-off say so, instead of implying "open this."** Change
   `Walkthrough (local, uncommitted): <verifyReportPath>` to something that states plainly it's
   only openable from the producing machine/sandbox when no externally-reachable copy exists.
   **Cost:** trivial — a string change, maybe paired with a capability check.
   **Consumer impact:** universal, no behavior change — pure honesty, in the same spirit D1d
   already uses ("nothing has rendered it… the least hospitable possible version of the moment").
   **Security:** none.

4. **Default the annotation layer to the touch profile when touch is detected** (`(hover: none)`
   media query: hover-outline off / flash-on-commit on by default; a one-tap way to pass a click
   through to the prototype without hunting for the mode toggle).
   **Cost:** moderate — this is a change to a shipped, heavily a11y-considered file and needs its
   own fixture per this repo's own "prompt/code changes are code changes" rule; explicitly **out
   of scope for this document** to actually make.
   **Consumer impact:** universal improvement for any touch reviewer, additive CSS/JS, no
   regression for mouse users.
   **Security:** none.

5. **A durable, glanceable "where things stand" surface**, so a human doesn't have to scroll
   chat history to find the current gate state on a small screen — in the spirit of D1c's proposed
   deterministic `handoff_lines[]`, or simply leaning on Conductor's own per-workspace status
   list (§7) instead of flow inventing a second one.
   **Cost:** mostly a convention change (field-manual §3's rules already exist; this is about
   applying them beyond gate 1) rather than new engine code.
   **Consumer impact:** mainly orchestrator-seat workflows, not every flow consumer — lower
   priority for the plugin itself, more relevant to how Ben specifically runs this program.
   **Security:** none.

## 9. Sources

**Primary (fetched/run directly):**
- `plugins/flow/skills/prototype/SKILL.md`, `plugins/flow/skills/verify-build/SKILL.md`,
  `plugins/flow/skills/verify-build/lib/annotation-layer.html`,
  `plugins/flow/skills/verify-build/lib/render-report.py`, `plugins/flow/skills/ship/SKILL.md`,
  `plugins/flow/skills/ship/lib/manifest-triage.py`,
  `plugins/flow/skills/ship/lib/insert-visual-history.py` — all read from this repo checkout,
  `main` @ `a250b66` (v1.55.0).
- `dev-docs/roadmap.md` §§ D1a/D1c/D1d/D5/V3/V3a/V3b; `research/orchestrator-field-manual.md` §§
  3, 7; `research/voice-annotation-pipeline-2026-07.md`.
- `conductor --help` / `conductor preview set --help` / `conductor auth whoami` (installed CLI
  v0.1.0, this session).
- [Conductor changelog 0.90.0 "Conductor for iOS"](https://www.conductor.build/changelog/0.90.0-conductor-for-ios) (2026-10-02)
- [Conductor changelog 0.78.0 "Introducing Conductor Cloud"](https://www.conductor.build/changelog/0.78.0-introducing-conductor-cloud)
- [Conductor changelog 0.62.0 "Repo settings, browser preview"](https://www.conductor.build/changelog/0.62.0-repo-settings-browser-preview)
- [Conductor docs — Settings reference](https://www.conductor.build/docs/reference/settings/reference)
- [Conductor docs — Cloud FAQ](https://www.conductor.build/docs/cloud/faq)

**Secondary (third-party reporting, not independently verified against Conductor's own docs):**
- [runtimewire.com — "Conductor launches an iPhone app to control cloud coding agents"](https://runtimewire.com/article/conductor-iphone-app-cloud-coding-agents)
- [grokipedia.com — "Conductor.build"](https://grokipedia.com/page/Conductorbuild)
- Search-result-only changelog summaries citing "mobile workspace rows now show the same status
  details as desktop" and "one-click PR approval" (§7, §1) — real changelog entries exist but
  were not independently re-fetched verbatim; treat as directionally right, not word-for-word
  confirmed.

**External comparison (primary where linked):**
- [Vercel — Preview Deployments](https://vercel.com/docs/deployments/environments),
  [Vercel — Deploying GitHub projects](https://vercel.com/docs/git/vercel-for-github) — URL-based
  PR previews, openable on any device including mobile, the direct contrast to flow's local-file
  artifacts.
- GitHub's own PR-comment image embedding (screenshot-to-PR-comment via Actions + API, no
  Conductor/flow-specific tooling needed) — the pattern behind option 2 above.
