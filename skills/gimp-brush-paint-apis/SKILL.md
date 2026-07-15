---
name: gimp-brush-paint-apis
description: GIMP 3.x paint APIs — paintbrush_default, pencil, and paintbrush for brush strokes without manual path creation
category: cave-painter
trigger: When drawing brush strokes, lines, or curves in Cave Painter — simpler alternatives to edit_stroke_item + path creation
---

## GIMP 3.x Paint APIs

These allow painting directly without creating Path objects manually.

### `Gimp.paintbrush_default(drawable, coords)`

Paints a smooth curve using the current brush + foreground color. Coordinates are `[x1, y1, x2, y2, x3, y3, ...]`.

```python
# Paint a bezier-like curve with current brush and foreground color
Gimp.context_set_foreground(gegl_color)
Gimp.context_set_brush_size(5.0)
Gimp.paintbrush_default(drawable, [50.0, 50.0, 150.0, 200.0, 250.0, 50.0, 350.0, 200.0])
Gimp.displays_flush()
```

### `Gimp.pencil(drawable, coords)`

Draws straight line segments with the pencil tool. Same coordinate format:

```python
# Draw a diagonal line
Gimp.context_set_foreground(gegl_color)
Gimp.pencil(drawable, [0, 200, 200, 0])
Gimp.displays_flush()
```

### `Gimp.paintbrush(drawable, coords)`

Same as paintbrush_default but with more control (stroke options, dynamics, etc.)

### Full Pattern: Colored Brush Stroke

```python
from gi.repository import Gegl

Gimp.context_push()
try:
    green = Gegl.Color.new("green")
    Gimp.context_set_foreground(green)
    Gimp.context_set_brush_size(20.0)
    Gimp.paintbrush_default(drawable, [100, 50, 200, 150, 300, 50])
finally:
    Gimp.context_pop()
Gimp.displays_flush()
```

### When to use which

| API | Use case |
|---|---|
| `paintbrush_default()` | Smooth curves, brush stroke with current settings |
| `pencil()` | Hard-edged straight lines |
| `edit_stroke_item(path)` | When you need a specific Path object (vectors, complex shapes) |
| `edit_stroke_selection()` | Stroke along selection boundary |
