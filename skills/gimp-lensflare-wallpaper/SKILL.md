---
name: gimp-lensflare-wallpaper
description: 'Create lens flare wallpapers in GIMP 3.x Python-Fu — black bg, multiple lens flares, gradient flares (Gflare 101/102), unsharp mask sharpen, and teal color overlay layer'
category: cave-painter
tags: [gimp, lens-flare, gradient-flare, wallpaper, python-fu, batch, compositing, overlay]
---

# GIMP Lens Flare Wallpaper Pipeline

Create a wallpaper in GIMP 3.x Python-Fu headless batch mode: **black background → 3 lens flares → 2 gradient flares → sharpen → teal color overlay.**

All operations use PDB procedure calls (`pdb.lookup_procedure(...)`) since lens flare and gradient flare are plug-in procedures, not direct Gimp.* API methods.

## Full Pipeline Script

```python
#!/usr/bin/env python3
"""
Create a lens flare wallpaper with compositing effects.
Usage: gimp --no-interface --batch-interpreter python-fu-eval -b "exec(open('script.py').read())" -b "pdb.gimp_quit(1)"
"""

from gi.repository import Gimp, Gegl, Gio, GLib
import sys

WIDTH = 1920
HEIGHT = 1080
OUTPUT_PATH = "/tmp/lensflare-wallpaper.png"

def main():
    # --- 1. Create image with black background ---
    image = Gimp.Image.new(WIDTH, HEIGHT, Gimp.ImageBaseType.RGB)
    image.undo_group_start()

    layer = Gimp.Layer.new(image, "Background", WIDTH, HEIGHT,
                           Gimp.ImageType.RGB_IMAGE, 100, Gimp.LayerMode.NORMAL)
    image.insert_layer(layer, None, -1)

    # Fill with black
    black = Gegl.Color.new("black")
    Gimp.context_set_background(black)
    Gimp.Drawable.edit_fill(layer, Gimp.FillType.BACKGROUND)
    Gimp.displays_flush()

    # --- 2. Create 3 lens flares at different positions ---
    pdb = Gimp.get_pdb()
    lens_flare = pdb.lookup_procedure("plug-in-lens-flare")
    if not lens_flare:
        print("ERROR: plug-in-lens-flare not found in PDB")
        sys.exit(1)

    lens_flare_positions = [
        (WIDTH * 0.3, HEIGHT * 0.35),   # Left third, upper
        (WIDTH * 0.7, HEIGHT * 0.4),    # Right third, upper
        (WIDTH * 0.5, HEIGHT * 0.75),   # Center, lower
    ]

    for i, (cx, cy) in enumerate(lens_flare_positions, 1):
        # Create a temp drawable — lens flare applies to the active drawable
        chip_layer = Gimp.Layer.new(image, f"LensFlare{i}", WIDTH, HEIGHT,
                                    Gimp.ImageType.RGB_IMAGE, 100, Gimp.LayerMode.NORMAL)
        image.insert_layer(chip_layer, None, -1)
        Gimp.context_set_background(black)
        Gimp.Drawable.edit_fill(chip_layer, Gimp.FillType.BACKGROUND)
        Gimp.displays_flush()

        cfg = lens_flare.create_config()
        cfg.set_property("image", image)
        cfg.set_property("drawable", chip_layer)
        cfg.set_property("center-x", float(cx))
        cfg.set_property("center-y", float(cy))
        # Optional: brightness/scale — check plug-in defaults
        cfg.set_property("brightness", 0.8)
        result = lens_flare.run(cfg)
        if result != Gimp.PDBStatusType.SUCCESS:
            print(f"WARNING: lens flare {i} returned {result}")

        # Merge down to main layer
        Gimp.Image.merge_down(image, chip_layer, Gimp.MergeType.EXPAND_AS_NECESSARY)
        Gimp.displays_flush()

    print("3 lens flares applied and merged.")

    # --- 3. Apply 2 gradient flares (Gflare 102 + Gflare 101) ---
    gradient_flare = pdb.lookup_procedure("plug-in-gradient-flare")
    if not gradient_flare:
        print("ERROR: plug-in-gradient-flare not found in PDB")
        sys.exit(1)

    # Gflare types: 101 and 102 are specific gradient flare presets
    gflare_configs = [
        {"type": 102, "x": WIDTH * 0.25, "y": HEIGHT * 0.3, "name": "Gflare102"},
        {"type": 101, "x": WIDTH * 0.75, "y": HEIGHT * 0.6, "name": "Gflare101"},
    ]

    for gfc in gflare_configs:
        chip_layer = Gimp.Layer.new(image, gfc["name"], WIDTH, HEIGHT,
                                    Gimp.ImageType.RGB_IMAGE, 100, Gimp.LayerMode.NORMAL)
        image.insert_layer(chip_layer, None, -1)
        Gimp.context_set_background(black)
        Gimp.Drawable.edit_fill(chip_layer, Gimp.FillType.BACKGROUND)
        Gimp.displays_flush()

        cfg = gradient_flare.create_config()
        cfg.set_property("image", image)
        cfg.set_property("drawable", chip_layer)
        cfg.set_property("center-x", float(gfc["x"]))
        cfg.set_property("center-y", float(gfc["y"]))
        cfg.set_property("flare-type", gfc["type"])  # 101 or 102
        result = gradient_flare.run(cfg)
        if result != Gimp.PDBStatusType.SUCCESS:
            print(f"WARNING: gradient flare {gfc['name']} returned {result}")

        Gimp.Image.merge_down(image, chip_layer, Gimp.MergeType.EXPAND_AS_NECESSARY)
        Gimp.displays_flush()

    print("2 gradient flares applied and merged.")

    # --- 4. Sharpen with Unsharp Mask ---
    unsharp = pdb.lookup_procedure("plug-in-unsharp-mask")
    if unsharp:
        cfg = unsharp.create_config()
        cfg.set_property("image", image)
        cfg.set_property("drawable", layer)
        cfg.set_property("radius", 2.0)
        cfg.set_property("amount", 0.8)
        cfg.set_property("threshold", 0)
        unsharp.run(cfg)
        Gimp.displays_flush()
        print("Unsharp mask applied.")
    else:
        print("WARNING: plug-in-unsharp-mask not found, skipping sharpen.")

    # --- 5. Create teal color overlay layer ---
    teal_overlay = Gimp.Layer.new(image, "Teal Overlay", WIDTH, HEIGHT,
                                  Gimp.ImageType.RGB_IMAGE, 100, Gimp.LayerMode.OVERLAY)
    image.insert_layer(teal_overlay, None, -1)

    # Fill with teal (hex: #008080 or hsl-based teal)
    teal = Gegl.Color.new("#008080")
    Gimp.context_set_foreground(teal)
    Gimp.Drawable.edit_fill(teal_overlay, Gimp.FillType.FOREGROUND)

    # Set layer blend mode — use OVERLAY (or try COLOR for a tinted look)
    teal_overlay.set_mode(Gimp.LayerMode.OVERLAY)

    # --- Alternative: use COLOR mode instead for subtler tint ---
    # teal_overlay.set_mode(Gimp.LayerMode.COLOR)

    Gimp.displays_flush()
    print("Teal overlay layer applied at OVERLAY mode.")

    image.undo_group_end()

    # --- 6. Export ---
    result = Gimp.file_save(
        Gimp.RunMode.NONINTERACTIVE,
        image,
        Gio.File.new_for_path(OUTPUT_PATH),
        None
    )
    if result == Gimp.PDBStatusType.SUCCESS:
        print(f"Exported to {OUTPUT_PATH}")
    else:
        print(f"Export failed: {result}")


if __name__ == "__main__":
    main()
```

