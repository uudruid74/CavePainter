"""
Gopher Draw Engine — GIMP 3.x headless image creation with session isolation.

Features:
  • Basic: fill, gradient, text, layer
  • Font selection (optional font name in text command)
  • GEGL filters (gaussian-blur, dropshadow, softglow, edge-neon, etc.)
  • Bezier path drawing (moveto, lineto, conicto, cubicto, close)

Multi-agent safety:
  Each drawing session gets a UUID. Recipes, output, and temp files
  are scoped to /tmp/gopher-draw/{session_id}/. A per-session lock file
  prevents concurrent GIMP launches for the same session.

Usage (batch mode):
  export GDB_SESSION_ID="$(uuidgen)"
  export GDB_RECIPE="/tmp/gopher-draw/$GDB_SESSION_ID/recipe.json"
  write_recipe "$GDB_RECIPE"
  HOME=/home/ekl gimp --no-interface --batch-interpreter python-fu-eval \
    -b "exec(open('...engine.py').read())" \
    --quit
"""

import json, os, sys, uuid, fcntl, traceback, tempfile
from gi.repository import Gimp, Gegl, GLib, Gio
from gi.overrides.Gio import File as GioFile

# ── Config ──────────────────────────────────────────────────────────────
BASE_DIR = "/tmp/gopher-draw"
LOCK_TIMEOUT = 60  # seconds to wait for lock

# ── Session management ──────────────────────────────────────────────────

def get_session():
    """Get session ID from environment or create one."""
    return os.environ.get("GDB_SESSION_ID", str(uuid.uuid4()))

def session_dir(session_id):
    """Get the session directory path."""
    return os.path.join(BASE_DIR, session_id)

def lock_path(session_id):
    """Get the lock file path for a session."""
    return os.path.join(session_dir(session_id), ".session.lock")

def acquire_lock(session_id):
    """Acquire exclusive lock for this session. Blocks if held."""
    sdir = session_dir(session_id)
    os.makedirs(sdir, exist_ok=True)
    lf = lock_path(session_id)
    fd = os.open(lf, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd  # caller must release
    except BlockingIOError:
        print(f"LOCK_WAIT:{session_id}", flush=True)
        fcntl.flock(fd, fcntl.LOCK_EX)  # blocks
        return fd

def release_lock(fd):
    """Release the lock."""
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)

# ── Color helper ────────────────────────────────────────────────────────

def color(r, g, b):
    """Create a GEGL color from 0-1 float RGB."""
    return Gimp.color_parse_css(f"rgb({int(r*255)},{int(g*255)},{int(b*255)})")

def color_rgba(r, g, b, a=1.0):
    """Create a GEGL color from 0-1 float RGBA."""
    return Gimp.color_parse_css(f"rgba({int(r*255)},{int(g*255)},{int(b*255)},{a})")

def set_context_color_from_rgb(c):
    """Set context foreground color from recipe [r,g,b] array."""
    Gimp.context_set_foreground(color(*c))

# ── Property value mapper for GEGL filter config ────────────────────────

def _set_gegl_prop(config, name, value):
    """Set a GEGL filter config property with type inference.

    Handles: float, int, bool, str, list/color, Gimp.Color objects.
    """
    if isinstance(value, bool):
        config.set_property(name, value)
    elif isinstance(value, int):
        config.set_property(name, float(value))
    elif isinstance(value, float):
        config.set_property(name, value)
    elif isinstance(value, str):
        config.set_property(name, value)
    elif isinstance(value, (list, tuple)) and len(value) >= 3:
        # Interpret as RGB color
        if len(value) >= 4:
            config.set_property(name, color_rgba(value[0], value[1], value[2], value[3]))
        else:
            config.set_property(name, color(value[0], value[1], value[2]))
    else:
        # Try direct
        config.set_property(name, value)

# ── Drawing engine ──────────────────────────────────────────────────────

