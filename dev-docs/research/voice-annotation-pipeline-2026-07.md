# Voice-first annotation — pipeline design (2026-07)

> **STATUS: PARKED — DO NOT BUILD (2026-07-29).** macOS system dictation solves the stated requirement with **zero code**. Verified end to end in flow's real annotation layer: a spoken sentence transcribed accurately into the note field, with the pin still anchored to its element and the located-descriptor export intact. Everything in § 2 (capture, sliding windows, commit points, two-tier transcription, edit-safety, the whisper service, the `/transcribe` proxy) is **unnecessary** and must not be built without new evidence that dictation is insufficient.
>
> This document is retained for two reasons: § 1 and § 1.1 record *why Web Speech can never work on this machine* (so it is never re-attempted), and § 2 is the design we would grow into if dictation ever proves inadequate. See § 9 for what actually shipped.

**Status:** design spec, superseded before implementation. Supersedes the Web Speech API approach that failed across four distinct modes (see § Why not Web Speech).

**Goal (user direction, 2026-07-27):** in the annotation layer, clicking an element starts *recording* by default rather than typing. Live transcript appears as you speak so you can see what's being picked up and catch errors. Typing stays available for edits. The element-level traceability that already exists is preserved unchanged.

**Why this matters beyond convenience:** typed feedback yields the correction; spoken feedback yields the *reasoning*. "Too heavy" is a blocklist entry. Ninety seconds of why it feels heavy is an axiom that applies to surfaces the agent hasn't built yet. The voice path is the input side of the taste-harvesting loop — it is the mechanism by which the agent's design judgment compounds instead of accumulating prohibitions.

---

## 1. Why not Web Speech

`SpeechRecognition` was the first attempt. Four failure modes, three fixed, one live:

| # | Symptom | Cause | Status |
|---|---|---|---|
| 1 | Blocked in the cloud preview browser | Sandbox grants no mic; often no device at all | Unfixable there — confirmed `not-allowed` at 5ms |
| 2 | Granting permission turned recording off | `start()` called before the permission decision resolved | Fixed — `getUserMedia` pre-flight |
| 3 | Re-prompted on every attempt | `file://` has no stable origin identity, so the grant never persists | Fixed — served over `http://localhost` |
| 4 | "Blinks then goes off" → `no-speech` after 340ms | Chrome cannot reach Google's speech backend — see below | **Diagnosed 2026-07-29** |

### 1.1 What the mic-check actually found (2026-07-29, `tools/mic-check.html`)

**The microphone is perfect.** Peak −8.7 dB, 38% of frames carrying signal across 8 seconds, `trackMuted: false`, built-in MacBook Pro mic, 79 KB of real opus in a 5-second recording, 88.5% non-zero PCM. Nothing is wrong with audio capture on this machine.

**The held-stream hypothesis is REJECTED.** The A/B ran the recogniser with the stream held and with it released. Both phases behaved identically:

```
A (stream held)     start@197ms → audiostart@351ms → ERROR:network@463ms → end
B (stream released) start@218ms → audiostart@550ms → ERROR:network@632ms → end
```

`audiostart` fired in **both** phases — the recogniser acquired the audio device either way, so holding a `getUserMedia` stream does not starve it. The prediction was that A would fail and B would succeed. Both failed, for the same reason, and that reason is not stream contention.

**The real cause is `ERROR:network`.** Chrome's Web Speech API is a *remote* service: it uploads audio to Google and returns text. The error means that upload cannot complete. Permission is granted, the device opens, audio flows — and the request to Google fails ~460 ms in. The earlier `no-speech after 340ms` was the same failure surfacing under a different error code; both are the recogniser giving up before any transcription happens.

**Consequence:** `SpeechRecognition` is unusable on this machine regardless of how the code is written. No amount of stream-lifecycle care fixes a backend it cannot reach. This converts the migration from a preference into a requirement — and it removes the last reason to spend time on the old code path.

The corollary is the good news: every layer the new pipeline actually depends on — `getUserMedia`, `MediaRecorder`, raw PCM — tested clean.

**Independent of that bug, Web Speech is the wrong foundation here:**

- It is a **network service** — Chrome uploads audio to Google and returns text. Not local, not private, and it fails instantly if that path is blocked.
- **Chrome and Safari only.** No Firefox.
- **Tuned for short commands.** This use case is 60–120 seconds of discursive reasoning — precisely where it is weakest and where a real transcription model is strongest.
- It will **never** work in the cloud preview browser.

