### FB-0117 — Every shell positional in a skill body is a host placeholder, and the obvious fix breaks awk

**Date:** 2026-09-26
**Source:** measured during the FB-0116 sweep; scope call by the orchestrator

**What was said:** the orchestrator, on being shown that `/flow:ship <any argument>` corrupts ship's own provenance block: *"This is the most valuable thing in your ping and it is a live bug on `main`… It is broader than `$ARGUMENTS` — if `$0` is substituted, every `$N` inside a block is suspect, which means awk, sed and shell positional usage across every skill. And the specific victim is the provenance block, i.e. the one artifact CLAUDE.md § 3 instructs every session to read before trusting a green pipeline. Shipped, believed to work, silently wrong."*

**Synthesized rule:**

1. **The placeholder family is `$ARGUMENTS`, `$ARGUMENTS[n]`, and `$0`–`$9`.** Everyone remembers the first. The third is the dangerous one, because `$0` and `$1` are *also* ordinary shell and awk syntax, so a skill body containing `awk 'index($0,H)'` reads as correct code and is silently rewritten the moment the skill is invoked with an argument — `$0` maps to the **first** argument token, so it fires on *any* argument, not only a malicious one. Measured on `main`: `/flow:ship <anything>` broke `sect()` in ship's FB-0107 provenance block, and `/flow:doctor` had the identical line.
2. **The victim being the provenance block is the lesson, not a detail.** FB-0107 exists because dogfooding runs the installed plugin, and CLAUDE.md § 3 tells every session to read the `## Flow run` rows before trusting a green pipeline. A bug that corrupts *that* block degrades the instrument the whole honesty story rests on — and it degrades it in the argument-passing case, which is exactly when a session is doing something unusual enough to want provenance.
3. **`${1}` for shell, `$(0)` for awk, and they are NOT interchangeable.** Brace form is invisible to the host's `/\$(\d+)(?!\w)/` and identical to `$1` in POSIX sh — but **awk has no brace form: `${0}` is a syntax error.** The first attempt at this fix used `${0}` inside awk, which silently broke the very function it was protecting; the harness caught it, reading the code did not. awk's field operator takes an expression, so `$(0)` is the whole record and is equally invisible to the host.
4. **Prefer a spelling that is inert to escaping.** `\$1` also works — but only when the host actually substitutes: it returns the body untouched for a null argument, so an escaped positional survives *literally* into precisely the no-argument case. `${1}`/`$(0)` are correct in both worlds. Reserve `\$` for prose and comments that are *about* a placeholder, where a literal is what you want anyway — and remember that an unescaped mention of a placeholder inside a comment is itself a live substitution site.

**Reproduced live, inside the ship run for this very fix.** `/flow:ship` was invoked with the
argument `v1.50.0 — the $ARGUMENTS prose rule (FB-0116/FB-0117)…`, which tokenises to
`$0`=`v1.50.0`, `$1`=`—`, `$2`=`the`. The **installed** 1.29.0 ship skill then rendered its own
Step 5b doc-currency gate as:

```sh
sect() { awk -v H="—" 'index(v1.50.0,H){f=1;next} f&&/^## /{exit} f' "the"; }
has_ver() {  # — = section text
  line=$(printf '%s\n' "—" | grep -E '^\*\*Plugin at ')
```

Every positional was replaced: the awk field became a bare word, the heading argument became an
em dash, and the filename became `the`. The gate that exists to *prove the docs are current* was
silently corrupted by the argument describing the fix for that corruption. Two things follow.
First, this is not a theoretical hazard reached by a crafted payload — it fires on an ordinary
descriptive argument, which is the normal way a human invokes a skill. Second, it is a
**demonstration of FB-0107 in the same breath**: the corruption appeared in the *installed* copy,
because dogfooding never runs the working tree, so the tree can be fixed and the next session
still sees the bug until the install converges.

**Applies to:** `plugins/flow/skills/{ship,doctor,contribute,verify-build}/SKILL.md`; `plugins/flow/evals/run_arg_safety_evals.py` (§4 asserts the extracted function's output is identical bare vs. under a 3-token argument); FB-0116 (the `$ARGUMENTS` half, same mechanism); FB-0107 (the provenance block this broke); `.claude/rules/general.md` § Consistency item 4.
