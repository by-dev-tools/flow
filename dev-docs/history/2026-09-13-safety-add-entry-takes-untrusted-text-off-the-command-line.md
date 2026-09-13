## 2026-09-13 — SAFETY: `add-entry` takes untrusted text off the command line entirely (v1.42.0, FB-0108)

**What was done.** `/flow:security-review` on #148 found that `manifest-triage.py add-entry` took
`--finding`/`--resolution` as raw argv while every producer site in `ship/SKILL.md` told the executing agent
to compose that command with attacker-influenceable text inside it. #148 shipped a narrow per-site fix; this
is the interface half. `add-entry`, `record-attempt` and `waive` now take `--finding-file` /
`--resolution-file` only; the argv flags are **removed**, kept declared solely to exit 2 with a message
naming the replacement. New `scratch-path --name …` resolves (and unlinks) producer scratch paths. The
non-empty/regular/non-symlink guard lives in the engine. All six producer sites migrated, the 12 lines of
#148's per-site safety prose deleted, and 11 eval call sites moved onto the file path.

**SAFETY markers — what changed, what was preserved.** *Modified:* the free-text input path (argv → file
path); error handling (four new exit-2 arms: removed-flag rejection, missing/empty/non-regular file,
symlinked file, failed `scratch-path`); input normalization (newline-only collapse, including a lone `\r`).
*Added:* write-side symlink unlink in `scratch-path`; `|| exit 1` at every producer site. *Preserved,
asserted by unedited tests:* `--kind`/`--needs` closed-vocabulary validation at write time; the manifest
line shape; everything `pr-coherence.py` reads; and fingerprint stability — a waiver recorded before this
change still subtracts its entry, pinned against a literal hex (`49070d421e4345de`) captured pre-change.

**Why the interface and not the call sites.** Correctness that depends on every future author remembering is
a convention, not a fix. The repo's scar is FB-0098: `/flow:doctor` defaulted doc-path slots to `core-docs/`
while the schema and 16 other call sites said `dev-docs/`. The human stated the bar precisely — *"the unsafe
door has to be closed, not merely joined by a safe one"* — so the flags are removed rather than deprecated.

**Tradeoffs.**

- **Removed the argv flags rather than keeping both.** Keeping them means the interface still *offers* the
  unsafe path. The cost is that removal converts a quoting hazard into a louder version of the pre-existing
  unchecked-`$?` hazard; that is why every producer site this PR touches now carries `|| exit 1`, and why
  the *inherited* unchecked sites are named in roadmap § Next rather than silently inherited.
- **No stdin/`-` affordance.** From a Bash call, stdin can only be fed by a heredoc or a quoted string —
  the two mechanisms this exists to remove. Offering it would re-offer the refuted path. Cost: the evals
  write real temp files.
- **Newlines only, not all whitespace.** Widening would silently reflow findings that compose correctly
  today. P12 is its paired negative.
- **Collapse rather than reject on a multi-line finding.** Rejecting routes ordinary well-meant input into
  the exit-2-appends-nothing path, i.e. it would drop a blocker (FB-0062).
- **`scratch-path` unlinks unconditionally.** The path is always engine-computed `.flow/<slug>` and never
  caller-supplied; `.flow/` is gitignored ephemeral scratch flow rewrites every run. Refusing instead would
  turn a plantable file into a permanent wedge of the ship pipeline. Idiom taken verbatim from
  `ship-spike/SKILL.md:253`. Escalated and approved at the plan gate as the one destructive change.
- **The allowlist is scoped to `ship/SKILL.md`.** Named explicitly rather than implied, because "allowlist"
  reads as "sealed": it cannot see an append in another file, one emitted by a script `SKILL.md` invokes, or
  one built from a runtime variable.

**What the review process caught that the author did not.**

