---
name: gimp-mcp-patterns
description: GIMP 3.x API patterns for Cave Painter — displays_flush, context management, GTK dialog widget reading, handoff protocol, native vision workflow, and GIMP API pitfalls
category: cave-painter
trigger: When building or debugging any GIMP 3.x Python operation — check patterns for context management, GTK dialog reading, native vision handoff, class-method syntax, PDB procedure calls, and displays_flush
---

## Native Vision Discovery (July 2026)

DeepSeek V4-Flash has native vision (rolled out June 18, 2026). Confirmed in production. Both the model and the deepseek-provider plugin handle multimodal messages natively — 90 KV cache entries per 800x800 image, $0.000013/image.

### Why This Changes Everything for Handoffs

**Before:** Canvas handoffs required `vision_analyze` tool call → auxiliary pipeline (different model, privacy-gated, hallucinates, expensive).
**After:** Attach PNGs as inline MEDIA: paths → the main model sees them natively. No tool call. No auxiliary pipeline. No privacy blocks. $0.000039 for three images.

### When to use MEDIA: inline vs vision_analyze

| Scenario | Use | Why |
|---|---|---|
| Canvas before/after | MEDIA: inline | Main model sees it natively, $0.000013/image |
| GTK dialog reading | Neither — read Gtk widgets directly | Values in process memory, zero cost |
| External image from URL | vision_analyze with provider=deepseek | Aux pipeline for remote images |
| User-uploaded photo in gateway | MEDIA: inline | Gateway already caches + injects it |

### Provider-specific behavior

Native vision only works when the model provider is **deepseek** (direct to api.deepseek.com) or **openrouter** with `deepseek/deepseek-v4-flash`. It does NOT work through providers that proxy or transform the model. Configure `auxiliary.vision.provider` and `auxiliary.vision.model` in agent config.yaml to match.

### One codebase approach

Do not pull in external GIMP MCP projects (maorcc, martinduartemore, mstampfer) when adding capability. Differences in architecture, socket protocols, plugin registration, and version targets WILL create subtle incompatibility bugs. Implement features directly in the cave-painter codebase. When referencing other projects, steal patterns and API call signatures — not code.

## Critical Patterns from gimp-mcp

### 1. Always call `Gimp.displays_flush()` after operations

This forces GIMP to commit pending changes. Our daemon never calls it, which may cause stale state.

```python
# After ANY operation that modifies the image:
Gimp.displays_flush()
```

### 2. Wrap every operation in `context_push()` / `context_pop()`

Ensures foreground color changes don't leak between operations:

```python
Gimp.context_push()
try:
    Gimp.context_set_foreground(fg_color)
    drawable.edit_fill(Gimp.FillType.FOREGROUND)
finally:
    Gimp.context_pop()
Gimp.displays_flush()
```

### 3. Use class-method syntax for `edit_fill()` and `edit_clear()`

Instead of `drawable.edit_fill(Gimp.FillType.FOREGROUND)`, use:

```python
Gimp.Drawable.edit_fill(drawable, Gimp.FillType.FOREGROUND)
Gimp.Drawable.edit_clear(drawable)
```

This is how gimp-mcp calls these methods — as class methods with the instance as first arg.

### 4. Wrap in `undo_group_start()` / `undo_group_end()`

For multi-step operations:

```python
image.undo_group_start()
try:
    # ... do work ...
finally:
    image.undo_group_end()
```

### 5. `Gimp.Selection.none(image)` to clear selection

Not the rectangle hack:

```python
Gimp.Selection.none(image)  # Proper way in GIMP 3.x
```

### 6. `Gimp.Selection.invert(image)` to invert

```python
Gimp.Selection.invert(image)
```

### 7. Create images with `Gimp.ImageBaseType` not `Gimp.ImageType`

```python
image = Gimp.Image.new(width, height, Gimp.ImageBaseType.RGB)
layer = Gimp.Layer.new(image, name, width, height, Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.NORMAL)
```

Note: `100` not `100.0` for the opacity parameter.

### 8. Fill with background color for initial canvas fill

```python
bg_color = Gegl.Color.new("color_name")  # "white", "black", "red", etc.
Gimp.context_set_background(bg_color)
Gimp.Drawable.edit_fill(layer, Gimp.FillType.BACKGROUND)
```

### 9. Layer color modes

