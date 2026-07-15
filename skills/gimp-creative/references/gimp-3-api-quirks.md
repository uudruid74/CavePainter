# GIMP 3.x API Quirks & Working Patterns

Hard-won from batch-mode Python-Fu development. These are things the GI docs
don't tell you and that changed between GIMP 2.x and 3.x.

## Colors: Gegl.Color, not Gimp.RGB

```python
# GIMP 2.x (gone)
Gimp.RGB(0.1, 0.2, 0.5)

# GIMP 3.x (correct)
Gimp.color_parse_css("rgb(26,51,128)")  # returns Gegl.Color
```

**Helper function** for the 0.0–1.0 float convention:
```python
def color(r, g, b):
    return Gimp.color_parse_css(f"rgb({int(r*255)},{int(g*255)},{int(b*255)})")
```

## Image and Layer Creation — Enum-heavy

```python
img = Gimp.Image.new(W, H, Gimp.ImageType.RGB_IMAGE)
lay = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.RGBA_IMAGE,
                     100.0, Gimp.LayerMode.NORMAL)
img.insert_layer(lay, None, -1)
Gimp.context_set_foreground(color(0.2, 0.3, 0.6))
lay.fill(Gimp.FillType.FOREGROUND)
```

**Gotcha:** `Gimp.Layer.new()` arg order is `(image, name, width, height, type, opacity, mode)`.
GIMP 2.x was `(image, width, height, type, name, opacity, mode)`. Name moved.

## Gradients — method lives on Drawable

```python
active.edit_gradient_fill(
    gradient_type=0, offset=0.0, supersample=False,
    supersample_max_depth=3, supersample_threshold=1.0, dither=True,
    x1=0.0, y1=0.0, x2=W, y2=H)
```

**Gotcha:** Called as `drawable.edit_gradient_fill(...)`, NOT `Gimp.drawable_gradient_fill(...)`.
The latter does NOT exist in GIMP 3.x.

## Text — font objects, not strings

```python
default_font = Gimp.context_get_font()  # Only way to get a font in batch
tl = Gimp.text_font(img, active, float(x), float(y),
                     text, -1, True, float(size), default_font)
```

**Gotchas:**
- `Gimp.context_set_font("Sans Bold")` FAILS — takes `Gimp.Font` object not string
- `Gimp.Font.get_by_name("Sans")` returns None in batch mode
- `Gimp.fonts_get_list("*")` returns empty
- `Gimp.text_layer_new` does NOT exist in GIMP 3.x — use `text_font` instead

## Saving — Gio.File, not filepath strings

```python
from gi.overrides.Gio import File as GioFile
gfile = GioFile.new_for_path("/tmp/output.png")
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, gfile, None)
```

**Gotchas:**
- GIMP 3.x `file_save` takes 4 args (was 5 in 2.x)
- No drawable parameter — saves the full image
- Gio is in `gi.overrides`, not `gi.repository`

## Cleanup

```python
Gimp.Image.delete(img)   # GIMP 3.x — NOT Gimp.image_delete(img)
```

## Full Working Invocation

```bash
GOPHER_DRAW_RECIPE=/tmp/recipe.json HOME=/home/ekl \
timeout 45 gimp --no-interface --batch-interpreter python-fu-eval \
  -b "exec(open('/path/to/script.py').read())" --quit 2>/dev/null
```

## Shebang Fix (Arch Linux quirk)

```bash
sudo find /usr/lib/gimp/3.0/ -name "*.py" -exec sed -i \
  's|#!/usr/bin/env python3|#!/usr/bin/python3.14|g' {} \;
```
