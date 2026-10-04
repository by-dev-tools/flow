## 2026-10-04 — Record Ben's iPhone test-kit results in the mobile-workflow research doc

**Branch:** `conductor/mobile-workflow-investigation` · **SHA:** [this commit] · **Mode:** research follow-up (findings-only, no shipped skill touched)

**What was done.** Ben read the 2026-10-03 mobile-workflow research doc and asked for all five ranked options to be built, with a request to test on his phone first (how HTML files and links actually behave on iOS) before building option 1. Built a throwaway test kit — a small self-contained HTML page served from a worker sandbox via `python3 -m http.server` + `conductor preview set` — and sent Ben a 7-item numbered test to run on his iPhone through the Conductor iOS app. Recorded his results (screenshots, reported back via the orchestrator) into `dev-docs/research/2026-10-mobile-workflow.md` §6/§8.

**Why.** §6 of the research doc had five genuinely open questions about iOS client capability (can it open an HTML artifact? does `file://` work? does an inline chat image render? does a `conductor preview set` URL open in Safari? does a long PR table render fully?) that the original research could only answer by reasoning from Conductor's docs/changelog, not by observation. This closes that gap with real evidence from the actual device.

**Design decisions.** Treated the test kit as throwaway (kept entirely under `.context/`, gitignored — never committed) per the orchestrator's explicit "test kit, not shipped code" framing. Substituted a public `raw.githubusercontent.com` image for item 6's original premise after discovering flow's own repo has zero committed images anywhere on `main` — verified this rather than inventing a path, and used an external URL at the identical mechanism instead of pushing a new asset just to satisfy the test.

**Technical decisions.** Confirmed the preview was live and correctly access-gated (`401 Sign in to view this preview`, the documented Conductor behavior) before handing the URL to Ben — never handed over an unverified artifact. Tore the server and preview down immediately after Ben's results came back, per instruction.

**Tradeoffs discussed.** None new beyond what's in the research doc's own §8 — the test surfaced one new option (inline workspace images in chat) ranked ahead of option 1 on cost, since it needs no server and no `conductor preview set` call at all.

**Lessons learned.** A side effect of the test, not something asked for: Python's `http.server` sends `text/html` with no charset, so a UTF-8 test page rendered as mojibake in Safari without an explicit `<meta charset="utf-8">`. Folded directly into option 1's cost in the research doc — any future build of the preview-serving mechanism needs to check `annotation-layer.html` and `render-report.py`'s output for the same gap before shipping.
