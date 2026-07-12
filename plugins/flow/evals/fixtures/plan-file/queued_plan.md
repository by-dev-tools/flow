# Queued plan — sync retry queue backoff

## Goal

Add exponential backoff with jitter to the sync retry queue so transient
upstream failures stop hammering the service.

## Steps

1. Add a `BackoffPolicy` type with base, cap, and jitter parameters.
2. Wire it into the retry queue's dequeue loop.
3. Surface a "retrying in Ns" status line in the sync panel.

**Spec-walk:**
- [ ] Backoff caps at 5 minutes — testBackoffCap
- [ ] Retry status line renders → verify: screenshot on-sim

DISTINCTIVE-PLAN-LINE: jittered-backoff-rollout-marker-7f3a
