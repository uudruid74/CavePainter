"""Cave Painter Daemon — Persistent GIMP command processor.
 
File-command protocol. Commands in {session}/commands/, results in {session}/results/.
 
Supports: canvas, layers, text, shapes, gradients, BEZIER/BRUSH painting, brush presets.
 
Brush system:
  new_brush(name, brush_name, size, hardness, ...)  → brush_001
  paint_stroke(img, brush_id, strokes, color)       → ok (path stroked with brush)
  paint_dab(img, brush_id, x, y, color)             → ok (single dab)
  drop_brush(brush_id)                               → released
  list_brushes()                                     -> [all 58 GIMP brush names]
"""
VERSION = "20260715.17"
import json, os, sys, uuid, time, traceback
from gi.repository import Gimp, Gegl, GLib, Gio
from pathlib import Path

SESSION_ID = os.environ.get("GDB_SESSION_ID", f"gimpd-{uuid.uuid4().hex[:8]}")
BASE = Path(f"/tmp/gopher-daemon/{SESSION_ID}")
CMD_DIR = BASE / "commands"
RES_DIR = BASE / "results"
os.makedirs(CMD_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

# ── State ──────────────────────────────────────────────────────────────
img = None
layers = []
brushes = {}         # handle -> {brush_name, size, hardness, aspect, angle, spacing}
hc = [0]

def h():
    hc[0] += 1
    return hc[0]

def res(seq, **kw):
    kw["seq"] = seq
    (RES_DIR / f"{seq:04d}_result.json").write_text(json.dumps(kw))

def color(c):
    return Gimp.color_parse_css(f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})")

def _drawable(args):
    idx = args.get("layer", -1)
    if idx >= 0 and idx < len(layers):
        return layers[idx]
    return None

def _deselect():
    global img
    if img:
        Gimp.Image.select_rectangle(img, Gimp.ChannelOps.REPLACE, 0, 0, 0, 0)

def _top_pos():
    """Return the insertion position that places a layer at the top of the stack."""
    return len(img.get_layers()) if img else 0

def _set_fg(c):
    """Set foreground color. Must be called BEFORE _apply_brush() AND right before paint ops.
    
    CRITICAL DISCOVERY: Gimp.context_set_brush() in GIMP 3.x SNAPSHOTS the
    current foreground color into the brush context. Calling _set_fg() AFTER
    _apply_brush() means the brush captures the STALE foreground. The fix:
    call _set_fg() BEFORE _apply_brush() so the brush snapshots the right color,
    then again AFTER as a safety net.
    """
    Gimp.context_set_foreground(c)

def _apply_brush(br):
    """Apply a brush preset to GIMP context.
    
    CRITICAL: Gimp.context_set_brush() in GIMP 3.x SNAPSHOTS the current
    foreground color into the brush context for subsequent paint operations.
    Therefore _set_fg() must be called BEFORE _apply_brush() to capture
    the correct color. The after-call is a safety net.
    """
    if not br:
        return
    
    # Look up the actual GIMP brush by name
    name = br.get("brush_name", "2. Hardness 100")
    name = name.replace("  ", " ")  # normalize whitespace
    all_brushes = Gimp.brushes_get_list("")
    for b in all_brushes:
        try:
            if b.get_name().lower() == name.lower():
                Gimp.context_set_brush(b)
                break
        except:
            pass
    
    if br.get("size") is not None:
        Gimp.context_set_brush_size(float(br["size"]))
    if br.get("hardness") is not None:
        Gimp.context_set_brush_hardness(float(br["hardness"]))
    if br.get("aspect_ratio") is not None:
        Gimp.context_set_brush_aspect_ratio(float(br["aspect_ratio"]))
    if br.get("angle") is not None:
        Gimp.context_set_brush_angle(float(br["angle"]))
    if br.get("spacing") is not None:
        Gimp.context_set_brush_spacing(float(br["spacing"]))
    if br.get("force") is not None:
        Gimp.context_set_brush_force(float(br["force"]))

# ── Brush commands ─────────────────────────────────────────────────────

def cmd_list_brushes(seq, args):
    """List all available GIMP brush names."""
    all_b = Gimp.brushes_get_list("")
    names = []
    for b in all_b:
        try:
            names.append(b.get_name())
        except:
            names.append(str(b))
    res(seq, ok=True, brushes=names, count=len(names))

def cmd_new_brush(seq, args):
    """Create a brush preset. Return handle like brush_001."""
    handle = h()
    preset = {
        "brush_name": args.get("brush_name", "2. Hardness 100"),
        "size": args.get("size"),
        "hardness": args.get("hardness"),
        "aspect_ratio": args.get("aspect_ratio"),
        "angle": args.get("angle"),
        "spacing": args.get("spacing"),
        "force": args.get("force"),
    }
    brushes[handle] = preset
    res(seq, ok=True, handle=f"brush_{handle:04d}", preset=preset)