## Key Procedures

| Step | PDB Procedure | Purpose |
|------|---------------|---------|
| Lens flare | `plug-in-lens-flare` | Creates lens flare at center-x, center-y |
| Gradient flare | `plug-in-gradient-flare` | Stylized gradient-based flare (types 101, 102) |
| Sharpen | `plug-in-unsharp-mask` | Unsharp mask (radius, amount, threshold) |

## PDB Procedure Call Pattern

Always discover and call plug-ins via the PDB API:

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("plug-in-lens-flare")
if proc:
    cfg = proc.create_config()
    cfg.set_property("param_name", value)
    result = proc.run(cfg)
```

### Discovering Procedure Parameters

To discover a plug-in's parameters at runtime:

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("plug-in-lens-flare")
if proc:
    print(f"Name: {proc.get_procedure_name()}")
    for arg in proc.get_arguments():
        print(f"  arg: {arg.get_name()} type={arg.get_value_type()} hint={arg.get_description()}")
```

## Layer Mode Options

| Mode | Effect | Use Case |
|------|--------|----------|
| `Gimp.LayerMode.OVERLAY` | Strong contrast boost + color cast | Dramatic teal glow |
| `Gimp.LayerMode.COLOR` | Recolors hue/saturation only, preserves luminance | Subtle teal tint |
| `Gimp.LayerMode.SOFTLIGHT` | Gentle color cast | Muted teal hue |