`ripe/core-docs/plan.md` already wrote down the correct escape hatch for the grocery app — *"fallback: MediaRecorder → server transcription"*. It was never applied to the annotation layer. This spec applies it.

---

## 2. Architecture

```
┌─ browser (annotation-layer.html) ──────────────┐     ┌─ localhost ───────────────┐
│                                                 │     │                           │
│  getUserMedia ──► AudioContext ──► PCM buffer   │     │  flow report server       │
│                        │            (16k mono)  │     │  (stdlib python)          │
│                        │                │       │     │   • serves report + assets│
│                        ▼                │       │     │   • POST /transcribe ─────┼──► whisper-server
│                   AnalyserNode          │       │     │   • GET  /transcribe/health│    (optional,
│                   (level + silence)     │       │     │                           │     user-managed)
│                                         ▼       │     │                           │
│                     every 2s: WAV(tail) ────────┼────►│                           │
│                     on stop:  WAV(all)  ────────┼────►│                           │
│                                                 │     │                           │
│  textarea ◄── committed text + interim text     │     └───────────────────────────┘
└─────────────────────────────────────────────────┘
```

**Everything the page talks to is same-origin.** The report server proxies `/transcribe`, so there is no CORS negotiation and no cross-origin permission surface. This is the single most important structural decision in the design — it is what makes the whole thing degrade cleanly instead of failing in six different ways.

### 2.1 Browser side

1. **Permission gate.** `getUserMedia({audio:true})`. Await the real decision — this was #2's fix and it is retained. Release the stream when recording stops rather than holding it for the session: not because of contention (§ 1.1 disproved that) but because holding a live mic open across an entire review session is the wrong default for a recording indicator the user can't see.
2. **Capture.** `AudioContext` → `ScriptProcessorNode` (or `AudioWorkletNode` where a Blob-URL module is permitted) yields raw `Float32` samples. Deprecated-but-universal beats elegant-but-blocked; a note-taking overlay does not need worklet-grade scheduling. Confirmed reachable: the mic-check pulled 81,920 samples at 88.5% non-zero.
3. **Rate handling — construct the context at 16 kHz.** Use `new AudioContext({ sampleRate: 16000 })` and let the browser resample. Do **not** hand-roll decimation: the mic-check measured a 48 kHz input track feeding a 44.1 kHz default context, giving a decimation factor of **2.75625** — non-integer, so the "box-average N consecutive samples" approach in the first draft of this spec would have aliased badly. The device rate and the context rate are independent and neither is guaranteed; asking for 16 kHz directly sidesteps both. Assert `ctx.sampleRate === 16000` after construction and fall back to linear-interpolation resampling if a browser declines the request.
4. **Buffer** append-only for the duration of the recording. Held in memory. Never written to disk.
5. **Level + silence detection** via `AnalyserNode` — drives both the live meter and the commit heuristic.
6. **Live windows.** Every 2 s, encode `buffer[committedSamples..end]` as a WAV and POST it. Render the response as *interim* text.
7. **Commit points.** When rolling RMS stays below threshold for 700 ms and interim text is non-empty, commit: interim becomes part of the committed prefix, `committedSamples` advances to the buffer end. Force-commit if the uncommitted window exceeds 25 s, to bound per-request cost.
8. **Final pass.** On stop, POST the entire buffer once. Its result replaces the accumulated live text (subject to § 2.4).

### 2.2 The two-tier model

| Tier | When | Input | Purpose | Quality bar |
|---|---|---|---|---|
| **Live** | every 2 s during recording | tail since last commit | let the user *see it working* and catch mistakes | good enough to read |
| **Final** | once, on stop | the complete recording | the text that actually gets saved | as good as the model allows |

This split is what makes the design tractable. The live tier can be fast and imperfect without costing anything, because it is never the artifact — it is a progress indicator made of words. The final pass is a single clean transcription of contiguous audio, which is also the shape whisper is best at.

v1 uses **one model (`base.en`) for both tiers**. The two-tier structure exists from the start so that pointing the final pass at a larger model later is a config change, not a rewrite.

### 2.3 Service side

**`whisper-server`** from whisper.cpp, run by the user, one model per process:

```
whisper-server -m models/ggml-base.en.bin --port 8081
```

flow does not vendor, install, or manage it. The report server proxies to it and probes `/transcribe/health` on page load.

*To verify at build time:* the exact endpoint path and multipart field name of the current whisper.cpp server build, and whether it sets permissive CORS headers (moot if we proxy, which we do).

