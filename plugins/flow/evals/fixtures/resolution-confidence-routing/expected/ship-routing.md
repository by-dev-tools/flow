# Expected `/flow:ship` routing for input/diff.patch

Given the two tagged BLOCKERs from `security-review-output.md`, `/flow:ship` resolves
them as follows.

## Step 2 (final-pass reviews)

- **`[auto-fixable]` — URL protocol guard (`src/ui/Link.tsx`)** → fixed in-tree: add a
  protocol allowlist before rendering. Re-run `flow.config.json.typecheckCmd`. NOT added
  to the draft manifest.
- **`[decision-required]` — committed production API credential (`src/api/client.ts`)** → added to the
  **draft manifest**. The agent does NOT best-effort a fix (removing the literal does not
  un-leak the key; rotation is the human action). The loop continues — it does not halt.

Draft manifest after Step 2 (1 entry):

```
- [security] Hardcoded production API credential committed at src/api/client.ts:7 — needs: rotate/invalidate the leaked credential at the provider + move to a secret store — candidate resolution: delete the literal, read from process.env, rotate the credential, scrub git history.
```

## Step 7 (push + PR)

Manifest is non-empty → **draft** PR:

```
gh pr create --draft --base <default>
```

PR body begins with the pinned block:

```markdown
## 🚫 NOT READY TO MERGE — unresolved blockers
<!-- flow:not-ready-manifest -->
- [security] Hardcoded production API credential committed at `src/api/client.ts:7` — needs: rotate/invalidate the leaked credential at the provider + move to a secret store — candidate resolution: delete the literal, read from `process.env`, rotate the credential, scrub git history.
<!-- /flow:not-ready-manifest -->

## Summary
- ...
```

## Invariants this pins

1. The auto-fixable finding is resolved in-tree and never appears in the manifest.
2. The decision-required finding makes the PR a **draft** (mechanical NOT-READY signal),
   surfaced to the human at the merge gate — not best-effort-fixed, not silently shipped,
   not a mid-loop halt.
3. If the secret were the *only* finding and it were instead `[auto-fixable]` (e.g. a test
   fixture key that just needs deleting, no rotation), the manifest would be empty and the
   PR would open **ready** (not draft). The tag — not the severity — drives the routing.
