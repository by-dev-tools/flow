---
paths:
  - "src/**"
  - "app/**"
  - "lib/**"
  - "packages/**"
---

# Exploration Surface Rule (flow plugin)

Loads automatically when touching code under common source roots (`src/`, `app/`, `lib/`, `packages/`). The trigger paths are intentionally generic; consumer projects with non-standard layouts can override by shipping a project-local rule that shadows this one (project-scope rules take precedence over plugin-scope rules).

The project's roadmap doc (`flow.config.json.roadmapPath`; default `dev-docs/roadmap.md`; consumer projects typically `core-docs/roadmap.md`) carries a § Exploration section. Items there collect open-ended directions surfaced by `/flow:staff-review`'s push-further lens or by user curiosity. Each entry carries a `Surfaces when:` trigger naming the file paths / area that should re-surface it.

## What this rule does

**Before finishing UI / code work**, scan the roadmap doc's § Exploration for items whose `Surfaces when:` trigger names the file(s) you touched. If any match:

1. **inline-cheap candidates** — propose applying inline if the user agrees; the work is small (≤30 min, single concern). Don't auto-apply without surfacing.
2. **roadmap-concrete candidates** — mention to the user for awareness. They may want to scope/queue the item as a real PR after the current one ships, or defer.
3. **future-exploration items** — mention only if the current change opens a path toward exploring the item, or directly demonstrates the gap the item names. Otherwise leave alone — the trigger fired, but if there's nothing to do about it on this PR, don't burden the conversation.

## Why this exists

Exploration items decay if no one looks at them. The Exploration section lives in the roadmap doc precisely so it's adjacent to the other planning docs an agent reads at session start — but a long Exploration section is hard to scan in full on every PR. The `Surfaces when:` trigger + this rule do the matching automatically so the right item shows up at the right moment without forcing every session to read the whole section.

## Don't

- **Don't auto-apply** an inline-cheap finding without proposing first. The exploration item is a suggestion, not a queued task.
- **Don't expand scope** of the current PR to address every triggered item. One inline-cheap fix bundled into a related PR is fine; three is scope creep. The remaining items wait for their own pass.
- **Don't add new exploration items here** — `/flow:staff-review`'s push-further lens owns that (or a future `/flow:uncommon-care`-style skill). This rule is read-only on the Exploration section.

## Coexists with safety.md

If the project ships its own `safety.md` rule (project-scope, paths-frontmatter-matched to safety-critical files), both this rule and `safety.md` may fire on the same change. They speak to different concerns:

- `safety.md` is about *not silently downgrading* existing safety behavior (error handling, persistence, sanitization) — protective, defensive.
- This rule is about *surfacing improvement opportunities* — generative, additive.

When both fire on the same file, honor `safety.md` first (preserve existing safety guarantees), then surface relevant Exploration items separately. The Exploration items themselves should already respect the safety surface (the push-further lens reads safety-critical paths while running), so collisions in practice are rare.
