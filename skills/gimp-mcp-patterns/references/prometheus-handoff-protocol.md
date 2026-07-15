# Prometheus Handoff Protocol v4

## Origin

Designed 2026-07-13. Replaces v2/v3 timer-based dialog interception (proven impossible in GIMP 3 — plugins exit after procedure returns). Uses **GEGL filter-stack introspection** instead.

**Key insight:** GIMP 3 applies filters non-destructively by default. When you open Gaussian Blur and adjust the radius, the filter is already a live `DrawableFilter` on the layer. The dialog is just a UI wrapper around something that already exists. No dialog interception needed.

## How It Works

```
User opens image → applies Gaussian Blur non-destructively
  → filter is on the layer as DrawableFilter(operation="gegl:gaussian-blur", config={std-dev-x: 1.5})
  → User clicks OK → filter stays on the layer (non-destructive default)
  → User clicks Tools → Prometheus Snapshot
  → Plugin reads: layer.get_filters()
  → Plugin exports PNG
  → Plugin writes handoff JSON
```

## Handoff Payload Format (v4)

```json
{
  "sequence": 1,
  "timestamp_utc": 1783924575.44,
  "image_state": {
    "image_name": "[current_xxx] (exported)",
    "width": 600,
    "height": 600,
    "precision": "150",
    "layer_count": 1,
    "layers": [{
      "name": "gopher-hero.png",
      "visible": true,
      "opacity": 100.0,
      "mode": "normal",
      "width": 600,
      "height": 600,
      "depth": 0,
      "filters": [{
        "operation": "gegl:gaussian-blur",
        "display_name": "Gaussian Blur",
        "opacity": 1.0,
        "visible": true,
        "blend_mode": "replace",
        "params": {
          "std-dev-x": 1.5,
          "std-dev-y": 1.5,
          "filter": "auto",
          "abyss-policy": "clamp",
          "clip-extent": true
        }
      }]
    }]
  },
  "current_PNG": "/tmp/prometheus/current_1783924575.png"
}
```

### Backward compatibility fields

v4 handoffs also include flattened `action_names` and `dialog_params_json` fields so external consumers expecting the old format still work:

```json
"action_names": ["gegl:gaussian-blur"],
"dialog_params_json": "{ \"gegl:gaussian-blur\": { \"std-dev-x\": 1.5, ... } }"
```

## GEGL Filter-Stack Introspection API

### Reading all filters on a layer

```python
filters = layer.get_filters()         # → [DrawableFilter, ...]
for f in filters:
    op_name = f.get_operation_name()   # → "gegl:gaussian-blur"
    display = f.get_name()             # → "Gaussian Blur"
    opacity = f.get_opacity()          # → 1.0
    visible = f.get_visible()          # → True
    blend = f.get_blend_mode()         # → Gimp.LayerMode constant
    
    config = f.get_config()            # → DrawableFilterConfig (GObject)
    pspecs = config.list_properties()  # → [GParamSpec, ...]
    for p in pspecs:
        val = config.get_property(p.name)  # → 1.5, "auto", True, etc.
```

### Serializing GObject property values

```python
def _serialize_gvalue(value):
    if value is None: return None
    if isinstance(value, (str, int, float, bool)): return value
    if isinstance(value, int) and hasattr(value, '__members__'):
        return value.value_nick if hasattr(value, 'value_nick') else int(value)
    if isinstance(value, int): return value
    try: return str(value)
    except: return None
```

### Reading complete image state

```python
def read_image_state(image):
    layers = image.get_layers()
    return {
        "image_name": image.get_name(),
        "width": image.get_width(), "height": image.get_height(),
        "layer_count": len(layers),
        "layers": [read_layer(layer) for layer in layers],
    }

def read_layer(layer, depth=0):
    return {
        "name": layer.get_name(), "visible": layer.get_visible(),
        "opacity": layer.get_opacity(), "mode": _get_mode_nick(layer),
        "width": layer.get_width(), "height": layer.get_height(),
        "depth": depth,
        "filters": [read_filter(f) for f in layer.get_filters()],
        "children": [read_layer(c, depth+1) for c in layer.get_children()],
    }
```

## Undo/Redo for Before/After Comparison

Since v4 captures only the current state (after filters applied), getting a "before" requires:

1. **Prometheus Snapshot** → captures current state
2. **Edit → Undo** (Ctrl+Z) → removes the non-destructive filter
3. **Prometheus Snapshot again** → captures "before" state
4. **Edit → Redo** (Ctrl+Shift+Z) → re-applies filter

GIMP 3 non-destructive filters cleanly undo/redo via the filter stack — no data loss. The AI can compare both PNGs to see what the filter actually changed.

## Key Numbers

- `Gimp.drawable.get_filters()` → list of `DrawableFilter` objects
- `DrawableFilter.get_config()` → `DrawableFilterConfig` GObject with all operation properties
- `config.list_properties()` → dynamically registered based on the GEGL operation
- No GIMP API to query undo stack contents — use `_SEQUENCE` counter
- Plugin process exits after procedure returns — no persistent timers possible

## Design Constraints

1. **GEGL filter-stack introspection**, not dialog interception (GIMP 3 plugins exit after procedure returns)
2. **Manual trigger** via Tools → Prometheus Snapshot (no auto-capture — no persistent process)
3. **Internal sequence counter** — never rely on GIMP undo position
4. **Full layer tree capture** — all layers, child layers, all filters on each
5. **PNG export** via `Gimp.file_save(NONINTERACTIVE, image, GFile, None)` — works in GUI plugins too (confirmed 2026-07-13)