### 2.4 Edit safety

The user may type at any time, including mid-recording. Rules:

- The transcript occupies a tracked character range in the textarea.
- If the user edits inside or across that range, flow **stops auto-managing it** and switches to append-at-end for subsequent interim text.
- On stop, the final pass **replaces the transcript range only if it is untouched**. If the user edited, the cleaner final text is offered as a one-click "use cleaner transcript" affordance rather than silently overwriting their words.

Never clobber something the user typed. This is the one place where being conservative costs nothing and being clever costs trust.

---

## 3. Delivery surface — an honest constraint

**A published Artifact cannot reach a local transcription service.** Artifacts run under a strict CSP that blocks requests to any external host; `http://localhost:8081` is external relative to `claude.ai`. Voice-in-artifact is not achievable with a local model.

This revises the earlier recommendation that the review prototype should simply be an Artifact. The resolution is two surfaces from one source file:

| Surface | Origin | Voice | Use |
|---|---|---|---|
| **Desktop review** | `http://localhost:PORT` (flow report server) | full pipeline, auto-start | the primary review loop |
| **Phone / sharing** | Artifact URL | **iOS system dictation** into the note field | reviewing away from the desk, sharing |

iOS dictation is genuinely good, on-device for many languages, and requires zero code from us — the textarea just has to be focusable, which it is. So the phone story is real, not a consolation prize; it simply arrives by a different route.

**Not viable:** serving over a LAN IP so the phone hits the desktop service. `getUserMedia` requires a secure context, and `http://` on a LAN IP does not qualify (only `localhost` is exempt). It would need HTTPS with a trusted cert — out of scope.

### 3.1 The report server is worth building regardless

Replacing `file://` report paths with a served `http://localhost:PORT/report.html` fixes failure mode #3 **permanently** and independently of voice: mic grants persist against a real origin, and `localhost` is a secure context. It also removes the awkward "open `/tmp/flow-verify-report.html`" hand-off.

Sketch: stdlib Python, started detached by `/flow:verify-build` Step 10, PID file in temp, idle-timeout (default 2 h) so servers do not accumulate. New slot `reportServerPort` (default `0` = pick a free port). It prints the URL where it currently prints a path.

---

## 4. Data policy

`by-dev-tools/flow` is **public**. All four consumer projects are private. The boundary is therefore load-bearing.

1. **Audio never touches disk.** PCM lives in browser memory and is discarded when the note is committed. There is no file to leak, and no cleanup step that can be forgotten.
2. **If buffering to disk is ever required for reliability**, it goes to an OS temp path — never inside a git working tree.
3. **Belt and braces:** audio extensions (`*.wav *.mp3 *.m4a *.webm *.ogg`) go into the scaffolded `.gitignore`, so a mistake cannot commit a recording.
4. **Transcripts are stricter about travel than they are about storage.** A transcript is the user thinking out loud and may mention anything. It is fine inside a private project repo. It must be classified **never-contributable** on the `/flow:contribute` path, which publishes to a public repo. Only the *synthesized principle* travels upstream — "secondary metadata carries less visual weight, because X" — never the ninety seconds spoken to arrive at it.

Point 4 is also the correct shape for the taste-harvesting loop generally: what compounds across projects is the distilled rule, not the raw speech.

---

## 5. Degradation

Every failure is a visible, explained downgrade to typing. Never a blocking prompt, never a silent no-op.

| Condition | Behaviour |
|---|---|
| Transcription service not running | Mic control hidden; one-line note that dictation needs the local service, with the command |
| `getUserMedia` unsupported / no device | Mic control hidden; typing only |
| Permission denied | Sticky, specific message naming the browser's site-permission control |
| Served over `file://` | Mic control disabled with the reason and the localhost URL to use instead |
| Cloud preview browser | Same as permission-denied; the message names the sandbox as the cause |
| Service reachable but erroring | Recording continues, interim text stalls with a visible "transcription stalled" state; the final pass is retried once on stop |

The existing in-code discipline holds and is worth restating: **one sticky, precise message beats a silent guess-and-retry loop.** An earlier auto-retry stomped the diagnostic before it could be read, which is what made #4 look like "blinks then goes off" — two failed attempts per click, not one.

---

## 6. Integration points

All in `plugins/flow/skills/verify-build/lib/annotation-layer.html`, which is already injected into every rendered report and is dependency-free vanilla JS.

