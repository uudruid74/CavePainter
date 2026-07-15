"""GIMP 3.x Python-Fu: Water Drop + Electrifying Effect.

7-step pipeline: gradient bg → blur → pinch distort → waves →
duplicate layer → difference clouds → saturation mode.

Run:
  HOME=/home/ekl \
  gimp --no-interface --batch-interpreter python-fu-eval \
    -b "exec(open('water_drop_electrifying.py').read())" --quit

Set env var OUTPUT_PATH to override (default: ./water_drop_electrifying_TIMESTAMP.png).
"""

import json, os, sys, time, traceback
from gi.repository import Gimp, Gegl, GLib, Gio

W, H = 800, 600
DEFAULT_OUTPUT = os.path.abspath(
    os.environ.get("OUTPUT_PATH",
                   f"water_drop_electrifying_{int(time.time())}.png")
)

# ── helpers ────────────────────────────────────────────────────────────

_saved_pdb = None


def _pdb():
    global _saved_pdb
    if _saved_pdb is None:
        _saved_pdb = Gimp.get_pdb()
    return _saved_pdb


def _gegl_proc():
    return _pdb().lookup_procedure("plug-in-gegl")


def _run_gegl(drawable, op_name, **props):
    """Run a GEGL operation on *drawable* via plug-in-gegl."""
    proc = _gegl_proc()
    cfg = proc.create_config()
    cfg.set_property("drawable", drawable)
    cfg.set_property("gegl", op_name)
    for k, v in props.items():
        cfg.set_property(k, v)
    result = proc.run(cfg)
    return result


def _css_color(r, g, b):
    """Create a Gegl.Color from 0-255 ints or 0.0-1.0 floats."""
    if max(r, g, b) <= 1.0:
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
    return Gimp.color_parse_css(f"rgb({r},{g},{b})")


# ── pipeline ───────────────────────────────────────────────────────────

try:
    img = Gimp.Image.new(W, H, Gimp.ImageType.RGB_IMAGE)
    bg = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.RGBA_IMAGE,
                        100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bg, None, -1)

    # ── Step 1 – Gradient background ──
    print("Step 1/7 – Gradient background", flush=True)
    Gimp.context_set_foreground(_css_color(0, 15, 60))     # deep dark blue
    Gimp.context_set_background(_css_color(40, 130, 220))   # bright blue
    bg.edit_gradient_fill(
        0,       # gradient_type: 0 = linear
        0.0,     # offset
        False,   # supersample
        3,       # max_depth
        1.0,     # threshold
        True,    # dither
        0.0, 0.0, float(W), float(H)  # diagonal top-left → bottom-right
    )

    # ── Step 2 – Gaussian blur ──
    print("Step 2/7 – Gaussian blur", flush=True)
    _run_gegl(bg, "gegl:gaussian-blur",
              std_dev_x=20.0, std_dev_y=20.0)

    # ── Step 3 – Pinch distort (water-drop lens) ──
    print("Step 3/7 – Pinch distort", flush=True)
    cx, cy = float(W) / 2, float(H) / 2
    pinch_radius = min(W, H) * 0.40
    _run_gegl(bg, "gegl:pinch",
              pinch_amount=0.5,
              radius=pinch_radius,
              center_x=cx, center_y=cy)

    # ── Step 4 – Waves (ripples) ──
    print("Step 4/7 – Waves", flush=True)
    _run_gegl(bg, "gegl:waves",
              amplitude=30.0, period=80.0,
              phase=0.0, shape=0, clamp=False)

    # ── Step 5 – Duplicate layer ──
    print("Step 5/7 – Duplicate layer", flush=True)
    dup = bg.copy()
    img.insert_layer(dup, None, 0)

    # ── Step 6 – Difference clouds (electrifying) ──
    print("Step 6/7 – Difference clouds", flush=True)
    _run_gegl(dup, "gegl:difference-clouds",
              seed=42, detail=2.5, turbulence=0.0)

    # ── Step 7 – Saturation blend mode ──
    print("Step 7/7 – Saturation layer mode", flush=True)
    dup.set_mode(Gimp.LayerMode.SATURATION)
    dup.set_opacity(80.0)

    # ── Export ──
    out_path = DEFAULT_OUTPUT
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    gfile = Gio.File.new_for_path(out_path)
    result = Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, gfile, None)
    print(f"SAVED -> {out_path}", flush=True)
    if os.path.exists(out_path):
        print(f"OK  {os.path.getsize(out_path)} bytes", flush=True)
    else:
        print(f"WARN output not found: {out_path}", flush=True)

    Gimp.Image.delete(img)
    print("Done.", flush=True)

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", flush=True)
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)
