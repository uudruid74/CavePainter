---
name: gimp-brush-install-and-use
description: Loading .gbr/.abr brushes, refreshing brush list, paintbrush vs pencil vs airbrush tools, scaling brushes in GIMP 3.x via Cave Painter
category: cave-painter
trigger: When you need to load custom brushes (.gbr/.abr), refresh the brush list, choose between paintbrush/pencil/airbrush tools, or scale/resize a brush in Cave Painter
---

## Brush Installation & Management in GIMP 3.x

### Brush File Types

| Extension | Type | Notes |
|---|---|---|
| `.gbr` | GIMP Brush | Native GIMP format, single brush per file |
| `.gbz` | Compressed GIMP brush | Rare |
| `.abr` | Adobe Photoshop Brush | GIMP imports these natively — may support multiple brushes per file |
| `.vbr` | GIMP Animated Brush | Animated/parametric brushes (deprecated in 3.x, use `.gbr`) |

### Loading Custom Brushes

Place `.gbr` or `.abr` files in GIMP's brushes folder, then refresh or restart GIMP.

**Brushes folder paths:**

| GIMP Version | Path |
|---|---|
| GIMP 3.0 | `~/.config/GIMP/3.0/brushes/` |
| GIMP 3.2 | `~/.config/GIMP/3.2/brushes/` |
| Snap/GNOME Flatpak | `~/snap/gimp/current/.config/GIMP/3.0/brushes/` or `~/.var/app/org.gimp.GIMP/config/GIMP/3.0/brushes/` |

**Process:**
```bash
# Copy a brush file to the brushes folder
cp my_custom_brush.gbr ~/.config/GIMP/3.2/brushes/

# Copy Photoshop .abr brushes (GIMP imports them automatically)
cp my_photoshop_brushes.abr ~/.config/GIMP/3.2/brushes/
```

### Refreshing the Brush List

After placing new brush files, you must refresh GIMP's brush registry. The MCP daemon runs inside an existing GIMP session, so you can't restart — use PDB:

```python
# Refresh brush list from disk
Gimp.get_pdb().lookup_procedure('gimp-brushes-refresh').execute([])
Gimp.displays_flush()

# Alternative via direct PDB call
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure('gimp-brushes-refresh')
proc.execute([])
```

After refreshing, the new brushes appear in `Gimp.brushes_list()`:

```python
all_brushes = Gimp.brushes_list()
new_brush = [b for b in all_brushes if "custom" in b.get_name().lower()]
```

### Available Built-in Brushes (58 total)

Visible via the Cave Painter MCP `list_brushes` tool. Key brushes:

| Category | Examples |
|---|---|
| **Pixels** | `1. Pixel`, `Pixel (1x1 square)` |
| **Blocks** | `2. Block 01`, `Block 02`, `Block 03` |
| **Hardness** | `2. Hardness 025`, `050`, `075`, `100` |
| **Acrylic** | `Acrylic 01` – `05` |
| **Chalk** | `Chalk 01`, `02`, `03` |
| **Charcoal** | `Charcoal 01`, `02`, `03` |
| **Oils** | `Oils 01`, `02`, `03` |
| **Pencil** | `Pencil 01`, `02`, `03`, `Pencil Scratch` |
| **Textures** | `Texture 01`, `02`, `Texture Hose 01`–`03` |
| **Effects** | `Smoke`, `Sparks`, `Splats 01`, `02`, `Confetti`, `Grass`, `Vine` |

### Cave Painter MCP Brush Workflow

1. **Create a canvas**: `create_canvas(width, height)`
2. **List available brushes**: `list_brushes(image)` — returns 58 built-in brush names
3. **Create a brush preset handle**: `new_brush(image, brush_name, size, hardness, aspect_ratio, angle, spacing, force)`
   - `brush_name`: string name from `list_brushes` (e.g. `"2. Hardness 100"`)
   - `size`: pixel diameter
   - `hardness`: 0.0–1.0
   - `aspect_ratio`: width/height ratio (default ~1.0)
   - `angle`: rotation in degrees
   - `spacing`: spacing between dabs as fraction of brush width
   - `force`: 0.0–1.0
