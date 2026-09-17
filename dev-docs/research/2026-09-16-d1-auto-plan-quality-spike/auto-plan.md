# Auto-written technical plan — click-to-pin annotation overlay

**Simulated context (§9.3 spike):** this plan is auto-written by the D1 agent immediately
after prototype approval (human gate 1), against the approved prototype at
`plugins/flow/skills/verify-build/lib/annotation-layer.html` (treated here as a freshly
approved prototype for a "reviewable surface gets located human feedback" feature, not as
the already-shipped artifact it happens to be in this repo — see the spike note for why).
No code has been written yet; this plan is the thing the machine gate (`auditor` +
`plan-critic` + push-further) would review before Execute.

**Goal:** Let a human leave *located* comments on a rendered HTML surface (a report, a
prototype, any reviewable static page) by injecting a self-contained overlay before
`</body>`. The human clicks an element, writes a note pinned to it, and exports every note
as one structured block the agent can act on — replacing free-text feedback the agent has
to guess the referent of.

**Scope (in):** the overlay script itself (mode toggle, pin placement, anchor resolution,
comment CRUD, batch export) and its integration point (inject-before-`</body>`, graceful
no-op when the target page has no frame to annotate).

**Scope (out):** the renderer that decides *when* to inject (assumed to already produce the
HTML page); multi-page/multi-report aggregation; server-side persistence (notes are
client-local only, `localStorage`).

**Files touched:** `overlay/annotation-layer.html` (new), the report renderer's injection
call site (existing file, one new call), a contract eval fixture for the injection path.

**Spec-walk:**
- [ ] Clicking an element while commenting mode is on opens a comment editor pinned to that element → verify: manual click-through in a browser.
- [ ] Commenting mode persists across reloads via `localStorage` and defaults to on → verify: toggle off, reload, confirm state survives.
- [ ] A modifier-click (or equivalent escape hatch) passes the click through to the underlying page so links and interactive prototypes still work while commenting is on → verify: manual check.
- [ ] Selecting text never creates a pin → verify: manual check (drag-select a paragraph, confirm no editor opens).
- [ ] Notes survive a page re-render/regeneration by matching on content (heading + tag + role + text sample, or an author-supplied `data-pin-id`) rather than DOM index → verify: manual check across two renders of the same content.
- [ ] An anchor that stops resolving after a re-render is kept and exported, flagged, rather than silently dropped → verify: manual check (remove the anchored element, confirm the pin still lists in the panel as lost).
- [ ] "Copy notes" produces one structured, per-screen text block on the clipboard → verify: manual click + paste.
- [ ] When the clipboard API is unavailable (e.g. `file://`), a visible select-and-copy fallback appears instead of failing silently → verify: manual check under `file://`.
- [ ] The overlay works correctly with no native `confirm`/`alert`/`prompt` calls (so it is safe to inject into any static page, including `file://`) → verify: grep the script for `confirm(`/`alert(`/`prompt(` and confirm none are present.
- [ ] Screen-reader users get an announcement when commenting mode toggles or the note count changes, via a visually-hidden live region → verify: manual check with a screen reader (or inspect the live-region text update in devtools).
- [ ] The floating control and comment panel behave as expected across light and dark mode → verify: manual check with OS dark mode toggled.
- [ ] Injection into a report with no captured frame is a no-op — the report still renders, read-only, no broken script errors → verify: manual check against a frameless report.
- [ ] An unreadable/corrupt overlay file degrades to the read-only report rather than crashing the renderer → verify: manual check with the overlay file temporarily truncated.
