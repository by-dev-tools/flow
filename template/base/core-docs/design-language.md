# Design language

The project's visual/interaction rulebook — grounding for `/flow:staff-review` (UX, design-engineer, push-further lenses) and `/flow:accessibility-review`. Optional: a project with no UI surface (`flow.config.json.uiSurface: false`) doesn't need this file.

This template ships **shape only** — sections every design-language doc needs to be usable by an agent, no content. Fill in your project's actual taste; delete any placeholder text you don't replace.

---

## Axioms

<!-- Numbered, falsifiable rules — phrased so a violation is pointable, not a matter of opinion. "Violate = design bug." One sentence each.
Example: "1. Every interactive control has a visible focus state. No exceptions for 'it looks cleaner without.'" -->

## Anti-patterns

<!-- Named patterns to recognize and reject on sight — giving a pattern a name makes it far easier for an agent to catch than a vague "avoid X-ish things." Group by surface if useful.
Example: "Neon accents. Raw hex in a component (use a token). Linear ease on anything longer than 150ms." -->

## Priority order

<!-- The single most commonly missing piece in design docs we've seen. When two rules in this file conflict, which wins? A numbered list, most important first.
Example:
1. Accessibility (contrast, focus, motion-reduction) — never traded away for aesthetics.
2. Content legibility — the reader's task always beats decoration.
3. Brand consistency — token/typography rules.
4. Novelty / delight — only after 1-3 are satisfied. -->

## Tokens

<!-- Pick ONE home for token values and say so explicitly — never both, or they will drift:
- "Values live inline in this doc — this file is the source of truth." (then list them below), OR
- "Values live in code at <path> — this doc names identifiers only, never raw values." (then list identifier names, not values)
A doc that duplicates values in two places is a doc that will drift; see the token names below only if you chose the code-pointer form. -->

## Coverage gaps

<!-- What has no standard yet? Naming the gap is cheaper than pretending it's covered, and tells an agent "improvise carefully here" instead of "follow a rule that doesn't exist."
Example: "No standard yet for empty-state illustration style. No standard yet for error-toast copy tone." -->

---

## Authoring rule

Write corrections as observable decisions, not impressions. An agent can check "let evidence tables use the full available width" against a render; it cannot check "make the table feel less cramped." When you correct a generated result, encode *what changed* here, in checkable language, rather than leaving the correction only in a PR comment or your own memory.