4. **Create a layer**: `new_layer(image, name)`
5. **Paint a single dab**: `paint_dab(image, brush, x, y, size, color_r, color_g, color_b)`
6. **Paint a stroke**: `paint_stroke(image, brush, strokes, color_r, color_g, color_b)` — same stroke format as `draw_bezier`
7. **Release brush**: `drop_brush(image, brush)` — frees the brush preset handle
8. **Export**: `export(image, path)` or `export_done(image, path)`

### Brush vs. Paint Tools: Which to Use

In GIMP 3.x Python API (not via MCP — for daemon-level script-fu), the paint tools are:

#### `Gimp.paintbrush_default(drawable, coords)`

Smooth, flowing strokes. Uses the current context brush + foreground color. Best for:
- Curves, calligraphy, soft edges
- Artistic strokes with textured brushes
- Anti-aliased edges

```python
Gimp.context_push()
green = Gegl.Color.new("green")
Gimp.context_set_foreground(green)
Gimp.context_set_brush_size(20.0)
Gimp.paintbrush_default(drawable, [100, 50, 200, 150, 300, 50])
Gimp.context_pop()
Gimp.displays_flush()
```

#### `Gimp.pencil(drawable, coords)`

Hard-edged straight line segments. No anti-aliasing. Best for:
- Pixel-art lines
- Precise hard edges
- Technical diagrams

```python
Gimp.context_push()
Gimp.context_set_foreground(gegl_color)
Gimp.pencil(drawable, [0, 200, 200, 0])
Gimp.context_pop()
Gimp.displays_flush()
```

#### `Gimp.airbrush(drawable, coords)`

Gradual, soft application — like spray paint. Paint accumulates while the brush stays in place. Best for:
- Soft gradients
- Shading
- Glow effects

```python
Gimp.context_push()
Gimp.context_set_foreground(gegl_color)
Gimp.context_set_brush_size(30.0)
Gimp.airbrush(drawable, [200, 150])
Gimp.context_pop()
Gimp.displays_flush()
```

### Scaling / Resizing Brushes

**Via MCP (Cave Painter):**
- Pass `size=N` to `new_brush()` — sets the brush diameter in pixels
- Pass `size=N` to `paint_dab()` — overrides the brush size for this single dab
- Pass `aspect_ratio=X` to `new_brush()` — scale non-uniformly

**Via GIMP Python API:**
```python
# Set brush size on the context
Gimp.context_set_brush_size(15.0)  # diameter in pixels

# Read current brush size
current_size = Gimp.context_get_brush_size()
```

### Full End-to-End Example

```python
# 1. Refresh brushes from disk (after installing new .gbr)
from gi.repository import Gimp, Gegl
pdb = Gimp.get_pdb()
refresh = pdb.lookup_procedure('gimp-brushes-refresh')
refresh.execute([])

# 2. List available brushes
brushes = Gimp.brushes_list()
for b in brushes:
    print(f"{b.get_name()} — size: {b.get_radius() * 2}")

# 3. Set a specific brush
Gimp.context_set_brush(brushes[10])  # by index
# OR by name
named_brush = next(b for b in brushes if b.get_name() == "2. Hardness 100")
Gimp.context_set_brush(named_brush)

# 4. Size the brush
Gimp.context_set_brush_size(50.0)

# 5. Paint with it
Gimp.context_push()
Gimp.context_set_foreground(Gegl.Color.new("red"))
Gimp.paintbrush_default(drawable, [50, 50, 200, 200])
Gimp.context_pop()
Gimp.displays_flush()
```

### Pitfalls

- **`context_set_foreground()` must be called BEFORE `context_set_brush()`** — the brush snapshots the current foreground color. Setting FG after the brush means stale color.
- **ABR multi-brush files**: GIMP imports all brushes from an `.abr` file, but each sub-brush shows up as a separate entry in `Gimp.brushes_list()` — you can't access sub-brushes by index within the file.
- **No restart needed**: `gimp-brushes-refresh` PDB procedure loads new brushes without restarting GIMP.
- **Animated brushes (.vbr)**: deprecated in GIMP 3.x. Convert to `.gbr` if possible.
- **Brush handles are ephemeral**: In Cave Painter MCP, `new_brush()` returns a handle (e.g. `brush_0002`). You must `drop_brush()` to free it — they're session-scoped and don't persist across daemon restarts.
- **The MCP layer handles brush context internally**: `paint_dab()` and `paint_stroke()` take explicit color and size parameters — they don't depend on GIMP context state. Only raw Python API calls need `context_set_foreground`/`context_set_brush`.