```python
mode_map = {
    "RGB":   Gimp.ImageBaseType.RGB,
    "RGBA":  Gimp.ImageBaseType.RGB,
    "GRAY":  Gimp.ImageBaseType.GRAY,
    "GRAYA": Gimp.ImageBaseType.GRAY,
}
layer_type_map = {
    "RGB":   Gimp.ImageType.RGB_IMAGE,
    "RGBA":  Gimp.ImageType.RGBA_IMAGE,
    "GRAY":  Gimp.ImageType.GRAY_IMAGE,
    "GRAYA": Gimp.ImageType.GRAYA_IMAGE,
}
```

### 10. Reading pixel colors (GIMP 3.2)

```python
pixel = drawable.get_pixel(x, y)
if hasattr(pixel, 'get_rgba'):
    r, g, b, a = pixel.get_rgba()  # Returns floats 0.0-1.0
    r_int, g_int, b_int = int(r*255), int(g*255), int(b*255)
```

### 11. Selection feathering

```python
image.select_ellipse(op, x, y, width, height)
Gimp.Selection.feather(image, feather_amount)  # float
```

## GIMP Dialog State Reading via GTK Introspection

GIMP 3.x filter dialogs are Gtk windows accessible from Python inside the same process. Any GIMP plugin can read every control's value without vision or C code — pure PyGObject.

### Widget type → value reader

| Gtk Widget | Reader | Captures |
|---|---|---|
| `Gtk.SpinButton` | `.get_value()`, `.get_adjustment()` | Value + min/max/step range |
| `Gtk.ComboBoxText` | `.get_active_text()` | Selected text |
| `Gtk.ComboBox` | `.get_active()`, `.get_model()` | Active index + options |
| `Gtk.CheckButton` | `.get_active()` | Boolean |
| `Gtk.ToggleButton` | `.get_active()` | Boolean |
| `Gtk.Entry` | `.get_text()` | Text |
| `Gtk.Scale` | `.get_value()`, `.get_adjustment()` | Slider value + range |
| `Gtk.Switch` | `.get_active()` | Boolean |
| `Gtk.RadioButton` | `.get_active()`, `.get_group()` | Selection + group count |
| `Gtk.ColorButton` | `.get_rgba()` | RGBA floats |
| `Gtk.FileChooserButton` | `.get_filename()` | File path |
| `Gtk.Label` | `.get_text()` | Text (for control identification) |

### Finding the dialog

```python
from gi.repository import Gtk

for window in Gtk.Window.list_toplevels():
    title = window.get_title() or ""
    if any(kw in title.lower() for kw in
           ['gaussian', 'blur', 'levels', 'curves', 'brightness',
            'shadow', 'bevel', 'unsharp', 'sharpen']):
        walk_and_read(window)
```

### Walking widget tree

```python
def walk_widgets(widget, depth=0):
    info = {"class": type(widget).__name__}
    if isinstance(widget, Gtk.SpinButton):
        info["value"] = widget.get_value()
        adj = widget.get_adjustment()
        info["range"] = [adj.get_lower(), adj.get_upper()]
        info["step"] = adj.get_step_increment()
    elif isinstance(widget, Gtk.ComboBoxText):
        info["selection"] = widget.get_active_text()
    elif isinstance(widget, Gtk.CheckButton):
        info["checked"] = widget.get_active()
    if hasattr(widget, 'get_children'):
        info["children"] = [walk_widgets(c, depth+1)
                           for c in widget.get_children()]
    return info
```

## 🚨 CRITICAL: GIMP 3 Plugin Process Lifecycle (2026-07-13 Discovery)

**GIMP 3 plugins run in a SEPARATE OS PROCESS that EXITS when the procedure returns.** This means:
- `GLib.timeout_add()` NEVER fires — the process is dead before any timer ticks
- GTK signal handlers don't persist — the process that registered them is gone
- No background watchers, no daemon-threaded hooks, no persistent state
- The plugin process: spawns → runs the procedure handler → writes output → exits. Period.

**This renders all timer-based and signal-based approaches fundamentally impossible.** Any architecture requiring a persistent background process in a GIMP 3 plugin is wrong. The only reliable pattern is: user clicks menu → plugin runs synchronously → writes output → exits.

## Prometheus Architecture (v4 — Canonical, July 2026)

