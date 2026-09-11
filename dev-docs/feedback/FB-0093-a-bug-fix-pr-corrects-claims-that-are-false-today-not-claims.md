### FB-0093 — A bug-fix PR corrects claims that are false today, not claims about work tracked elsewhere

**What was said (2026-08-27):** Approving the Phase 00 plan (FB-0085's fix — converting 4 dead `rules/*.md` files to path-activated skills, plus a doctor loader-verification check), the user added: "Do NOT update README.md's user-facing claims beyond what is true when your PR lands; README currency is being tracked separately and must not describe unbuilt behavior."

**Synthesized rule:** When a fix makes a previously-false doc claim true (here: "4 auto-loading rules" — false before this PR, true after), leave that claim's wording alone — the fix already closed the gap, no edit needed. Don't use the same PR to also advertise *other* not-yet-built behavior, or to get ahead of a doc-currency initiative that's tracked as its own separate effort. Scope discipline applies to doc claims exactly like it applies to code: fix what's actually broken by this change, not what could be improved while you're in the file.

**Why:** README is a project's most-read surface; a bug-fix PR that quietly expands its claims (even accurately, even with good intent) makes README currency two owners' responsibility instead of one, and the second owner won't know this PR touched it.

**Applies to:** any flow PR that fixes a doc claim to make it true — check whether the fix alone suffices before adding surrounding polish. Related: [[FB-0010]] (fan-out discipline — the same "don't touch what wasn't asked" boundary, applied to prose instead of code).
