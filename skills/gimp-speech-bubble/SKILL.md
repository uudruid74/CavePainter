---
name: gimp-speech-bubble
description: Create comic-style speech bubbles (text balloons) via Cave Painter MCP tools or direct GIMP Python-Fu. Covers ellipse oval + polygon tail, white fill, path conversion, stroke, and text insertion.
category: cave-painter
trigger: When the user asks to add speech bubbles, text balloons, dialogue bubbles, or thought bubbles to a Cave Painter image.
---

## Overview

A speech bubble combines:
1. A **rounded/elliptical body** (main text area)
2. A **triangular tail/pointer** (points at the speaker)
3. **White fill** with a **dark outline/stroke**
4. **Text** inside the body

Two approaches are documented below. Use the **MCP tool approach** when working with a live Cave Painter daemon session. Use the **GIMP Python-Fu script** when you need precise control (custom tail geometry, precise path stroking, etc.).

---

## Approach 1: Cave Painter MCP Tools (Simple Oval + Inset Tail)

The MCP tools don't expose `select_polygon()` (free select) or `edit_stroke_path()` directly, so we compose the bubble from available primitives.

### Steps

**Step 1 — Create canvas and reference layer**

```
create_canvas(width=800, height=600, bg_r=0.05, bg_g=0.1, bg_b=0.2)
  → img_abc123
```

**Step 2 — Draw the oval body**

Use `draw_ellipse()` as the bubble body. This draws a filled ellipse on the background layer. The `fill_r/g/b` controls the fill color — use white (1.0, 1.0, 1.0) or near-white.

```
draw_ellipse(img_abc123, cx=350, cy=280, rx=240, ry=140, fill_r=1.0, fill_g=1.0, fill_b=1.0)
```

**Step 3 — Create a new layer for the tail**

```
new_layer(img_abc123, name="Tail")
```

**Step 4 — Draw tail triangle**

Use two rectangles or one ellipse to approximate the tail. For example, a small rotated-looking tail at the bottom-left:

```
draw_rect(img_abc123, x=120, y=380, w=80, h=60, fill_r=1.0, fill_g=1.0, fill_b=1.0)
```

You can also use small overlapping ellipses for a rounded tail.

**Step 5 — Add text inside the bubble**

```
add_text(img_abc123, "Hello!", x=200, y=250, size=36, r=0.0, g=0.0, b=0.0)
```

**Step 6 — Export**

```
export(img_abc123, "speech-bubble.png")
  → or export_done(img_abc123, "speech-bubble.png")
```

### Limitations of MCP Approach

- No border/outline on the bubble (no `edit_stroke_item` access through MCP)
- Tail positioning limited to overlapping rects/ellipses rather than a clean triangle
- For fully polished bubbles with black stroke borders, use Approach 2

---

## Approach 2: Direct GIMP Python-Fu Script (Full Feature)

For proper speech bubbles with:
- Ellipse body selection
- Polygon tail selection (free select / polygonal lasso)
- White fill + black stroke border
- Selection → path → stroke path

Use a GIMP Python-Fu batch script. The script below creates a complete speech bubble.

### Script: `speech-bubble.py`

