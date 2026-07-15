# GIMP MCP Protocol — Reference

Source: https://github.com/maorcc/gimp-mcp/blob/main/GIMP_MCP_PROTOCOL.md

## Key APIs

### paintbrush_default() — Simplified brush strokes

```python
Gimp.paintbrush_default(drawable, [50.0, 50.0, 150.0, 200.0, 250.0, 50.0])
Gimp.displays_flush()
```

### pencil() — Straight lines

```python
Gimp.pencil(drawable, [0, 200, 200, 0])
Gimp.displays_flush()
```

### Important GIMP 3.0 Findings

**Working:**
- `Gimp.get_images()` — returns list of open images
- `image.get_layers()` — gets layers
- `image.get_active_layer()` — gets active layer
- `Gimp.context_get_foreground()` / `context_set_foreground(gegl_color)`
- `Gimp.Drawable.edit_fill(drawable, type)` — class-method form
- `Gimp.Selection.none(image)` — clear selection
- `Gimp.Display.new(image)` — display image in window
- `image.select_item(Gimp.ChannelOps.REPLACE, layer)` — select from layer alpha

**NOT working (removed in GIMP 3.0):**
- `Gimp.get_active_image()` ❌
- `Gimp.list_images()` ❌
- `Gimp.get_active_layer()` ❌
- `from gimpfu import *` ❌
- `Gimp.file_new_for_path()` ❌ (use `Gio.File.new_for_path()`)
