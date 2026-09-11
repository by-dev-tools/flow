### FB-0004: Security regression tests must assert on what would leak, not on a proxy for it
**Date:** 2026-05-25
**Source:** review feedback (PR 3 engineer-lens dogfood)

**What was said:** PR 3 Phase 7's engineer lens caught that `test_absolute_outside_cwd_rejected` asserted `"/etc/hosts" not in result.stdout` — passes trivially because a content leak prints `127.0.0.1` (the host file's content), not the path string. A regression that drops the cwd check but doesn't print the path would pass the test silently. The dotdot-traversal test in the same file got it right: `"127.0.0.1" not in stdout and "::1" not in stdout`. Both rejection + accept tests were strengthened in the same Phase 7 fix commit to use content sentinels.

**Synthesized rule:** When writing a security regression test, identify what a real leak/breach would actually output, then assert on THAT. A real leak of `/etc/hosts` prints loopback addresses, not the path. A real leak of `~/.ssh/id_rsa` prints `-----BEGIN OPENSSH PRIVATE KEY-----`. A real shell injection prints `pwned` or creates a marker file. The path string is a proxy and proxies have escape hatches. When in doubt: write a deliberately-broken implementation locally, run the test, verify it FAILS. If the test passes with a known-broken implementation, the assert is vacuous.

**Applies to:** security regression testing, workflow

**Validation:** 1 BLOCKER caught in PR 3 Phase 7. Original assert: `"/etc/hosts" not in result.stdout or "outside" in combined.lower() or "external" in combined.lower()` — three disjuncts, any of which trivially satisfies. Replaced with `"127.0.0.1" not in result.stdout and "::1" not in result.stdout` — content-only, no escape hatch.
