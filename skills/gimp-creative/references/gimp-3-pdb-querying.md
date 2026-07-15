# GIMP 3.x PDB Querying — Finding Procedures by Name

GIMP's Procedure Database holds **1,028 procedures** (in 3.2.4). You can
discover available tools by querying the PDB via GI bindings rather than
guessing procedure names from GIMP 2.x documentation.

## Key API

```python
import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

pdb = Gimp.get_pdb()
```

### `query_procedures()` — Search by substring across 8 fields

```python
pdb.query_procedures(
    name: str,       # procedure name
    blurb: str,      # short description
    help: str,       # help text
    help_id: str,    # help ID
    authors: str,    # author name
    copyright: str,  # copyright
    date: str,       # date
    proc_type: str,  # procedure type
) -> list[str]
```

Each field is a substring match. Pass empty strings `''` to leave a field
unfiltered. Returns a list of matching procedure names.

### Example: List all procedures

```python
all_procs = pdb.query_procedures('', '', '', '', '', '', '', '')
print(f"Total: {len(all_procs)}")
```

### Example: Find shadow/glow/blur/undo procedures

```python
r = pdb.query_procedures('', '', '', '', '', '', '', '')
effects = [s for s in r if any(x in s.lower() for x in
    ['shadow', 'blur', 'glow', 'undo', 'bevel', 'neon',
     'emboss', 'stroke', 'vectors', 'drop', 'flatten'])]
```

### Example: Find by name prefix

```python
# All gimp-drawable-* procedures
drawable_procs = [s for s in pdb.query_procedures('', '', '', '', '', '', '', '')
                  if s.startswith('gimp-drawable')]

# All file export procedures
export_procs = [s for s in pdb.query_procedures('', '', '', '', '', '', '', '')
                if s.startswith('file-') and ('save' in s or 'export' in s)]
```

### `lookup_procedure()` — Check if a specific procedure exists

```python
exists = pdb.lookup_procedure('gimp-image-undo-group-start')
```

Returns `None` if not found, or a procedure object if it exists.

### `procedure_exists()` — Simple boolean check

```python
if pdb.procedure_exists('gimp-drawable-merge-shadow'):
    print("Drop shadow available!")
```

## Key Procedures Found

| Category | Procedure | What it does |
|---|---|---|
| Drop Shadow | `gimp-drawable-merge-shadow` | Merge shadow onto drawable |
| Free Shadow | `gimp-drawable-free-shadow` | Freeform shadow cast |
| Shadow/HL | `gimp-drawable-shadows-highlights` | Shadow/highlight adjustment |
| Drop Shadow SF | `script-fu-drop-shadow` | Classic drop shadow (Scheme) |
| Bevel | `script-fu-add-bevel` | Bevel/emboss effect |
| Lighting | `plug-in-lighting` | Full lighting effect |
| Flame | `plug-in-flame` | Fractal flame generator |
| Warp | `plug-in-warp` | Warp/distort effect |
| Undo Group | `gimp-image-undo-group-start` | Begin undo group |
| Undo Group | `gimp-image-undo-group-end` | End undo group |
| Undo Enable | `gimp-image-undo-enable` | Enable/disable undo |
| Undo Thaw | `gimp-image-undo-thaw` | Re-enable undo |
| Stroke | `gimp-drawable-edit-stroke-item` | Stroke a path to drawable |
| Stroke Width | `gimp-vector-layer-set-stroke-width` | Set path stroke width |
| Stroke Color | `gimp-vector-layer-set-stroke-color` | Set path stroke color |
| Stroke Dash | `gimp-vector-layer-set-stroke-dash-pattern` | Dashed strokes |
| Bezier | `gimp-path-bezier-stroke-new-moveto` | Start bezier path |
| Bezier | `gimp-path-bezier-stroke-conicto` | Conic bezier segment |
| Flatten | `gimp-image-flatten` | Flatten all layers |
| Merge Down | `gimp-image-merge-down` | Merge layer down |
| Merge Visible | `gimp-image-merge-visible-layers` | Merge visible layers |
| Sharpen | `gimp-selection-sharpen` | Sharpen selection edges |
| GEGL Browser | `plug-in-gegl-filter-browser` | Access all GEGL filters |
| Brushes | `gimp-brushes-get-list` | List available brushes |
| Brush API | `gimp-context-get-brush-size` | Brush size, angle, hardness... |
| Font List | `gimp-fonts-get-list('*')` | List fonts (may return empty in batch) |
| PNG Save | `file-png-save` | Export PNG |
| JPEG Save | `file-jpeg-save` | Export JPEG |
| WebP Save | `file-webp-save` | Export WebP |
| GIF Save | `file-gif-save` | Export GIF |
| SVG Save | `file-svg-save` | Export SVG |

## Note on GIMP 3.x vs 2.x Names

Many classic GIMP 2.x procedure names have changed. Don't rely on old
documentation — always query the PDB first:
- `gimp_drawable_gradient_fill` → `drawable.edit_gradient_fill()` (method on object, not PDB)
- `gimp_text_fontname` → `Gimp.text_font()` (method, not PDB)
- `gimp_edit_bucket_fill` → `layer.fill(FillType.FOREGROUND)` (method, not PDB)
- `gimp_image_delete` → `Gimp.Image.delete(img)` (class method)

Always prefer the GI method API over PDB procedures when available — they're
the idiomatic GIMP 3.x way. Use PDB querying for plug-in effects (lighting,
flame, warp, GEGL) that don't have GI wrappers.