```python
#!/usr/bin/env python3
"""Create a comic speech bubble with proper selection, path, and stroke."""

W, H = 800, 600

# Bubble oval center + size
cx, cy = 350, 280
rx, ry = 240, 140

# Tail triangle points (bottom-left of bubble)
tail = [
    (120, 380),   # left point
    (200, 420),   # tip (points at speaker)
    (200, 350),   # right point on bubble edge
]

def create_speech_bubble(img, layer):
    """Create a speech bubble on the given image and layer."""

    # --- Step 1: Ellipse selection for body ---
    Gimp.Image.select_ellipse(
        img, Gimp.ChannelOps.REPLACE,
        float(cx - rx), float(cy - ry),  # x, y
        float(rx * 2), float(ry * 2)      # w, h
    )

    # --- Step 2: Add tail via polygon (free select in ADD mode) ---
    # Flatten the tail points into [x1, y1, x2, y2, x3, y3, ...]
    tail_pts = []
    for tx, ty in tail:
        tail_pts.append(float(tx))
        tail_pts.append(float(ty))

    Gimp.Image.select_polygon(
        img, Gimp.ChannelOps.ADD,
        len(tail), tail_pts
    )

    # --- Step 3: Fill selection with white ---
    white = Gimp.color_parse_css("white")
    Gimp.context_push()
    try:
        Gimp.context_set_foreground(white)
        Gimp.Drawable.edit_fill(layer, Gimp.FillType.FOREGROUND)
    finally:
        Gimp.context_pop()

    # --- Step 4: Convert selection to path ---
    # Use PDB for reliable selection-to-path conversion
    pdb = Gimp.get_pdb()
    sel_to_path = pdb.lookup_procedure("gimp-selection-to-path")
    if sel_to_path:
        cfg = sel_to_path.create_config()
        sel_to_path.run(cfg)

    # --- Step 5: Stroke the path ---
    # Get the path(s) from the image
    paths = img.get_paths()
    if paths:
        path_obj = paths[0]
        # Set foreground to black for stroke
        black = Gimp.color_parse_css("black")
        Gimp.context_set_foreground(black)
        Gimp.context_set_stroke_method(0)  # 0 = stroke line
        Gimp.context_set_line_width(4.0)
        # Still the drawable (layer) and stroke it
        Gimp.Drawable.edit_stroke_item(layer, path_obj)

    # --- Step 6: Clear selection ---
    Gimp.Image.select_rectangle(
        img, Gimp.ChannelOps.REPLACE,
        0.0, 0.0, 0.0, 0.0
    )
    Gimp.displays_flush()


if __name__ == "__main__":
    # Create a fresh image
    img = Gimp.Image.new(W, H, Gimp.ImageType.RGB_IMAGE)
    layer = Gimp.Layer.new(
        img, "Background", W, H,
        Gimp.ImageType.RGBA_IMAGE,
        100.0, Gimp.LayerMode.NORMAL
    )
    img.insert_layer(layer, None, 0)

    # Fill background with a color (optional)
    bg_color = Gimp.color_parse_css("rgb(12,25,51)")
    Gimp.context_set_background(bg_color)
    layer.fill(Gimp.FillType.BACKGROUND)

    # Create a separate bubble layer
    bubble_layer = Gimp.Layer.new(
        img, "Bubble", W, H,
        Gimp.ImageType.RGBA_IMAGE,
        100.0, Gimp.LayerMode.NORMAL
    )
    img.insert_layer(bubble_layer, None, -1)
    # Initialize bubble layer alpha
    bubble_layer.fill(Gimp.FillType.TRANSPARENT)

    create_speech_bubble(img, bubble_layer)

    # Save
    gfile = Gio.File.new_for_path("/tmp/speech-bubble.png")
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, gfile, None)
    Gimp.Image.delete(img)
```

### Running the Script

```bash
GIMP_HOME=~/.config/GIMP/3.0 \
HOME=/home/ekl \
gimp --no-interface --batch-interpreter python-fu-eval \
     -b "exec(open('/path/to/speech-bubble.py').read())" \
     --quit
```

---

## API Reference

### Selection Operations (GIMP 3.x)

| Operation | Call | ChannelOps |
|---|---|---|
| Ellipse select | `Gimp.Image.select_ellipse(img, op, x, y, w, h)` | `REPLACE`, `ADD`, `SUBTRACT`, `INTERSECT` |
| Polygon (free) select | `Gimp.Image.select_polygon(img, op, num_pts, [x1,y1,...])` | `ADD` extends current selection |
| Rectangle select | `Gimp.Image.select_rectangle(img, op, x, y, w, h)` | — |
| Clear selection | `Gimp.Image.select_rectangle(img, REPLACE, 0, 0, 0, 0)` | — |
| Invert selection | `Gimp.Selection.invert(img)` | — |
| Feather selection | `Gimp.Selection.feather(img, float_radius)` | — |

### Path Operations

| Step | Call | Notes |
|---|---|---|
| Selection → Path | PDB `gimp-selection-to-path` | Use PDB procedure, not direct API |
| Get image paths | `img.get_paths()` | Returns list of `Gimp.Path` objects |
| Create new path | `Gimp.Path.new(img, name)` | Returns path object |
| Insert path into image | `img.insert_path(path, None, 0)` | **⚠️ REQUIRED** before stroking or path is invisible |
| Stroke path | `Gimp.Drawable.edit_stroke_item(layer, path_obj)` | Uses current context brush/line settings |
| Bezier start | `path.bezier_stroke_new_moveto(x, y)` → stroke_id | — |
| Bezier line | `path.bezier_stroke_lineto(stroke_id, x0, y0)` | — |
| Bezier close | `path.stroke_close(stroke_id)` | — |

