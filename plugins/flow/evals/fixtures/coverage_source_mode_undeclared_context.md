# Coverage-audit context fixture — SOURCE MODE, genuine under-declaration

This is the assembled context `/flow:audit-coverage` feeds the auditor in coverage
mode when invoked with a path (`/flow:audit-coverage <path-to-prototype>`): the same
declared-criteria block, with an approved prototype's SOURCE TREE in place of the
workspace diff. There is no diff at this point in the loop — the prototype has been
approved and a technical plan written, but nothing has been executed.

Drawn from the real D1 §9.3 spike (`dev-docs/research/2026-09-16-d1-auto-plan-quality-spike.md`):
the criteria are verbatim from that spike's auto-written plan, and the source is excerpted
from the prototype it audited (`skills/verify-build/lib/annotation-layer.html`). The
expected auditor output is the sibling `.expected.txt`, covering the spike's finding 1 —
the keyboard-only interaction path, on a prototype whose own comments cite WCAG 2.1.1.

Offline-validated by run_evals.py, exactly like the three diff-mode coverage fixtures:
it pins the assembled-context shape and the expected output schema. It does NOT
demonstrate live LLM behavior — the live invocation is the deferred pluggable step for
every auditor fixture in this suite. The judgment half of this mode's evidence is the
spike's own hand-run plus one live confirmation recorded in the history entry: n=1.

## Declared `**Spec-walk:**` criteria (the claim of what the work covers)

{"criteria": ["Clicking an element while commenting mode is on opens a comment editor pinned to that element → verify: manual click-through in a browser.", "Commenting mode persists across reloads via `localStorage` and defaults to on → verify: toggle off, reload, confirm state survives.", "Selecting text never creates a pin → verify: manual check (drag-select a paragraph, confirm no editor opens).", "Every control in the overlay chrome has an accessible name, and state changes are announced via a polite live region → verify: manual check with a screen reader."], "source_path": "dev-docs/plan.md", "source_heading": "**Spec-walk:**", "warnings": []}

## What was actually built — the workspace diff, or (source mode) the named source tree

[audit-coverage] source mode — repo root: /repo
[audit-coverage] approved source tree: /repo/prototypes/annotation-layer/annotation-layer.html
[audit-coverage] files read: /repo/prototypes/annotation-layer/annotation-layer.html
----- source -----
----- file: /repo/prototypes/annotation-layer/annotation-layer.html -----
  // ---- keyboard walk (WCAG 2.1.1: everything reachable by pointer must be
  // reachable by keyboard; Tab alone cannot reach non-interactive prose, so
  // Shift+Arrow walks the element tree from the current focus) ----------------
  function walkStep(dir) {
    var next = dir < 0 ? prevSibling(current) : nextSibling(current);
    if (next) focusWalkTarget(next);
  }
  function walkDepth(dir) {
    var next = dir < 0 ? current.parentElement : firstEligibleChild(current);
    if (next) focusWalkTarget(next);
  }
  function focusWalkTarget(el) {
    setTarget(el, true);
    el.setAttribute('tabindex', '-1');
    el.focus({ preventScroll: false });
    announce(describe(el) + ' focused. Press Enter to comment.');
  }
  doc.addEventListener('keydown', function (e) {
    if (!modeOn) return;
    if (e.key === 'Enter' && current) { openEditorFor(current); return; }
    if (e.shiftKey && e.key === 'ArrowRight') { walkStep(1); e.preventDefault(); }
    if (e.shiftKey && e.key === 'ArrowLeft')  { walkStep(-1); e.preventDefault(); }
    if (e.shiftKey && e.key === 'ArrowDown')  { walkDepth(1); e.preventDefault(); }
    if (e.shiftKey && e.key === 'ArrowUp')    { walkDepth(-1); e.preventDefault(); }
  });
  doc.addEventListener('focusin', function (e) {
    var el = pickTarget(e.target);
    if (el && el !== current) { setTarget(el, true); targetFromPointer = false; }
  }, true);
