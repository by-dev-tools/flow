### FB-0037: Designer perspectives are load-bearing in the loop — the ux-designer / design-engineer / push-further lenses must survive dynamic-workflows adoption, not collapse into a generic reviewer
**Date:** 2026-06-03
**Source:** user direction (dynamic-workflows alignment conversation)

**What was said:** "flow's structure intentionally centers designer perspectives, which I want to preserve even as we fully adopt workflows."

**Synthesized rule:** Flow's review surface deliberately carries three design-oriented lenses (`lens-ux-designer`, `lens-design-engineer`, `lens-push-further`) alongside the engineering lens, plus the `designLanguagePath` doc they read from. When `/flow:staff-review` (or any review stage) is ported to a native dynamic workflow, these remain **distinct, named phases** — the workflow fans out *more* coverage per lens (e.g. per-file), it does not merge the four lenses into one general-purpose reviewer to save agents. The `reviewLenses` config slot is the opt-out mechanism (with a documented reason in the plan), not a default-collapse. Design and UX review catch a different class of issue than engineering review; the four-lens triangulation is the value, and it is exactly what fan-out should amplify, never flatten.

**Applies to:** `/flow:staff-review` workflow port, `lens-*` agent definitions, `designLanguagePath`, `reviewLenses` slot, dynamic-workflows adoption
