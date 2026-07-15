---
name: gimp-pdb-procedures
description: Using GIMP's PDB (Procedure Database) for fallback when direct API calls fail — the gimp-mcp reference implementation pattern
category: cave-painter
trigger: When a direct Gimp.* API call fails, returns None, or has unclear behavior — try the PDB procedure route instead
---

## GIMP 3.x PDB Procedure Calls

Some GIMP operations work more reliably through PDB procedures than through direct `Gimp.*` method calls. The gimp-mcp project uses PDB extensively.

### Pattern

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-procedure-name")
if proc:
    cfg = proc.create_config()
    cfg.set_property("param_name", value)
    result = proc.run(cfg)
```

### Discovering Procedure Arguments

To find what properties a PDB procedure expects, use `get_arguments()`:

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-file-save")
for i, arg in enumerate(proc.get_arguments()):
    print(i, type(arg).__name__, arg)
# Example output:
# 0 GParamEnum  → run-mode
# 1 GimpParamImage  → the image
# 2 GParamObject  → Gio.File for path
# 3 GimpParamExportOptions  → export format options
```

### PDB Procedures vs Direct API

| Operation | Direct API | PDB Procedure |
|---|---|---|
| Save XCF | `Gimp.file_save(...)` | `pdb.lookup_procedure("gimp-xcf-save")` |
| Drawable histogram | `drawable.histogram(...)` | `pdb.lookup_procedure("gimp-drawable-histogram")` |
| Deselect all | `image.select_rectangle(REPLACE, 0,0,0,0)` | `pdb.lookup_procedure("gimp-selection-none")` |
| Font text | `Gimp.text_font(img, None, ...)` | `pdb.lookup_procedure("gimp-text-fontname")` |

### Key PDB Procedures for Cave Painter

- `gimp-file-save` — export PNG/JPEG. GIMP 3.2 args: run-mode (enum), image (GimpParamImage), file (GParamObject/GFile), export-options (GimpParamExportOptions). Two working forms:
  - **Config-based:** `proc.create_config()` + `set_property()` + `proc.run(config)`
  - **Direct:** `Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, gfile, None)` (works in batch AND GUI)
- `gimp-selection-none` — clear selection (alternative to manual rectangle hack)
- `gimp-edit-fill` — fill selection with FG/BG/white/transparent
- `gimp-edit-bucket-fill` — flood fill
- `gimp-context-set-foreground` — set FG color via PDB
- `gimp-image-select-ellipse` — elliptical selection via PDB
- `gimp-image-select-rectangle` — rectangle selection via PDB
- `gimp-image-select-item` — select from path/channel

### GIMP 3.2 API Changes (from gimp-mcp commits)

| Old API | New/Replacement |
|---|---|
| `Gimp.display_list()` | `Gimp.get_displays()` |
| `GimpDoubleArray.set_property()` | `drawable.curves_spline()` |
| `layer.copy(TRUE)` | `layer.copy()` (no args in 3.2) |
| `gimp-blend` procedure | GEGL `gegl:linear-gradient` / `gegl:radial-gradient` |
| `Gimp.text_fontname()` | PDB `gimp-text-fontname` |
| `image.select_none()` | PDB `gimp-selection-none` |
| `get_pixel()` returns tuple | Returns `Gegl.Color` — use `.get_rgba()` for `(r,g,b,a)` floats |
