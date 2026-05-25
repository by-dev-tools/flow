#!/usr/bin/env node
// Tauri-rust-ts preflight runner.
//
// JS/TS side:  typecheck + build + test
// Rust side:   cargo fmt --check + cargo clippy -D warnings + cargo test
//
// See template/stacks/web/tools/preflight/check.mjs header for the workflow
// contract and the loud-warning idiom for unset config slots.
//
// Exit codes: 0 = green, 1 = red gate, 2 = script error.

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

function runGate(name, cmd, { cwd = ".", warnOnUnset = false } = {}) {
  if (!cmd) {
    if (warnOnUnset) {
      console.error(`${TAG} ⚠️ ${name} command not set in flow.config.json. Skipping. Set the corresponding slot to enable.`);
    }
    GATES.push({ name, status: "skipped" });
    return;
  }
  console.error(`${TAG} ${name} (cwd=${cwd}): ${cmd}`);
  try {
    execSync(cmd, { stdio: "inherit", shell: "/bin/sh", cwd });
    GATES.push({ name, status: "pass" });
  } catch {
    GATES.push({ name, status: "fail" });
    failed++;
  }
}

const config = loadConfig();
const rustDir = config.rustWorkspaceDir || "src-tauri";  // tauri convention

// JS/TS gates
runGate("ts:typecheck", config.typecheckCmd, { warnOnUnset: true });
runGate("ts:build", config.buildCmd || "npm run build");
runGate("ts:test", config.testCmd || "npm test --silent");

// Rust gates (only if rustDir exists)
if (existsSync(rustDir)) {
  runGate("rust:fmt", `cargo fmt --all -- --check`, { cwd: rustDir });
  runGate("rust:clippy", `cargo clippy --workspace --all-targets -- -D warnings`, { cwd: rustDir });
  runGate("rust:test", `cargo test --workspace`, { cwd: rustDir });
} else {
  console.error(`${TAG} ⚠️ ${rustDir}/ not found. Skipping Rust gates. Set flow.config.json.rustWorkspaceDir if your Rust code lives elsewhere.`);
}

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
