# Goal: STT Narration for Prometheus Pipeline

**Status:** Open (assigned: Gopher 🐹)
**Filed:** 2026-07-14 by Evan
**Tracker:** Prometheus / Cave Painter ecosystem

## Vision

While painting in GIMP, Evan speaks into a microphone describing what he's doing and why. This audio gets transcribed via STT (Speech-to-Text) and included in the Prometheus handoff payload alongside the existing canvas snapshot + GTK widget introspection data.

## Why it matters

The current Prometheus pipeline captures **what** the user did (operation name, dialog parameters, canvas diff). It does **not** capture **why**. Narration fills this gap — the AI learns intent, technique, and artistic reasoning, not just mechanical operation sequences.

Result: Cave Painter skills capture the *full* decision tree, not just the terminal leaves.

## How it would work

1. Evan starts painting in GIMP and speaks aloud: *"Gaussian blur the background, radius 15"*
2. Evan clicks **Prometheus Snapshot**
3. Prometheus captures canvas state + reads GTK dialog widgets
4. A parallel audio capture grabs N seconds of mic input
5. Whisper (local, `whisper.cpp`) transcribes the audio to text
6. Transcript is appended to the handoff JSON payload
7. I receive: `{operation, widgets, narration: "Gaussian blur the background, radius 15", canvas_png}`
8. I write skills that understand intent, not just operation names

## Handoff payload shape (proposed)

```json
{
  "operation": "gegl:gaussian-blur",
  "widgets": {"radius": 15.0, "x": 0, "y": 0},
  "narration": "Softening the background layer so foreground text pops — radius 15 should be enough to lose edge detail",
  "narration_timestamp": "2026-07-14T01:55:00Z"
}
```

## Technical requirements

- **STT engine:** `whisper.cpp` (local, fast, no API cost) or `faster-whisper`
- **Audio capture:** `parec` (PulseAudio/pipewire) or `arecord` (ALSA) — triggered by Prometheus Snapshot button
- **Integration hook:** `prometheus-record` GIMP procedure triggers parallel audio capture
- **MCP handoff:** JSON field `narration` and `narration_timestamp`
- **Continuation feed:** Transcript lands in agent session alongside canvas image — no context re-init

## Implementation checklist

- [ ] Capture tool identified/installed (whisper.cpp or faster-whisper)
- [ ] Audio capture CLI command wired to Prometheus Snapshot
- [ ] Prometheus plugin triggers parallel capture + transcription
- [ ] Handoff payload includes `narration` + `narration_timestamp`
- [ ] Agent receives narration in continuation feed alongside canvas PNG

## Related

- Prometheus MCP return path (same handoff pipeline)
- Continuation feed architecture (same injection mechanism)
- Realtime GIMP orchestration (Cave Painter ecosystem)
