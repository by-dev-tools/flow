### FB-0090 — Escalate decisions with recommendation + confidence + justification, by default

**What was said (2026-08-26):** After the orchestrator surfaced a gate-machinery decision, the user had to explicitly ask the worker for confidence scores before they could decide. "I want what I asked for by default: recommendations with confidence scores and justifications for why — that will help me make the decisions."

**Synthesized rule:** When escalating **any** decision to the human — a plan/merge gate, a design fork, an open question — present it **by default** as the triple: the **recommendation**, a **confidence score** (high / medium / low), and the **justification** (the *why*). The human should never have to ask for the confidence or the reasoning; supplying them up front is what lets the human decide fast.

**Why:** The orchestrator-seat model concentrates the human's attention on decisions; a decision handed over without its confidence and rationale forces a round-trip that defeats that.

**How to apply:** Every orchestrator hand-off of a decision, and every worker paused at a gate, uses this triple. Codified in the canonical cloud-workflow plan §4.8 (gate delegation) and the dispatch-brief template. Related: [[FB-0011]] (the autonomy bar — *when* to escalate) governs the trigger; this governs the *format*.
