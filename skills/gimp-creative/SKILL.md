---
name: gimp-creative
description: 'Create and edit images programmatically via GIMP 3.x Python-Fu batch mode.'
category: creative
tags: [gimp, image-creation, python-fu, batch, drawing, compositing]
---

# GIMP Creative — Programmatic Image Creation via Python-Fu

Create images, apply effects, composite layers, and export — all through GIMP 3.x
Python-Fu executed headlessly. Works without display via `--no-interface`.

**Production project:** **[Cave Painter](skill_view(name='gopher-draw'))** (kanban: `cave-painter`, directory: `~/Documents/Programming/cave-painter/`, Hermes project: `hermes project show gopher-draw`) — the full multi-agent-safe pipeline with UUID session isolation, fcntl locking, PDB inventory, 6 Neo tasks building MCP server + fonts + filters + paths + installation + E2E testing, and the Plato's Cave multi-model self-portrait research experiment at the end. Business case: zero copyright liability for logos, web assets, diagrams — because GIMP doesn't train on any images. Use `gopher-draw` skill when you need the project-scope wrapper; use `gimp-creative` when you need the raw GIMP 3.x API reference below.

## When to Use

- Creating illustrations, diagrams, or concept art programmatically
- Compositing multiple elements with layers, gradients, text, and filters
- Generating images where SVG or plain Python (Pillow/Cairo) lacks the effect
  you need (glows, gradients, complex layer blending, GEGL filters)
- Building a persistent creative session via an MCP server for iterative drawing

## How It Works

1. Write a JSON recipe describing the canvas + drawing commands
2. Set `GOPHER_DRAW_RECIPE` env var to the recipe path
3. Invoke GIMP headless with Python-Fu eval
4. GIMP creates the image, applies effects, exports PNG

### Prerequisites

- GIMP 3.2.4+ installed (`gimp --version`)
- Python 3.14 with GI bindings (GIMP 3 ships these; on Arch `python-gobject`
  provides `gi` for the right Python version)
- Python-Fu shebangs fixed: GIMP 3.x plug-in files use `#!/usr/bin/env python3`
  but may need `#!/usr/bin/python3.14` if `gi` is only available under a
  secondary Python version. Fix all with:
  ```bash
  sudo find /usr/lib/gimp/3.0/ -name "*.py" -exec sed -i \
    's|#!/usr/bin/env python3|#!/usr/bin/python3.14|g' {} \;
  ```

### Command-line Invocation

```bash
GOPHER_DRAW_RECIPE=/path/to/recipe.json \
HOME=/real/home \
gimp --no-interface --batch-interpreter python-fu-eval \
  -b "exec(open('/path/to/script.py').read())" \\
  --quit
```

Key flags:
- `--no-interface` — suppress GUI
- `--batch-interpreter python-fu-eval` — use Python-Fu
- `-b "..."` — Python code to eval (one or more `-b` flags, executed in order)
- `--quit` — exit GIMP after batch completes (must be last flag)

## Recipe Format (JSON)

```json
{
  "canvas": {"width": 800, "height": 600, "bg": [0.08, 0.12, 0.25]},
  "commands": [
    {"op": "fill", "color": [0.2, 0.3, 0.6]},
    {"op": "gradient", "fg": [0.0, 0.5, 0.8], "bg": [0.08, 0.05, 0.15]},
    {"op": "text", "text": "HELLO", "x": 50, "y": 50, "size": 48,
     "r": 1.0, "g": 1.0, "b": 1.0, "font": "Sans Bold"},
    {"op": "layer", "name": "Glow", "opacity": 70.0}
  ],
  "output": "/tmp/out.png"
}
```

Colors are 0.0–1.0 floats. Commands execute in order on the current active layer.

### Testing Recipes

When building or modifying GIMP headless recipes, use a test harness that:

