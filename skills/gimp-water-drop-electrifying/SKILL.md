---
name: gimp-water-drop-electrifying
description: 'Multi-filter GIMP pipeline: gradient bg → blur → pinch distort → waves → duplicate layer → difference clouds → saturation mode — produces a water drop + lightning effect.'
category: creative
tags: [gimp, python-fu, gegl, filters, water-drop, lightning, batch]
---

# GIMP Water Drop + Electrifying Effect Pipeline

Create a **water drop / lightning** effect through a 7-step GEGL filter pipeline:

1. **Gradient background** — dark blue→light blue linear gradient
2. **Gaussian blur** — softens the gradient
3. **Pinch distort** — creates the water-drop lensing effect
4. **Waves** — ripples around the drop
5. **Duplicate layer** — for the electrifying overlay
6. **Difference clouds** — lightning/energy texture
7. **Saturation mode** — blends the clouds as colorful electrical discharge

Run entirely headless via GIMP 3.x Python-Fu (`--no-interface --batch-interpreter python-fu-eval`).

## When to Use

- Creating sci-fi / fantasy water-drop icons or backgrounds
- Producing lightning + water composite effects programmatically
- Learning how to chain GEGL filters in batch mode
- Generating reactive textured backgrounds for UI/digital art

## How to Run

### Quick Command (with bundled script)

```bash
HOME=/home/ekl \
gimp --no-interface --batch-interpreter python-fu-eval \
  -b "exec(open('/home/ekl/.hermes/profiles/gopher/skills/creative/gimp-water-drop-electrifying/scripts/water_drop_electrifying.py').read())" \
  --quit
```

### Output

Generates `water_drop_electrifying_<timestamp>.png` in the current directory (or a custom path, see script).

## The 7-Step Pipeline Explained

### Step 1 — Gradient Background

Creates a dark blue to light blue diagonal gradient. The gradient provides the depth that the pinch/wave distortion will manipulate into a 3D water-drop illusion.

```python
fg = Gimp.color_parse_css("rgb(0,15,60)")      # deep dark blue
bg = Gimp.color_parse_css("rgb(40,130,220)")    # bright blue
Gimp.context_set_foreground(fg)
Gimp.context_set_background(bg)
# 0 = linear gradient, from top-left to bottom-right
active.edit_gradient_fill(0, 0.0, False, 3, 1.0, True, 0, 0, float(W), float(H))
```

### Step 2 — Gaussian Blur

Softens the gradient into a smooth atmospheric glow so the later distortions look organic rather than pixelated.

```python
pdb = Gimp.get_pdb()
gegl_proc = pdb.lookup_procedure("plug-in-gegl")
cfg = gegl_proc.create_config()
cfg.set_property("drawable", active)
cfg.set_property("gegl", "gegl:gaussian-blur")
cfg.set_property("std-dev-x", 20.0)
cfg.set_property("std-dev-y", 20.0)
gegl_proc.run(cfg)
```

### Step 3 — Pinch Distort

Creates the water-drop lensing effect — pinches pixels toward the center, simulating a spherical droplet. Adjust `pinch-amount` (0.0-1.0, 0.5 recommended) and `radius` to control the droplet size.

```python
cfg = gegl_proc.create_config()
cfg.set_property("drawable", active)
cfg.set_property("gegl", "gegl:pinch")
cfg.set_property("pinch-amount", 0.5)
cfg.set_property("radius", min(W, H) * 0.4)
cfg.set_property("center-x", float(W) / 2)
cfg.set_property("center-y", float(H) / 2)
gegl_proc.run(cfg)
```

### Step 4 — Waves

Adds ripples radiating outward from the droplet. Amplitude controls ripple height, period controls spacing.

```python
cfg = gegl_proc.create_config()
cfg.set_property("drawable", active)
cfg.set_property("gegl", "gegl:waves")
cfg.set_property("amplitude", 30.0)
cfg.set_property("period", 80.0)
cfg.set_property("phase", 0.0)
cfg.set_property("shape", 0)  # 0=sine, 1=triangle, 2=sawtooth
cfg.set_property("clamp", False)
gegl_proc.run(cfg)
```

### Step 5 — Duplicate Layer

