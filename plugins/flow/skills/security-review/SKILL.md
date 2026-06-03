---
name: security-review
description: >
  Cold-reads the current workspace diff vs the project's default branch
  for security issues: XSS via dangerouslySetInnerHTML or unsafe URL
  handling, secrets in committed files, persistence-layer leakage of
  sensitive data, unsafe third-party deps, path traversal, prototype
  pollution, unsafe iframe / postMessage patterns. Returns BLOCKER /
  NIT / FOLLOW-UP findings. Skips doc-only or trivially safe diffs
  (e.g. copy tweaks) with a clean early-exit message. Use during
  /flow:ship's final-pass review, on demand for any change touching
  rendering, file I/O, third-party data, or persistence, or when the
  user says "security review", "audit this for security", or similar.
  Invokable directly by the user (`/flow:security-review`) or
  programmatically by `/flow:ship` via the Skill tool.
allowed-tools: Read, Glob, Grep, Bash, Agent
---

# Security review

Cold-read the workspace diff for security issues. This skill is invoked by `/flow:ship` as a final-pass review, and can be invoked directly when the user asks.

## When to invoke

- `/flow:ship` invokes this automatically as one of the two final-pass reviews.
- The user asks for a "security review" or "audit for security".
- A change touches rendering (markdown, HTML, user-content), file I/O, URL handling, persistence, or adds a third-party dependency.

Skip if the diff is doc-only or trivially safe (e.g. a copy tweak).

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Spec doc (for context): !`SPEC=$(cat flow.config.json 2>/dev/null | jq -r '.specPath // empty'); [ -z "$SPEC" ] && SPEC="dev-docs/spec.md"; [ -f "$SPEC" ] && echo "$SPEC" || echo "(no spec doc at $SPEC)"`
- Feedback doc (for context): !`FB=$(cat flow.config.json 2>/dev/null | jq -r '.feedbackPath // empty'); [ -z "$FB" ] && FB="dev-docs/feedback.md"; [ -f "$FB" ] && echo "$FB" || echo "(no feedback doc at $FB)"`

## 1. Save the diff

Capture both committed-since-base and uncommitted, plus untracked files (which `git diff` misses):