Instead of intercepting filter dialogs (impossible due to plugin process lifecycle), use **GEGL filter-stack introspection**. GIMP 3 applies filters non-destructively by default — the moment you open Gaussian Blur and adjust the radius, that filter is a live `DrawableFilter` object on the layer. The dialog is just a UI wrapper.

### Flow

```
User opens image → applies Gaussian Blur (non-destructive)
  → filter is already on the layer as DrawableFilter
  → User clicks OK → filter stays on the layer
  → User clicks Tools → Prometheus Snapshot
  → Plugin runs synchronously:
      1. layer.get_filters() → reads ALL DrawableFilter objects
      2. For each filter: get_operation_name(), get_config(), get_opacity()
      3. config.list_properties() → get_property(name) for EVERY param
      4. Export PNG via Gimp.file_save()
      5. Write handoff JSON to /tmp/prometheus/handoff_NNNN.json
      6. Process exits
```

### Key API calls

```python
for layer in image.get_layers():
    for f in layer.get_filters():
        op_name = f.get_operation_name()    # "gegl:gaussian-blur"
        display = f.get_name()              # "Gaussian Blur"
        opacity = f.get_opacity()           # 1.0
        visible = f.get_visible()           # True
        blend = f.get_blend_mode()
        config = f.get_config()             # DrawableFilterConfig GObject
        for pspec in config.list_properties():
            val = config.get_property(pspec.name)  # 1.5, "auto", True, etc.
```

### Captured data

- Full layer tree (names, visibility, opacity, mode, dimensions)
- Every filter on every layer (exact GEGL operation name, all GObject properties)
- PNG of current image state

### Before/after comparison (optional)

Since v4 captures only the current state:
1. **Prometheus Snapshot** → captures current
2. **Edit → Undo** (Ctrl+Z) → removes filter
3. **Snapshot again** → captures before
4. **Edit → Redo** → filter back

GIMP 3 non-destructive filters cleanly undo/redo — no data loss.

### Implementation

Complete working plugin (306 lines) at:
`/home/ekl/.config/GIMP/3.2/plug-ins/prometheus/prometheus.py`

See `references/prometheus-handoff-protocol.md` for the full handoff format,
serialization helpers, and API reference.

## ⛔ Deprecated: v3 Timer-Based Dialog Interception

**DO NOT USE.** Proved impossible in GIMP 3.2.4 (July 2026). Root cause:
GIMP 3 plugins run in a separated process that exits when the procedure returns.
No timer, signal handler, or background thread survives past the procedure boundary.

Kept in the git history of the plugin file for reference only. The widget-reading
code (`walk_widgets()`, `read_widget_value()`) is still valid for the **Cave Painter
daemon** (which has a persistent Gtk main loop). For GUI plugins, use
`layer.get_filters()` instead.

### ⚠️ Pitfall: GIMP 3.2.4 user plugin directory is `3.2/` NOT `3.0/`

**This was the root cause of an entire session of debugging (2026-07-12).**

GIMP 3.2.4 stores user plugins in:
```
~/.config/GIMP/3.2/plug-ins/
```
NOT `~/.config/GIMP/3.0/plug-ins/`.

Every `~/.config/GIMP/3.0/` path seen in tutorials or older docs is for GIMP 3.0.x. Version 3.2 changed the directory number.

**Check before deploying:**
```python
from gi.repository import Gimp
print(f"{Gimp.MAJOR_VERSION}.{Gimp.MINOR_VERSION}.{Gimp.MICRO_VERSION}")
```
- 3.0.x → `~/.config/GIMP/3.0/`
- 3.2.x → `~/.config/GIMP/3.2/`

### Plugin structure for GUI-discovered Python plugins

Create a named subdirectory matching the plugin:
```
~/.config/GIMP/3.2/plug-ins/prometheus/
    prometheus.py    ← Main entry with Gimp.main() + Gimp.PlugIn subclass
```

Required: shebang `#!/usr/bin/python3.14`, `gi.require_version('Gimp', '3.0')`, `gi.require_version('Gegl', '0.4')`.

**Testing:** Check Tools menu in GIMP after restart. DO NOT `exec()` the plugin from the Python-Fu Console — `Gimp.main()` will crash the console and corrupt GIMP state.

### GIMP 3.2 PNG Export

