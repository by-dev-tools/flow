# Design brief — Undo last delete

**Problem:** Users who delete an item by mistake have no way to get it back.
**Whose moment:** Anyone who deletes a row in the list view, immediately after the action.
**Constraints:** Must work within the existing list view; no new backend storage.
**Intended scope:** Add an "Undo" text link that appears for 5 seconds after a delete, restoring the item on click.
**Deliberately excluded:** No undo history, no multi-item undo, no keyboard shortcut.
**Where this pushes past the literal request:** Nowhere — this satisfies exactly what was asked.
