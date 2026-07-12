"""Gopher GIMP Daemon v3 — Correct GIMP 3.x API. File-command protocol.

Commands via numbered JSON files in {session}/commands/
Results written to {session}/results/

API truths discovered:
- Gimp.Image.select_ellipse(img, op, x, y, w, h) ✓
- sel.all(img) → bool (selects all, no deselect)
- Deselect with: Gimp.Image.select_rectangle(img, REPLACE, 0, 0, 0, 0)
- Gimp.Path.new(img, name) ✓
- Gimp.file_save(RunMode.NONINTERACTIVE, flat_layer, gfile, None) ✓
"""
import json, os, sys, uuid, time, traceback
from gi.repository import Gimp, Gegl, GLib, Gio
from pathlib import Path

SESSION_ID = os.environ.get("GDB_SESSION_ID", f"gimpd-{uuid.uuid4().hex[:8]}")
BASE = Path(f"/tmp/gopher-daemon/{SESSION_ID}")
CMD_DIR = BASE / "commands"
RES_DIR = BASE / "results"
os.makedirs(CMD_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

img = None        # Active Gimp.Image
layers = []       # Stack of named layers
hc = [0]

def h():
    hc[0] += 1
    return hc[0]

def res(seq, **kw):
    kw["seq"] = seq
    rfile = RES_DIR / f"{seq:04d}_result.json"
    with open(rfile, "w") as f:
        json.dump(kw, f)

def color(c):
    return Gimp.color_parse_css(f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})")

# ── Command handlers ───────────────────────────────────────────────────

def cmd_create(seq, args):
    global img, layers
    W = args.get("width", 800)
    H = args.get("height", 600)
    bg = args.get("bg", [0.05, 0.1, 0.2])
    
    img = Gimp.Image.new(W, H, Gimp.ImageType.RGB_IMAGE)
    bl = Gimp.Layer.new(img, "Bg", W, H, Gimp.ImageType.RGBA_IMAGE, 1.0, Gimp.LayerMode.NORMAL)
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
    ly = Gimp.Layer.new(img, name, W, H, Gimp.ImageType.RGBA_IMAGE, 1.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(ly, None, 0)
    layers.append(ly)
    res(seq, ok=True, handle=h(), layer_index=len(layers)-1, name=name)

def _drawable(args):
    idx = args.get("layer", -1)
    if idx >= 0 and idx < len(layers):
        return layers[idx]
    return None

def _deselect():
    """Clear all selections."""
    global img
    Gimp.Image.select_rectangle(img, Gimp.ChannelOps.REPLACE, 0, 0, 0, 0)

def cmd_ellipse(seq, args):
    global img
    if not img: res(seq, error="No image"); return
    cx, cy, rx, ry = args["cx"], args["cy"], args["rx"], args["ry"]
    fill = args.get("fill", [0.5, 0.5, 0.5])
    
    _deselect()
    Gimp.Image.select_ellipse(img, Gimp.ChannelOps.REPLACE, cx-rx, cy-ry, rx*2, ry*2)
    Gimp.context_set_foreground(color(fill))
    
    d = _drawable(args)
    if d:
        d.fill(Gimp.FillType.FOREGROUND)
    else:
        temp = Gimp.Layer.new(img, "_tmp", img.get_width(), img.get_height(),
                              Gimp.ImageType.RGBA_IMAGE, 1.0, Gimp.LayerMode.NORMAL)
        img.insert_layer(temp, None, 0)
        temp.fill(Gimp.FillType.FOREGROUND)
    
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
    if d:
        d.fill(Gimp.FillType.FOREGROUND)
    else:
        temp = Gimp.Layer.new(img, "_tmp", img.get_width(), img.get_height(),
                              Gimp.ImageType.RGBA_IMAGE, 1.0, Gimp.LayerMode.NORMAL)
        img.insert_layer(temp, None, 0)
        temp.fill(Gimp.FillType.FOREGROUND)
    
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
    font = font_name if font_name else Gimp.context_get_font()
    
    tx = Gimp.Layer.new(img, "_txt", img.get_width(), img.get_height(),
                         Gimp.ImageType.RGBA_IMAGE, 1.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(tx, None, 0)
    
    try:
        Gimp.text_font(img, None, float(x), float(y), text, -1, True, float(size), font)
    except Exception as e:
        res(seq, error=f"text: {e}")
        return
    
    idx = args.get("layer", -1)
    if idx >= 0 and idx < len(layers):
        try:
            tx.merge_to(layers[idx])
        except:
            layers.append(tx)
    
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
        x = lambda k: float(s.get(k, 0))
        if st == "moveto":
            sid = po.bezier_stroke_new_moveto(x("x"), x("y"))
        elif st == "lineto" and sid is not None:
            po.bezier_stroke_lineto(sid, x("x0"), x("y0"))
        elif st == "conicto" and sid is not None:
            po.bezier_stroke_conicto(sid, x("x0"), x("y0"), x("x1"), x("y1"))
        elif st == "cubicto" and sid is not None:
            po.bezier_stroke_cubicto(sid, x("x0"), x("y0"), x("x1"), x("y1"), x("x2"), x("y2"))
        elif st == "close" and sid is not None:
            po.stroke_close(sid)
    
    vl = Gimp.VectorLayer.new(img, po)
    img.insert_layer(vl, None, -1)
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
    style = args.get("style", 0)  # 0=linear, 1=radial
    
    gl = Gimp.Layer.new(img, "_grad", img.get_width(), img.get_height(),
                         Gimp.ImageType.RGBA_IMAGE, 1.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(gl, None, 0)
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
    res(seq, ok=True, pong=True, has_image=img is not None, layers=len(layers))

# ── Main loop ──────────────────────────────────────────────────────────

HANDLERS = {
    "create_canvas": cmd_create,
    "new_layer": cmd_new_layer,
    "draw_ellipse": cmd_ellipse,
    "draw_rect": cmd_rect,
    "add_text": cmd_text,
    "draw_bezier": cmd_bezier,
    "draw_gradient": cmd_gradient,
    "export": cmd_export,
    "export_done": lambda s, a: (cmd_export(s, a), cmd_export),
    "ping": cmd_ping,
    "done": lambda s, a: None,
    "export_done": lambda s, a: cmd_export(s, a),
}

if __name__ == "__main__":
    processed = set()
    seq = 0
    running = True
    
    while running:
        cmd_files = sorted(CMD_DIR.glob("*.json"))
        for cf in cmd_files:
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
                
                if ctype == "done" or ctype == "export_done":
                    running = False
                    break
            except Exception as e:
                print(f"Parse error: {e}", file=sys.stderr)
                processed.add(cf.name)
        
        if running:
            time.sleep(0.1)
    
    sys.exit(0)