Two confirmed-working approaches, both tested in GUI plugin and headless contexts:

1. **Direct call (simpler, works everywhere):**
   ```python
   Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, gfile, None)
   ```
2. **Config-based PDB (more control over export options):**
   ```python
   from gi.repository import Gimp, Gio
   pdb = Gimp.get_pdb()
   proc = pdb.lookup_procedure("gimp-file-save")
   config = proc.create_config()
   config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
   config.set_property("image", image)
   config.set_property("file", Gio.File.new_for_path("/tmp/output.png"))
   config.set_property("export-options", Gimp.ExportOptions.new())
   result = proc.run(config)
   ```

To discover arguments for any procedure:
```python
for i, arg in enumerate(pdb.lookup_procedure("gimp-file-save").get_arguments()):
    print(i, type(arg).__name__, arg)
# 0: GParamEnum (run-mode), 1: GimpParamImage, 2: GParamObject (GFile), 3: GimpParamExportOptions
```

See `references/gimp-3-2-file-save-api.md` for full details.

### Headless vs GUI API Notes

**GIMP 3.x headless batch mode** (`--batch-interpreter python-fu-eval`) and **GUI plugin mode** share the SAME API surface for all synchronous calls (create images, edit fills, export PNG, etc.). The key difference is **process lifecycle**:

- **Headless daemon:** Persistent process with an active Gtk main loop → can use timers, signal handlers, and background watchers
- **GUI plugin:** Separate process that exits when the procedure returns → NO timers, NO persistent state, NO background watchers

Both modes support the same `Gimp.file_save()` API — confirmed working by Neo (2026-07-13).

## Per-profile HOME path resolution

Each Hermes agent profile has its own `~` resolution:
- Gopher: `/home/ekl/.hermes/profiles/gopher/home/`
- Zephyr: `/home/ekl/.hermes/profiles/zephyr/home/`
- Neo: `/home/ekl/.hermes/profiles/neo/home/`

This means `~/.config/GIMP/3.0/plug-ins/` resolves to a DIFFERENT directory depending on which agent writes it. When Zephyr writes a skill with `~/.hermes/profiles/gopher/skills/...`, the `~` expands to Zephyr's home, not Gopher's.

**Fix:** Always use absolute paths when referencing files across agent profiles. Never use `~/` or `$HOME` in:
- Kanban task body paths
- Skill creation file paths
- Config file references
- Any cross-agent communication

When creating a skill intended for another agent's profile, write to the absolute path of that agent's skill directory.

### Anti-pattern: exec() plugin file from Python-Fu console

Do NOT run `exec(open('/path/to/plugin.py').read())` in GIMP's Python-Fu Console to test plugin loading. The `Gimp.main()` call at the bottom of the plugin file is designed for GIMP startup — calling it from the console tries to re-register procedures in a running session, which crashes GIMP (the plugin itself becomes a dying process with corrupted internal state). If GIMP warns "the dying plug-in may have messed up GIMP's internal state," save your work and restart GIMP.

