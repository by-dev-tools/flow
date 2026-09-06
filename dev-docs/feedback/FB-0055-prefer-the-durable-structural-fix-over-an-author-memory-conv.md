### FB-0055: Prefer the durable structural fix over an author-memory convention; decouple an independent capture path from a sibling extraction's success

**Date:** 2026-06-21
**Source:** user direction

**What was said:** Choosing how far to go on the Spec-walk routing fix, the user declined the lighter "warn + document the qualify-your-retained-headings convention" option and asked: "is option 2 what we ultimately want? do the most robust fix in line with our intent." I.e. fix the root structure, not paper over it with a convention that depends on authors remembering to qualify headings.

**Synthesized rule:**
1. **Robust over interim.** When a parser tolerates non-canonical input, prefer the structural fix (here: scope extraction to the active/first block) over a convention that relies on author memory to avoid breakage — the latter is the FB-0010 "consistency depends on author memory" smell. The interim "retained Spec-walk blocks MUST qualify their heading so they self-exclude" convention is now retired: the active PR's plan goes at the top, retained blocks are ignored, no qualification needed.
2. **Watch for co-dependent changes.** Loosening the heading match and scoping-to-first-block had to land *together*: under the old strict regex, retained blocks self-excluded *because* their qualified headings failed to match; loosening the match alone would have re-aggregated every stale block. When relaxing a matcher, check what previously depended on its strictness.
3. **Decouple independent pipelines.** An independent capture path (visual, §5a) must never be gated behind a sibling extraction's success (behavioral Spec-walk). The two declare separate blocks; coupling them let a behavioral-extraction failure silently drop the visual deliverable. Each gate gets its own predicate.

**Applies to:** workflow, code, architecture — `verify-build` lib parsers, §5a routing, plan-discipline conventions, and the general "robust-vs-convention" + "decouple independent gates" disciplines.