def cmd_paint_stroke(seq, args):
    """
    Paint a path strokes with a brush.
    Args:
      brush: brush handle (e.g. "brush_001") or inline dict
      strokes: same format as draw_bezier strokes
      color: [r, g, b]
      layer: optional layer index
    """
    global img, layers
    if not img: res(seq, error="No image"); return
    
    # Resolve brush
    brush_ref = args.get("brush", {})
    if isinstance(brush_ref, str) and brush_ref.startswith("brush_"):
        idx = int(brush_ref.split("_")[1])
        br = brushes.get(idx)
        if not br:
            res(seq, error=f"Brush not found: {brush_ref}")
            return
    elif isinstance(brush_ref, dict):
        br = brush_ref
    else:
        br = {"brush_name": "2. Hardness 100", "size": 20.0}
    
    col = args.get("color", [0.0, 0.0, 0.0])
    
    Gimp.context_push()
    
    # Set foreground BEFORE brush — context_set_brush() snapshots foreground!
    col_obj = color(col)
    _set_fg(col_obj)
    
    _apply_brush(br)
    
    strokes = args.get("strokes", [])
    if not strokes:
        Gimp.context_pop()
        res(seq, error="No strokes"); return
    
    # Create path
    pname = f"brush_{uuid.uuid4().hex[:6]}"
    po = Gimp.Path.new(img, pname)
    sid = None
    for s in strokes:
        st = s["type"]
        if st == "moveto":
            sid = po.bezier_stroke_new_moveto(float(s["x"]), float(s["y"]))
        elif st == "lineto" and sid is not None:
            po.bezier_stroke_lineto(sid, float(s["x0"]), float(s["y0"]))
        elif st == "conicto" and sid is not None:
            po.bezier_stroke_conicto(sid, float(s["x0"]), float(s["y0"]),
                                      float(s["x1"]), float(s["y1"]))
        elif st == "cubicto" and sid is not None:
            po.bezier_stroke_cubicto(sid, float(s["x0"]), float(s["y0"]),
                                      float(s["x1"]), float(s["y1"]),
                                      float(s["x2"]), float(s["y2"]))
        elif st == "close" and sid is not None:
            po.stroke_close(sid)
    
    # Insert path into image — required for edit_stroke_item to find it
    img.insert_path(po, None, 0)
    
    # Re-set foreground after brush as safety net
    _set_fg(col_obj)
    
    # Stroke with brush
    d = _drawable(args)
    if d:
        d.edit_stroke_item(po)
    else:
        img.get_layers()[0].edit_stroke_item(po)
    
    Gimp.context_pop()
    Gimp.displays_flush()
    
    res(seq, ok=True, strokes=len(strokes))

def cmd_paint_dab(seq, args):
    """
    Single brush dab at (x, y).
    Args: brush, x, y, color, size (optional override), layer
    """
    global img, layers
    if not img: res(seq, error="No image"); return
    
    brush_ref = args.get("brush", {})
    if isinstance(brush_ref, str) and brush_ref.startswith("brush_"):
        idx = int(brush_ref.split("_")[1])
        br = brushes.get(idx)
        if not br:
            res(seq, error=f"Brush not found: {brush_ref}")
            return
    elif isinstance(brush_ref, dict):
        br = brush_ref
    else:
        br = {"brush_name": "2. Hardness 100", "size": 20.0}
    
    col = args.get("color", [0.0, 0.0, 0.0])
    
    Gimp.context_push()
    
    # Set foreground BEFORE brush — context_set_brush() snapshots foreground!
    col_obj = color(col)
    _set_fg(col_obj)
    
    _apply_brush(br)
    
    if args.get("size") is not None:
        Gimp.context_set_brush_size(float(args["size"]))

    x, y = float(args["x"]), float(args["y"])
    size = args.get("size", 20.0)
    
    # Use a circular selection + edit_fill for a solid dab
    _deselect()
    Gimp.Image.select_ellipse(img, Gimp.ChannelOps.REPLACE, x - size/2, y - size/2, size, size)
    
    # Re-set foreground after brush+selection as safety net
    _set_fg(col_obj)
    
    d = _drawable(args)
    if d:
        Gimp.Drawable.edit_fill(d, Gimp.FillType.FOREGROUND)
    else:
        Gimp.Drawable.edit_fill(img.get_layers()[0], Gimp.FillType.FOREGROUND)
    _deselect()
    
    Gimp.context_pop()
    Gimp.displays_flush()
    
    res(seq, ok=True, x=x, y=y)