Instead, check plugin registration via PDB lookup:

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("your-procedure-name")
print("Registered!" if proc else "Not found")
```

Or simply check the Tools menu after restarting GIMP.

### Anti-pattern: Vision for dialog reading

Do NOT screenshot the dialog and run vision. All values are in-process. Vision adds latency, cost, and OCR errors for zero gain. Reserve vision for the canvas itself (before/after diffs).

### What this enables

- **Training corpus**: capture "user set Gaussian Blur radius 5.0, type IIR" paired with pixel effect. Over repeated captures, the AI learns parameter patterns per tool.
- **Self-documentation**: Prometheus dumps any dialog's structure as JSON — no hardcoded UI map needed.
- **Parameter inheritance**: AI defaults to observed values instead of guessing (fixes alpha 1.0 vs 100 problems permanently).

### Wintermute's Design Corrections (v4 update, July 2026)

Applies to Prometheus and any plugin reading filter state:

| # | Principle | Why |
|---|---|---|
| **1** | **GEGL introspection, not dialog interception** | GIMP 3 plugins exit after the procedure returns — no timers, no signal handlers. Use `layer.get_filters()` instead. |
| **2** | **Flatten-before-diff** (if doing before/after diffs) | Transparent/masked layers produce false-positive diffs if you diff the layer stack directly |
| **3** | **Internal sequence counter** — Prometheus tracks its own sequence | GIMP has no undo introspection API |
| **4** | **Manual trigger, not auto-capture** | User clicks Prometheus Snapshot when they want to record state. No auto-capture because no persistent process. |

### Handoff Protocol (v4 — Native Vision + Filter-Stack Introspection)

```json
{
  "sequence": 1,
  "timestamp_utc": 1783924575.44,
  "image_state": {
    "image_name": "[current_xxx] (exported)",
    "width": 600, "height": 600,
    "layer_count": 1,
    "layers": [{
      "name": "gopher-hero.png",
      "visible": true, "opacity": 100.0, "mode": "normal",
      "filters": [{
        "operation": "gegl:gaussian-blur",
        "display_name": "Gaussian Blur",
        "opacity": 1.0, "visible": true,
        "params": {
          "std-dev-x": 1.5, "std-dev-y": 1.5,
          "filter": "auto", "abyss-policy": "clamp"
        }
      }]
    }]
  },
  "current_PNG": "/tmp/prometheus/current_1783924575.png"
}
```

The MEDIA: path attaches the image inline. The model (DeepSeek V4-Flash with native vision) sees it directly — no auxiliary vision tool. Cost: ~$0.000013/image.

See `references/prometheus-handoff-protocol.md` for the full format specification, serialization helpers, and API reference.

## Cross-Platform IPC: Unix Sockets (Chosen) vs File-Based (Rejected)

**Our choice:** Unix sockets, with TCP localhost fallback on Windows < Python 3.12.

Unix domain sockets work on:
- **Linux:** Native
- **macOS:** Native
- **Windows:** Python 3.12+ with Windows 10 build 17063+ (path-based only, no abstract sockets)

```python
import sys
if sys.platform == "win32" and sys.version_info < (3, 12):
    # Fall back to TCP localhost for old Windows
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
else:
    server = await asyncio.start_unix_server(handler, socket_path)
```

**Why Unix sockets over file-based IPC:**
- Lower latency (in-memory buffer vs filesystem I/O)
- Cleaner lifecycle (socket gone when process exits vs stale files)
- Simpler code (one socket call vs numbered file sequencing + polling loop)

**Why file-based IPC was rejected (Vaughn's approach, commit `190eb7b`):**
The user explicitly rejected file-based IPC, calling it "horrible."
The file-based pattern writes numbered JSON files to commands/ and results/ directories,
which works everywhere but adds filesystem overhead and requires cleanup logic.

**Prometheus socket protocol:** Single JSON line per connection.
See `gopher-draw` skill's Prometheus section for the full architecture.

## 🎤 Prometheus STT Narration Pipeline (Planned, July 2026)

Goal filed at `goals/stt-narration-prometheus.md` in the Cave Painter repo. Full design captured as fabric task `t_c622` (assigned Gopher).

### Vision

User paints in GIMP and speaks aloud describing what they're doing and why. Audio gets transcribed via local STT (whisper.cpp, tiny model, ~200ms latency) and included in the Prometheus handoff payload alongside canvas state + GTK widget data.

**Why:** Current pipeline captures WHAT. STT captures WHY. This turns Prometheus from a tool logger into an apprenticeship pipeline — the AI learns intent, not just keystrokes.

### Handoff payload with narration

```json
{
  "operation": "gegl:gaussian-blur",
  "widgets": {"radius": 15.0},
  "narration": "Softening the background layer so foreground text pops — radius 15 should be enough to lose edge detail",
  "narration_timestamp": "2026-07-14T01:55:00Z"
}
```

### Trigger word automation

Instead of clicking a button, the user says natural trigger words — "this", "that", "here", "there" — while painting. Whisper streams continuously; on trigger match, the system:
1. Grabs the rolling transcript buffer (~last 5 seconds)
2. Triggers Prometheus snapshot (canvas + GTK introspection)
3. Packages both into one handoff → agent sees canvas AND narration

### STT engine: whisper.cpp

| Option | Latency | Streaming | Verdict |
|--------|---------|-----------|---------|
| **whisper.cpp** 🏆 | ~200-400ms (tiny) | ✅ Built-in `stream` | **Winner** |
| faster-whisper | ~300-500ms | ⚠️ Needs wrapper | Close second |
| Vosk | ~100-200ms | Good but less accurate |
| OpenAI Whisper | ~1-3s | ❌ Batch only | Too slow |

### Integration sketch

- `prometheus-record` GIMP procedure triggers parallel audio capture
- whisper.cpp transcribes via `./stream` or Python bindings
- Transcript appended to handoff JSON as `narration` + `narration_timestamp`
- Handoff injected as continuation feed (no Memory OS re-init)
- Agent writes skills capturing full intent

### Status

- [x] Research complete — whisper.cpp identified
- [x] Goal filed in fabric + GitHub
- [ ] whisper.cpp installed (`paru -S whisper.cpp`, model: `ggml-tiny.bin`)
- [ ] Audio capture wired to Prometheus Snapshot
- [ ] Handoff includes narration
- [ ] Agent receives narration in continuation feed

## Vision Fallback Chain Across Profiles

Different Hermes profiles handle images differently:

| Profile | Model | `image_input_mode` | Vision |
|---------|-------|-------------------|--------|
| **Gopher** 🐹 | `deepseek-v4-flash` (custom/Direct API) | `auto` | ✅ Native — inline images in context |
| **Neo** 👨‍💻 | (varies) | `auto` | ✅ Depends on provider |
| **Wintermute** 🏛️ | `nvidia/nemotron-free` | `auto` | ⚠️ Provider-dependent |
| **Zephyr** 🌬️ | `cohere/north-mini-code:free` (OpenRouter free) | `no` | ❌ No native vision |

### The fallback

When any agent calls `vision_analyze(url)`, the auxiliary provider handles it:

```yaml
# Root config.yaml
auxiliary:
  vision:
    provider: auto     # routes to best available model with vision
    model: ''
