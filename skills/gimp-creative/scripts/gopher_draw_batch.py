"""Gopher Draw — GIMP 3.x Python-Fu batch image creation.
Drop-in script. Set GOPHER_DRAW_RECIPE to a JSON recipe path and invoke:

  GOPHER_DRAW_RECIPE=/tmp/recipe.json HOME=/home/ekl \\
  gimp --no-interface --batch-interpreter python-fu-eval \\
    -b "exec(open('/path/to/gopher_draw_batch.py').read())" --quit
"""

import json, os, sys, traceback
from gi.repository import Gimp, Gegl, GLib, Gio

recipe_path = os.environ.get("GOPHER_DRAW_RECIPE", "/tmp/gopher_recipe.json")
if not os.path.exists(recipe_path):
    print("ERROR: no recipe", flush=True); sys.exit(1)

with open(recipe_path) as f:
    R = json.load(f)

cvs = R.get("canvas", {"width": 800, "height": 600, "bg": [0.05, 0.1, 0.2]})
W, H = cvs["width"], cvs["height"]


def c(r, g, b):
    """Create a Gegl.Color from 0-1 float RGB."""
    return Gimp.color_parse_css(f"rgb({int(r*255)},{int(g*255)},{int(b*255)})")


try:
    img = Gimp.Image.new(W, H, Gimp.ImageType.RGB_IMAGE)
    lay = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.RGBA_IMAGE,
                          100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(lay, None, -1)
    Gimp.context_set_foreground(c(*cvs["bg"]))
    lay.fill(Gimp.FillType.FOREGROUND)
    active = lay
    default_font = Gimp.context_get_font()

    for cmd in R.get("commands", []):
        op = cmd.get("op")
        if op == "fill":
            Gimp.context_set_foreground(c(*cmd["color"]))
            active.fill(Gimp.FillType.FOREGROUND)
        elif op == "gradient":
            fg = cmd.get("fg", [0, 0.5, 1])
            bg_g = cmd.get("bg", [0.1, 0.05, 0.2])
            Gimp.context_set_foreground(c(*fg))
            Gimp.context_set_background(c(*bg_g))
            active.edit_gradient_fill(cmd.get("style", 0), 0.0, False, 3, 1.0, True, 0, 0, W, H)
        elif op == "text":
            Gimp.context_set_foreground(c(cmd["r"], cmd["g"], cmd["b"]))
            tl = Gimp.text_font(img, active, float(cmd["x"]), float(cmd["y"]),
                                 cmd["text"], -1, True,
                                 float(cmd.get("size", 48)), default_font)
        elif op == "layer":
            active = Gimp.Layer.new(img, cmd["name"], W, H,
                                     Gimp.ImageType.RGBA_IMAGE,
                                     cmd.get("opacity", 100.0),
                                     Gimp.LayerMode.NORMAL)
            img.insert_layer(active, None, -1)

    out = R["output"]
    abspath = os.path.abspath(out)
    gfile = Gio.File.new_for_path(abspath)
    result = Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, gfile, None)
    print(f"SAVED:{result} -> {abspath}", flush=True)
    if os.path.exists(abspath):
        print(f"OK:{os.path.getsize(abspath)}b", flush=True)
    Gimp.Image.delete(img)

except Exception as e:
    print(f"ERROR:{type(e).__name__}:{e}", flush=True)
    traceback.print_exc(file=sys.stdout)
