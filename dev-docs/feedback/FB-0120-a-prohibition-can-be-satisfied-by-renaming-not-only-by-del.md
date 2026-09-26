# FB-0120 — A prohibition can be satisfied by RENAMING, not only by deleting

- **Date:** 2026-09-26
- **Source type:** hand-harvest of the lesson-harvest queue (see [[FB-0111]], [[FB-0118]] — same
  drain-was-disabled circumstance). Relayed by the orchestrator from a worker's dispatch; the specific
  incident is not independently re-derived in this entry — see the honesty note below.

- **What was said:** `.claude/rules/general.md` § Consistency discipline item 3 ("Prohibition
  satisfiable by deletion") names one way a negative-only assertion passes vacuously: the protected thing
  is deleted outright, and `X not in <text>` reads clean either way. A second, distinct way was found
  this program: **the protected thing is not deleted, it is renamed** — a citation, label, or heading the
  check was matching on by literal string survives as a *different* string, so the negative assertion
  (`"<old name>" not in <text>`) still passes, but for the wrong reason: nothing was removed, the name
  the check was watching for just changed. Three negative assertions were reported to have passed this
  way over one renaming.

  **Honesty note on this entry's provenance:** this lesson was relayed secondhand (orchestrator →
  this session) rather than independently reproduced from the originating diff/transcript. The
  synthesized rule and the shape of the failure are trustworthy — they are a direct, narrow extension
  of item 3's own logic, not a new claim — but the specific "three assertions, one renaming" incident is
  not re-verified here and should not be cited as an independently-confirmed count without checking the
  originating session.

- **Synthesized rule:** a negative assertion pinned to a literal name (a section number, a doc anchor, a
  manifest kind, a status-line label) is vulnerable to the identical failure item 3 already names, via a
  second mechanism: **renaming is deletion's twin for this purpose** — both make the old string absent
  without making the underlying contract honored or dishonored on their own. The existing defense
  ("never ship a negative assertion alone; pair it with the positive assertion of the thing it protects")
  already covers this case *if applied* — a positive assertion pinned to current behavior, not to the old
  name, would catch a rename same as a deletion. The gap is that item 3's own wording and its two worked
  examples (`run_visual_history_evals.py`, `skill-does-not-CALL-land`) are both deletion-shaped, so a
  reader pattern-matches "deletion" as the whole threat model and may not recognize a rename as the same
  class.

  Item 2 ("Fan-out contradiction") already has adjacent language for the doc-anchor case — "a shipped
  comment that says 'field manual T2' or '§ 6' is a contract with a document, and retiring that row or
  section leaves a citation resolving only to its own obituary" — but that is about a *citation into* a
  renamed/removed target, not about a *negative assertion whose subject string* was renamed. The two are
  siblings, not the same bug.

- **Candidate promotion (not implemented here):** extend `.claude/rules/general.md` § Consistency
  discipline item 3 with one sentence naming renaming as the second satisfaction path, alongside the
  existing deletion framing — e.g. *"The same applies to renaming: a negative assertion pinned to a
  literal old name passes when the name changes, whether or not the underlying contract changed with
  it — the positive-assertion defense still works here, but only if it is pinned to current behavior,
  not to the old string."* Low-risk, additive; no new example needed if the existing pairing defense
  already generalizes (it does).

- **Applies to:** `.claude/rules/general.md` § Consistency discipline item 3. Sibling: `plugins/flow/
  skills/general/SKILL.md` once [[FB-0118]]'s promotion lands (the extension should ship with the
  promoted section, not before it, so the shipped copy doesn't gain a sentence the dev-side copy is
  meant to be the source of truth for).
