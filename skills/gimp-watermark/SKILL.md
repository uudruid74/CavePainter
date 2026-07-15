---
name: gimp-watermark
description: 'Create text watermarks in GIMP 3.x — text layer creation, opacity adjustment, rotation, layer merging, and JPEG export with quality settings'
category: cave-painter
trigger: When adding semi-transparent text watermarks to images in Cave Painter — covers the full watermark pipeline from text creation to JPEG export
---

## Watermark Pipeline Overview

The watermark workflow in GIMP 3.x consists of 5 steps:

1. **Create text layer** — add watermark text as a dedicated layer
2. **Set opacity** — reduce to 25–40% for subtle watermark appearance
3. **Rotate layer** — tilt the watermark (e.g. 30–45 degrees) for diagonal placement
4. **Merge layers** — flatten the watermark onto the background
5. **Export as JPEG** — save with configurable quality for filesize control

## 1. Text Layer Creation

### Via PDB `gimp-text-fontname` (most reliable)

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-text-fontname")
if proc:
    cfg = proc.create_config()
    # (image, drawable, x, y, text, border, antialias, size, unit, font)
    cfg.set_property("image", image)
    cfg.set_property("drawable", layer)          # None or -1 for floating selection / new layer
    cfg.set_property("x", 60.0)
    cfg.set_property("y", 160.0)
    cfg.set_property("text", "WATERMARK")
    cfg.set_property("border", 0)                # -1 = auto, 0 = no border
    cfg.set_property("antialias", True)
    cfg.set_property("size", 48.0)
    cfg.set_property("unit", Gimp.Unit.PIXEL)    # or use the integer value
    cfg.set_property("font", "Sans Bold")        # font name string
    result = proc.run(cfg)
    text_layer = result.get_value()              # Returns the new layer
```

### Via `Gimp.text_font()` (GIMP 3.x direct API)

```python
default_font = Gimp.context_get_font()  # Get default font object
tl = Gimp.text_font(
    image,                               # image
    layer,                               # drawable (None for floating)
    float(x), float(y),                  # position
    "WATERMARK",                         # text
    -1,                                  # border (-1 = auto)
    True,                                # antialias
    float(size),                         # font size in pixels
    default_font                         # Gimp.Font object (not string!)
)
```

### Via `Gimp.text_fontname()` (legacy/GIMP 2.x style, still works via PDB)

The transcript-style call uses positional args matching GIMP 2.x PDB convention:

```python
tl = Gimp.text_fontname(
    image,              # Gimp.Image
    None,               # drawable (None = new floating text layer)
    60,                 # x position
    160,                # y position
    "WATERMARK",        # text content
    0,                  # border (-1 or 0 = no border)
    True,               # antialias
    48,                 # font size
    Gimp.Unit.PIXEL,    # unit (Gimp.Pixels in GIMP 2.x → Gimp.Unit.PIXEL in 3.x)
    "Sans Bold"         # font name string
)
```

**⚠️ Note:** In GIMP 3.x, `Gimp.text_fontname()` may not exist as a direct class method. Use the PDB procedure `gimp-text-fontname` for the most reliable string-based font name approach.

### Text Layer Properties

After creation, the text layer is a floating layer or a new layer in the image. Access its properties:

```python
# Text layer is returned as the drawable
text_layer = result.get_value()  # from PDB procedure
# or
text_layer = tl  # from direct API call

# Get text layer bounds for centering calculations
x1, y1, x2, y2 = text_layer.get_bounding_box()
text_width = x2 - x1
text_height = y2 - y1
```

## 2. Set Layer Opacity

Watermarks use low opacity (typically 25–40%) so the underlying image remains visible through the text.

```python
# Opacity is 0–100 scale (NOT 0–1!)
text_layer.set_opacity(25.0)  # 25% opacity — subtle watermark
```

**Common opacity values for watermarks:**

| Opacity | Effect |
|---------|--------|
| 10–15% | Very subtle, nearly invisible |
| 20–30% | Typical watermark — visible but not distracting |
| 35–50% | Strong watermark — clearly readable |
| 60–80% | Heavy overlay, partially obscures image |

## 3. Rotate Layer

### Via PDB `gimp-item-transform-rotate`

```python
pdb = Gimp.get_pdb()
rot_proc = pdb.lookup_procedure("gimp-item-transform-rotate")
if rot_proc:
    rot_cfg = rot_proc.create_config()
    rot_cfg.set_property("item", text_layer)
    rot_cfg.set_property("angle", -0.523599)       # -30 degrees in radians
    rot_cfg.set_property("auto-center", True)       # rotate around layer center
    # Alternative: manual center point
    # rot_cfg.set_property("center-x", cx)
    # rot_cfg.set_property("center-y", cy)
    rot_proc.run(rot_cfg)
