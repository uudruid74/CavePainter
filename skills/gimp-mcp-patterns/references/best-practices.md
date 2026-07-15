# gimp-mcp Best Practices — Reference

Source: https://github.com/maorcc/gimp-mcp/blob/main/docs/best_practices.md

## Filling Shapes — Polygon Selection

Best method for solid filled shapes:

```python
points = [x1, y1, x2, y2, x3, y3, ...]  # Flat array of coordinates
Gimp.Image.select_polygon(image, Gimp.ChannelOps.REPLACE, points)
Gimp.context_set_foreground(color)
Gimp.Drawable.edit_fill(drawable, Gimp.FillType.FOREGROUND)
Gimp.Selection.none(image)
Gimp.displays_flush()
```

## Bezier Paths — Outlines Only

- ✅ Use for stroked outlines with curves → `edit_stroke_item(drawable, path)`
- ❌ `path.to_selection()` does NOT exist in GIMP 3.0 — AttributeError!
- For filled curved shapes, approximate with polygon selections or overlapping ellipses

## Copy Layer Between Images

```python
image1.select_rectangle(Gimp.ChannelOps.REPLACE, 0, 0, width, height)
drawable = image1.get_selected_layers()[0]
Gimp.edit_copy([drawable])
floating_sel = Gimp.edit_paste(target_drawable, True)[0]
Gimp.floating_sel_anchor(floating_sel)
Gimp.displays_flush()
```

## Variable Persistence

PyGObject console maintains persistent Python environment. Variables persist between calls:
- First call: set up `image1`, `layer1`, `drawable1`
- Later calls: reuse them — no need to re-import or re-initialize
- Don't repeat imports or initialization

## Self-Critique Checklist

After drawing, check:
- [ ] Shapes match intended form
- [ ] Edges sharp and clean (not feathered/blurry)
- [ ] Colors correct and consistent
- [ ] Selections cleared after use
- [ ] `Gimp.displays_flush()` called

Common artifacts: blurry edges (feathering), cloudy areas (overlapping feathered selections), missing elements (wrong layer), unexpected colors (forgot to set foreground)

## Verifying Colors

Check `get_context_state()` before operations that depend on settings:
- User can change colors in GIMP UI at any time
- Verify foreground/background before drawing
