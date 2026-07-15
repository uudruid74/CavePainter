---
name: gimp-context-management
description: Save/restore GIMP context state (foreground, brush, paint mode) using context_push/pop around operations
category: cave-painter
trigger: When setting foreground color, brush, or paint mode in Cave Painter daemon — especially when multiple operations with different colors follow each other
---

## GIMP 3.x Context Management

GIMP's "context" holds the current state: foreground/background color, brush, opacity, paint mode, gradient, font, etc. Operations like `edit_fill(FOREGROUND)`, `edit_stroke_item()`, and `edit_bucket_fill()` all read from this context.

### The Problem

`Gimp.context_set_foreground()` sometimes doesn't stick between operations in the same daemon session — the next operation may use the **previous** foreground color instead of the one just set. This was empirically observed in Cave Painter v14.

### Root Cause (Discovered by Neo, v16)

**`Gimp.context_set_brush()` snapshots the current foreground color** into the brush context. If you change the foreground AFTER setting the brush, the brush ignores it — it uses the snapshot.

#### The Fix: **Order of Operations**

Always call `_set_fg()` **BEFORE** `_apply_brush()`:

```python
# ✅ CORRECT ORDER
Gimp.context_set_foreground(color([0.2, 0.8, 0.2]))  # Set foreground FIRST
_apply_brush(br)                                       # Then set brush (snapshots current fg)

# ❌ WRONG ORDER (stale color)
_apply_brush(br)                                       # Brush snapshots old fg color
Gimp.context_set_foreground(color([0.2, 0.8, 0.2]))   # Too late — brush ignores it
```

This applies to BOTH `paint_stroke` and `paint_dab` operations.

### Additional Safety: `context_push()` / `context_pop()`

Wrap each operation that modifies the context in push/pop to ensure clean state—prevents color leakage between operations:

```python
Gimp.context_push()            # Save current context

Gimp.context_set_foreground(color(yellow))  # Set desired color
_apply_brush(br)                             # Brush snapshots correct color
# ... perform operation (fill, stroke, etc.) ...

Gimp.context_pop()             # Restore original context
```

### Full Pattern: Context-Safe Operation

```python
def with_foreground_color(img, rgb_color, fn):
    """Execute a function with a specific foreground color, restoring original afterward."""
    Gimp.context_push()
    Gimp.context_set_foreground(color(rgb_color))
    try:
        result = fn()
        return result
    finally:
        Gimp.context_pop()

# Usage:
def fill_ellipse():
    Gimp.Image.select_ellipse(img, Gimp.ChannelOps.REPLACE, x, y, w, h)
    img.get_layers()[0].edit_fill(Gimp.FillType.FOREGROUND)
    _deselect()

with_foreground_color(img, [0.8, 0.2, 0.2], fill_ellipse)
```

### Additional Context Functions

| Function | Purpose |
|---|---|
| `Gimp.context_push()` | Save entire context state to stack |
| `Gimp.context_pop()` | Restore most recently saved context |
| `Gimp.context_set_foreground(color)` | Set foreground (Gegl.Color) |
| `Gimp.context_set_background(color)` | Set background (Gegl.Color) |
| `Gimp.context_set_default_colors()` | Reset FG to black, BG to white |
| `Gimp.context_set_opacity(100.0)` | Set paint opacity (0-100 scale!) |
| `Gimp.context_set_paint_mode(mode)` | Set blend mode |
| `Gimp.context_get_foreground()` | Read current foreground (returns Gegl.Color) |

### Debugging Tip

To verify the foreground color is actually being set, read it back immediately:

```python
Gimp.context_set_foreground(color([0.8, 0.8, 0.0]))
check = Gimp.context_get_foreground()
# Compare check to expected — if different, context isn't persisting
```

### Context-Sensitive Functions

These functions read the current context and may not behave as expected if the context is stale:

- `drawable.edit_fill(Gimp.FillType.FOREGROUND)` — uses context foreground
- `drawable.edit_bucket_fill(Gimp.BucketFillMode.FG, ...)` — uses context foreground
- `drawable.edit_stroke_item(path)` — uses context brush + foreground
- `drawable.fill(Gimp.FillType.FOREGROUND)` — uses context foreground (entire layer, ignores selection)
