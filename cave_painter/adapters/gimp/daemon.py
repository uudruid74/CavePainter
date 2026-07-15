"""GIMP-side command processor. Runs *inside* GIMP's python-fu-eval interpreter
(loaded via `exec(open(daemon.py).read())`), which is the only place
`gi.repository.Gimp` is importable. Talks to the client adapter (client.py,
running in the MCP server's own process) over a Unix socket (or TCP on older
Windows). Newline-delimited JSON for both commands and responses.

This is a port of the original cave_painter_daemon.py, with the file-based
command/result protocol replaced by socket IPC, and the three bug fixes
(fill->edit_fill, path traversal check, opacity 100.0) applied.
"""
import json
import os
import socket
import sys
import traceback
import uuid
from pathlib import Path

from gi.repository import Gimp, Gio

# This file is loaded via exec(open(...).read()) inside GIMP's python-eval
# plugin, not a normal import -- __file__ here would resolve to the *loader's*
# path, not this file. So the project root has to come from an env var.
_ROOT = os.environ.get("CAVE_PAINTER_ROOT")
if _ROOT and _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cave_painter import config

SESSION_ID = os.environ.get("CAVE_PAINTER_SESSION_ID", f"gimpd-{uuid.uuid4().hex[:8]}")
SOCKET_PATH = os.environ.get("CAVE_PAINTER_SOCKET_PATH", "")

# -- State ----------------------------------------------------------------
img = None
layers = []
brushes = {}  # handle -> preset dict
hc = [0]


def h():
    hc[0] += 1
    return hc[0]


def send_response(sock, seq, **kw):
    """Send a JSON response over the socket (newline-delimited)."""
    kw["seq"] = seq
    msg = (json.dumps(kw) + "\n").encode("utf-8")
    sock.sendall(msg)


def color(c):
    return Gimp.color_parse_css(f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})")


def _drawable(args):
    idx = args.get("layer", -1)
    if idx is not None and idx >= 0 and idx < len(layers):
        return layers[idx]
    return None


def _deselect():
    global img
    if img:
        Gimp.Image.select_rectangle(img, Gimp.ChannelOps.REPLACE, 0, 0, 0, 0)


def _apply_brush(br):
    if not br:
        return
    name = br.get("brush_name", "2. Hardness 100").replace("  ", " ")
    for b in Gimp.brushes_get_list(""):
        try:
            if b.get_name().lower() == name.lower():
                Gimp.context_set_brush(b)
                break
        except Exception:
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


def _resolve_brush(brush_ref):
    if isinstance(brush_ref, str) and brush_ref.startswith("brush_"):
        idx = int(brush_ref.split("_")[1])
        return brushes.get(idx)
    if isinstance(brush_ref, dict):
        return brush_ref
    return {"brush_name": "2. Hardness 100", "size": 20.0}


def _build_path(pname, strokes):
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
    return po


# -- Brush commands ------------------------------------------------------

def cmd_list_brushes(seq, args):
    names = []
    for b in Gimp.brushes_get_list(""):
        try:
            names.append(b.get_name())
        except Exception:
            names.append(str(b))
    return {"ok": True, "brushes": names, "count": len(names)}


def cmd_new_brush(seq, args):
    handle = h()
    preset = {
        "brush_name": args.get("brush_name", "2. Hardness 100"),
        "size": args.get("size"), "hardness": args.get("hardness"),
        "aspect_ratio": args.get("aspect_ratio"), "angle": args.get("angle"),
        "spacing": args.get("spacing"), "force": args.get("force"),
    }
    brushes[handle] = preset
    return {"ok": True, "handle": f"brush_{handle:04d}", "preset": preset}