```

**Important:** The rotation angle is in **radians**, not degrees. Common values:

| Degrees | Radians |
|---------|---------|
| 15°     | 0.261799 |
| 30°     | 0.523599 |
| 45°     | 0.785398 |
| -30°    | -0.523599 |
| -45°    | -0.785398 |

Negative values rotate counter-clockwise (common for watermarks).

### Via `Gimp.Item.transform_rotate()` (Direct API)

```python
# Direct method on items (GIMP 3.x)
# transform_rotate(angle, auto_center, center_x, center_y, transform_direction, interpolation)
text_layer.transform_rotate(
    -0.523599,                               # angle in radians (-30°)
    True,                                    # auto_center
    0, 0,                                    # center_x, center_y (ignored if auto_center=True)
    Gimp.TransformDirection.FORWARD,         # transform direction
    Gimp.InterpolationType.LINEAR            # interpolation quality
)
```

**⚠️ Note:** `Gimp.Item.transform_rotate()` may not exist in all GIMP 3.x versions. The PDB route `gimp-item-transform-rotate` is the most reliable approach.

## 4. Merge Layers

Flatten the watermark text layer onto the background layer below it.

### Merge all visible layers

```python
# Merges all visible layers from bottom up, clipping to image bounds
merged = image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
```

### Merge specific layers only

If you need finer control (e.g., only merge the watermark with the layer directly below):

```python
# Merge the active layer down
floating = pdb.lookup_procedure("gimp-edit-anchor")  # Anchor floating selection
# or
# Use merge down for specific layer merging
merge_down = pdb.lookup_procedure("gimp-image-merge-down")
if merge_down:
    cfg = merge_down.create_config()
    cfg.set_property("image", image)
    cfg.set_property("merge_layer", text_layer)
    merge_down.run(cfg)
```

## 5. Export as JPEG

### Via `Gimp.file_save()` (Recommended for export)

```python
from gi.repository import Gio

# Determine output path
output_path = "/tmp/watermarked.jpg"
gfile = Gio.File.new_for_path(output_path)

# Save the image (flattened single-layer result from merge)
Gimp.file_save(
    Gimp.RunMode.NONINTERACTIVE,
    image,
    merged,              # The merged layer (or image's active layer)
    gfile,
    None                 # No save options (uses defaults)
)
```

### Via PDB `gimp-file-save` for JPEG with quality control

```python
pdb = Gimp.get_pdb()
save_proc = pdb.lookup_procedure("gimp-file-save")
if save_proc:
    save_cfg = save_proc.create_config()

    # Set the save target
    from gi.repository import Gio
    gfile = Gio.File.new_for_path(output_path)
    save_cfg.set_property("file", gfile)
    save_cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    save_cfg.set_property("image", image)
    save_cfg.set_property("drawable", merged)  # or the active drawable

    save_proc.run(save_cfg)
```

### Via PDB `gimp-file-save-jpeg` (Explicit JPEG quality)

For explicit JPEG quality control:

```python
save_jpeg = pdb.lookup_procedure("gimp-file-save-jpeg")
if save_jpeg:
    jpeg_cfg = save_jpeg.create_config()
    jpeg_cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    jpeg_cfg.set_property("image", image)
    jpeg_cfg.set_property("drawable", merged)

    from gi.repository import Gio
    jpeg_cfg.set_property("file", Gio.File.new_for_path("/tmp/watermarked.jpg"))

    # JPEG quality (0–100, default 75)
    jpeg_cfg.set_property("quality", 85)       # 85 = high quality
    jpeg_cfg.set_property("smoothing", 0.0)    # no smoothing
    jpeg_cfg.set_property("subsampling", 3)    # 0=4:4:4 high chroma, 1=4:2:2, 2=4:1:1, 3=4:2:0 small
    jpeg_cfg.set_property("optimize", True)    # optimize Huffman tables
    jpeg_cfg.set_property("progressive", False) # baseline vs progressive
    jpeg_cfg.set_property("comment", None)     # optional comment
    # jpeg_cfg.set_property("exif", True)      # preserve EXIF data
    # jpeg_cfg.set_property("iptc", True)      # preserve IPTC data
    # jpeg_cfg.set_property("xmp", True)       # preserve XMP data

    save_jpeg.run(jpeg_cfg)
```

### JPEG Quality Guidelines

| Quality | Filesize | Visual Quality | Use Case |
|---------|----------|----------------|----------|
| 60–70  | Small | Good | Web preview, low-bandwidth |
| 75–85  | Medium | Very good | Default, general purpose |
| 85–95  | Large | Excellent | High-quality, social media |
| 95–100 | Very large | Nearly lossless | Archival before PNG |

## Complete Watermark Example

```python
from gi.repository import Gimp, Gio, Gegl

