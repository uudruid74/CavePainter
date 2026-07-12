"""Cave Painter MCP Server v4 — Persistent GIMP daemon process.
 
Architecture:
  MCP server manages GIMP subprocess per session.
  Commands go via file protocol (JSON to {session}/commands/).
  Results come back via {session}/results/.
  GIMP process stays alive between commands.
 
Tool calls:
  create_canvas(w, h, bg)        -> img_01
  new_layer(img_01, name)         -> ly_02
  add_text(img_01, text, x, y)   -> ok
  draw_ellipse(img_01, cx, cy, rx, ry, fill)
  draw_rect(img_01, x, y, w, h, fill)
  draw_bezier(img_01, strokes, color, stroke_width, fill)
  draw_gradient(img_01, fg, bg, style)
  export(img_01, path)            -> releases handle
  export_done(img_01, path)       -> releases + exits GIMP
  done(img_01)                    -> exits GIMP without saving
"""
import asyncio
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ── Config ─────────────────────────────────────────────────────────────
DAEMON = Path("/home/ekl/Documents/Programming/cave-painter/src/cave_painter_daemon.py")
ENGINE = Path("/home/ekl/Documents/Programming/cave-painter/src/engine.py")
DAEMON_BASE = Path("/tmp/gopher-daemon")
os.makedirs(DAEMON_BASE, exist_ok=True)

# ── Session manager ────────────────────────────────────────────────────
# Each session = one GIMP subprocess + one command/result directory
_sessions: dict[str, dict] = {}
_next_handle = [0]

def _new_handle():
    _next_handle[0] += 1
    return _next_handle[0]

