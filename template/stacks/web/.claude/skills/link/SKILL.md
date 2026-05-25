---
name: link
description: >
  Start the project's local dev server (Vite by convention) and return the URL.
  Use whenever you've made a UI change and want to see it in-browser, or whenever
  /flow:staff-review's UX-designer / design-engineer / push-further lens needs
  a live URL to reference. Idempotent — if the server is already running, just
  returns the URL.
disable-model-invocation: false
allowed-tools: Bash
---

# Start the project dev server

This is a **project-specific skill** — it lives in `.claude/skills/link/` (not in the flow plugin) because the dev server command + port are stack-specific. The web-stack template ships this Vite version; swap to your project's actual command if different.

## Workflow

1. Check whether the dev server is already running:

   ```sh
   PORT=$(node -e "try{const v=require('./vite.config.ts'); console.log(v.default?.server?.port || v.server?.port || 5173)}catch{console.log(5173)}" 2>/dev/null || echo 5173)
   if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}" | grep -qE '^(200|301|302|404)$'; then
     echo "Dev server already running at http://localhost:${PORT}"
     exit 0
   fi
   ```

2. Start the server in the background:

   ```sh
   npm run dev &
   ```

3. Poll for readiness (max 10 seconds), then return the URL:

   ```sh
   for i in {1..20}; do
     if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}" | grep -qE '^(200|301|302|404)$'; then
       echo "Dev server ready at http://localhost:${PORT}"
       exit 0
     fi
     sleep 0.5
   done
   echo "⚠️ Dev server did not become ready within 10s. Check 'npm run dev' output." >&2
   exit 1
   ```

## Notes

- **Default port is Vite's 5173** unless your `vite.config.ts` overrides it.
- **Hot-reload is on by default** — UI changes hot-reload without restarting. No need to re-invoke `/link` after edits.
- **For non-Vite stacks** (Next.js, Astro, etc.) replace the port-detection logic and `npm run dev` invocation accordingly.