### Fill Operations

| Operation | Call | Selection-aware? |
|---|---|---|
| Fill selection | `edit_fill(FOREGROUND/BACKGROUND/WHITE/TRANSPARENT)` | ✅ Yes — sets alpha=255 |
| Fill entire layer | `fill(FOREGROUND/BACKGROUND/WHITE/TRANSPARENT)` | ❌ No — ignores selection; alpha=0 on new layers |
| Flood fill | `edit_bucket_fill(mode, x, y)` | Flood from point |

### Stroke Context (for `edit_stroke_item`)

```python
Gimp.context_set_foreground(color)     # Stroke color
Gimp.context_set_line_width(float)      # Line thickness in pixels
Gimp.context_set_line_cap_style(0)      # 0=butt, 1=round, 2=square
Gimp.context_set_line_join_style(0)     # 0=miter, 1=round, 2=bevel
Gimp.context_set_line_miter_limit(5.0)  # Miter limit
Gimp.context_set_stroke_method(0)       # 0=stroke line, 1=paint with brush
```

### Color Setup

```python
# Create colors
white = Gimp.color_parse_css("white")
black = Gimp.color_parse_css("black")
red   = Gimp.color_parse_css("rgb(204,51,51)")

# Or from 0-1 floats
color_obj = Gegl.Color.new("rgb(0.8, 0.2, 0.2)")

# Set context
Gimp.context_set_foreground(color_obj)
Gimp.context_set_background(color_obj)
```

---

## Common Tail Geometries

### Triangular Tail (Bottom-Left)
```python
tail = [(120, 380), (80, 480), (220, 420)]
#           left          tip        right
```

### Triangular Tail (Bottom-Center)
```python
tail = [(300, 400), (350, 510), (400, 400)]
```

### Triangular Tail (Left-Side, Mid)
```python
tail = [(100, 220), (30, 280), (100, 300)]
```

---

## Pitfalls

### 💀 `fill()` Ignores Selection
`layer.fill(FillType.FOREGROUND)` fills the **entire layer**, ignoring any active selection. Use `edit_fill()` for selection-based fills or you'll get a solid rectangle instead of a bubble shape. See the `gimp-fill-operations` skill.

### 💀 Layer Opacity = 0-100 Scale
`Gimp.Layer.new(img, "B", W, H, RGBA_IMAGE, 1.0, NORMAL)` = **1% opacity** (invisible!). Always use `100.0` for full opacity.

### 💀 `insert_path()` Required Before `edit_stroke_item()`
```python
# ⚠️ This silently does nothing:
path_obj = Gimp.Path.new(img, "bubble")
# ... add strokes ...
layer.edit_stroke_item(path_obj)  # Path not in image! Silent no-op.

# ✅ This works:
path_obj = Gimp.Path.new(img, "bubble")
img.insert_path(path_obj, None, 0)  # REQUIRED
layer.edit_stroke_item(path_obj)
```

### 💀 PDB `gimp-selection-to-path` vs Direct API
The direct API method for selection→path conversion may not exist in GIMP 3.x. Always prefer the PDB procedure route:
```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-selection-to-path")
if proc:
    cfg = proc.create_config()
    proc.run(cfg)
```
See the `gimp-pdb-procedures` skill.

### 💀 Context State Leaks
Always wrap fill/stroke operations in `context_push()/context_pop()` to avoid leaking color or brush changes to subsequent operations:
```python
Gimp.context_push()
try:
    Gimp.context_set_foreground(white)
    layer.edit_fill(Gimp.FillType.FOREGROUND)
finally:
    Gimp.context_pop()
Gimp.displays_flush()
```

### 💀 `Gimp.displays_flush()` After Every Mod
Always call `Gimp.displays_flush()` after any operation that modifies the image to commit pending changes.

---

## Related Skills

| Skill | Why |
|---|---|
| `gimp-fill-operations` | `edit_fill()` vs `fill()` behavior — critical for bubble fills |
| `gimp-mcp-patterns` | `context_push/pop`, `displays_flush`, class-method syntax |
| `gimp-pdb-procedures` | PDB `gimp-selection-to-path` for selection→path conversion |
| `gimp-context-management` | Proper context save/restore around operations |
| `gopher-draw` | Main Cave Painter workflow (MCP tools, daemon lifecycle) |
