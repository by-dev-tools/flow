### FB-0095 — Don't silently narrow a requested audit scope; disclose the exclusion as its own escalation

**What was said (2026-08-27, plan-gate critique + human review of the AB Step 1 plan):** `/flow:critique-plan` flagged that the drafted v1 harness-weight audit scope silently dropped "gates" from the roadmap's own "always-loaded surface **+ gates**" framing — two disclosed phasing decisions existed, but the gate-scope narrowing wasn't one of them. Separately, the human's plan-gate review caught that excluding full `SKILL.md` bodies as "JIT-loaded, not always-loaded" was technically correct but practically wrong for `ship/SKILL.md` (1,384 lines, the heaviest prompt in the repo) — a scope rule applied too literally, missing the case it most needed to catch.

**Synthesized rule:** When a plan narrows a requested scope for a defensible reason, that narrowing is itself a decision that needs its own explicit escalation (recommendation + confidence + justification) — not just the phasing/placement decisions that were already top-of-mind. A generically-correct exclusion rule (e.g. "JIT-loaded content isn't in scope") must be checked against its most consequential instance before being applied, not just against the abstract category.

**Why:** A scope narrowing that never gets named reads, at review time, identically to a scope narrowing nobody noticed — the reviewer (human or `/flow:critique-plan`) can't distinguish "considered and deferred" from "silently dropped" unless it's written down. This is the same failure shape FB-0010 names for fan-out contradictions, applied to plan scope instead of code contracts.

**Applies to:** any plan that scopes a request down from what was literally asked (audits, refactor boundaries, "which surfaces/files does this touch"); plan-gate discipline generally.

**Validation:** caught before execution both times — once by `/flow:critique-plan` (gate scope), once by the human (SKILL.md-body scope) — zero cost beyond a plan revision, exactly because the escalation format surfaced the reasoning for review before code was written.

**Renumbered from FB-0093** at rebase — FB-0093 was independently claimed and merged by `conductor/phase-00-rules-as-skills-hooks-fix-fb-0085` for an unrelated concept ("a bug-fix PR corrects claims that are false today") while this branch was in flight.
