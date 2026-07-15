---
name: gimp-layer-masks
description: Layer masks in GIMP 3.x API — add, remove, edit masks for selective transparency, based on the official GIMP tutorial
category: cave-painter
trigger: When creating selective transparency, luminosity masking, or non-destructive opacity control
---

## GIMP 3.x Layer Masks API

Layer masks allow non-destructive opacity control — they modify layer transparency without altering the layer's pixels.

### API Methods

| Task | API |
|---|---|
| Create a mask | `Gimp.LayerMask.new(layer, mask_type)` |
| Add mask to layer | `layer.add_mask(mask, True)` |
| Remove mask | `layer.remove_mask(Gimp.MaskApplyMode.APPLY)` |
| Discard mask | `layer.remove_mask(Gimp.MaskApplyMode.DISCARD)` |

### Mask Types (`Gimp.AddMaskType`)

| Value | Effect |
|---|---|
| `Gimp.AddMaskType.WHITE` | Fully opaque (default) |
| `Gimp.AddMaskType.BLACK` | Fully transparent |
| `Gimp.AddMaskType.ALPHA` | From layer's alpha channel |
| `Gimp.AddMaskType.SELECTION` | From active selection |
| `Gimp.AddMaskType.GRAY_CHANNEL` | From grayscale copy |
| `Gimp.AddMaskType.TRANSPARENCY` | Inverted alpha |

### Full Example: Selective Opacity via Mask

```python
from gi.repository import Gegl

# Get drawable
image = Gimp.get_images()[0]
drawable = image.get_selected_layers()[0]

# Add white (fully opaque) mask
mask = Gimp.LayerMask.new(drawable, Gimp.AddMaskType.WHITE)
drawable.add_mask(mask, True)

# Activate mask for editing
Gimp.Image.set_active_layer(image, drawable)

# Paint black on mask to create transparency
black = Gegl.Color.new('black')
Gimp.context_set_foreground(black)
Gimp.Image.select_rectangle(image, Gimp.ChannelOps.REPLACE, 50, 50, 200, 150)
Gimp.Drawable.edit_fill(mask, Gimp.FillType.FOREGROUND)
Gimp.Selection.none(image)

Gimp.displays_flush()
```

### Selective Colorization Pattern

Duplicate → Desaturate → Add mask → Paint on mask:

```python
# 1. Duplicate layer
dup = drawable.copy()
image.insert_layer(dup, None, 0)

# 2. Desaturate the duplicate
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-drawable-desaturate")
if proc:
    cfg = proc.create_config()
    cfg.set_property("drawable", dup)
    cfg.set_property("desaturate-mode", Gimp.DesaturateMode.LUMINANCE)
    proc.run(cfg)

# 3. Add white mask to the desaturated layer
mask = Gimp.LayerMask.new(dup, Gimp.AddMaskType.WHITE)
dup.add_mask(mask, True)

# 4. Paint black on mask to reveal color below
Gimp.context_set_foreground(Gegl.Color.new('black'))
# ... paint on mask to reveal color from layer below
```

### Visual Guide

```
Layer stack:                 Mask state:
[Desaturated layer]          [White = full opacity]
  └─ [Layer Mask]            [Black = transparent (shows below)]
[Original color layer]
```

### Mask Editing Notes

- When a mask is active, painting operations affect the mask, not the layer
- White on mask = opaque (visible), Black = transparent (hidden)
- Gray values give partial transparency
- Use `drawable.get_mask()` to retrieve the mask from a layer
