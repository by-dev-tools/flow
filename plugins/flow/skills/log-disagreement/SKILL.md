---
name: log-disagreement
description: |
  Log the user's disagreement with a specific finding from /flow:audit-plan, /flow:audit-completion, or /flow:critique-plan. Invoke automatically when ALL of the following hold:
  1. One of those audit/critique commands has produced output earlier in the conversation.
  2. The user's most recent message disputes a finding from that output. Disagreement takes any form: "no, finding 2 is wrong", "false positive", "that's not a scope drift", "the spec rule doesn't apply here", "ignore that", "I disagree", or any rejection of a specific finding's claim or premise.
  3. The disagreement is about a specific finding, not general conversation, clarifying questions, or acceptance of findings.
  The user does not need to invoke this skill manually — you should invoke it the moment you detect disagreement so the feedback feeds future prompt tuning. Do NOT invoke for general project questions, acceptance ("ok, fixing 3 now"), or pushback that isn't about an audit finding.
allowed-tools: Bash
---

# Task: Log audit disagreement

The user has just pushed back on a finding from a recent audit / critique. Capture the disagreement so it can become an eval fixture in the next prompt-tuning pass.

## What to do

1. From the conversation, identify:
   - **Reviewer** — which command produced the disputed finding (`auditor` for `/flow:audit-plan` or `/flow:audit-completion`; `plan-critic` for `/flow:critique-plan`).
   - **Category** — exact category name from the finding (e.g., "Scope drift", "Unverified assumption").
   - **Severity** — if the finding is from `plan-critic`, one of BLOCKER / REDIRECT / FOLLOW-UP. Empty string for auditor findings (which don't carry severity).
   - **Claim** — the disputed `Claim:` or `Plan element:` quote from the finding. Keep it short — first 100 chars is fine.
   - **Reason** — one short sentence paraphrasing why the user thinks the finding is wrong.

2. Run the capture script:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/log_disagreement.py \
     --reviewer "<reviewer>" \
     --category "<category>" \
     --severity "<severity or empty>" \
     --claim "<short claim quote>" \
     --reason "<one-sentence paraphrase>"
   ```

3. Output exactly one confirmation line to the user, matching this shape:

   ```
   Logged: <reviewer>/<category> disagreement → <path printed by script>
   ```

4. Then continue with whatever the user wants next. Do not editorialize about whether the finding was right or wrong — that is the user's call, not yours. Do not apologize for the finding. Do not promise the prompt will be changed; that happens in a separate tuning cycle.

## What not to do

- Do not invoke this skill more than once per disagreement. If the user disputes multiple findings in one message, invoke once per disputed finding — but do not invent disagreements that the user did not state.
- Do not invoke this skill on general pushback unrelated to a specific audit finding ("this whole plugin is wrong", "I don't want to use this") — those go in `DISAGREE.md` manually, not here.
- Do not block the user's next request while logging. The log is for later analysis; it does not gate the conversation.
