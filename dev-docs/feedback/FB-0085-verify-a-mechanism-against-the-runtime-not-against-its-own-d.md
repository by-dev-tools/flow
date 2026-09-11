### FB-0085: Verify a mechanism against the runtime, not against its own documentation

**Date:** 2026-08-12  *(renumbered FB-0075 → FB-0084 → FB-0085; #92/#95 then #106 took the numbers while this branch was open)*
**Source:** user direction

**What was said:** Asked to make Flow service-agnostic, the user twice redirected toward verification rather than design: "make sure we do not risk the existing plugin running correctly (several projects rely on this)", and later "make sure that this doc is easily findable... I don't want research docs buried... we should make sure there aren't stale docs." Both asks were about whether a claimed mechanism actually fires, not about whether it was well described.

**Synthesized rule:** A claim that a mechanism works is only as good as the runtime check behind it. Before proposing a structural change to a shipped artifact, exercise the real loader — not the docs *about* the loader. Applying this to a proposed multi-host layout found two shipped-but-never-loading features that every doc asserted were load-bearing: plugin `rules/` is not a Claude Code plugin component (no loader call site joins a plugin root), and `hooks/default-hooks.json` matches no auto-discovery default. Both were advertised in `README.md`, the marketplace description, and `/flow:doctor`. The same discipline caught a `bin/` PATH-injection hazard in the proposal itself before it was written. Corollary for docs: a point-in-time doc is buried by default — index it at creation and give it a `Status:` line that is true *now*, because a stale "in progress" is indistinguishable from a current one.

**Applies to:** plugin packaging, `/flow:doctor` checks, dev-docs indexing, any multi-host adapter work, FB-0074's class