```

With `provider: auto`, it routes to DeepSeek V4-Flash (Gopher's custom API). Zephyr can call `vision_analyze(url)` and get back text — his model never sees the image, but the auxiliary pipeline handles it.

### When to use what

- **MEDIA: inline path** — Only when `image_input_mode: auto`. Use for Prometheus canvas diffs, user screenshots. $0.000013/image.
- **vision_analyze(url)** — Works for any agent via fallback. Extra ~2-3s latency. Use for external URLs (web images, documentation diagrams).

### Verify any profile's image mode

```bash
grep image_input_mode ~/.hermes/profiles/<profile>/config.yaml
```

Full DeepSeek V4-Flash vision specs: `references/native-vision-deepseek-v4.md`

## 🚨 Pitfall: Path Traversal in export()

**Vulnerability:** Agent-controlled `filename` like `"../../.env"` can write
outside the intended output directory if not validated.

**Fix:** Resolve and verify the path against the output directory BEFORE
sending the filename anywhere (defense in depth — also re-check in the
daemon/GIMP process):

```python
from pathlib import Path
OUTPUT_DIR = Path("/tmp/prometheus/")

def resolve_output_path(filename: str) -> Path:
    candidate = (OUTPUT_DIR / filename).resolve()
    if candidate != OUTPUT_DIR and OUTPUT_DIR not in candidate.parents:
        raise ValueError(f"path escapes the output directory")
    return candidate
```

Apply in TWO places:
1. **Client side** (before sending to GIMP) — primary defense
2. **Daemon/GIMP side** (before writing) — defense in depth

Originally discovered by Vaughanwj in their cross-platform fork
(commit `190eb7b`).

### References
- `references/dialog-reading.md` — Full session transcript and test output for GTK dialog reading
- `references/prometheus-handoff-protocol.md` — Complete handoff format spec
- `references/gimp-mcp-protocol.md` — MCP socket architecture
- `references/per-profile-home-resolution.md` — Per-agent HOME path resolution table and pitfalls
- `references/native-vision-deepseek-v4.md` — DeepSeek V4-Flash native vision specs and API examples
- `references/gimp-3-4-plugin-deployment.md` — GIMP 3.4 plugin deployment notes
- **`references/gimp-3-2-file-save-api.md`** — GIMP 3.2.4 file-save API (config-based PDB procedure pattern, added 2026-07-12)
- **`references/gimp-3-2-plugin-deployment.md`** — Full plugin deployment debugging chain (added 2026-07-12)
- **`references/vaughanwj-fork-notes.md`** — Vaughanwj's hexagonal-architecture fork with cross-platform support and bug fixes (added 2026-07-13)