def _start_gimp(session_id: str) -> dict:
    """Start a GIMP daemon for a session. Returns session info."""
    sdir = DAEMON_BASE / session_id
    cmd_dir = sdir / "commands"
    res_dir = sdir / "results"
    os.makedirs(cmd_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)
    
    proc = subprocess.Popen(
        ["gimp", "--no-interface", "--batch-interpreter", "python-fu-eval",
         "-b", f"exec(open('{DAEMON}').read())"],
        env={**os.environ, "GDB_SESSION_ID": session_id, "HOME": "/home/ekl",
        "GIMP2_DIRECTORY": "/home/ekl/.config/GIMP/3.0"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    info = {
        "session_id": session_id,
        "proc": proc,
        "pid": proc.pid,
        "cmd_dir": cmd_dir,
        "res_dir": res_dir,
        "handle": _new_handle(),
        "seq": 0,
    }
    _sessions[session_id] = info
    time.sleep(2.5)  # wait for GIMP to initialize
    return info

def _send_cmd(session_id: str, cmd: dict, timeout: float = 30.0) -> dict:
    """Write a command, wait for result, return it."""
    info = _sessions.get(session_id)
    if not info:
        return {"error": f"Session not found: {session_id}"}
    
    info["seq"] += 1
    seq = info["seq"]
    cmd_name = f"{seq:04d}_{cmd['cmd']}.json"
    cmd_path = info["cmd_dir"] / cmd_name
    
    with open(cmd_path, "w") as f:
        json.dump(cmd, f)
    
    # Wait for result file
    result_path = info["res_dir"] / f"{seq:04d}_result.json"
    start = time.time()
    while time.time() - start < timeout:
        if result_path.exists():
            with open(result_path) as f:
                return json.load(f)
        time.sleep(0.05)
    
    return {"error": f"Timeout waiting for result (seq={seq}, cmd={cmd['cmd']})"}

def _cleanup(session_id: str):
    """Terminate GIMP and clean up session."""
    info = _sessions.pop(session_id, None)
    if info:
        try:
            info["proc"].terminate()
            info["proc"].wait(timeout=5)
        except:
            info["proc"].kill()

# ── Tool implementations ───────────────────────────────────────────────

def tool_create_canvas(**kw):
    sid = f"cp-{uuid.uuid4().hex[:8]}"
    info = _start_gimp(sid)
    cmd = {"cmd": "create_canvas", "width": kw.get("width", 800), "height": kw.get("height", 600),
           "bg": [kw.get("bg_r", 0.05), kw.get("bg_g", 0.1), kw.get("bg_b", 0.2)]}
    result = _send_cmd(sid, cmd)
    if result.get("ok"):
        result["handle"] = f"img_{sid}"
    return result

def tool_load_image(**kw):
    # Use PIL to read image info, create GIMP canvas with matching size
    from PIL import Image as PILImg
    path = kw["path"]
    try:
        pil = PILImg.open(path)
        w, h = pil.size
    except Exception as e:
        return {"error": f"Cannot open image: {e}"}
    
    sid = f"cp-{uuid.uuid4().hex[:8]}"
    info = _start_gimp(sid)
    cmd = {"cmd": "create_canvas", "width": w, "height": h, "bg": [0.0, 0.0, 0.0]}
    result = _send_cmd(sid, cmd)
    if result.get("ok"):
        result["handle"] = f"img_{sid}"
        result["width"] = w
        result["height"] = h
    return result

def _assert_session(args):
    """Extract session ID from handle like 'img_abc123'"""
    handle = args.get("image") or args.get("target") or ""
    if handle.startswith("img_"):
        sid = handle[4:]
        if sid in _sessions:
            return sid
    return None

def tool_new_layer(**kw):
    sid = _assert_session(kw)
    if not sid:
        return {"error": "Invalid or missing image handle. Use the handle returned by create_canvas."}
    return _send_cmd(sid, {"cmd": "new_layer", "name": kw.get("name", "Layer")})

def tool_add_text(**kw):
    sid = _assert_session(kw)
    if not sid:
        return {"error": "Invalid or missing image/target handle"}
    return _send_cmd(sid, {
        "cmd": "add_text", "text": kw["text"],
        "x": kw.get("x", 60), "y": kw.get("y", 160),
        "size": kw.get("size", 20),
        "color": [kw.get("r", 1.0), kw.get("g", 1.0), kw.get("b", 1.0)],
        "layer": kw.get("layer", -1)
    })

def tool_draw_ellipse(**kw):
    sid = _assert_session(kw)
    if not sid:
        return {"error": "Invalid or missing image handle"}
    return _send_cmd(sid, {
        "cmd": "draw_ellipse", "cx": kw["cx"], "cy": kw["cy"],
        "rx": kw["rx"], "ry": kw["ry"],
        "fill": [kw.get("fill_r", 0.78), kw.get("fill_g", 0.52), kw.get("fill_b", 0.29)],
        "layer": kw.get("layer", -1)
    })

def tool_draw_rect(**kw):
    sid = _assert_session(kw)
    if not sid:
        return {"error": "Invalid or missing image handle"}
    return _send_cmd(sid, {
        "cmd": "draw_rect", "x": kw["x"], "y": kw["y"],
        "w": kw["w"], "h": kw["h"],
        "fill": [kw.get("fill_r", 0.5), kw.get("fill_g", 0.5), kw.get("fill_b", 0.5)],
        "layer": kw.get("layer", -1)
    })

def tool_export(**kw):
    sid = _assert_session(kw)
    if not sid:
        return {"error": "Invalid or missing image handle"}
    path = kw.get("path", f"export_{sid}.png")
    abs_path = str(Path("/home/ekl/Documents/Programming/cave-painter/tests/output") / path)
    return _send_cmd(sid, {"cmd": "export", "path": abs_path})

def tool_export_done(**kw):
    """Export and release the GIMP process."""
    sid = _assert_session(kw)
    if not sid:
        return {"error": "Invalid or missing image handle"}
    path = kw.get("path", f"export_{sid}.png")
    abs_path = str(Path("/home/ekl/Documents/Programming/cave-painter/tests/output") / path)
    result = _send_cmd(sid, {"cmd": "export", "path": abs_path})
    _cleanup(sid)
    result["released"] = True
    return result

def tool_done(**kw):
    """Release the GIMP process without saving."""
    sid = _assert_session(kw)
    if not sid:
        return {"error": "Invalid or missing image handle"}
    _cleanup(sid)
    return {"ok": True, "released": True}

def tool_status(**kw):
    return {"ok": True, "sessions": len(_sessions),
            "handles": [f"img_{s}" for s in _sessions.keys()]}

# ── MCP Server ─────────────────────────────────────────────────────────

app = Server("cave-painter-v4")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="create_canvas",
             description="Create a new blank canvas. Returns handle like 'img_abc123'. Use this handle in all subsequent calls.",
             inputSchema={"type":"object","properties":{
                 "width":{"type":"integer","default":800},
                 "height":{"type":"integer","default":600},
                 "bg_r":{"type":"number","default":0.05},
                 "bg_g":{"type":"number","default":0.1},
                 "bg_b":{"type":"number","default":0.2}
             }}),
        Tool(name="new_layer",
             description="Create a new transparent layer on an existing image.",
             inputSchema={"type":"object","properties":{
                 "image":{"type":"string","description":"Image handle from create_canvas"},
                 "name":{"type":"string","default":"Layer"},
             },"required":["image"]}),
        Tool(name="add_text",
             description="Add text to an image.",
             inputSchema={"type":"object","properties":{
                 "target":{"type":"string","description":"Image handle"},
                 "text":{"type":"string"},
                 "x":{"type":"integer","default":60},
                 "y":{"type":"integer","default":160},
                 "size":{"type":"integer","default":20},
                 "r":{"type":"number","default":1.0},
                 "g":{"type":"number","default":1.0},
                 "b":{"type":"number","default":1.0},
             },"required":["target","text"]}),
        Tool(name="draw_ellipse",
             description="Draw a filled ellipse on an image.",
             inputSchema={"type":"object","properties":{
                 "image":{"type":"string"},"cx":{"type":"number"},"cy":{"type":"number"},
                 "rx":{"type":"number"},"ry":{"type":"number"},
                 "fill_r":{"type":"number","default":0.78},
                 "fill_g":{"type":"number","default":0.52},
                 "fill_b":{"type":"number","default":0.29},
             },"required":["image","cx","cy","rx","ry"]}),
        Tool(name="draw_rect",
             description="Draw a filled rectangle on an image.",
             inputSchema={"type":"object","properties":{
                 "image":{"type":"string"},"x":{"type":"number"},"y":{"type":"number"},
                 "w":{"type":"number"},"h":{"type":"number"},
                 "fill_r":{"type":"number","default":0.5},
                 "fill_g":{"type":"number","default":0.5},
                 "fill_b":{"type":"number","default":0.5},
             },"required":["image","x","y","w","h"]}),
        Tool(name="export",
             description="Export image to PNG. Image handle stays valid for more edits.",
             inputSchema={"type":"object","properties":{
                 "image":{"type":"string"},"path":{"type":"string","default":"export.png"},
             },"required":["image"]}),
        Tool(name="export_done",
             description="Export image and release the GIMP process. Image handle becomes invalid.",
             inputSchema={"type":"object","properties":{
                 "image":{"type":"string"},"path":{"type":"string","default":"export.png"},
             },"required":["image"]}),
        Tool(name="done",
             description="Release the GIMP process WITHOUT saving. Image handle becomes invalid.",
             inputSchema={"type":"object","properties":{
                 "image":{"type":"string"}
             },"required":["image"]}),
        Tool(name="status",
             description="Show active image sessions.",
             inputSchema={"type":"object","properties":{}}),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "create_canvas": tool_create_canvas,
        "new_layer": tool_new_layer,
        "add_text": tool_add_text,
        "draw_ellipse": tool_draw_ellipse,
        "draw_rect": tool_draw_rect,
        "export": tool_export,
        "export_done": tool_export_done,
        "done": tool_done,
        "status": tool_status,
    }
    fn = handlers.get(name)
    if not fn:
        result = {"error": f"Unknown tool: {name}"}
    else:
        try:
            result = fn(**arguments)
        except Exception as e:
            result = {"error": f"{type(e).__name__}: {e}"}
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