1. **Injects absolute output paths** — The engine does `os.path.join(session_dir, output)`. When `output` is an absolute path, `os.path.join` returns it verbatim, bypassing the session-scoped temp dir. Use Python to read the recipe JSON, overwrite `.output` with the desired absolute path (including a timestamp suffix for uniqueness), and write a temp recipe file:
   ```python
   R = json.load(open("recipe.json"))
   R["output"] = "/tmp/tests/output/my-recipe-$(date +%s).png"
   json.dump(R, open(tmp_path, "w"))
   ```
2. **Generates a UUID session per recipe run** — Set `GDB_SESSION_ID=$(uuidgen)` to give each recipe its own lock scope.
3. **Checks output size** — A valid GIMP-generated PNG should be > 1000 bytes. Zero-byte files or files under that threshold indicate failure.
4. **Tests session isolation** — Run two recipes concurrently as background GIMP processes, `wait` on both, then compare outputs with `md5sum`. Different checksums prove the sessions did not collide or share state.

For a full working implementation, see the Cave Painter test suite at `~/Documents/Programming/cave-painter/tests/run-tests.sh` (skill: `skill_view(name='gopher-draw')`).

## GIMP 3.x Python API Reference (GI Bindings)

GIMP 3 changed the Python API significantly from 2.x. Key differences:

| Concept | GIMP 2.x | GIMP 3.x |
|---------|----------|----------|
| Color | `Gimp.RGB(r, g, b)` | `Gimp.color_parse_css("rgb(R,G,B)")` → `Gegl.Color` |
| Image type | int `0` (RGB) | `Gimp.ImageType.RGB_IMAGE` |
| Layer type | int `1` (RGBA) | `Gimp.ImageType.RGBA_IMAGE` |
| Layer mode | int `0` (normal) | `Gimp.LayerMode.NORMAL` |
| Fill type | int `0` (foreground) | `Gimp.FillType.FOREGROUND` |
| Gradient fill | `pdb.gimp_drawable_gradient_fill(...)` | `drawable.edit_gradient_fill(type, offset, sup, max_d, thresh, dither, x1, y1, x2, y2)` |
| Text creation | `pdb.gimp_text_fontname(...)` | `Gimp.text_font(image, drawable, x, y, text, border, antialias, size, font)` |
| Font object | string name | `Gimp.Font` — get via `Gimp.context_get_font()` (default) |
| File save | `pdb.file_png_save(1, img, layer, path, ...)` | `Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(path), None)` |
| Delete image | `pdb.gimp_image_delete(img)` | `Gimp.Image.delete(img)` (the method lives on the class) |

### Gradient Fill Correct Signature

```python
active.edit_gradient_fill(
    gradient_type,  # 0=linear, 1=radial, etc.
    offset,        # 0.0
    supersample,   # False
    max_depth,     # 3
    threshold,     # 1.0
    dither,        # True
    x1, y1, x2, y2  # float coordinates
)
```

### Text Layer Creation

```python
default_font = Gimp.context_get_font()  # Get default font object
tl = Gimp.text_font(img, active, float(x), float(y),
                     text, -1, True, float(size), default_font)
# Font objects can't be set by name string via context in GIMP 3.x
```

## Available GIMP Plug-ins

GIMP ships with `python-eval` and `python-console` plug-ins. Place custom
plug-ins in `~/.config/GIMP/3.0/plug-ins/` with execute permission. They are
auto-discovered on GIMP launch.

Script-Fu (Scheme) scripts go in `~/.config/GIMP/3.0/scripts/` and are loaded
as `.scm` files. Use `-b` with the registered function name.

## Multi-Agent Session Isolation

When multiple Hermes agents (Gopher, Neo, Wintermute) draw simultaneously, **each must get its own session** to prevent file collisions. The `gopher-draw` project implements this with:

