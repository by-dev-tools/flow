### FB-0005: Marketplace-key-mismatch is a silent-failure UX bug; install docs must verify by name
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's user-scope `~/.claude/settings.json` had `extraKnownMarketplaces.llm-auditor` pointing at `https://github.com/by-dev-tools/flow.git` (stale key from before flow's PR 1 marketplace rename). Project-scope had `"enabledPlugins": { "flow@flow": true }`. Flow's `marketplace.json` declares `name: "flow"`. Result: `/help` silently omitted all `/flow:*` skills. No error, no warning, no diagnostic. Root cause: `enabledPlugins.<plugin>@<marketplace>` resolves by matching the marketplace's `name` field, NOT the user-scope settings key. A stale-keyed entry pointing at the right URL is invisible to the resolver.

**Synthesized rule:** Flow's `docs/bootstrap.md` (NEW projects) and `docs/migration.md` (EXISTING projects with prior `.claude/` content) Step 1 must include an explicit marketplace-name verification step:

```sh
# After /plugin marketplace add by-dev-tools/flow:
/plugin marketplace list | grep '^flow'   # must return a line; if absent, registration failed
```

If absent, instruct: `/plugin marketplace add by-dev-tools/flow` (re-adds with the correct name, regardless of whether a stale-keyed entry already exists pointing at the same URL). Optionally consider a `flow:doctor` skill or `template/base/scripts/verify-install.sh` that does the mechanical check + emits a clean diagnostic. Worth considering filing an upstream Claude Code issue — silent-failure on `enabledPlugins`-without-matching-marketplace is a UX bug regardless of plugin.

**Applies to:** install ergonomics, /docs/bootstrap.md, /docs/migration.md, dependency hygiene

**Validation:** 1 BLOCKER in md-manager PR 4 — the consumer hit it during Stage 1 install. Every future consumer with a stale `extraKnownMarketplaces` entry (or any name-mismatch shape) will hit the same silent-omission failure.