def add_watermark(image, text="© WATERMARK"):
    """Add a diagonal watermark to an image and export as JPEG."""
    pdb = Gimp.get_pdb()

    # 1. Create text layer via PDB
    text_proc = pdb.lookup_procedure("gimp-text-fontname")
    if not text_proc:
        raise RuntimeError("gimp-text-fontname procedure not found")

    cfg = text_proc.create_config()
    cfg.set_property("image", image)
    cfg.set_property("drawable", image.get_active_layer())
    cfg.set_property("x", 60.0)
    cfg.set_property("y", 160.0)
    cfg.set_property("text", text)
    cfg.set_property("border", 0)
    cfg.set_property("antialias", True)
    cfg.set_property("size", 48.0)
    cfg.set_property("unit", Gimp.Unit.PIXEL)
    cfg.set_property("font", "Sans Bold")
    result = text_proc.run(cfg)
    text_layer = result.get_value()

    # 2. Set watermark color to white
    white = Gegl.Color.new("white")
    Gimp.context_push()
    try:
        Gimp.context_set_foreground(white)
        text_layer.edit_fill(Gimp.FillType.FOREGROUND)
    finally:
        Gimp.context_pop()
    Gimp.displays_flush()

    # 3. Set opacity to 25%
    text_layer.set_opacity(25.0)

    # 4. Rotate -30 degrees
    rot_proc = pdb.lookup_procedure("gimp-item-transform-rotate")
    if rot_proc:
        rot_cfg = rot_proc.create_config()
        rot_cfg.set_property("item", text_layer)
        rot_cfg.set_property("angle", -0.523599)   # -30°
        rot_cfg.set_property("auto-center", True)
        rot_proc.run(rot_cfg)

    # 5. Merge layers
    merged = image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)

    # 6. Export as JPEG (quality 85)
    save_jpeg = pdb.lookup_procedure("gimp-file-save-jpeg")
    if save_jpeg:
        jpeg_cfg = save_jpeg.create_config()
        jpeg_cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
        jpeg_cfg.set_property("image", image)
        jpeg_cfg.set_property("drawable", merged)
        jpeg_cfg.set_property("file", Gio.File.new_for_path("/tmp/watermarked.jpg"))
        jpeg_cfg.set_property("quality", 85)
        jpeg_cfg.set_property("optimize", True)
        jpeg_cfg.set_property("subsampling", 3)     # 4:2:0 chroma subsampling
        jpeg_cfg.set_property("progressive", False)
        save_jpeg.run(jpeg_cfg)

    return "/tmp/watermarked.jpg"
```

## MCP Cave Painter Equivalent

When using the Cave Painter MCP daemon (persistent GIMP session via `cave_painter_server.py`), the watermark workflow uses these tools:

```bash
# 1. Create canvas
create_canvas(width=800, height=600)

# 2. Add text
add_text(target=image_handle, text="WATERMARK", x=60, y=160, size=48)

# 3. Export
export(image_handle, "watermarked.png")
```

The MCP daemon handles opacity, rotation, and JPEG export through its own tool set. For full watermark control (opacity, rotation, JPEG quality), use the Python-Fu batch approach above.

## Pitfalls

- **`set_opacity()` uses 0–100 scale, NOT 0–1!** `layer.set_opacity(25.0)` = 25% opacity. Using `0.25` creates 0.25% opacity (nearly invisible).
- **Rotation angle is radians, not degrees.** Common mistake: passing 30 instead of 0.523599. Use the conversion: `radians = degrees * (π / 180)`.
- **`gimp-text-fontname` may not accept font name strings in all GIMP 3.x builds.** If the PDB procedure fails with the font parameter, try the default font: `cfg.set_property("font", "Sans-serif")`.
- **JPEG export requires a single drawable.** Always merge layers first (`merge_visible_layers()`) before JPEG export. Multi-layer images may export with unexpected results.
- **`Gimp.file_save()` infers format from file extension.** For JPEG, use `.jpg` or `.jpeg` extension. For maximum control over quality, use the explicit `gimp-file-save-jpeg` PDB procedure.
- **`merge_visible_layers()` returns a new drawable** — use the returned value, not the old text_layer handle.
- **Text layer may be a floating selection** — if so, anchor it first with `gimp-edit-anchor` before further operations like opacity or rotation.
- **`Gimp.context_push()/pop()`** — Always wrap foreground color changes in context_push/pop to prevent leaking state between operations.
- **`Gimp.displays_flush()`** — Call after every operation that modifies the image to ensure GIMP commits pending changes.
