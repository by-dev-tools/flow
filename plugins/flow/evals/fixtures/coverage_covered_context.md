# Coverage-audit context fixture — fully covered (must NOT flag)

The low-false-positive control: every behavior change in the diff maps to a
declared criterion, so the correct output is `No issues flagged.` See sibling
`.expected.txt`.

## Declared `**Spec-walk:**` criteria (the claim of what the work covers)

{"criteria": ["User can submit the contact form and see a success toast.", "Submitting with an empty email shows an inline validation error."], "source_path": "dev-docs/plan.md", "source_heading": "**Spec-walk:**", "warnings": []}

## Workspace diff — source files changed vs the default branch (what was actually built)

Behavior-bearing files changed: src/contact.js
----- diff -----
@@ src/contact.js @@
+async function submit(data) {
+  // empty-email validation (declared criterion 2)
+  if (!data.email) {
+    showInlineError('email', 'Email is required');
+    return;
+  }
+  // success toast (declared criterion 1)
+  const res = await fetch('/api/contact', { method: 'POST', body: JSON.stringify(data) });
+  if (res.ok) showToast('Sent!');
+}
-// (renamed an internal helper; no behavior change)
-function _fmt(x) { return x.trim(); }
+function formatField(x) { return x.trim(); }