def execute(recipe_path, session_id=None):
    """
    Execute a drawing recipe within a session.

    Args:
        recipe_path: Path to JSON recipe file
        session_id: Unique session ID (generated if None)

    Returns:
        Path to output file, or None on failure
    """
    if not recipe_path or not os.path.exists(recipe_path):
        print("ERROR: recipe not found", flush=True)
        return None

    sid = session_id or get_session()
    lfd = acquire_lock(sid)

    try:
        with open(recipe_path) as f:
            R = json.load(f)

        cvs = R.get("canvas", {"width": 800, "height": 600, "bg": [0.05, 0.1, 0.2]})
        W, H = cvs["width"], cvs["height"]

        # Create image
        img = Gimp.Image.new(W, H, Gimp.ImageType.RGB_IMAGE)
        lay = Gimp.Layer.new(img, "Background", W, H,
                             Gimp.ImageType.RGBA_IMAGE, 100.0,
                             Gimp.LayerMode.NORMAL)
        img.insert_layer(lay, None, -1)
        Gimp.context_set_foreground(color(*cvs["bg"]))
        lay.fill(Gimp.FillType.FOREGROUND)
        active = lay

        # PDB shortcut
        pdb = Gimp.get_pdb()

        # Process commands
        for cmd_idx, cmd in enumerate(R.get("commands", [])):
            op = cmd.get("op")
            cmd_label = cmd.get("label", f"cmd#{cmd_idx}:{op}")

            try:
                if op == "fill":
                    Gimp.context_set_foreground(color(*cmd["color"]))
                    active.fill(Gimp.FillType.FOREGROUND)

                elif op == "gradient":
                    Gimp.context_set_foreground(color(*cmd["fg"]))
                    Gimp.context_set_background(color(*cmd["bg"]))
                    style = cmd.get("style", 0)
                    active.edit_gradient_fill(
                        0, 0.0, False, 3, 1.0, True, 0, 0, W, H
                    )

                elif op == "text":
                    Gimp.context_set_foreground(
                        color(cmd["r"], cmd["g"], cmd["b"])
                    )
                    font_name = cmd.get("font", None)
                    if font_name:
                        # Find font by name from available fonts
                        all_fonts = Gimp.fonts_get_list("")
                        font_obj = Gimp.context_get_font()  # fallback
                        for f in all_fonts:
                            if f.get_name() == font_name:
                                font_obj = f
                                break
                    else:
                        font_obj = Gimp.context_get_font()
                    # text_font returns a new text layer — make it active
                    new_layer = Gimp.text_font(
                        img, None,
                        float(cmd["x"]), float(cmd["y"]),
                        cmd["text"], -1, True,
                        float(cmd["size"]), font_obj
                    )
                    if new_layer is not None:
                        active = new_layer

                elif op == "layer":
                    active = Gimp.Layer.new(
                        img, cmd["name"], W, H,
                        Gimp.ImageType.RGBA_IMAGE,
                        cmd.get("opacity", 100.0),
                        Gimp.LayerMode.NORMAL
                    )
                    img.insert_layer(active, None, -1)

                elif op == "gegl":
                    """Apply a GEGL filter to the active layer.

                    Recipe format:
                    {
                        "op": "gegl",
                        "filter": "gegl:gaussian-blur",
                        "label": "My Blur",    # optional
                        "params": {
                            "std-dev-x": 5.0,
                            "std-dev-y": 5.0
                        }
                    }
                    """
                    filter_name = cmd["filter"]
                    filt = Gimp.DrawableFilter.new(
                        active, filter_name, cmd.get("label", filter_name)
                    )
                    config = filt.get_config()

                    # Set parameters
                    for pname, pval in cmd.get("params", {}).items():
                        _set_gegl_prop(config, pname, pval)

                    # Merge filter onto drawable
                    active.merge_filter(filt)

                elif op == "bezier":
                    """Draw bezier/path strokes as a vector layer.

                    Creates a Gimp.VectorLayer from the path geometry with
                    stroke and fill properties set directly.

                    Recipe format:
                    {
                        "op": "bezier",
                        "name": "my-path",
                        "strokes": [
                            {"type": "moveto", "x": 100, "y": 100},
                            {"type": "lineto", "x0": 200, "y0": 100},
                            {"type": "conicto", "x0": 250, "y0": 250, "x1": 300, "y1": 200},
                            {"type": "cubicto", "x0": 350, "y0": 150, "x1": 400, "y1": 200, "x2": 450, "y2": 100},
                            {"type": "close"}
                        ],
                        "stroke_params": {
                            "width": 3.0,
                            "color": [1.0, 0.0, 0.0],
                            "cap-style": 0,
                            "join-style": 0
                        },
                        "fill": false
                    }
                    """
                    path_name = cmd.get("name", f"path-{cmd_idx}")
                    path_obj = Gimp.Path.new(img, path_name)

                    # Add bezier strokes
                    stroke_id = None
                    for stroke in cmd.get("strokes", []):
                        stype = stroke.get("type")
                        if stype == "moveto":
                            stroke_id = path_obj.bezier_stroke_new_moveto(
                                float(stroke["x"]), float(stroke["y"])
                            )
                        elif stype == "lineto" and stroke_id is not None:
                            path_obj.bezier_stroke_lineto(
                                stroke_id,
                                float(stroke["x0"]), float(stroke["y0"])
                            )
                        elif stype == "conicto" and stroke_id is not None:
                            path_obj.bezier_stroke_conicto(
                                stroke_id,
                                float(stroke["x0"]), float(stroke["y0"]),
                                float(stroke["x1"]), float(stroke["y1"])
                            )
                        elif stype == "cubicto" and stroke_id is not None:
                            path_obj.bezier_stroke_cubicto(
                                stroke_id,
                                float(stroke["x0"]), float(stroke["y0"]),
                                float(stroke["x1"]), float(stroke["y1"]),
                                float(stroke["x2"]), float(stroke["y2"])
                            )
                        elif stype == "close" and stroke_id is not None:
                            path_obj.stroke_close(stroke_id)

                    # Create vector layer from path (self-rendering layer)
                    vl = Gimp.VectorLayer.new(img, path_obj)
                    img.insert_layer(vl, None, -1)

                    # Configure stroke using direct VectorLayer methods
                    sp = cmd.get("stroke_params", {})
                    if sp.get("width") is not None:
                        vl.set_stroke_width(float(sp["width"]))
                        vl.set_enable_stroke(True)

                    if sp.get("color"):
                        vl.set_stroke_color(color(*sp["color"]))

                    # Fill path
                    if cmd.get("fill"):
                        fill_color = sp.get("fill-color", sp.get("color", [1, 1, 1]))
                        vl.set_fill_color(color(*fill_color))
                        vl.set_enable_fill(True)

                else:
                    print(f"WARN: unknown op '{op}' in {cmd_label}", flush=True)

            except Exception as cmd_err:
                print(f"ERROR in {cmd_label}: {type(cmd_err).__name__}: {cmd_err}",
                      flush=True)
                traceback.print_exc(file=sys.stdout)
                # Continue processing remaining commands

        # ── Save ──────────────────────────────────────────────────────
        out_name = R.get("output", "output.png")
        out_dir = session_dir(sid)
        abspath = os.path.join(out_dir, out_name)
        gfile = GioFile.new_for_path(abspath)
        result = Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, gfile, None)

        if os.path.exists(abspath):
            print(f"OK:{os.path.getsize(abspath)}b:{abspath}:{sid}", flush=True)
            return abspath
        else:
            print(f"FAIL:save returned {result}", flush=True)
            return None

    except Exception as e:
        print(f"ERROR:{type(e).__name__}:{e}:{sid}", flush=True)
        traceback.print_exc(file=sys.stdout)
        return None
    finally:
        release_lock(lfd)

# ── CLI entry point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    recipe = os.environ.get("GDB_RECIPE") or (sys.argv[1] if len(sys.argv) > 1 else None)
    sid = os.environ.get("GDB_SESSION_ID")

    if not recipe:
        print("Usage: GDB_RECIPE=/path/to/recipe.json [GDB_SESSION_ID=...] python3.14 engine.py",
              flush=True)
        sys.exit(1)

    result = execute(recipe, sid)
    if not result:
        sys.exit(1)
