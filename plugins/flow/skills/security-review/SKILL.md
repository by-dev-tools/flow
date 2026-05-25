---
name: security-review
description: >
  Cold-reads the current workspace diff vs the project's default branch
  for security issues: XSS via dangerouslySetInnerHTML or unsafe URL
  handling, secrets in committed files, persistence-layer leakage of
  sensitive data, unsafe third-party deps, path traversal, prototype
  pollution, unsafe iframe / postMessage patterns. Returns BLOCKER /
  NIT / FOLLOW-UP findings. Use during /flow:ship's final-pass review,
  on demand for any change touching rendering, file I/O, third-party
  data, or persistence, or when the user says "security review", "audit
  this for security", or similar. Invokable directly by the user
  (`/flow:security-review`) or programmatically by `/flow:ship` via the
  Skill tool.
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
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main")
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

> You are a staff security engineer cold-reading a diff. The project's tech stack and product domain are documented in the spec doc (path injected above) and `flow.config.json`. Read those first to ground your audit; don't assume Vite/React/TypeScript or any specific stack.
>
> **Inputs:**
> - Diff: `/tmp/flow-sec-diff.patch`
> - Untracked files (Read them in full): `/tmp/flow-sec-untracked.txt`
> - Spec doc (path injected by the SKILL above; may be absent)
> - Feedback doc (path injected by the SKILL above; may be absent)
>
> **Hunt for:**
> 1. **Injection in rendering** — `dangerouslySetInnerHTML`, raw HTML pass-through, unsanitized `<a href>`/`<img src>` URLs in any markdown/HTML/template renderer. If the project renders user content, the renderer's sanitizer config is load-bearing.
> 2. **Unsafe URL handling** — `javascript:` URLs accepted; `window.open(userInput)`; user-controlled redirects; URL parsing that trusts the protocol.
> 3. **Secrets in tree** — API keys, tokens, `.env` content, OAuth secrets in source files, configs, or test fixtures. Check `package.json`, build configs, and any new file.
> 4. **Persistence leakage** — `localStorage` / `sessionStorage` / `IndexedDB` / Keychain / filesystem stores holding PII, tokens, or credentials in cleartext. Note that `localStorage` is readable by any script on the origin.
> 5. **Dependency risk** — any new dep with a known reputation issue, very low download count, recent ownership change, or unpinned version range. Flag for human review; don't run an audit tool here.
> 6. **Path traversal** — if file/repo/disk paths come from user input and are joined to filesystem reads or writes, check for `..` and absolute-path injection.
> 7. **Prototype pollution / object injection** — `Object.assign({}, userInput)` patterns, `JSON.parse` of user data merged into shared objects.
> 8. **CSP / iframe / postMessage** — new iframes need `sandbox` attrs; `postMessage` usage needs `origin` validation.
> 9. **Auth/session boundaries** — any new endpoint, file write, or shell exec that crosses a privilege boundary without a clear permission check.
>
> **Output format**, grouped by severity:
> ```
> ## BLOCKER
> - <one-line description> — `path:line` — why it's a blocker — suggested fix
>
> ## NIT
> - <one-line description> — `path:line` — suggested fix
>
> ## FOLLOW-UP
> - <one-line description> — why it's deferred — proposed owner/horizon
> ```
>
> If you find nothing of consequence in a category, say so explicitly. The bar is **honesty over polish**; do not invent findings to look productive.

## 4. Triage and act

When invoked standalone (not via `/flow:ship` — which handles triage itself):

- **BLOCKER** — fix in workspace. Re-run the project's typecheck (`flow.config.json.typecheckCmd` via `sh -c "$TYPECHECK"` with the standard loud-warning fallback if unset).
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