- `openEditor()` (~line 423) — where recording auto-starts. `editText` is the target textarea.
- `closeEditor()` / `commitNote()` / Escape (~lines 439–465) — must stop recording and release the stream on every exit path.
- Toolbar (~line 467) — a "new notes: voice / typing" default toggle, mirroring the existing pick-mode toggle idiom.
- Export (`copyText`, ~line 539) — unchanged. Transcribed text is just text; the located-descriptor export format needs no modification.

The pin/anchor/traceability machinery is untouched. This adds an input method to an existing note; it changes nothing about how notes bind to elements.

---

## 7. Build sequence

1. ~~**`tools/mic-check.html`**~~ — **DONE 2026-07-29.** Mic delivers real audio; every layer the pipeline depends on tested clean. Held-stream hypothesis rejected; Web Speech ruled out for good (§ 1.1). Keep the tool — it is the right first check whenever voice misbehaves on a new machine, and a candidate `/flow:doctor` check.
2. **Report server** — stdlib, serves the report over `localhost`, `/transcribe` proxy + health probe. Independently valuable; fixes failure #3 for good.
3. **Capture + live transcription** in the annotation layer, behind the degradation matrix in § 5.
4. **Edit-safety rules** (§ 2.4) and the final-pass replacement.
5. **Rescue + upstream** the untracked prototypes in `health-tracker/.claude/worktrees/clever-wilbur-a1aecf/craft/explorations/` — commit in place (private repo, preserves the debugging history), then port only the annotation-layer code into flow.

---

## 8. Open questions

- **Model choice for the final tier.** `base.en` for v1. Whether `small.en` is worth the latency on a 90-second note is an empirical question, answered once there is real usage.
- **Commit-point tuning.** The 700 ms silence threshold and 25 s force-commit are starting values, not measured ones.
- **Worklet vs ScriptProcessor.** v1 uses `ScriptProcessorNode` for universality. Whether an `AudioWorklet` via Blob URL survives the artifact CSP is untested — and moot while voice is localhost-only.
- **Does the live tier earn its cost?** If the final pass is what gets saved, the live tier is purely a confidence signal. Worth measuring whether users actually correct mid-stream or just watch it scroll — if the latter, a level meter plus a word count would be far cheaper and might be enough. *(Answered by § 9: the whole tier is moot — dictation renders text live at the OS level for free.)*

---

## 9. Outcome — what actually shipped (2026-07-29)

**Nothing from § 2.** macOS dictation met the requirement with no code.

**The test.** `tools/dictation-test.html` — flow's real `render-report.py` output with the production `annotation-layer.html` injected. Pin → click an element → note box opens with focus already in the textarea → press the macOS dictation shortcut → speak. Result, verbatim from the layer's own export:

```
#1
   at h1 "Verify-build walkthrough"
   note: All right, this is a test for entering comments via dictation in the
   flow annotation layer let's see how much stuff I can say in this comment.
```

Accurate transcription, element anchor preserved, export format untouched.

**Why it works where every prior attempt failed.** Dictation is an *input method*: macOS captures audio and inserts characters into the focused field. The page never calls `getUserMedia`, never calls a speech API, and cannot distinguish dictation from typing. All four failure modes in § 1 live in the browser layer, and dictation does not pass through it. The `annotation-layer.html` preconditions were already satisfied — `openEditor()` calls `editText.focus()`, and the target is a plain `<textarea>` with no `readOnly`, `disabled`, `inputMode`, or `autocomplete` constraints.

**Consequences beyond voice.** § 3's "two surfaces" compromise is dissolved. It existed only because a local whisper service is unreachable from an Artifact's CSP — with no local service, that conflict disappears. A prototype published as an Artifact now supports voice feedback on desktop *and* phone (iOS dictation), from one URL, with no local server. Likewise § 3.1: the report server loses its two load-bearing justifications (mic-grant persistence, the same-origin proxy). Any remaining case for it is ergonomic, not structural, and should be argued on its own merits.

**Observed limitation.** Sentence-boundary punctuation is imperfect — the sample ran two sentences together at "layer let's see". Trivial to fix by typing, and irrelevant to harvesting reasoning from the text.

**The only change worth making to the annotation layer:** a quiet hint that dictation is available. The capability was there the whole time and went unused for a year purely because nothing surfaced it. Discoverability was the actual bug.

**Retained:** `tools/mic-check.html` — still the right first diagnostic if audio ever misbehaves on a new machine, and a candidate `/flow:doctor` check.
