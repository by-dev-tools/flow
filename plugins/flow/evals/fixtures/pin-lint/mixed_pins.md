# Plan — sync retry queue backoff

**Spec-walk:**
- [ ] Retries back off exponentially with jitter — testBackoffJitterBounds
- [ ] Queue drains FIFO under load — `test_queue_fifo_under_load`
- [ ] Config table documents the new retryBudget slot → verify: doc-diff in the PR body
- [ ] Rate limiting works correctly end to end
- [ ] Middleware ordering is preserved

**Confidence verdicts:** none.