## Teal Color Values

```python
# Hex string (Gegl.Color.new parses most CSS hex colors)
teal = Gegl.Color.new("#008080")      # Standard teal
teal = Gegl.Color.new("#00A8A8")      # Brighter teal / cyan-teal
teal = Gegl.Color.new("#00796B")      # Darker teal (Material Design 800)

# RGB floats 0.0-1.0
teal.set_rgba(0.0, 0.5, 0.5, 1.0)    # R=0, G=128, B=128
teal.set_rgba(0.0, 0.66, 0.66, 1.0)  # Brighter teal
```

## Layer-per-Source (Lens Flare Isolation)

Each lens flare and gradient flare is created on its own temporary layer, then merged down with `Gimp.Image.merge_down()`. This prevents one flare from overwriting another when the plug-in operates on the active drawable.

This isolation also means you can:
- Adjust brightness/scale per flare independently
- Change blend mode per flare (if you skip the merge-down step)
- Reorder flares by changing insert position

## Full Command

```bash
gimp --no-interface --batch-interpreter python-fu-eval \
  -b "exec(open('/path/to/lensflare_script.py').read())" \
  -b "pdb.gimp_quit(1)"
```

## Pitfalls

- **PDB procedure names differ from menu names.** Always verify with `pdb.lookup_procedure()` before calling. Use `Gimp.get_pdb().query_procedures("lens", ...)` to search available procedures.
- **`set_property` type matters.** Coordinates may be `float` even if the variable name suggests int. The plug-in's config schema defines the expected types — use the runtime discovery snippet above to check.
- **`Gimp.LayerMode.OVERLAY` vs legacy int.** GIMP 3.x uses typed enums, not integer constants. Always use `Gimp.LayerMode.OVERLAY` (or `Gimp.LayerModeColor.OVERLAY` depending on the GIMP 3 sub-version).
- **Layer opacity is 0–100 scale**, not 0–1. `Gimp.Layer.new(opacity=100)` for fully opaque.
- **`edit_fill()` respects selections; `fill()` does not.** Use `Gimp.Drawable.edit_fill()` with foreground/background for proper fill behavior.
- **Context management:** Wrap color changes and fills in `Gimp.context_push()`/`Gimp.context_pop()` to prevent foreground color leaks between operations.
- **Flare overlay may need NORMAL layer mode** if the flare plug-in itself handles transparency. If flares look wrong in NORMAL, check if the procedure auto-multiplies or screens — some GIMP plug-ins expect the drawable to have transparent background, not black fill.
- **`plug-in-lens-flare` parameter names** may vary between GIMP versions. Common parameter names: `center-x`, `center-y`, `brightness`, `scale`, `intensity`. Use the discovery snippet to find exact names for your GIMP version.
- **Gflare 101 vs 102:** These are preset IDs for the gradient flare plug-in. 101 typically produces a narrow beam flare; 102 a wider soft glow. The exact visual depends on GIMP's installed gradient preset definitions.
