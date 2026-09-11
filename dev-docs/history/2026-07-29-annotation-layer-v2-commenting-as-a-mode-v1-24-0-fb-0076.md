## 2026-07-29 — Annotation-layer v2: commenting as a mode (v1.24.0, FB-0076)

**Branch:** `claude/flow-design-workflow-3a9392` · **SHA:** `e4d6f51`

**What was done (user-facing).** The `/flow:verify-build` annotation overlay was redesigned. Commenting is now a persistent mode, on by default: click an element, write or dictate, `↵`, click the next one — no re-arming between comments. Chrome collapsed from a full-width page header + two dock buttons to ONE circular floating control (the minimized comment container; filled = live, carries the count) that expands to a panel holding a labelled Commenting switch, hover-outlining and hide-pins toggles, per-row copy/delete, Copy all, and a two-tap Delete all. Toasts were removed entirely. Anchors, the located-descriptor export, and the `file://` hardening are unchanged.

**Why.** Six rounds of user review, conducted by annotating the prototype with the prototype (see FB-0076). The decisive note: having to re-press "Pin" between every comment made the button, not the mode, the design error.

**Design decisions.**
- **Mode over action.** Considered keeping a per-comment arm (familiar, no escape hatches needed) vs a persistent mode. Chose the mode because the loop is "many comments in one sitting" — but a mode that swallows every click would break interactive prototypes, which the user names as their highest-value artifact. So the mode ships *with* three escape hatches: modifier-click passthrough, a text-selection guard, and Esc. Keeping the button as an off-switch (rather than deleting it, as the user initially proposed) is what makes the mode safe on a prototype you actually need to click through.
- **The switch outranks the icons.** Commenting changes what a click *does*; hover-outlining and hide-pins only change what you *see*. Encoding all three as peer grey icons made the most consequential control invisible. The switch got its own labelled row at the top; the comment count dropped to an eyebrow beneath it.
- **Feedback on the control, not floating over it.** Toasts were covering the very buttons they described. Each control now states its own condition (switch, swapped icon, transient label), following the two-step Delete-all pattern that already existed. A visually-hidden `role="status"` region carries the same information to screen readers — removing the toast removed the only announcement channel, which would have been a silent a11y regression.
- **Kept flow's anchors over ripe's.** The ripe project's overlay (the visual reference for the floating chrome) anchors by tag + child-index path, which breaks whenever the document is re-rendered — i.e. most of the time for a report regenerated every iteration. Only the chrome was adopted; the content-derived anchor was kept.

**Technical decisions.**
- Element ids renamed `annot-*` → `an-*`; storage key `flow-annot:` → `flow-annotations-v2:`. Existing comments are NOT migrated — a review overlay's notes are per-iteration and the migration cost was not worth the code.
- `#an-chip:not(.has)` rather than a bare `#an-chip` for the hidden state: `#an-dock button` is more specific than a lone id, so the plain rule lost and the empty chip rendered "0".

**SAFETY — three defects found by the staff design + UX review, all silent-failure class.**
1. **Capture-phase `preventDefault` on every `Enter`/arrow.** The keydown handler cancelled the default action before checking whether a pick target existed. Because `Enter`'s default action on a button IS the synthetic click, this made every control in the layer un-activatable by keyboard, blocked arrow-key scrolling, and swallowed `Enter` inside the host page's own form fields. Confirmed empirically before fixing. Now scoped: chrome and form fields return early, and `preventDefault` only fires when a target is actually set.
2. **White-on-accent failed WCAG in dark mode** across five filled surfaces (pin numerals, FAB count, list badges, Save, armed Delete-all) — 2.68:1 against the lightened dark accent. Replaced with themed `--an-on-accent` / `--an-on-danger`. Light mode was fine, which is why it survived: nobody screenshotted the other mode.
3. **18 invalid `font:` shorthands** (`font: 600 13px/1 inherit`). A CSS-wide keyword cannot be a shorthand component, so every declaration was dropped and the layer had been rendering in the host report's typography the whole time. Found only because the user reported the hierarchy read flat and the sizes were measured rather than eyeballed. Converted to longhands.

**Tradeoffs discussed.**
- **Two clicks between comments.** A click while the editor is open saves and returns; it does not also start the next pin. Committing *and* picking from one click is a one-line change but a real behaviour decision — deliberately deferred rather than made in-tree (roadmap § Next).
- **Turning commenting back on takes two clicks** when the panel is closed (open panel → flip switch), where the old arm-button took one. Accepted because commenting defaults to on and stays on; flagged to the user.
- **`resolve()` is O(nodes × heading-walk) and runs twice per comment per render**, with render bound to a `ResizeObserver`. Fine at the comment counts seen so far; memoization is queued rather than done speculatively.

**Follow-ups routed to the roadmap** (not done here): type-scale/spacing/radius systematization, the accent's hue collision with the report's own `need` chip, panel/popover entrance animation, focus-trap architecture for the two dialogs, `resolve()` memoization, and the positioned-ancestor exposure (`transform` on a host ancestor breaks `position: fixed` chrome).
