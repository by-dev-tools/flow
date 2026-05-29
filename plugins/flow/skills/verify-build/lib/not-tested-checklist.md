# "What we did NOT test" per-platform checklist (PR Q Phase 5)

**Status:** Phase 5 stub. Fixed checklist (closed-form ✗ / ✓ per item) emitted to stdout at `/flow:verify-build` Step 9 for the PR-body author.

## Purpose

A verify-build that PASSED isn't a guarantee. Real device behavior, real network, real auth, real payments — none of these run in simulator / headless / dev-server modes. The checklist forces the agent to explicitly mark what was NOT tested rather than free-form narrate it (FB-0010 silent-skip defense — free-form prose under-lists by default).

## Output format

Closed-form list with per-item ✗ / ✓:

```
What we did NOT test:
  [✗] <item 1>
  [✗] <item 2>
  ...
```

Agent flips ✗ → ✓ only where it actually tested that surface. Items remaining ✗ are explicit gaps in the verify pass.

## Per-platform checklists

### Web

```
What we did NOT test:
  [✗] Real device (used Playwright headless / dev browser)
  [✗] Real network (used dev server; no production CDN, no real latency)
  [✗] Authenticated flows requiring 2FA / SSO
  [✗] Push notifications
  [✗] Payment flows
  [✗] >1 viewport size (mobile / tablet)
  [✗] >1 locale / language
  [✗] >1 browser engine (only Chromium tested by default)
```

### iOS

```
What we did NOT test:
  [✗] Real device (used simulator)
  [✗] Real network (used simulator network)
  [✗] Biometric auth (Face ID / Touch ID)
  [✗] Push notifications
  [✗] In-App Purchase flows
  [✗] >1 device size
  [✗] >1 iOS version
  [✗] Background / suspended-app behavior
```

### Android

```
What we did NOT test:
  [✗] Real device (used emulator)
  [✗] Real network (used emulator network)
  [✗] Biometric auth (Fingerprint / Face Unlock)
  [✗] Push notifications (FCM)
  [✗] In-App Purchase / Play Billing
  [✗] >1 device size
  [✗] >1 Android API level
  [✗] Background / Doze-mode behavior
```

### CLI

```
What we did NOT test:
  [✗] Real terminal (TUI subtleties may differ from captured stdout)
  [✗] Real-world arg parsing edge cases (escaping, unicode in args)
  [✗] >1 shell (bash / zsh / fish / dash compat)
  [✗] >1 OS (POSIX vs Windows path conventions)
  [✗] Large-input performance / streaming behavior
  [✗] Signal handling (SIGINT, SIGTERM, SIGPIPE)
```

### Library

Library projects skip verify-build at Step 1.2 (`flow.config.json.platform=library` or no runnable target). No `What we did NOT test` checklist is emitted in this case — the skill exits before reaching Step 9.

## Status footer (Phase 5 to refine)

Stub. Phase 5 work: validate per-platform lists against consumer feedback; add `flow.config.json.notTestedExtraItems` slot for project-specific additions (e.g. a project with HIPAA constraints might add "✗ De-identification flow").