Creates the overlay layer that will hold the lighting effect.

```python
dup = active.copy()
img.insert_layer(dup, None, 0)  # insert on top
```

### Step 6 — Difference Clouds

Generates a fractal/plasma noise texture that forms the lightning/electrical discharge pattern.

```python
cfg = gegl_proc.create_config()
cfg.set_property("drawable", dup)
cfg.set_property("gegl", "gegl:difference-clouds")
cfg.set_property("seed", 42)      # fixed seed for reproducibility
cfg.set_property("detail", 2.5)   # higher = more fine detail
cfg.set_property("turbulence", 0.0)
gegl_proc.run(cfg)
```

### Step 7 — Saturation Layer Mode

Sets the duplicate layer to SATURATION blend mode. This applies the clouds as a color overlay, making the light/dark cloud patterns affect only the saturation of the underlying gradient — creating colorful electrical discharge while preserving the base image's luminance.

```python
dup.set_mode(Gimp.LayerMode.SATURATION)
# Optional: adjust layer opacity
dup.set_opacity(80.0)
```

## GEGL Filter Parameter Discovery

GEGL operation property names can be discovered by querying the operation directly:

```python
from gi.repository import Gegl
# List all properties of a GEGL operation
op = Gegl.Node()
gegl_operation = op.create_child("gegl:gaussian-blur")
# Use dir() or introspection to see available properties
```

For a simpler approach, use `gimp:gegl-graph` to apply operations, or browse GEGL operation properties in the GIMP GEGL dialog. Common GEGL operations and their key params:

| GEGL Op | Key Properties | Type |
|---|---|---|
| `gegl:gaussian-blur` | `std-dev-x`, `std-dev-y` | float |
| `gegl:pinch` | `pinch-amount`, `radius`, `center-x`, `center-y` | float |
| `gegl:waves` | `amplitude`, `period`, `phase`, `shape`, `clamp` | float/int/bool |
| `gegl:difference-clouds` | `seed`, `detail`, `turbulence` | int/float |

## Complete Example Script

The bundled script at `water_drop_electrifying.py` implements the full pipeline. Save it to a known path and invoke via:

```bash
HOME=/home/ekl \
gimp --no-interface --batch-interpreter python-fu-eval \
  -b "exec(open('/path/to/water_drop_electrifying.py').read())" \
  --quit
```

### Customization Tips

| Effect | Parameter | Tweak |
|---|---|---|
| Larger water drop | Increase `radius` in pinch step (up to min(W,H)*0.45) | |
| More ripples | Increase `amplitude`, decrease `period` in waves | |
| Finer lightning | Increase `detail` in difference-clouds (2.0–4.0) | |
| Stronger electrical | Lower `opacity` on saturation layer (below 60% weakens) | |
| Color shift | Change gradient colors for different mood (green→cyan for poison, red→orange for fire) | |
| Reproducible | Fixed `seed` in difference-clouds gives same cloud pattern | |
| Random | Set `seed=0` for unpredictable lightning patterns | |

## Pitfalls

- **`plug-in-gegl` is the gateway** — All GEGL ops run through `pdb.lookup_procedure("plug-in-gegl")`. Do NOT try to call GEGL operations directly as PDB procedures (they don't register individually).
- **Property names are case-sensitive** — GEGL operation properties use kebab-case (e.g. `std-dev-x`, not `stdDevX`). Wrong names silently fail or use defaults.
- **`copy()` returns a non-inserted layer** — Always call `img.insert_layer(dup, None, 0)` after `layer.copy()`. The copied layer isn't part of the image hierarchy until inserted.
- **Layer mode must be set AFTER insertion** — Some GIMP versions require the layer to be in the image before `set_mode()` takes effect.
- **Batch export path** — `Gimp.file_save()` writes to the path given as `Gio.File`. The output path must exist (directory created) or it fails silently.
- **HOME for config** — Always pass `HOME=/home/ekl` so GIMP finds its config plug-ins. Without it, Python-Fu scripts may not load.
- **GEGL parameter type mismatches** — Set `float` params as Python floats and `int` params as Python ints. Setting a float where an int is expected (or vice versa) may crash `proc.run()`.
