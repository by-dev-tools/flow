# FB-0121 — "Nothing found" must say whether that means "nothing there" or "I could not see" — fixed in `/flow:audit-coverage`'s engine, stated nowhere a consumer reads

- **Date:** 2026-09-26
- **Source type:** hand-harvest of the lesson-harvest queue (see [[FB-0111]], [[FB-0118]] — same
  drain-was-disabled circumstance).

- **What was said:** `/flow:audit-coverage`'s engine already implements the fix — verified 2026-09-26 at
  `plugins/flow/skills/audit-coverage/SKILL.md:83,111`: an unresolvable base ref emits its own
  `ROOT-UNRESOLVED`-shaped line and is explicitly never allowed to collapse into the ordinary `SKIPPED`
  ("nothing to audit") line. `.claude/rules/general.md` § Consistency item 4 states the general version
  of the same principle in its worked example: *"the engine's empty-file-list path is unreachable from
  the shipped shell, and the shell's substitute printed SKIPPED ... for a whole PR's behaviour."*

  But the principle — **a gate that found nothing must distinguish "there was genuinely nothing to
  check" from "I was unable to check"** — exists only in shell-comment form at the two engine call sites
  and in one worked example inside a dev-side rules file. `plugins/flow/skills/audit-coverage/SKILL.md`
  has no "Gotchas" / design-principle section stating it as a rule a future maintainer (of this skill, or
  of a similarly-shaped one) would read before writing a new short-circuit path. It is discoverable only
  by reading the shell comments inline, which a maintainer skimming the skill's prose sections would
  not naturally do.

- **Synthesized rule:** a fix that closes a specific "clean-looking wrong answer" bug should also state
  the general principle *once, in prose, at the surface a future maintainer of that surface actually
  reads* — not only as an inline comment at the two lines it happened to touch. This is the same shape as
  [[FB-0118]] and [[FB-0119]]: the principle is real and correctly applied, but it lives one layer below
  where the next person making a similar decision would look for it.

- **Candidate promotion (not implemented here):** add a short "Gotchas" or "Design principle" note to
  `plugins/flow/skills/audit-coverage/SKILL.md` — *"A short-circuit path (SKIPPED, no findings, clean
  pass) must never be reachable from an error state (unresolvable ref, malformed input, tool failure).
  If enumeration could not run, say so distinctly — never let 'I could not look' render as 'there was
  nothing to find.'"* — near the engine sections it already governs (Stage 1/Stage 2, or "What to
  check"). Same family as FB-0082's `absent`/`invalid`/`stale`/`ok` distinction; this is that doctrine
  applied to a coverage gate's empty-result case specifically.

- **Applies to:** `plugins/flow/skills/audit-coverage/SKILL.md`. Related: [[FB-0082]] (the distinct-state
  family this belongs to), `.claude/rules/general.md` § Consistency item 4 (where the principle is
  currently stated, dev-side only).
