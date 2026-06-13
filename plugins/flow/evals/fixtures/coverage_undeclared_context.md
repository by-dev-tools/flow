# Coverage-audit context fixture — genuine under-declaration

This is the assembled context `/flow:audit-coverage` feeds the auditor in coverage
mode (declared criteria + the source diff). The expected auditor output is the
sibling `.expected.txt`. Offline-validated by run_evals.py; the live invocation is
the deferred pluggable step (same as every other auditor fixture).

## Declared `**Spec-walk:**` criteria (the claim of what the work covers)

{"criteria": ["User can submit the contact form and see a success toast."], "source_path": "dev-docs/plan.md", "source_heading": "**Spec-walk:**", "warnings": []}

## Workspace diff — source files changed vs the default branch (what was actually built)

Behavior-bearing files changed: src/contact.js
----- diff -----
@@ src/contact.js @@
+async function submit(data) {
+  // success-toast path (declared)
+  const res = await fetch('/api/contact', { method: 'POST', body: JSON.stringify(data) });
+  if (res.ok) showToast('Sent!');
+
+  // NEW behavior: client-side rate limit — after 3 submits in 60s, block the
+  // submission and show a "Too many requests — try again later" banner instead.
+  if (rateLimiter.exceeded()) {
+    showBanner('Too many requests — try again later');
+    return;
+  }
+}
