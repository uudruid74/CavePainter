---
name: gimp-rounded-corners-red-eye
description: Two simple GIMP 3.x image utilities — (1) rounded corners using select_round_rectangle + invert + clear, (2) red eye removal using ellipse select + gimp-red-eye-removal PDB procedure
category: cave-painter
trigger: When asked to add rounded corners to an image or remove red eye from photos using GIMP Python-Fu
---

## Overview

Two self-contained GIMP 3.x Python-Fu utility functions:

1. **`add_rounded_corners()`** — Makes image corners rounded by selecting a round rectangle, inverting the selection, and clearing to transparency
2. **`remove_red_eye()`** — Removes red-eye effect from eyes using ellipse selection and the PDB `gimp-red-eye-removal` procedure

Both work on existing images and layers — open an image, apply the utility, and save.

---

## Utility 1: Rounded Corners

### How It Works

1. Select a **rounded rectangle** matching the image bounds with a given corner radius
2. **Invert** the selection so the corner areas (outside the round rect) are selected
3. **Clear** the selection — this deletes those corner pixels to transparency
4. **Remove** the selection

### API

```python
Gimp.Image.select_round_rectangle(
    image,
    Gimp.ChannelOps.REPLACE,   # Operation: REPLACE, ADD, SUBTRACT, INTERSECT
    x,                         # Starting x (float)
    y,                         # Starting y (float)
    width,                     # Selection width (float)
    height,                    # Selection height (float)
    radius,                    # Corner radius in pixels (float)
    1.0                        # Antialias (1.0 = on)
)
```

### Function

```python
from gi.repository import Gimp, Gio


def add_rounded_corners(image, drawable, radius=30.0):
    """Apply rounded corners to an image layer.

    Deletes the corner areas outside the round rectangle to transparency.
    The drawable must have an alpha channel (RGBA) for this to work.

    Args:
        image: Gimp.Image
        drawable: Gimp.Drawable (must be RGBA with alpha channel)
        radius: Corner radius in pixels (default 30)
    """
    width = image.get_width()
    height = image.get_height()

    # Step 1: Select rounded rectangle covering the whole image
    Gimp.Image.select_round_rectangle(
        image,
        Gimp.ChannelOps.REPLACE,
        0.0, 0.0,                # x, y
        float(width), float(height),  # w, h
        float(radius),            # corner radius
        1.0                       # antialias
    )

    # Step 2: Invert selection (selects corner areas outside the round rect)
    Gimp.Selection.invert(image)

    # Step 3: Clear the selected corner areas to transparency
    Gimp.Drawable.edit_clear(drawable)

    # Step 4: Remove selection
    Gimp.Selection.none(image)

    Gimp.displays_flush()
```

### Usage Example

```python
from gi.repository import Gimp, Gio, Gegl

# Open an image
gfile = Gio.File.new_for_path("/path/to/input.png")
image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, gfile, gfile)

# Get the active layer
layer = image.get_active_layer()

# Add alpha channel if needed (required for transparency)
if not layer.has_alpha():
    Gimp.Layer.add_alpha(layer)

# Apply rounded corners (radius 40px)
add_rounded_corners(image, layer, radius=40.0)

# Export as PNG (preserves transparency)
outfile = Gio.File.new_for_path("/path/to/output.png")
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, layer, outfile, None)

Gimp.Image.delete(image)
```

---

## Utility 2: Red Eye Removal

### How It Works

1. Select an **ellipse** around the eye
2. **Feather** the selection for a smooth transition (optional but recommended)
3. Run the PDB **`gimp-red-eye-removal`** procedure with a configurable threshold
4. **Remove** the selection and repeat for the other eye

### PDB Procedure: `gimp-red-eye-removal`

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-red-eye-removal")
config = proc.create_config()
config.set_property("image", image)
config.set_property("drawable", drawable)
config.set_property("threshold", 0.5)   # Sensitivity (0.0 = aggressive, 1.0 = conservative)
proc.run(config)
```

**Threshold parameter:**
- `0.0` — Very aggressive, removes all red tones (may desaturate other reds in the image)
- `0.5` — Default / balanced (recommended starting point)
- `0.8` — Very conservative, only removes intense red eye
- `1.0` — Barely any effect

### Function

```python
from gi.repository import Gimp, Gio


