#!/usr/bin/env node
// Web-stack preflight runner. Bundles typecheck + build + test into one
// deterministic mechanical gate. Runs at workflow step 4 (between
// Execute and /simplify) and again after /simplify applies any fixes.
//
// Per the flow workflow contract: preflight must be green before any
// reviewer (simplify, staff-review, security-review, accessibility-
// review) runs. Reviewers waste judgment on mechanical bugs a script
// catches in milliseconds.
//
// Convention: print a loud ⚠️ warning for any unset config slot;
// never silently no-op. (Matches the flow plugin's /flow:ship pattern.)
//
// Exit codes:
//   0 — all gates green
//   1 — at least one gate red (caller should not advance to /simplify)
//   2 — script error (missing dependency, missing config)

import { execSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";

const TAG = "[preflight]";
const GATES = [];
let failed = 0;

function loadConfig() {
  if (!existsSync("flow.config.json")) {
    console.error(`${TAG} ⚠️ flow.config.json not found at repo root. Using all built-in defaults; some gates may not run.`);
    return {};
  }
  try {
    return JSON.parse(readFileSync("flow.config.json", "utf-8"));
  } catch (err) {
    console.error(`${TAG} ⚠️ flow.config.json parse error: ${err.message}. Using built-in defaults.`);
    return {};
  }
}

function runGate(name, cmd, { warnOnUnset = false } = {}) {
  if (!cmd) {
    if (warnOnUnset) {
      console.error(`${TAG} ⚠️ ${name} command not set in flow.config.json. Skipping. Set the corresponding slot to enable.`);
    }
    GATES.push({ name, status: "skipped" });
    return;
  }
  console.error(`${TAG} ${name}: ${cmd}`);
  try {
    execSync(cmd, { stdio: "inherit", shell: "/bin/sh" });
    GATES.push({ name, status: "pass" });
  } catch {
    GATES.push({ name, status: "fail" });
    failed++;
  }
}

const config = loadConfig();

// Gate 1: typecheck (config slot)
runGate("typecheck", config.typecheckCmd, { warnOnUnset: true });

// Gate 2: build (web-stack convention — npm/pnpm/yarn run build)
runGate("build", config.buildCmd || "npm run build");

// Gate 3: test (web-stack convention)
runGate("test", config.testCmd || "npm test --silent");

// Summary
console.error(`\n${TAG} summary:`);
for (const g of GATES) {
  const icon = g.status === "pass" ? "✓" : g.status === "fail" ? "✗" : "—";
  console.error(`  ${icon} ${g.name}: ${g.status}`);
}

if (failed > 0) {
  console.error(`\n${TAG} ${failed} gate(s) failed. Fix before /simplify runs.`);
  process.exit(1);
}
console.error(`\n${TAG} all gates green.`);
process.exit(0);
