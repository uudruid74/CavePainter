---
name: gimp-fill-operations
description: Selection-aware and flat fill operations in GIMP 3.x — edit_fill, fill, edit_bucket_fill, and the alpha behavior of each
category: cave-painter
trigger: When filling a selection or layer in Cave Painter — choosing between edit_fill(), fill(), or edit_bucket_fill()
---

## GIMP 3.x Fill Operations

Three fill functions on `Gimp.Drawable`, each with different behavior:

### `drawable.edit_fill(fill_type)` — Selection-Aware (Recommended)

- **Respects selection** — only fills within the active selection
- Uses `Gimp.FillType` enum: `FOREGROUND`, `BACKGROUND`, `WHITE`, `TRANSPARENT`
- Sets RGB + Alpha correctly on Bg layers (alpha=255)
- Affected by: `context_set_foreground()`, `context_set_background()`, `context_set_opacity()`, `context_set_paint_mode()`
- **⚠️ On NEW RGBA layers**, may leave alpha at 0 — best used on existing Bg layer

```python
Gimp.Image.select_ellipse(img, Gimp.ChannelOps.REPLACE, 50, 50, 200, 150)
Gimp.context_set_foreground(color([0.8, 0.2, 0.2]))
img.get_layers()[0].edit_fill(Gimp.FillType.FOREGROUND)  # Fills selection only
```

### `drawable.fill(fill_type)` — Entire Layer (Ignores Selection)

- **Ignores selection** — fills entire drawable
- On NEW RGBA layers: sets RGB but **leaves alpha at 0** (invisible!)
- On existing layers with alpha=255: works correctly
- Best use: initial background fill on a newly created layer

```python
# Initialize a new layer:
bl = Gimp.Layer.new(img, "Bg", W, H, Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
bl.fill(Gimp.FillType.FOREGROUND)  # Fills entire layer — RGB set, alpha may be wrong on new layer
```

### `drawable.edit_bucket_fill(fill_type, x, y)` — Flood Fill

- **Flood fill** — fills contiguous area of similar color starting at (x, y)
- NOT selection-aware in the same way as edit_fill
- Takes `(fill_type, x, y)` coordinates
- Best use: filling bounded areas like a paint bucket tool

```python
drawable.edit_bucket_fill(Gimp.FillType.FOREGROUND, 100.0, 100.0)
```

### FillType Enum Values

| Value | Effect |
|---|---|
| `Gimp.FillType.FOREGROUND` | Uses current context foreground color |
| `Gimp.FillType.BACKGROUND` | Uses current context background color |
| `Gimp.FillType.WHITE` | White fill (ignores context) |
| `Gimp.FillType.TRANSPARENT` | Sets alpha to 0 (clears pixels, layers with alpha only) |

### Recommendations

| Scenario | Function |
|---|---|
| Fill selection on Bg layer | `edit_fill(FOREGROUND)` |
| Initialize new layer | `fill(FOREGROUND)` then draw on top |
| Flood fill bounded area | `edit_bucket_fill(FOREGROUND, x, y)` |
| New layer with selection | `edit_fill(FOREGROUND)` — sets RGB + alpha=255 correctly |
