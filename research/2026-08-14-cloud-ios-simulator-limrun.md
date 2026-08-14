# Cloud iOS Simulator Testing for Agents — Limrun & Alternatives

> **Scope note:** This is an exploratory research note, **not** part of the flow
> plugin. It concerns running/testing iOS simulators in the cloud for other
> projects (health-tracker, trio) and lives under `research/` so it stays
> greppable without touching any plugin surface (`plugins/flow/`), flow's own
> dev-tracking (`dev-docs/`), or project-dev infra (`.claude/`). Nothing here
> ships with the plugin.
>
> - **Date:** 2026-08-14
> - **Status:** Parked — not being pursued right now.
> - **Trigger:** Difficulty running cloud agents that build/test iOS apps.

## Problem

A cloud Linux agent (e.g. Claude Code on the web) **cannot** build or run an iOS
app: no macOS kernel, no Xcode toolchain, no `xcrun simctl`, no Simulator.app.
Apple's simulator only runs on macOS and iOS builds legally require macOS. So a
cloud agent can edit Swift and reason about diffs, but cannot close the loop that
matters: `xcodebuild` → boot simulator → launch app → tap through → screenshot →
confirm it works.

## Limrun (lim.run)

- 2025 YC-backed startup (S26), founder **Muvaffak Onuş** (ex-Upbound/Crossplane —
  "cloud primitives as an API" DNA).
- Pitch: native mobile dev environments (macOS/Xcode, iOS Simulators, Android
  emulators, physical devices) exposed as **on-demand cloud instances** a Linux
  cloud agent drives remotely. Targets exactly the "coding agents in the cloud
  can't do mobile" gap.
- Customers are agent companies: **Replit, Rork, Momentic, Minitap**.

**Technical model**
- An **"instance"** = an iOS simulator, Android emulator, or Xcode build sandbox.
  Has an ID, own endpoints, lives until deleted or an inactivity timeout fires.
- SDK **`@limrun/api`** (TypeScript / Python / Go), all wrapping one REST API,
  meant to be called from *your backend* to provision on behalf of users.
- iOS instances ship with **WebDriverAgent pre-installed**; drive via **Appium**.
  Creation params include `wait: true`, `reuseIfExists: true`, initial-asset specs.
- Output is agent-friendly: build + validate → **demo videos** + embeddable
  **live-preview URL** reviewers open in any browser.
- Pricing: idle/build-time, on-demand. **Exact per-minute/hour rates unconfirmed**
  (pricing page behind a 403; not in any cached source). Get this directly before
  committing, plus **concurrent-instance limits on the entry tier**.

## Alternatives / landscape

| Option | What it's for | Notes |
|---|---|---|
| **Limrun** | Agent-driven mobile build+drive+preview | Built for the coding-agent workflow specifically |
| **Appetize.io** | Browser-embeddable sims, shareable links, CI | Strong on demos/preview, weaker as general build host |
| **Corellium** | True ARM iOS *virtualization* | Overkill/expensive unless real-device fidelity / security research |
| **BrowserStack App Live / TestMu (ex-LambdaTest)** | Real-device QA clouds | More QA-team than build-agent oriented |

**Open-source / DIY building blocks**
- **[callstack/agent-device](https://github.com/callstack/agent-device)** — CLI/MCP
  server purpose-built for AI agents to inspect/drive iOS/Android via accessibility
  trees + deterministic taps/scrolls + evidence capture. Has an "Agent Device Cloud"
  for Linux runners against macOS executors. Closest OSS analog to Limrun's
  agent-control half.
- **[conorluddy/ios-simulator-skill](https://github.com/conorluddy/ios-simulator-skill)**
  — Claude Code skill wrapping `xcodebuild`/`simctl` so an agent running *on a Mac*
  can build/run/interact with simulators.
- Underneath: `xcodebuild`, `simctl`, Appium + WebDriverAgent, Maestro/idb.
- **Caveat:** all DIY paths still need a real macOS host (Mac mini, EC2 Mac,
  MacStadium, Scaleway Apple Silicon, MacinCloud).

## Options considered

- **A — Integrate Limrun (managed).** Fastest to a working cloud-agent iOS loop;
  no macOS ops. Best if the goal is to unblock now and not own infra.
- **B — DIY from OSS.** Own a Mac host + `agent-device` + the simulator skill.
  Control, no per-minute markup; inherits macOS ops, Xcode version mgmt, sim flake.
- **C — Hybrid (recommended if revisited).** Rent one Apple-silicon macOS box, run
  `agent-device` (MCP) on it, expose to cloud agents over SSH/MCP. ~90% of Limrun's
  value for one machine; fall back to Limrun for burst parallelism / physical devices
  / shareable preview URLs.

## If revisited — next steps

1. Get Limrun's real pricing + entry-tier concurrency limits.
2. Prototype Option C: point a cloud Claude Code session at a macOS executor running
   `agent-device`; measure the build→drive→screenshot loop.
3. Compare against a small Limrun SDK spike (create iOS instance → install build →
   Appium tap-through → pull screenshot).

## Sources

- https://lim.run/ · https://docs.limrun.com/docs · https://www.ycombinator.com/companies/limrun
- https://f4.fund/startups/lim-run · https://www.mintlify.com/limrun-inc/typescript-sdk/examples/appium-ios
- https://github.com/callstack/agent-device · https://agent-device.dev/cloud
- https://github.com/conorluddy/ios-simulator-skill
- https://www.corellium.com/compare · https://qodex.ai/blog/browserstack-alternatives