- **Nine rounds of `/flow:critique-plan` at the plan gate**, which refuted three successive designs: two
  heredoc variants and a separator sentinel, all killed by the same property — every text-based boundary can
  appear inside the text. Also caught a shared-scratch-file scheme that would have collapsed the
  `record-attempt`/`add-entry` fingerprints and thereby changed manifest classification, and a template
  carrying the scratch path in `$F` across a Write tool call, where shell variables do not survive.
- **Those nine rounds ran DOCUMENT-BLIND**, and measuring it was the most useful thing done in the pass. The
  installed plugin is v1.29.0, which cannot comma-split this repo's `referenceGlob` (the comma form #146
  introduced when `feedback.md` was fragmented), so the preprocessor resolved **0 of 196** reference
  documents. The FB-0082 warning fired loudly and every round disclosed it — the guard worked; the
  config/version pairing did not. A document-aware re-run then found five corpus-dependent findings, two of
  them blockers: FB-0062 (the failure-open producers above) and FB-0004 (payload P8 asserted on an exit code,
  a proxy, where a read-then-check implementation would pass having already read the secret).
- **The orchestrator caught the allowlist shipping as a bare universal** — vacuously true at zero append
  sites, so deleting the producers would have turned it green. The FB-0077 shape, in the very check proposed
  as the thing that closes the class, one commit after citing that rule approvingly about other code. Now
  paired and mutation-tested: six mutations, all killed.

**Verification.** `run_manifest_triage_evals.py` gains a `[injection]` section: 14 payloads executed through
`/bin/sh -c`, with red arms matched per hazard (argv for command substitution and quote breakout; a real
heredoc for the delimiter collision, reproducing v1.41.0's own first-attempt bug). P8 asserts the
`-----BEGIN OPENSSH PRIVATE KEY-----` sentinel appears in neither stdout nor stderr nor the manifest.
`run_scratch_isolation_evals.py` gains a `producer-*` group that extracts and **executes** CALL 1 and CALL 2
as separate processes with no inherited shell state — the one evidence shape that survives FB-0107, since
dogfooding would exercise v1.29.0. Six mutation tests confirm each new assertion can fail. All 31 harnesses
green; `ci.yml`'s harness/runner join passes.

**Payload P10 found a real gap mid-implementation:** `[ \t]*(?:\r?\n)+[ \t]*` left a lone `\r` untouched, and
a bare CR is a line break to plenty of consumers, so it could split a manifest entry exactly like `\n`.
Fixed to `(?:\r\n|\r|\n)+`. Found by attacking, not by reading.

**Two pre-existing parser defects found and NOT fixed** (approved scope was the input path; both recorded in
roadmap § Next with measurements). **P5, severe:** `manifest_contract.py`'s
`.split(MANIFEST_CLOSE, 1)[0]` truncates at the first close marker, so a finding containing that literal
erases every later entry — measured on `origin/main`, 2 entries → 0 and verdict `DECIDE` → **`READY`**, i.e.
a non-draft PR over an erased behavioural gate. It is a **latent self-trigger one docs commit from live**: the
marker already sits in ordinary prose at `dev-docs/roadmap.md:720`, and the `[status-surface]` producer
quotes verbatim status-doc lines into findings — it does not fire today only because `roadmap.md` is not in
`statusSurfaceCandidates` and none of the six defaults currently contains the marker, though `README.md`
already discusses the manifest. **P7, low:** the field separator can be forged, truncating the finding the
human reads; it does **not** downgrade classification, because `classify()` keys on `kind` and not on the
parsed `confidence` — verified across four kinds, correcting a stronger claim made before measuring.

**Why a round-trip test would have found neither.** Both attack the parser's *own vocabulary* — its fence
marker and its field separator. A round-trip test asks "does my input survive?"; these ask "can my input
impersonate the mechanism?" Only the second question generates the payloads, and it is only asked by someone
attacking the mechanism they chose rather than confirming the happy path. That is the reusable lesson, and it
is worth more than the two bugs.
