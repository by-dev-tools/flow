### FB-0091 — The orchestrator routes *itself* as deliberately as it routes workers (table + logged why, never by feel)

**What was said (2026-08-26):** Asked why the successor orchestrator was spawned on `sonnet-5-1m`/high — "was that on purpose according to a settled decision?" The *family* (sonnet, not opus) matched the routing table, but the *effort* (high) was a by-feel bump with no logged rationale.

**Synthesized rule:** Every model/effort choice the orchestrator makes — dispatching a worker **or spawning its own successor** — is drawn from the §4.3 routing table (research/2026-08-22 §6) and recorded as `model · effort · why` (the usage.tsv discipline). A discretionary deviation is allowed but must be **stated and justified**, never silent-by-feel. Picking a tier or effort "because it felt right" is exactly the un-principled routing the measurement track exists to remove.

**Why:** Token efficiency and quality both depend on routing being evidence-driven; an unlogged by-feel choice can't be audited or improved, and it quietly normalizes guessing.

**How to apply:** at any `conductor workspace create` / dispatch, cite the table entry + effort + a one-clause why. Related: [[FB-0083]] (measurement-first routing), and canonical plan §4.3 (the table + usage.tsv) / §4.8 (gate delegation).
