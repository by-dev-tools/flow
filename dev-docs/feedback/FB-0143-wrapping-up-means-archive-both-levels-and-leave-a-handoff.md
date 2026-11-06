### FB-0143 — "Wrap up" means archive both levels (session AND workspace) and leave a handoff doc for anything not done, not just stop

**Date:** 2026-11-06

**Source type:** user direction

**What was said:** Ben, across several messages while winding the session down: "do not add any more scope, just try to get everything landed and next steps documented... we are not creating any new workers, just trying to finish up what's in progress." Then, for the one item that was genuinely unfinished (the touch prototype, round 3 in review, no approval given): "I don't want to kick any more work off. I want you to document that in the repo and then prepare for archive... we want everything to be packaged so that it can be picked up later by others." Separately, mid-session: "if the worker workspaces are done, archive them (you should already be doing this when it's safe to do so)" — surfaced because `conductor session archive` closes the chat but leaves the **workspace** itself in a `ready` state; Ben had to point out from his own sidebar that three workspaces showed "no open chats" (session archived) while still listed as live workspaces.

**Synthesized rule:**
1. "Wrap up" / "pause" is not "stop" — it has two deliverables: (a) archive everything that's actually done, at **both** levels (`conductor session archive` AND `conductor workspace archive` — they are different operations with different visible states, and only archiving the session leaves a workspace that reads as still active), and (b) for anything genuinely unfinished, write a durable handoff doc (this repo's convention: `dev-docs/handoffs/`, indexed in `dev-docs/README.md` in the same change) rather than just leaving it in chat history — a future session or a different person needs to be able to pick it up cold, without re-deriving context from a conversation they weren't part of.
2. Don't wait for an explicit instruction to archive a finished session/workspace — once a PR has merged and a worker has nothing further to do, archiving both levels is the default, safe action, not something that needs to be asked for each time.

**Applies to:** orchestrator-seat sessions wrapping up or pausing work across any dispatched worker fleet; any point where a workstream is paused rather than finished (write the handoff before archiving the workspace that held the context, or the context is gone).