| Mechanism | What it prevents |
|---|---|
| **UUID session IDs** (`GDB_SESSION_ID`) | Two agents never write to the same temp path |
| **fcntl per-session file lock** | Two agents never launch GIMP for the same session ID |
| **Session-scoped output dirs** | `/tmp/gopher-draw/{uuid}/` — agents can't collide |
| **Per-session GIMP process** | Each session is an independent GIMP invocation |

**Simple approach (no MCP server yet):** Generate a UUID per draw call, pass it as `GDB_SESSION_ID`, and scope the recipe's output path under `/tmp/gopher-draw/{uuid}/`. The lock file at `/tmp/gopher-draw/{uuid}/.session.lock` ensures serialization within a session.

```bash
export GDB_SESSION_ID=$(uuidgen)
mkdir -p "/tmp/gopher-draw/$GDB_SESSION_ID"
# Write recipe with output: "output.png" (relative → /tmp/gopher-draw/{uuid}/output.png)
# Then invoke GIMP as normal
```

## Architecture: Batch (deprecated) vs MCP Daemon (v5)

**Batch mode (deprecated):** Old one-shot approach. GIMP starts, creates image, quits. ~15-30s cold start per invocation. Still works for simple one-offs but avoid for iterative work.

**MCP Daemon (v5, preferred):** Persistent GIMP process that stays alive between tool calls. Image handles (`img_abc123`) let you draw incrementally.

| Aspect | Batch (old) | Daemon (v5) |
|---|---|---|
| GIMP process | Starts, renders, dies per call | Stays alive, processes file commands |
| State | None — each call starts fresh | Shared — image persists between calls |
| Edits | Full re-render every time | Incremental — add one shape at a time |
| Handles | None | `img_abc123`, `ly_0002` |
| Cold start | ~15s every call | ~15s once, then ~0.1s per command |
| Location | `engine.py` (343 LOC) | `cave_painter_server.py` (326 LOC, 9 tools) |

**MCP Daemon (v5) exposes 9 tools:**
- `create_canvas`, `new_layer`, `add_text`, `draw_ellipse`, `draw_rect`, `export`, `export_done`, `done`, `status`

Invocation via Hermes config:
```yaml
cave-painter:
  command: python3
  args: [/home/ekl/Documents/Programming/cave-painter/cave_painter_server.py]
  timeout: 300
  connect_timeout: 30
```

## GIMP PDB Tool Inventory

GIMP's Procedure Database contains 1,028 registered procedures in 3.2.4. A comprehensive
scan of drawing-relevant ones (shadows, bevels, lighting, undo, vector paths, brushes,
blurs, gradients, selections, exports, and animations) is in:

👉 `skill_view(name='gimp-creative', file_path='references/gimp-3-pdb-inventory.md')`
👉 `skill_view(name='gimp-creative', file_path='references/gimp-3-pdb-querying.md')` — how to discover procedures by name via `Gimp.get_pdb().query_procedures()`

This is the catalog to consult when adding new operations to the engine or MCP server.
Every shadow, stroke, filter, and export format GIMP supports is findable there.

## In-Place Editing (Post-Render Fixes)

**❌ NEVER use PIL/Pillow as a GIMP substitute** — this bypasses Cave Painter entirely and defeats the experiment's purpose of proving AI can express through real GIMP tool calls. PIL is only for file I/O outside the pipeline (image metadata for sizing), never for drawing.

For small changes to an existing rendered image (adding text, fixing a detail), **use the persistent GIMP daemon** (see `skill_view(name='gopher-draw')` for the full workflow):

```
# Image is already in a running GIMP session with handle img_abc123
add_text(img_abc123, "G", x=295, y=378, size=14, r=0.2, g=0.2, b=0.2)
export(img_abc123, "output.png")  # same GIMP process, no re-render
```

**Why:** The old batch approach (`gimp --batch --quit`) took ~15s per re-render. The persistent daemon reduces edits to milliseconds and preserves image state between calls.

## File Loading Fails in GIMP 3.x Batch Mode

