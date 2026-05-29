# Plan

## Active Work Items

### Toy feature — submit button

**Mode:** feature (small)
**Goal:** Add a submit button to the home page that POSTs to /api/submit and shows a success toast.

**Scope (in):**
- One button labeled "Submit" on the index page.
- Click handler: POST /api/submit, show toast on 2xx response.
- Server returns 201 with empty body.

**Scope (out):**
- Form validation (no fields).
- Authentication.
- Analytics or tracking.

**Spec-walk:**
- [ ] User can click the Submit button and see a "Submitted successfully" toast within 500ms.
- [ ] Clicking the button twice within 200ms results in only one POST request and one toast.

**Confidence verdicts:** none — toy fixture, no load-bearing assumptions.

**Files touched:** app/index.html, app/src/main.js, app/server.mjs.
