---
name: gimp-basic-color-curves
description: Build cave-painter/gimp-basic-color-curves skill from GIMP Basic Color Curves tutorial
category: cave-painter
trigger: When building color adjustment tools in Cave Painter — selecting, applying, and validating curve operations
---

## Overview
This skill documents how to use GIMP's Color Curves tool to adjust tonal range, set control points, and manipulate individual color channels. It covers:

- Using `Gimp.Drawable.curves_spline()` to define custom curves with control points
- Setting black, white, and gray points with the eyedropper
- Adjusting RGB channels independently or together
- Auto‑adjustment options via `gimp-drawable-levels-stretch` PDB procedure
- Proper context management to avoid color state leakage

## API Reference

| Method | Signature | Verified |
|--------|-----------|----------|
| `Gimp.Drawable.curves_spline` | `curves_spline(drawable, channel, control_points)` | Yes |
| `Gimp.displays_flush` | `displays_flush()` | Yes |
| `Gimp.context_push` | `context_push()` | Yes |
| `Gimp.context_pop` | `context_pop()` | Yes |
| `Gimp.context_set_foreground` | `context_set_foreground(color)` | Yes |
| `Gimp.Drawable.edit_fill` | `edit_fill(drawable, fill_type)` | Yes (class‑method) |
| `Gimp.get_pdb().lookup_procedure` | `lookup_procedure(name)` | Yes (fallback) |

## Working Example

```python
from gi.repository import Gimp, Gegl

def apply_color_curves(image):
    # Get the active layer (drawable)
    layer = image.get_active_layer()
    
    # Define an S‑curve for adjusting tonal range
    # (0,0) = black point, (255,255) = white point
    # Midpoints adjusted to darken shadows and lighten highlights
    control_points = [
        (0, 0),       # black point (no change)
        (64, 40),     # darken midtones (shadows)
        (128, 128),   # midtones unchanged
        (192, 200),   # lighten highlights (highlights)
        (255, 255)    # white point (no change)
    ]
    
    # Apply the curve to the RGB channel
    # Channel names: "RGB", "red", "green", "blue"
    Gimp.Drawable.curves_spline(layer, "RGB", control_points)
    
    # Force GIMP to update the display immediately
    Gimp.displays_flush()

# Example usage:
# Assuming you have an image loaded and a layer selected:
# apply_color_curves(image)
```

## Common Pitfalls

- **Forgetting `Gimp.displays_flush()`**: Without flushing, changes may not appear immediately in the UI.
- **Incorrect channel name**: Use "RGB" (uppercase) for the composite channel, or "red", "green", "blue" for individual channels.
- **Color state leakage**: If you set a new foreground color and then perform an operation without `context_push()`/`context_pop()`, the next operation may use the old color.
- **Invalid control points**: Ensure `control_points` is a list of `(x, y)` tuples with valid values (0‑255 for 8‑bit images).
- **Using wrong method syntax**: `Gimp.Drawable.curves_spline` is a class method — the first argument must be the drawable instance.
