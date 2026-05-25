---
description: UI / design-system rules — loads when editing UI source.
paths:
  - "src/**/*.tsx"
  - "src/**/*.jsx"
  - "src/**/*.vue"
  - "src/**/*.svelte"
  - "src/**/*.css"
  - "src/**/*.scss"
  - "app/**/*.tsx"
  - "packages/ui/**/*"
---

# UI rules

## Read design-language.md first

If `core-docs/design-language.md` exists, **read it before changing any UI file**. It defines:
- Tokens (color, space, radius, type, motion) and which to use where.
- Axioms (load-bearing decisions the design language depends on).
- Component conventions (chrome, hover/focus, empty/loading/error states).
- Motion principles (duration, easing, reduced-motion handling).

If `design-language.md` doesn't exist yet, surface that — propose creating it for non-trivial UI work. Even a 1-pager naming the token vocabulary saves rework.

## Tokens, not raw values

- Use design tokens (`var(--space-*)`, `var(--radius-*)`, `var(--text-*)`, theme classes) — NOT hardcoded `px`, hex colors, or magic numbers.
- New token? Add to `design-language.md` first, then use it.
- Exceptions: animation timing under 100ms (often hardcoded for performance reasons), one-off layout calculations driven by content.

## Accessibility baseline (WCAG 2.1 AA)

- Semantic HTML over div/span with handlers (`<button>` not `<div onClick>`).
- Every interactive element keyboard-reachable; tab order matches visual order.
- Focus rings visible on every focusable element (`:focus-visible`).
- Color contrast: 4.5:1 for text; 3:1 for UI components (focus rings, borders).
- `prefers-reduced-motion` honored on every transition > 150ms.
- Icon-only buttons have `aria-label` describing the action ("Open menu", not "Three dots").

`/flow:accessibility-review` runs at /flow:ship time. **Don't rely on it as the only gate** — author with a11y baseline in mind.

## When in doubt

- `/flow:staff-review` runs 4 lenses including UX-designer and design-engineer; they'll surface drift from design-language.md and craft issues.
- Push-further lens flags missed opportunities to push the surface beyond on-system to memorable; output is honest by default (empty is valid).
