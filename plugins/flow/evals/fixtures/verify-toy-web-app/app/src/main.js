// Toy submit handler — illustrates the feature pinned by the plan's Spec-walk.
// Implements double-submit guard via in-flight flag so the second click no-ops.

const button = document.getElementById("submit");
const toast = document.getElementById("toast");
let inFlight = false;

button.addEventListener("click", async () => {
  if (inFlight) return;
  inFlight = true;
  try {
    const res = await fetch("/api/submit", { method: "POST" });
    if (res.ok) {
      toast.textContent = "Submitted successfully";
    } else {
      toast.textContent = `Submit failed (${res.status})`;
    }
  } finally {
    inFlight = false;
  }
});
