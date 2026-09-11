## Service-agnostic research + Codex/Cursor roadmap, and a dev-docs index

**Date:** 2026-08-12
**Branch:** `claude/flow-service-agnostic-96aec1` — merged #105 @ `e1a73937f`
**Mode:** feature (docs-only) — no plugin artifacts changed

**What was done.** Two research docs and an index. `dev-docs/research/service-agnostic-2026-07.md` is the field survey (standards landscape, prior art, a 13-host capability map). `dev-docs/handoffs/service-agnostic-roadmap-2026-07.md` is the execution plan — self-contained for a cold pickup, with 23 spec-walk checkboxes and 6 confidence verdicts. `dev-docs/README.md` indexes every dev-doc; `CLAUDE.md` now points at it.

**Why.** Two questions had to be answered before any multi-host work could start: can Flow run on Codex/Cursor at all, and what would it cost? The answer changed twice during the research, which is why the survey carries inline supersedes.

**Design decisions.**
- **One repo, one plugin root, three generated manifests** — not three forks, not a runtime abstraction. Chosen because every project that tried runtime abstraction is dead or Claude-only, while the two that work (spec-kit, rulesync) generate per-host artifacts from a neutral source. 36 repos ship this layout; `firebase/agent-skills` has already drifted its `license` across its three manifests, which is the argument for generating two of them rather than hand-maintaining three.
- **The gate guarantee moves out of the host.** Both Codex and Cursor fail hooks OPEN — on timeout, on non-zero-but-not-2 exits, on exit-2-with-empty-stderr. A crashed gate permits and looks like a pass. The answer is the stamped-context invariant, which generalizes machinery Flow already has (`render-test-plan.py`'s "un-stamped buffer reads as un-judged").
- **`tools/flow`, not `bin/flow`.** `bin/` is a documented Claude Code component that PATH-injects; a bare `flow` would collide with Facebook's Flow type-checker in exactly the `web`/`tauri-rust-ts` stacks flow ships.
- **Index + `Status:` lines over archival.** Stale docs were marked, not deleted — three handoffs describing shipped work carried status lines that read as active.

**Technical decisions.** Claude Code regression safety was established empirically (CLI v2.1.141, identical 17-skill/9-agent inventory with all proposed sibling dirs present), not inferred. Codex/Cursor claims are docs- or source-derived and marked ⚠️ where undocumented; neither CLI was installed, so 10 spikes are named as blocking rather than guessed at.

**Tradeoffs.** The survey is left partially superseded rather than rewritten — a research doc records what was believed when, and silently rewriting it would erase the correction trail. Cost: a reader must heed the banner. Accepted because the roadmap is named authoritative for every execution decision.

**Lessons learned.** Two shipped features were found to never load (see FB-0085 and the roadmap's §17/Phase 00). Both were advertised in three places each. The research also drifted against main during the session — five releases — and the rebase caught an FB-number collision (FB-0075 → FB-0084 → FB-0085, twice on this one PR) plus ~15 stale counts, which is the `reserved-feedback-numbers.md` protocol and the stale-base gate both working as designed.