def remove_red_eye(image, drawable, eye_centers, threshold=0.5, eye_radius=20.0):
    """Remove red-eye effect from one or both eyes.

    Args:
        image: Gimp.Image
        drawable: Gimp.Drawable (usually the background layer)
        eye_centers: List of (cx, cy) tuples — center of each eye
        threshold: Red-eye removal sensitivity (0.0-1.0, default 0.5)
        eye_radius: Radius of the eye selection ellipse in pixels (default 20)
    """
    pdb = Gimp.get_pdb()
    proc = pdb.lookup_procedure("gimp-red-eye-removal")
    if not proc:
        raise RuntimeError("gimp-red-eye-removal PDB procedure not found")

    for cx, cy in eye_centers:
        # Step 1: Select ellipse around the eye
        Gimp.Image.select_ellipse(
            image,
            Gimp.ChannelOps.REPLACE,
            float(cx - eye_radius),         # x
            float(cy - eye_radius),         # y
            float(eye_radius * 2),          # width
            float(eye_radius * 2)           # height
        )

        # Step 2: Feather selection for smooth edge (optional)
        Gimp.Selection.feather(image, float(eye_radius * 0.2))

        # Step 3: Run red-eye removal on the selection
        config = proc.create_config()
        config.set_property("image", image)
        config.set_property("drawable", drawable)
        config.set_property("threshold", float(threshold))
        proc.run(config)

    # Step 4: Clear selection
    Gimp.Selection.none(image)
    Gimp.displays_flush()
```

### Usage Example

```python
from gi.repository import Gimp, Gio

# Open a photo
gfile = Gio.File.new_for_path("/path/to/portrait.jpg")
image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, gfile, gfile)
layer = image.get_active_layer()

# Fix both eyes — find coordinates manually or from a face detection step
# (cx, cy) pairs for left and right eye centers
eyes = [(320, 240), (420, 240)]  # Example coordinates

remove_red_eye(image, layer, eye_centers=eyes, threshold=0.5, eye_radius=22.0)

# Save result
outfile = Gio.File.new_for_path("/path/to/fixed-portrait.jpg")
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, layer, outfile, None)

Gimp.Image.delete(image)
```

---

## Combined Script: Both Utilities

```python
#!/usr/bin/env python3
"""Rounded corners + red eye removal utilities for GIMP 3.x."""
from gi.repository import Gimp, Gio


def add_rounded_corners(image, drawable, radius=30.0):
    """Apply rounded corners — deletes corner areas to transparency."""
    w, h = float(image.get_width()), float(image.get_height())

    Gimp.Image.select_round_rectangle(
        image, Gimp.ChannelOps.REPLACE,
        0.0, 0.0, w, h, float(radius), 1.0
    )
    Gimp.Selection.invert(image)
    Gimp.Drawable.edit_clear(drawable)
    Gimp.Selection.none(image)
    Gimp.displays_flush()


def remove_red_eye(image, drawable, eye_centers, threshold=0.5, eye_radius=20.0):
    """Remove red-eye from specified eye center coordinates."""
    pdb = Gimp.get_pdb()
    proc = pdb.lookup_procedure("gimp-red-eye-removal")
    if not proc:
        raise RuntimeError("gimp-red-eye-removal not found")

    for cx, cy in eye_centers:
        Gimp.Image.select_ellipse(
            image, Gimp.ChannelOps.REPLACE,
            float(cx - eye_radius), float(cy - eye_radius),
            float(eye_radius * 2), float(eye_radius * 2)
        )
        Gimp.Selection.feather(image, float(eye_radius * 0.2))

        config = proc.create_config()
        config.set_property("image", image)
        config.set_property("drawable", drawable)
        config.set_property("threshold", float(threshold))
        proc.run(config)

    Gimp.Selection.none(image)
    Gimp.displays_flush()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: gimp --no-interface --batch-interpreter python-fu-eval")
        print("       -b \"exec(open('gimp-rounded-corners-red-eye.py').read())\"")
        print("       --quit")
        sys.exit(1)

    # Example: apply rounded corners to input.png
    input_path = sys.argv[1]
    output_path = sys.argv[2]

    infile = Gio.File.new_for_path(input_path)
    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, infile, infile)
    layer = image.get_active_layer()

    if not layer.has_alpha():
        Gimp.Layer.add_alpha(layer)

    add_rounded_corners(image, layer, radius=30.0)

    outfile = Gio.File.new_for_path(output_path)
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, layer, outfile, None)
    Gimp.Image.delete(image)
