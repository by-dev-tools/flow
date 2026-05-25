---
description: Tauri UI / design-system rules — loads when editing frontend source.
paths:
  - "src/**/*.tsx"
  - "src/**/*.jsx"
  - "src/**/*.vue"
  - "src/**/*.svelte"
  - "src/**/*.css"
  - "src/**/*.scss"
---

# UI rules (Tauri front-end)

Same rules as the web stack — read `core-docs/design-language.md` first; use tokens, not raw values; WCAG 2.1 AA baseline; honor `prefers-reduced-motion`.

## Tauri-specific additions

- **Window chrome.** Tauri apps can have OS-native or custom decorations. If custom: implement drag region, traffic-light controls, focus/blur visual feedback. If OS-native: don't reinvent.
- **Native menus.** macOS app menus (File / Edit / View) need keyboard shortcuts that don't conflict with web shortcuts in the same surface.
- **Tauri invoke calls have latency.** Frontend should show optimistic UI or loading states for `invoke()` calls > 100ms.
- **No web-only APIs in Rust-bound code.** `localStorage`, `IndexedDB`, etc. work in the WebView but their behavior under Tauri's CSP may differ from a browser. Verify in `tauri dev`.

## When in doubt

`/flow:staff-review`'s UX-designer and design-engineer lenses cover both web and Tauri-shell idioms. Push-further lens specifically looks for opportunities to use Tauri-native affordances (system tray, notifications, file-system integration) where the web equivalent is weaker.
