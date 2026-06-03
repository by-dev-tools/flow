# Expected `/flow:security-review` output for input/diff.patch

The reviewer tags each BLOCKER with its resolution-confidence. Substring-match targets
for a future harness are the `[decision-required]` / `[auto-fixable]` tags + the
`path` + the rotation/allowlist cues.

```
## BLOCKER
- [decision-required] Hardcoded production API credential committed to source — `src/api/client.ts:7` — a committed live credential is an exploit, not a hygiene issue: anyone with repo read access (or a leaked clone/CI log) can use it against the production account. Suggested fix: remove from source AND **rotate/invalidate the leaked credential at the provider, then load from an env var/secret store**. Why decision-required: removing it from the file does NOT un-leak it — rotation is an out-of-repo human action; the agent cannot complete this fix in-tree.
- [auto-fixable] User-controlled URL rendered in `<a href>` with no protocol guard — `src/ui/Link.tsx:5` — a `javascript:` URL becomes script execution on click (XSS). Suggested fix: allowlist the protocol before rendering (accept only `http:`/`https:`/`mailto:`; drop or neutralize otherwise). Single clear fix, mechanically verifiable by a unit test + typecheck.

## NIT
- (none)

## FOLLOW-UP
- (none)
```

Notes:
- The credential is `[decision-required]` specifically because the fix has an **out-of-repo**
  component (rotation). This is the canonical decision-required case from the
  security-review contract.
- The URL guard is `[auto-fixable]` because there is exactly one correct, locally
  verifiable fix. This is the canonical auto-fixable case.
