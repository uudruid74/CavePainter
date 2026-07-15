# GIMP 3.x PDB Inventory — Available Drawing & Effect Procedures

Comprehensive scan of GIMP 3.2.4's Procedure Database (1,028 total procedures)
relevant to programmatic image creation. Queried via `Gimp.get_pdb().query_procedures()`.

## Undo / History
| Procedure | Purpose |
|---|---|
| `gimp-image-undo-group-start` | Begin undo transaction group |
| `gimp-image-undo-group-end` | End undo group (commit) |
| `gimp-image-undo-enable` | Enable/disable undo system entirely |
| `gimp-image-undo-thaw` | Re-enable undo after freeze |

## Drop Shadow & Bevel
| Procedure | Purpose |
|---|---|
| `gimp-drawable-merge-shadow` | Merge a cast shadow onto the drawable |
| `gimp-drawable-free-shadow` | Freeform/perspective shadow |
| `script-fu-drop-shadow` | Classic drop shadow (Scheme, callable from PDB) |
| `script-fu-add-bevel` | Bevel/emboss border effect |

## Lighting & Flames
| Procedure | Purpose |
|---|---|
| `plug-in-lighting` | Full lighting effect with direction, intensity, color |
| `plug-in-flame` | Fractal flame generator (procedural fire/plasma) |
| `plug-in-ifscompose` | Iterated Function System — fractal composition |
| `plug-in-warp` | Warp/distort effect |

## Blur & Sharpen
| Procedure | Purpose |
|---|---|
| `script-fu-tile-blur` | Tile-based blur effect |
| `gimp-selection-sharpen` | Sharpen selection edges |
| `plug-in-gegl-filter-browser` | Gateway to ALL GEGL filters (gaussian blur, etc.) |

## Image Operations
| Procedure | Purpose |
|---|---|
| `gimp-image-flatten` | Flatten all layers to single background |
| `gimp-image-merge-down` | Merge active layer with layer below |
| `gimp-image-merge-visible-layers` | Merge all visible layers |
| `gimp-drawable-shadows-highlights` | Shadow/highlight tonal adjustment |

## Vector Paths & Strokes
| Procedure | Purpose |
|---|---|
| `gimp-vector-layer-set-stroke-width` | Set path stroke thickness |
| `gimp-vector-layer-set-stroke-color` | Set path stroke color |
| `gimp-vector-layer-set-stroke-dash-pattern` | Dashed/dotted stroke pattern |
| `gimp-vector-layer-set-enable-stroke` | Toggle stroke visibility |
| `gimp-vector-layer-set-stroke-cap-style` | Round, square, or butt caps |
| `gimp-vector-layer-set-stroke-miter-limit` | Miter limit for sharp corners |
| `gimp-drawable-edit-stroke-item` | Render a path stroke onto a drawable |
| `gimp-path-bezier-stroke-new-moveto` | Start a new bezier sub-path |
| `gimp-path-bezier-stroke-conicto` | Add conic bezier segment |
| `gimp-path-stroke-get-points` | Read path point coordinates |
| `gimp-path-stroke-get-length` | Get path length |
| `gimp-path-stroke-rotate` | Rotate path stroke |

## Brushes & Painting
| Procedure | Purpose |
|---|---|
| `gimp-brush-new` | Create a custom brush |
| `gimp-brush-set-size/angle/hardness/shape/spacing` | Configure brush parameters |
| `gimp-brush-set-radius` | Set brush radius |
| `gimp-brush-set-spikes` | Spikey brush shape |
| `gimp-brush-is-generated` | Check if brush is parametric |
| `gimp-airbrush` | Airbrush paint with pressure sensitivity |
| `gimp-airbrush-default` | Airbrush with default settings |
| `gimp-brushes-get-list` | List available brushes |
| `gimp-context-set-brush` | Set active brush |
| `gimp-context-get-paint-method` | Get current paint method |
| `gimp-context-list-paint-methods` | List all paint methods |

## Gradient Blending
| Procedure | Purpose |
|---|---|
| `gimp-gradient-segment-range-blend-colors` | Blend color across gradient segment |
| `gimp-gradient-segment-range-blend-opacity` | Blend opacity across gradient segment |
| `gimp-context-set-gradient-blend-color-space` | Set gradient color space (RGB, perceptual) |

## Selection
Available: rect, ellipse, free, fuzzy, color-based selection via PDB.

## Layer Effects
| Procedure | Purpose |
|---|---|
| `gimp-layer-set-blend-space` | Set layer blend color space |
| Layer mode enums: NORMAL, MULTIPLY, SCREEN, OVERLAY, GRAIN_MERGE, etc. |

## File Export
PNG, JPEG, WebP, TIFF, BMP, GIF, SVG, PDF — all via `file-*-save` procedures.

## Usage Note

Query the PDB from Python-Fu:
```python
pdb = Gimp.get_pdb()
procedures = pdb.query_procedures("shadow", "", "", "", "", "", "", "")
```
