---
description: Surface the dev URL after UI work — loads when editing UI source.
paths:
  - "src/**/*.tsx"
  - "src/**/*.jsx"
  - "src/**/*.vue"
  - "src/**/*.svelte"
  - "src/**/*.css"
  - "src/**/*.scss"
  - "app/**/*.tsx"
---

# Dev server surfacing

After a UI change lands (or before `/flow:staff-review` runs on a UI diff), invoke `/link` to start (or confirm) the project dev server, then surface the URL in your reply so the user can verify in-browser.

The `/link` skill is **project-specific** (port + start command differ per stack). The web-stack template ships a Vite-on-5173 version; your project may differ.

## Pattern

When a UI change is implementation-complete:
1. Run `/link`.
2. Include the returned URL in your final message: "Dev URL: http://localhost:5173" (or wherever).
3. `/flow:staff-review` will reference the URL in its reviewer-notes template so human review can hit the same surface.

Skip this rule for backend-only changes, doc-only changes, or non-UI refactors.