def cmd_drop_brush(seq, args):
    """Release a brush preset."""
    brush_ref = args.get("brush", "")
    if isinstance(brush_ref, str) and brush_ref.startswith("brush_"):
        idx = int(brush_ref.split("_")[1])
        if idx in brushes:
            del brushes[idx]
            res(seq, ok=True, released=brush_ref)
        else:
            res(seq, error=f"Brush not found: {brush_ref}")
    else:
        res(seq, error="Not a brush handle")

# ── Existing commands ──────────────────────────────────────────────────

def cmd_create(seq, args):
    global img, layers
    W = args.get("width", 800)
    H = args.get("height", 600)
    bg = args.get("bg", [0.05, 0.1, 0.2])
    img = Gimp.Image.new(W, H, Gimp.ImageType.RGB_IMAGE)
    bl = Gimp.Layer.new(img, "Bg", W, H, Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bl, None, 0)
    Gimp.context_set_foreground(color(bg))
    bl.fill(Gimp.FillType.FOREGROUND)
    layers = []
    res(seq, ok=True, handle=h(), width=W, height=H, session=SESSION_ID)

def cmd_new_layer(seq, args):
    global img, layers
    if not img: res(seq, error="No image"); return
    name = args.get("name", f"Layer_{len(layers)}")
    W, H = img.get_width(), img.get_height()
    ly = Gimp.Layer.new(img, name, W, H, Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(ly, None, _top_pos())
    layers.append(ly)
    res(seq, ok=True, handle=h(), layer_index=len(layers)-1, name=name)

def cmd_ellipse(seq, args):
    global img
    if not img: res(seq, error="No image"); return
    cx, cy, rx, ry = args["cx"], args["cy"], args["rx"], args["ry"]
    fill = args.get("fill", [0.5, 0.5, 0.5])
    _deselect()
    Gimp.Image.select_ellipse(img, Gimp.ChannelOps.REPLACE, cx-rx, cy-ry, rx*2, ry*2)
    Gimp.context_set_foreground(color(fill))
    d = _drawable(args)
    if d: d.edit_fill(Gimp.FillType.FOREGROUND)
    else:
        # Fill on Bg layer (index 0) — edit_fill respects selection
        img.get_layers()[0].edit_fill(Gimp.FillType.FOREGROUND)
    _deselect()
    res(seq, ok=True)

def cmd_rect(seq, args):
    global img
    if not img: res(seq, error="No image"); return
    x, y, w, h = args["x"], args["y"], args["w"], args["h"]
    fill = args.get("fill", [0.5, 0.5, 0.5])
    _deselect()
    Gimp.Image.select_rectangle(img, Gimp.ChannelOps.REPLACE, x, y, w, h)
    Gimp.context_set_foreground(color(fill))
    d = _drawable(args)
    if d: d.edit_fill(Gimp.FillType.FOREGROUND)
    else:
        # Fill on Bg layer (index 0) — edit_fill respects selection
        img.get_layers()[0].edit_fill(Gimp.FillType.FOREGROUND)
    _deselect()
    res(seq, ok=True)

def cmd_text(seq, args):
    global img, layers
    if not img: res(seq, error="No image"); return
    text = args.get("text", "")
    x, y = args.get("x", 0), args.get("y", 0)
    size = args.get("size", 20)
    col = args.get("color", [1.0, 1.0, 1.0])
    font_name = args.get("font", "")
    Gimp.context_set_foreground(color(col))
    # Resolve font: if name given, look it up; otherwise use current context font
    if font_name:
        font_obj = Gimp.context_get_font()  # fallback
        for f in Gimp.fonts_get_list(""):
            if f.get_name() == font_name:
                font_obj = f
                break
    else:
        font_obj = Gimp.context_get_font()
    try:
        # text_font creates and inserts text at position 0 (bottom) when parent=None.
        # Reorder to top so Bg stays at index 0 for draw operations.
        tl = Gimp.text_font(img, None, float(x), float(y), text, -1, True, float(size), font_obj)
        if tl is not None:
            layers.append(tl)
            # Reorder text layer to top of stack (above Bg and any other layers)
            all_layers = img.get_layers()
            top_pos = len(all_layers) - 1
            if all_layers[0] == tl:  # only reorder if it's at the bottom
                img.reorder_item(tl, None, top_pos)
            Gimp.displays_flush()
        else:
            res(seq, error="text_font returned None")
            return
    except Exception as e:
        res(seq, error=f"text: {e}")
        return
    res(seq, ok=True)

def cmd_bezier(seq, args):
    global img
    if not img: res(seq, error="No image"); return
    strokes = args.get("strokes", [])
    col = args.get("color", [1.0, 0.2, 0.2])
    sw = args.get("stroke_width", 3.0)
    do_fill = args.get("fill", False)
    fc = args.get("fill_color", col)
    pname = f"p_{uuid.uuid4().hex[:6]}"
    po = Gimp.Path.new(img, pname)
    sid = None
    for s in strokes:
        st = s["type"]
        if st == "moveto":
            sid = po.bezier_stroke_new_moveto(float(s["x"]), float(s["y"]))
        elif st == "lineto" and sid is not None:
            po.bezier_stroke_lineto(sid, float(s["x0"]), float(s["y0"]))
        elif st == "conicto" and sid is not None:
            po.bezier_stroke_conicto(sid, float(s["x0"]), float(s["y0"]), float(s["x1"]), float(s["y1"]))
        elif st == "cubicto" and sid is not None:
            po.bezier_stroke_cubicto(sid, float(s["x0"]), float(s["y0"]), float(s["x1"]), float(s["y1"]), float(s["x2"]), float(s["y2"]))
        elif st == "close" and sid is not None:
            po.stroke_close(sid)
    vl = Gimp.VectorLayer.new(img, po)
    img.insert_layer(vl, None, _top_pos())
    vl.set_stroke_width(float(sw))
    vl.set_enable_stroke(True)
    vl.set_stroke_color(color(col))
    if do_fill:
        vl.set_fill_color(color(fc))
        vl.set_enable_fill(True)
    res(seq, ok=True)

def cmd_gradient(seq, args):
    global img
    if not img: res(seq, error="No image"); return
    fg = args.get("fg", [0.0, 0.5, 0.8])
    bg = args.get("bg", [0.08, 0.05, 0.15])
    style = args.get("style", 0)
    gl = Gimp.Layer.new(img, "_grad", img.get_width(), img.get_height(),
                         Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(gl, None, _top_pos())
    Gimp.context_set_foreground(color(fg))
    Gimp.context_set_background(color(bg))
    if style == 1:
        gl.edit_gradient_fill(Gimp.GradientType.RADIAL, 0.0, False, 1.0, 0.0, True)
    else:
        gl.edit_gradient_fill(Gimp.GradientType.LINEAR, 0.0, False, 1.0, 0.0, True)
    res(seq, ok=True)

def cmd_export(seq, args):
    global img
    if not img: res(seq, error="No image"); return
    path = args.get("path", str(BASE / "output.png"))
    gfile = Gio.File.new_for_path(path)
    try:
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, gfile, None)
        size = os.path.getsize(path)
        res(seq, ok=True, path=path, size_bytes=size)
    except Exception as e:
        res(seq, error=f"save: {e}")

def cmd_ping(seq, args):
    res(seq, ok=True, pong=True, has_image=img is not None, layers=len(layers), brushes=len(brushes))

# ── Handler registry ───────────────────────────────────────────────────

HANDLERS = {
    "create_canvas": cmd_create,
    "new_layer": cmd_new_layer,
    "draw_ellipse": cmd_ellipse,
    "draw_rect": cmd_rect,
    "add_text": cmd_text,
    "draw_bezier": cmd_bezier,
    "draw_gradient": cmd_gradient,
    "export": cmd_export,
    "ping": cmd_ping,
    "done": lambda s, a: None,
    "export_done": lambda s, a: cmd_export(s, a),
    # Brush commands
    "list_brushes": cmd_list_brushes,
    "new_brush": cmd_new_brush,
    "paint_stroke": cmd_paint_stroke,
    "paint_dab": cmd_paint_dab,
    "drop_brush": cmd_drop_brush,
}

# ── Main loop ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    processed = set()
    seq = 0
    running = True
    while running:
        for cf in sorted(CMD_DIR.glob("*.json")):
            if cf.name in processed:
                continue
            try:
                cmd = json.loads(cf.read_text())
                seq += 1
                ctype = cmd.get("cmd", "")
                handler = HANDLERS.get(ctype)
                if handler:
                    try:
                        handler(seq, cmd)
                    except Exception as e:
                        res(seq, error=f"Handler error: {type(e).__name__}: {e}")
                        traceback.print_exc()
                else:
                    res(seq, error=f"Unknown cmd: {ctype}")
                processed.add(cf.name)
                if ctype in ("done", "export_done"):
                    running = False
                    break
            except Exception as e:
                print(f"Parse error: {e}", file=sys.stderr)
                processed.add(cf.name)
        if running:
            time.sleep(0.1)
    sys.exit(0)
