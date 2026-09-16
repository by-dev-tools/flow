# Design brief (simulated — reconstructed for the §9.3 spike, not a real session artifact)

1. **Problem** — reviewers leave feedback on rendered reports as loose prose the agent has to guess the referent of; comments get disconnected from the exact element they're about.
2. **Whose moment** — the human at the merge-gate review, reading a rendered HTML report and wanting to point at specific things.
3. **Constraints** — must work on a static/injected page, no server, no build step, no native browser dialogs, must degrade safely if injected into a page with nothing to annotate.
4. **Intended scope** — click an element, pin a comment to it, export all comments as one structured block; persist locally across reloads.
5. **Deliberately excluded** — multi-user/real-time collaboration, server-side storage, editing the underlying report content itself.
6. **Where this pushes past the literal request** — accessibility parity (screen-reader announcements, keyboard operability) even though the ask was framed only around mouse-driven pinning.

**Prototype approved at gate 1 (simulated):** `plugins/flow/skills/verify-build/lib/annotation-layer.html`.
