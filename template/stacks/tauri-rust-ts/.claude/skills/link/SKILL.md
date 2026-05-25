---
name: link
description: >
  Start the project's Tauri dev environment (Vite frontend + Rust backend with
  hot-reload) and return the URL. Use whenever you've made a UI change or a
  Rust command change and want to see it running locally. Idempotent.
disable-model-invocation: false
allowed-tools: Bash
---

# Start the Tauri dev environment

`tauri dev` boots Vite (frontend hot-reload) AND a Rust process running the Tauri shell, with bidirectional invoke hot-reload. This skill is **project-specific** — port + start command may differ.

## Workflow

1. Check whether dev is already running:

   ```sh
   PORT=$(node -e "try{const v=require('./vite.config.ts'); console.log(v.default?.server?.port || v.server?.port || 5173)}catch{console.log(5173)}" 2>/dev/null || echo 5173)
   if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}" | grep -qE '^(200|301|302|404)$'; then
     echo "Dev server already running at http://localhost:${PORT}"
     echo "Note: Tauri window may or may not be open — bring it to foreground if needed."
     exit 0
   fi
   ```

2. Start `tauri dev` in the background:

   ```sh
   npm run tauri dev &
   ```

3. Poll for readiness (Tauri takes longer than Vite alone — cargo build on first run):

   ```sh
   # Vite usually ready in seconds; Rust may take a minute on first run.
   for i in {1..120}; do
     if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}" | grep -qE '^(200|301|302|404)$'; then
       echo "Tauri dev ready at http://localhost:${PORT}"
       echo "Tauri window should open automatically. If not, check 'npm run tauri dev' output."
       exit 0
     fi
     sleep 1
   done
   echo "⚠️ Tauri dev did not become ready within 120s. Check the cargo build output for errors." >&2
   exit 1
   ```

## Notes

- **First `tauri dev` is slow** — cargo builds all dependencies. Subsequent runs are fast.
- **Two hot-reload loops:** Vite reloads frontend; Tauri reloads Rust commands when `src-tauri/` changes (incremental cargo build, ~5-15s).
- **The web-stack URL is the dev URL** — Tauri's window points at the same Vite server.
