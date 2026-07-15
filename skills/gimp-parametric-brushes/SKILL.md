---
name: gimp-parametric-brushes
description: Create and configure parametric (.vbr) brushes in GIMP 3.x — radius, hardness, spikes, aspect ratio, paintbrush vs airbrush, and Dry Media presets
category: cave-painter
trigger: When setting up custom brush presets for painting — parametric brushes for pencil, charcoal, pastel effects
---

## GIMP 3.x Parametric Brushes

Parametric brushes (.vbr) are vector-based brushes configurable via API parameters: radius, hardness, spikes, aspect ratio, angle, and spacing.

### Available Brushes (58 built-in)

Use `Gimp.brushes_get_list("")` to list all available brush names.

Common parametric brushes by category:

| Category | Examples |
|---|---|
| Hardness | `"2. Hardness 100"`, `"2. Hardness 075"`, `"2. Hardness 050"`, `"2. Hardness 025"` |
| Blocks | `"3. Block 01"`, `"3. Block 02"` |
| Pixels | `"pixel (01)"`, `"pixel (03)"`, `"pixel (05)"` |
| Acrylic | `"2. Acrylic 01"`, `"2. Acrylic 03"` |
| Chalk | `"2. Chalk 01"` |
| Charcoal | `"2. Charcoal 01"`, `"2. Charcoal 03"`, `"2. Charcoal 05"`, `"2. Charcoal 06"` |
| Oils | `"2. Oils 01"`, `"2. Oils 04"` |
| Pencil | `"2. Pencil 01"`, `"2. Pencil 02"` |
| Textures | `"2. Texture 01"`, `"2. Texture 02"` |

### Setting Brushes via API

```python
# Select a brush by name with size override
brush = Gimp.brushes_get_list("")[0]  # or use brush name lookup
Gimp.context_set_brush(brush)
Gimp.context_set_brush_size(20.0)       # radius in pixels
Gimp.context_set_brush_hardness(1.0)    # 0.0-1.0
Gimp.context_set_brush_spacing(10)      # stamp spacing
```

### Painting Tools Comparison

| Function | Best For | Edge Quality |
|---|---|---|
| `Gimp.paintbrush_default(drawable, coords)` | Smooth strokes with current brush | Soft/smooth |
| `Gimp.pencil(drawable, coords)` | Hard-edged lines with same brush | Hard/sharp |
| `Gimp.airbrush(drawable, coords)` | Gradual build-up, soft coverage | Variable by rate |

### Context Safety

```python
Gimp.context_push()
try:
    Gimp.context_set_foreground(Gegl.Color.new('black'))
    brush = Gimp.brushes_get_list("")[0]
    Gimp.context_set_brush(brush)
    Gimp.context_set_brush_size(15.0)
    Gimp.context_set_brush_hardness(0.8)
    Gimp.paintbrush_default(drawable, [100, 100, 200, 200])
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### Dry Media Presets (from GIMP tutorial)

| Medium | Brush | Size | Hardness | Spacing | Tool |
|---|---|---|---|---|---|
| Pencil | 2. Pencil 01 | 3 | 1.0 | 1 | Paintbrush |
| Charcoal | 2. Charcoal 03 | 15 | 0.6 | 20 | Paintbrush |
| Pastel | 2. Chalk 01 | 40 | 0.3 | 30 | Airbrush |
| Color Pencil | 2. Pencil 02 | 8 | 0.8 | 8 | Paintbrush |

### Creating Custom Brushes (MCP Cave Painter)

Via the Cave Painter daemon, use `new_brush()`:

```python
new_brush(image=img, brush_name="2. Hardness 100", size=20.0)
# Returns a brush handle like brush_0001
```

Then use `paint_stroke()` or `paint_dab()` with the handle.