`Gimp.Image.new_from_file()`, `Gimp.file_load()`, and GIMP PDB `gimp-file-load` all **fail** in headless batch mode (`--no-interface`). GIMP 3.x batch sessions cannot open existing PNG files.

**Workaround:** Use persistent daemon mode (gopher-draw skill) which keeps GIMP alive — but even then loading is unreliable. For loading existing images, read metadata with Python PIL (sizes only, no drawing), then create a matching canvas via `create_canvas(width, height)` and draw equivalent shapes.

## Bezier Circle/Ellipse Approximation

GIMP 3.x `bezier` ops don't have native circle/ellipse primitives. Approximate with 4 cubic bezier segments using the magic constant `k = 0.5522847498`:

```python
k = 0.5522847498 * radius * scale
# Start at (cx, cy - r)
# 4 cubicto segments at ±k and ±r from center
# Close
```

| Shape | Segments | Formula |
|-------|----------|---------|
| Circle | 4 cubicto + close | Start at (cx, cy-r), control at ±k from center |
| Ellipse | 4 cubicto + close | kx = k × rx, ky = k × ry |
| Rectangle | moveto + 3 lineto + close | Straight edges |

Full SVG-to-Cave-Painter conversion in `skill_view(name='svg-to-cave-painter')`.

## Pitfalls

- **Layer opacity is 0-100 scale (NOT 0-1)!** `Gimp.Layer.new()` takes opacity as 0-100. Using `1.0` creates a layer at 1% opacity — every pixel exports at alpha=2-5. Always use `100.0`. This was the root cause of invisible Cave Painter output for hours of debugging.
- **`img.insert_path()` required before `edit_stroke_item()`** — Brush/paint stroking silently does nothing if the Gimp.Path isn't first inserted into the image via `img.insert_path(po, None, 0)`. Always insert before stroke.
- **Font resolution:** `Gimp.text_font()` takes a `Gimp.Font` object, not a name string. Use `Gimp.fonts_get_list("")` for name lookup.
- **`fill()` vs `edit_fill()`** — `fill()` fills the entire drawable ignoring selections. `edit_fill()` respects selection bounds and sets alpha correctly. Use `edit_fill()` for selection fills.
- **HOME override (CRITICAL)**: GIMP reads config from `~/.config/GIMP/3.0/`. If the Hermes profile overrides `$HOME`, scripts/plug-ins won't be found at the expected path. **This bites us every single time.** Always pass `HOME=/home/ekl` AND `GIMP2_DIRECTORY=/home/ekl/.config/GIMP/3.0` when launching GIMP as a subprocess.
- **GIMP 3.x batch**: The `--batch-interpreter` flag is required. Without it,
  `-b` falls back to Script-Fu. Use `python-fu-eval` for Python.
- **GIMP 3.x API**: The old `gimpfu` module is gone. Use GI bindings
  (`gi.repository.Gimp`). Almost all GIMP 2.x constants (int codes) have been
  replaced with typed enums. See `references/gimp-3-api-quirks.md` for the
  complete gotcha catalog.
- **Python version mismatch**: `gi`/PyGObject may be installed for a different
  Python version than `python3`. Fix shebangs or use the correct Python binary.
- **Timeout**: GIMP takes ~10-15s to initialize. Set terminal timeout ≥ 45s.
- **Font names**: Cannot be set by string in GIMP 3.x batch mode. Only the
  default 'Sans-serif' font is available via `Gimp.context_get_font()`. Font
  resolution via PDB or MCP server is a future improvement.
- **Absolute output paths**: The engine saves via `os.path.join(session_dir, output)`.
  When `output` is an absolute path, `os.path.join` ignores the session dir and
  writes directly to the absolute path. This is useful for test harnesses that
  want output in a specific directory, but risky for multi-agent scenarios where
  you expect session isolation — use relative output filenames in production
  (e.g. `"output.png"`) and absolute paths only in test contexts.
