---
description: Surface the dev URL after UI work — loads when editing UI source.
paths:
  - "src/**/*.tsx"
  - "src/**/*.jsx"
  - "src/**/*.vue"
  - "src/**/*.svelte"
  - "src/**/*.css"
  - "src/**/*.scss"
---

# Dev server surfacing (Tauri)

After a UI or Rust-command change lands (or before `/flow:staff-review` runs on a UI diff), invoke `/link` to start (or confirm) the Tauri dev environment, then surface the URL in your reply so the user can verify in-browser AND in the Tauri window.

The `/link` skill is **project-specific** (port + start command differ per stack). The tauri-rust-ts template ships a `tauri dev`-on-5173 version; your project may differ.

## Pattern

When a UI or `src-tauri/` change is implementation-complete:
1. Run `/link`.
2. Include the returned URL in your final message: "Dev URL: http://localhost:5173" (Tauri window opens automatically; URL also browseable for headless verification).
3. `/flow:staff-review` will reference the URL in its reviewer-notes template so human review can hit the same surface.

Skip this rule for backend-only changes that don't touch `src-tauri/`, doc-only changes, or non-UI refactors.

## Tauri-specific note

First `tauri dev` run is slow (cargo builds all deps; can be 60-120s). Subsequent runs are fast. If the dev environment is slow to surface, that's likely the first-build penalty, not a failure.