```

### Running the Script

```bash
GIMP_HOME=~/.config/GIMP/3.0 \
HOME=/home/ekl \
gimp --no-interface --batch-interpreter python-fu-eval \
     -b "exec(open('/path/to/gimp-rounded-corners-red-eye.py').read())" \
     --quit
```

---

## API Reference

### Selection Operations

| Operation | Call | Notes |
|---|---|---|
| Round rectangle | `Gimp.Image.select_round_rectangle(img, op, x, y, w, h, radius, antialias)` | `radius` = corner radius in px, `antialias` = 1.0 or 0.0 |
| Ellipse | `Gimp.Image.select_ellipse(img, op, x, y, w, h)` | Standard ellipse selection |
| Invert | `Gimp.Selection.invert(img)` | Reverses active selection |
| Remove | `Gimp.Selection.none(img)` | Clears all selection |
| Feather | `Gimp.Selection.feather(img, radius)` | Softens selection edge (float) |

### ChannelOps Enum

| Value | Effect |
|---|---|
| `Gimp.ChannelOps.REPLACE` | Replace current selection |
| `Gimp.ChannelOps.ADD` | Add to current selection |
| `Gimp.ChannelOps.SUBTRACT` | Subtract from current selection |
| `Gimp.ChannelOps.INTERSECT` | Intersect with current selection |

### Fill / Clear Operations

| Operation | Call | Behavior |
|---|---|---|
| Clear selection | `Gimp.Drawable.edit_clear(drawable)` | Deletes selection contents to transparency (alpha=0). Requires alpha channel. |
| Fill selection | `Gimp.Drawable.edit_fill(drawable, fill_type)` | Fills within selection boundaries |

---

## Pitfalls

### 💀 `select_round_rectangle` radius units
The radius is in **pixels** (float). If the radius exceeds half the image width or height, the corners will be excessively rounded or the selection may behave unexpectedly. Sanity-check: `radius <= min(width, height) / 2`.

### 💀 `edit_clear()` requires alpha channel
`Gimp.Drawable.edit_clear()` on a layer without an alpha channel fills the selection with the background color instead of making it transparent. **Always call `Gimp.Layer.add_alpha(layer)`** before applying rounded corners on a non-RGBA layer:
```python
if not layer.has_alpha():
    Gimp.Layer.add_alpha(layer)
```

### 💀 Red-eye threshold tuning
If the removal is too weak (eyes still red), **lower** the threshold. If it desaturates too much of the surrounding skin or iris, **raise** the threshold. Start at 0.5 and adjust ±0.15:
- `0.35` — Strong removal, may affect non-red areas
- `0.50` — Balanced default
- `0.65` — Gentle, only intense reds

### 💀 `gimp-red-eye-removal` procedure may not exist
Some GIMP installations (e.g., minimal headless builds) may not bundle the red-eye removal plug-in. Check availability:
```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-red-eye-removal")
if not proc:
    raise RuntimeError("gimp-red-eye-removal unavailable — install gimp-plugin-registry or gimp-help")
```

### 💀 `Gimp.displays_flush()` after operations
Always call `Gimp.displays_flush()` after any selection/modification to commit pending changes. See the `gimp-mcp-patterns` skill.

### 💀 Eye center coordinates
The user must provide eye center coordinates. For automated detection, integrate with a face detection library (e.g., OpenCV) before calling the GIMP script. This skill does not include face detection.

### 💀 Export format for rounded corners
Always export to **PNG** (or another format that supports transparency) after applying rounded corners. JPEG does not support alpha channels and will fill the transparent corners with black/white:
```python
# ✅ Correct — preserves transparency
gfile = Gio.File.new_for_path("output.png")
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, layer, gfile, None)

# ❌ Wrong — JPEG destroys transparency
gfile = Gio.File.new_for_path("output.jpg")  # Transparent areas become solid!
```

---

## Related Skills

| Skill | Why |
|---|---|
| `gimp-mcp-patterns` | `displays_flush`, `context_push/pop`, class-method calling convention |
| `gimp-fill-operations` | `edit_fill()` vs `fill()` behavior — critical for understanding edit_clear() |
| `gimp-speech-bubble` | Selection operations (`select_ellipse`, `select_polygon`), selection→path conversion |
| `gimp-pdb-procedures` | PDB procedure lookup and execution pattern |