def cmd_paint_stroke(seq, args):
    global img
    if not img:
        return {"error": "No image"}
    br = _resolve_brush(args.get("brush", {}))
    if br is None:
        return {"error": f"Brush not found: {args.get('brush')}"}
    Gimp.context_push()
    Gimp.context_set_foreground(color(args.get("color", [0.0, 0.0, 0.0])))
    _apply_brush(br)
    strokes = args.get("strokes", [])
    if not strokes:
        Gimp.context_pop()
        return {"error": "No strokes"}
    po = _build_path(f"brush_{uuid.uuid4().hex[:6]}", strokes)
    d = _drawable(args)
    if d:
        d.edit_stroke_item(po)
    else:
        temp = Gimp.Layer.new(img, "_bp", img.get_width(), img.get_height(),
                              Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
        img.insert_layer(temp, None, 0)
        temp.edit_stroke_item(po)
    Gimp.context_pop()
    Gimp.displays_flush()
    return {"ok": True, "strokes": len(strokes)}


def cmd_paint_dab(seq, args):
    global img
    if not img:
        return {"error": "No image"}
    br = _resolve_brush(args.get("brush", {}))
    if br is None:
        return {"error": f"Brush not found: {args.get('brush')}"}
    Gimp.context_push()
    Gimp.context_set_foreground(color(args.get("color", [0.0, 0.0, 0.0])))
    _apply_brush(br)
    if args.get("size") is not None:
        Gimp.context_set_brush_size(float(args["size"]))
    x, y = float(args["x"]), float(args["y"])
    po = Gimp.Path.new(img, f"dab_{uuid.uuid4().hex[:6]}")
    sid = po.bezier_stroke_new_moveto(x, y)
    po.bezier_stroke_lineto(sid, x + 0.1, y)
    d = _drawable(args)
    if d:
        d.edit_stroke_item(po)
    else:
        temp = Gimp.Layer.new(img, "_dab", img.get_width(), img.get_height(),
                              Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
        img.insert_layer(temp, None, 0)
        temp.edit_stroke_item(po)
    Gimp.context_pop()
    Gimp.displays_flush()
    return {"ok": True, "x": x, "y": y}


def cmd_drop_brush(seq, args):
    brush_ref = args.get("brush", "")
    if isinstance(brush_ref, str) and brush_ref.startswith("brush_"):
        idx = int(brush_ref.split("_")[1])
        if idx in brushes:
            del brushes[idx]
            return {"ok": True, "released": brush_ref}
    return {"error": f"Brush not found: {brush_ref}"}


# -- Canvas / shape / text commands --------------------------------------

def cmd_create(seq, args):
    global img, layers
    W, H = args.get("width", 800), args.get("height", 600)
    bg = args.get("bg", [0.05, 0.1, 0.2])
    img = Gimp.Image.new(W, H, Gimp.ImageType.RGB_IMAGE)
    bl = Gimp.Layer.new(img, "Bg", W, H, Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bl, None, 0)
    Gimp.context_set_foreground(color(bg))
    bl.edit_fill(Gimp.FillType.FOREGROUND)  # BUG FIX: was bl.fill()
    layers = []
    return {"ok": True, "handle": h(), "width": W, "height": H, "session": SESSION_ID}


def cmd_new_layer(seq, args):
    global img, layers
    if not img:
        return {"error": "No image"}
    name = args.get("name", f"Layer_{len(layers)}")
    W, H = img.get_width(), img.get_height()
    ly = Gimp.Layer.new(img, name, W, H, Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(ly, None, 0)
    layers.append(ly)
    return {"ok": True, "handle": h(), "layer_index": len(layers) - 1, "name": name}


def _fill_selection(seq, args, fill):
    """Fill the active selection on the target drawable. Uses edit_fill()
    (NOT fill()) because fill() ignores the active selection and fills the
    entire drawable -- this was the fill bug."""
    d = _drawable(args)
    Gimp.context_set_foreground(color(fill))
    if d:
        d.edit_fill(Gimp.FillType.FOREGROUND)  # BUG FIX: was d.fill()
    else:
        temp = Gimp.Layer.new(img, "_tmp", img.get_width(), img.get_height(),
                              Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
        img.insert_layer(temp, None, 0)
        temp.edit_fill(Gimp.FillType.FOREGROUND)  # BUG FIX: was temp.fill()
    _deselect()
    return {"ok": True}


def cmd_ellipse(seq, args):
    global img
    if not img:
        return {"error": "No image"}
    cx, cy, rx, ry = args["cx"], args["cy"], args["rx"], args["ry"]
    _deselect()
    Gimp.Image.select_ellipse(img, Gimp.ChannelOps.REPLACE, cx - rx, cy - ry, rx * 2, ry * 2)
    return _fill_selection(seq, args, args.get("fill", [0.5, 0.5, 0.5]))


def cmd_rect(seq, args):
    global img
    if not img:
        return {"error": "No image"}
    x, y, w, hh = args["x"], args["y"], args["w"], args["h"]
    _deselect()
    Gimp.Image.select_rectangle(img, Gimp.ChannelOps.REPLACE, x, y, w, hh)
    return _fill_selection(seq, args, args.get("fill", [0.5, 0.5, 0.5]))


def cmd_text(seq, args):
    global img, layers
    if not img:
        return {"error": "No image"}
    text = args.get("text", "")
    x, y = args.get("x", 0), args.get("y", 0)
    size = args.get("size", 20)
    Gimp.context_set_foreground(color(args.get("color", [1.0, 1.0, 1.0])))
    font_name = args.get("font", "")
    font = font_name if font_name else Gimp.context_get_font()
    tx = Gimp.Layer.new(img, "_txt", img.get_width(), img.get_height(),
                        Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(tx, None, 0)
    try:
        Gimp.text_font(img, None, float(x), float(y), text, -1, True, float(size), font)
    except Exception as e:
        return {"error": f"text: {e}"}
    idx = args.get("layer", -1)
    if idx is not None and idx >= 0 and idx < len(layers):
        try:
            tx.merge_to(layers[idx])
        except Exception:
            layers.append(tx)
    Gimp.displays_flush()
    return {"ok": True}


def cmd_bezier(seq, args):
    global img
    if not img:
        return {"error": "No image"}
    strokes = args.get("strokes", [])
    col = args.get("color", [1.0, 0.2, 0.2])
    sw = args.get("stroke_width", 3.0)
    do_fill = args.get("fill", False)
    fc = args.get("fill_color", col)
    po = _build_path(f"p_{uuid.uuid4().hex[:6]}", strokes)
    vl = Gimp.VectorLayer.new(img, po)
    img.insert_layer(vl, None, -1)
    vl.set_stroke_width(float(sw))
    vl.set_enable_stroke(True)
    vl.set_stroke_color(color(col))
    if do_fill:
        vl.set_fill_color(color(fc))
        vl.set_enable_fill(True)
    return {"ok": True}


def cmd_gradient(seq, args):
    global img
    if not img:
        return {"error": "No image"}
    fg = args.get("fg", [0.0, 0.5, 0.8])
    bg = args.get("bg", [0.08, 0.05, 0.15])
    style = args.get("style", 0)
    gl = Gimp.Layer.new(img, "_grad", img.get_width(), img.get_height(),
                        Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(gl, None, 0)
    Gimp.context_set_foreground(color(fg))
    Gimp.context_set_background(color(bg))
    if style == 1:
        gl.edit_gradient_fill(Gimp.GradientType.RADIAL, 0.0, False, 1.0, 0.0, True)
    else:
        gl.edit_gradient_fill(Gimp.GradientType.LINEAR, 0.0, False, 1.0, 0.0, True)
    return {"ok": True}


def cmd_export(seq, args):
    global img
    if not img:
        return {"error": "No image"}
    path = args.get("path", str(config.OUTPUT_DIR / "output.png"))
    # Defense in depth: the client already validated this against
    # config.OUTPUT_DIR before sending the command, but re-check here.
    resolved = Path(path).resolve()
    if config.OUTPUT_DIR != resolved and config.OUTPUT_DIR not in resolved.parents:
        return {"error": f"Refusing to write outside output dir: {path}"}
    gfile = Gio.File.new_for_path(str(resolved))
    try:
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, gfile, None)
        return {"ok": True, "path": str(resolved), "size_bytes": os.path.getsize(resolved)}
    except Exception as e:
        return {"error": f"save: {e}"}


def cmd_ping(seq, args):
    return {"ok": True, "pong": True, "has_image": img is not None,
            "layers": len(layers), "brushes": len(brushes)}


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
    "done": lambda s, a: {"_signal": "done"},
    "export_done": cmd_export,
    "list_brushes": cmd_list_brushes,
    "new_brush": cmd_new_brush,
    "paint_stroke": cmd_paint_stroke,
    "paint_dab": cmd_paint_dab,
    "drop_brush": cmd_drop_brush,
}


def run():
    """Connect to the MCP server's socket and process commands."""
    if not SOCKET_PATH:
        print("ERROR: CAVE_PAINTER_SOCKET_PATH not set", file=sys.stderr)
        sys.exit(1)

    # Connect to the socket
    if config.USE_TCP_FALLBACK:
        host, port_str = SOCKET_PATH.split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port_str)))
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)

    sock.settimeout(None)  # blocking, no timeout -- wait for commands

    buf = b""
    running = True
    seq = 0

    while running:
        # Read until we have a complete line
        while b"\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                running = False
                break
            buf += chunk
        if not running:
            break

        line, buf = buf.split(b"\n", 1)
        try:
            cmd = json.loads(line.decode("utf-8"))
            seq += 1
            ctype = cmd.get("cmd", "")
            handler = HANDLERS.get(ctype)
            if handler:
                try:
                    result = handler(seq, cmd)
                    if isinstance(result, dict) and result.get("_signal") == "done":
                        send_response(sock, seq, ok=True)
                        running = False
                        continue
                    send_response(sock, seq, **result)
                except Exception as e:
                    send_response(sock, seq, error=f"Handler error: {type(e).__name__}: {e}")
                    traceback.print_exc()
            else:
                send_response(sock, seq, error=f"Unknown cmd: {ctype}")
        except Exception as e:
            print(f"Parse error: {e}", file=sys.stderr)
            send_response(sock, seq, error=f"Parse error: {e}")

    sock.close()
    sys.exit(0)


if __name__ == "__main__":
    run()
