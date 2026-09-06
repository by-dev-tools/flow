### Roadmap hygiene — Deliverable-quality track V2/V3 labels + de-stale `## Now`/PR Q
**Date:** 2026-06-05
**Branch:** `claude/flow-roadmap-hygiene-v2v3-labels` (SHA at squash-merge)

**What was done:** Docs-only roadmap cleanup, immediately after #36 merged:
- **Reconciled the V2/V3 labels.** The O8 entry's acceptance block called its two PRs `V2/V3a` + `V3b`, but the track section uses `V2` = capture, `V3` = render — so "V2" meant different things in the two places. Relabeled to **PR-1 = track V2 (capture) + V3a (renderer), coupled by FB-0003** and **PR-2 = track V3b (durable record)**, with an explicit stage-mapping sentence. Swept the one living cross-reference in the blueprint research doc (the `history.md` mention is an append-only record of #36's state, left as-is).
- **De-staled `## Now`.** Was frozen at "Plugin at v1.2.6 … This PR (PR H3)"; refreshed to **v1.5.1** with an accurate "what shipped since" line (PR Q/S/U + v1.4.x + #35/#37/#36) and reframed the execution-order intro around the three live streams (Track 1 K/L, Track 2 N/O/P, Deliverable-quality V2–V4).
- **Marked PR Q shipped.** The `## Next` PR Q bullet still read "in flight … Phase 11 next"; updated to **SHIPPED (v1.3.0, #26)** and pointed at the Deliverable-quality track it feeds.

**Why:** Surfaced when the user asked whether the roadmap had clear next steps after #36. The track's next-step path (V1 shipped → V2 next → V3 → V4) was clear, but the V2/V3a label mismatch and the stale `## Now`/PR Q lines muddied it.

**Design decision:** Kept the K/L/N/O/P track *descriptions* intact (still the live plan for those PRs) — only fixed the framing/version anchors, rather than rewriting queues whose status I couldn't fully verify. Append-only history entries (e.g. #36's tightening note) left untouched even where they carry the old label.

**Tradeoffs discussed:** Could have moved the whole O8 entry up under the track section for locality; declined — the cross-reference is clear and the move is larger surgery for marginal gain. A fuller `## Now` execution-order audit (K/L/N/O/P current status) is left as separate hygiene.