```sh
# Resolve default branch via the 3-tier fallback chain with [ -z ] guards
# (NOT the pipe-OR form — that fails on empty stdout; see /flow:ship Step 1a + FB-0008 lesson).
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && BASE=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$BASE" ] && BASE=main

# Per-diff source-file detection (PR D / FB-0006). If no source/config files in the diff,
# emit a clean early-exit instead of spawning the reviewer agent on a doc-only diff.
# Patterns configurable via flow.config.json.sourceFilePatterns (extended regex); the
# default below covers TS/JS/Python/Rust/Swift/Go/Ruby/Java/Kotlin/Shell + JSON/YAML/TOML
# + Terraform/Dockerfile/SQL/proto/GraphQL (security-relevant config classes).
SOURCE_PATTERN=$(jq -r '.sourceFilePatterns // empty' flow.config.json 2>/dev/null)
[ -z "$SOURCE_PATTERN" ] && SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'

# Validate the regex before using it. Invalid regex would error → empty result → silent skip
# (the EXACT failure mode FB-0008 warned about). Fall back to default on invalid input +
# log a loud warning so consumers know their override didn't take.
#
# CRITICAL: capture grep's raw exit code BEFORE testing — the pattern `! cmd && [ $? ... ]`
# tests $? against the negation's result, not grep's. grep -qE exits 0 (match), 1 (no
# match), or 2 (regex error). Valid regex on empty stdin → exit 1; invalid → exit 2.
echo "" | grep -qE "$SOURCE_PATTERN" 2>/dev/null
GREP_RC=$?
if [ "$GREP_RC" -gt 1 ]; then
  echo "⚠️ [security-review] flow.config.json.sourceFilePatterns is invalid as an extended regex (grep exit $GREP_RC); falling back to default." >&2
  SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'
fi

# Three checks (not two) — must also catch uncommitted modifications to tracked files,
# which `git diff origin/$BASE..HEAD --name-only` (committed-only) and `git ls-files
# --others` (untracked-only) both miss. Without this third check, the common
# 'iterate locally, then /flow:ship' loop silently skips review of work-in-progress.
SOURCE_FILES_IN_DIFF=$(git diff "origin/$BASE..HEAD" --name-only 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
SOURCE_MODIFIED=$(git diff HEAD --name-only 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
UNTRACKED_SOURCE=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
if [ -z "$SOURCE_FILES_IN_DIFF" ] && [ -z "$SOURCE_MODIFIED" ] && [ -z "$UNTRACKED_SOURCE" ]; then
  echo "[security-review] STATUS: SKIPPED — no source/config files in diff (committed+uncommitted+untracked). Pattern: $SOURCE_PATTERN. Override via flow.config.json.sourceFilePatterns."
  exit 0
fi

{ git diff "origin/$BASE..HEAD"; git diff HEAD; } > /tmp/flow-sec-diff.patch
git ls-files --others --exclude-standard > /tmp/flow-sec-untracked.txt
```

## 2. Run focused greps for high-signal patterns

These often surface findings the model reviewer misses (mechanical patterns):

```sh
git diff "origin/$BASE..HEAD" | grep -nE 'dangerouslySetInnerHTML|innerHTML\s*=|eval\(|new Function\(|document\.write' || true
git diff "origin/$BASE..HEAD" | grep -nE 'http://[^/]|https?://\$\{|window\.open' || true
grep -rEn '(api[_-]?key|secret|password|token|bearer)\s*[:=]\s*["'\''][^"'\'']{8,}' --include='*.{ts,tsx,js,json,py,rs,swift,kt}' . 2>/dev/null || true
```

Treat any survivors as candidate findings.

## 3. Launch the security reviewer

Single `Agent` call with `subagent_type: Explore`. Cap at ~1000 words. Prompt scaffold:

> You are a **red-team operator**. Your goal is to find an **exploitable vulnerability** in this diff — not to evaluate whether the code is clean or follow style preferences. Assume an attacker is reading this diff with intent and access to whatever user-input surfaces the application exposes. The project's tech stack and product domain are documented in the spec doc (path injected above) and `flow.config.json`. Read those first to ground your threat model; don't assume Vite/React/TypeScript or any specific stack.
>
> **Flag only gaps that are exploitable or that materially raise the attack surface.** Treat style preferences, unprovable risks, and "this could theoretically be unsafe in some hypothetical scenario" as out of scope. A red-team prompted to find vulnerabilities will usually report some, even when the code is sound — stay narrow. A missing input validator on a value that never reaches user-controlled data is not a finding; a sanitizer config that is wrong-by-default *is*. The over-engineering tax compounds across PRs.
>
> **Inputs:**
> - Diff: `/tmp/flow-sec-diff.patch`
> - Untracked files (Read them in full): `/tmp/flow-sec-untracked.txt`
> - Spec doc (path injected by the SKILL above; may be absent)
> - Feedback doc (path injected by the SKILL above; may be absent)
>
> **Attack surface (categories to probe):**
> 1. **Injection in rendering** — `dangerouslySetInnerHTML`, raw HTML pass-through, unsanitized `<a href>`/`<img src>` URLs in any markdown/HTML/template renderer. If the project renders user content, the renderer's sanitizer config is load-bearing. Trace user-controlled data to the sink.
> 2. **Unsafe URL handling** — `javascript:` URLs accepted; `window.open(userInput)`; user-controlled redirects; URL parsing that trusts the protocol. Where is the attacker URL?
> 3. **Secrets in tree** — API keys, tokens, `.env` content, OAuth secrets in source files, configs, or test fixtures. Check `package.json`, build configs, and any new file. A committed secret is an exploit, not a hygiene issue.
> 4. **Persistence leakage** — `localStorage` / `sessionStorage` / `IndexedDB` / Keychain / filesystem stores holding PII, tokens, or credentials in cleartext. Note that `localStorage` is readable by any script on the origin — an XSS becomes a credential leak.
> 5. **Dependency risk** — any new dep with a known reputation issue, very low download count, recent ownership change, or unpinned version range. Flag for human review; don't run an audit tool here.
> 6. **Path traversal** — if file/repo/disk paths come from user input and are joined to filesystem reads or writes, check for `..` and absolute-path injection. Can the attacker name a file outside the intended root?
> 7. **Prototype pollution / object injection** — `Object.assign({}, userInput)` patterns, `JSON.parse` of user data merged into shared objects.
> 8. **CSP / iframe / postMessage** — new iframes need `sandbox` attrs; `postMessage` usage needs `origin` validation. Where does cross-origin trust enter?
> 9. **Auth/session boundaries** — any new endpoint, file write, or shell exec that crosses a privilege boundary without a clear permission check. Is the boundary enforced server-side, or only by client convention?
>
> **Before emitting each BLOCKER/NIT, attempt to disprove it.** Trace the dangerous sink back to the input source: if the input source is not user-controllable in any realistic execution path, drop the finding. If you cannot construct a concrete attacker scenario in one sentence, the finding is speculative — drop it. A finding that survives this disproof is publishable; a finding that depends on an unstated assumption ("if an attacker could somehow…") is not.
>
> **Tag every BLOCKER with a resolution-confidence axis** (orthogonal to severity), because it decides whether the agent fixes in-tree or routes the finding to a draft PR for the human:
> - `[auto-fixable]` — there is a single clear fix, and it is mechanically verifiable afterward (a typecheck/test/build would confirm it). Example: an unescaped value with one correct sanitizer call.
> - `[decision-required]` — any of: more than one valid fix (a design choice), the fix requires an out-of-repo human action (rotate a leaked secret, vet a dependency), or it is not auto-fixable at all (dep-reputation risk). **Default to `[decision-required]` whenever you are unsure** — over-escalating is safe (it routes to a human); auto-fixing something that needed a decision is not.
>
> **Output format**, grouped by severity:
> ```
> ## BLOCKER
> - [auto-fixable|decision-required] <one-line description> — `path:line` — why it's exploitable (the attacker scenario in one sentence) — suggested fix. For [decision-required]: list the candidate fixes + exactly what human input/action is needed.
>
> ## NIT
> - <one-line description> — `path:line` — suggested fix
>
> ## FOLLOW-UP
> - <one-line description> — why it's deferred — proposed owner/horizon
> ```
>
> If you find nothing of consequence in a category, say so explicitly. The bar is **honesty over polish**; do not invent findings to look productive. A clean review is a valid honest outcome.

## 4. Triage and act

When invoked standalone (not via `/flow:ship` — which handles triage itself):

- **BLOCKER `[auto-fixable]`** — fix in workspace. Re-run the project's typecheck (`flow.config.json.typecheckCmd` via `sh -c "$TYPECHECK"` with the standard loud-warning fallback if unset).
- **BLOCKER `[decision-required]`** — do **not** best-effort a fix. Surface it to the user with the candidate fixes + the human action needed. (When invoked via `/flow:ship`, this routes to the draft-PR manifest — accumulated at Step 2, consumed at Step 7; ship never silently proceeds past it and never hard-halts the loop.)
- **NIT** — fix if cheap (single-file, <5 min).
- **FOLLOW-UP** — capture to the project's roadmap or plan (via `flow.config.json.{roadmapPath,planPath}` slots; defaults `dev-docs/roadmap.md` / `dev-docs/plan.md` for flow's own repo; consumer projects typically `core-docs/*`). **Never only in the PR body** — the doc entry is canonical.

## 5. Report

- **Standalone invocation**: send the categorized findings + what you fixed to the user.
- **Via `/flow:ship`**: return findings to the ship flow so it can incorporate them into the Reviewer notes.

## Gotchas

- **Don't run `npm audit` (or `cargo audit`, `pip-audit`, etc.) automatically.** Output is noisy and slow. Mention dependency risk as a FOLLOW-UP for the user to investigate.
- **Persistence is not a vulnerability by itself** — only when it stores something sensitive. Don't flag generic UI state in localStorage.
- **Sanitization config is renderer-specific.** If the project uses `marked` / `markdown-it` / `react-markdown` / similar, check its config for HTML-disable + sanitizer hooks.
- **Reviewers can be confidently wrong.** Spot-check high-impact findings against the actual code before fixing.
- **Built-in Claude Code `/security-review` exists** as a more general out-of-band tool. `/flow:security-review` is tuned for in-flow ship pipelines with config-slot doc-path resolution; use this one when running inside `/flow:ship`.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | Step 1 (diff base) |
| `flow.config.json.typecheckCmd` | unset → loud warning | Step 4 (post-fix re-check) |
| `flow.config.json.specPath` | `dev-docs/spec.md` | Project context section |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Project context section |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Step 4 (FOLLOW-UP routing) |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Step 4 (FOLLOW-UP routing) |
