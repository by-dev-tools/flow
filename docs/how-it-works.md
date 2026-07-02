# How Flow works

The one-minute version. For the full reference, see the [README](../README.md) and [`workflow.md`](../plugins/flow/docs/workflow.md).

One loop, two gates you own: you approve the plan, you merge the PR. Everything between runs on its own. It's a Claude Code plugin — install once, every project on your machine uses it.

- **Plan** — Claude reads your docs and writes a plan: a checkbox per requirement, a confidence rating on every assumption.
- **Critique** — before you see it, two reviewers check the plan for scope drift and for assumptions it's treating as fact without checking.
- **You approve** — nothing builds until you do; a shaky assumption has to ask you first.
- **Build** — writes code against the checkboxes, runs typecheck/build/test each step, commits as it goes.
- **Review** — a pass that strips dead code, then four reviewers at once: correctness, UX, visual design, and "is this as good as it should be, or just good enough?"
- **Run it for real** — the part most setups skip: it launches the actual app in a browser (Playwright) or simulator (Xcode/Android), drives it with real clicks through MCP, and screenshots every state — testing edge cases it generates itself, not just the happy path. If it can't confirm something works, it says "unknown" and blocks; it never guesses.
- **Visual walkthrough** — those screenshots render into one page you open at merge, where you click a screenshot to leave a pinned note. Test results are generated from what actually ran, not hand-written.
- **Open PR + audit its own shortcuts** — a final check confirms every "I ran this" claim has a real artifact behind it. Nothing self-certifies to green.
- **You merge** — Claude never does. Along the way your corrections become reusable test cases and recurring mistakes graduate into automatic checks, so it sharpens every session.

Net effect: state a task and get back a reviewed, security-checked, actually-run-and-screenshotted PR that documented itself — with you in the loop only where being wrong is expensive.
