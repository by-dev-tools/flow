### FB-0044: Low confidence during Execute is a signal to *iterate*, not to stop — the agent iterates against the plan's success criteria + craft bar until the design is genuinely good, then ships; only a genuine *preference fork* escalates
**Date:** 2026-06-09
**Source:** user direction

**What was said:** When the agent executes and isn't fully confident, it must NOT just stop. The user wants consistent agentic iteration to make the design genuinely good *before* opening the PR — grounded in strong success criteria + a craft bar established in the plan ("agentic iteration is critical here, based on the strong success criteria and craft bar that need to be established in the plan"). This refines (and corrects) an earlier framing that an uncertain agent should ship a draft early: design uncertainty is something the agent should iterate *through*, not hand off prematurely.

**Synthesized rule:** When the agent is not fully confident at Execute/Present, the **default is to iterate** against the plan's declared success criteria + craft/experience bar — never a premature stop, never a premature draft. Split FB-0011's escalation on a clean line:
- **Quality gap** ("not good *enough* yet") → **iterate.** The agent closes this itself; iteration is the dominant behavior, and its ceiling is set by how strong the plan's criteria + craft bar are.
- **Preference fork** ("not sure which *way* you want it" — a one-way-door, or two comparable directions only the human's taste resolves) → **escalate.** No amount of craft resolves a preference; only the human does.

Reserve **stop-before-PR** for genuine one-way-door decisions where even a draft would prejudice the human's choice; otherwise escalation routes INTO a draft PR + NOT-READY manifest (FB-0034), so the human always enters at the PR, never mid-loop. **Safety precondition:** craft-iteration loops on *judgment*, which is honest — not reward-hacked (cf. FB-0012's prohibition on iterating to a *correctness* reviewer's approval) — only when the judge sees **real captured artifacts (V2)**, not the worker's narration, against **declared criteria**, under a **bounded budget**, with the **human merge gate** as the final backstop. So safe autonomous craft-iteration is **V2-gated**; the loop driver should key on the verify-build verdict (a Stop-hook or `/goal` anchored to a mechanically-demonstrable PASS), never on open-ended taste.

**Applies to:** workflow (Step 8/9 loop), autonomy bar (FB-0011), Deliverable-quality track (V2 is the precondition; FB-0041 the umbrella), draft-routing (FB-0034).
