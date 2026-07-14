"""Cave Painter MCP Server — Persistent GIMP daemon process.
 
MCP tool registry. Manages GIMP subprocesses per session.
Communicates via file protocol (JSOn commands/results).
 
Tools: create_canvas, new_layer, add_text, draw_ellipse, draw_rect,
       draw_bezier, draw_gradient, export, export_done, done, status,
       list_brushes, new_brush, paint_stroke, paint_dab, drop_brush
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

DAEMON = Path("/home/ekl/Documents/Programming/cave-painter/src/cave_painter_daemon.py")
DAEMON_BASE = Path("/tmp/gopher-daemon")
os.makedirs(DAEMON_BASE, exist_ok=True)

_sessions: dict[str, dict] = {}

def _start_gimp(sid):
    sdir = DAEMON_BASE / sid
    cmd_dir = sdir / "commands"
    res_dir = sdir / "results"
    os.makedirs(cmd_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)
    proc = subprocess.Popen(
        ["gimp", "--no-interface", "--batch-interpreter", "python-fu-eval",
         "-b", f"exec(open('{DAEMON}').read())"],
        env={**os.environ, "GDB_SESSION_ID": sid, "HOME": "/home/ekl",
             "GIMP2_DIRECTORY": "/home/ekl/.config/GIMP/3.0"},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    info = {"session_id": sid, "proc": proc, "pid": proc.pid,
            "cmd_dir": cmd_dir, "res_dir": res_dir, "seq": 0}
    _sessions[sid] = info
    time.sleep(2.5)
    return info

def _send_cmd(sid, cmd, timeout=30):
    info = _sessions.get(sid)
    if not info: return {"error": f"Session not found: {sid}"}
    info["seq"] += 1
    seq = info["seq"]
    cmd_path = info["cmd_dir"] / f"{seq:04d}_{cmd['cmd']}.json"
    with open(cmd_path, "w") as f: json.dump(cmd, f)
    result_path = info["res_dir"] / f"{seq:04d}_result.json"
    start = time.time()
    while time.time() - start < timeout:
        if result_path.exists():
            with open(result_path) as f: return json.load(f)
        time.sleep(0.05)
    return {"error": f"Timeout (seq={seq}, cmd={cmd['cmd']})"}

def _cleanup(sid):
    info = _sessions.pop(sid, None)
    if info:
        try: info["proc"].terminate(); info["proc"].wait(timeout=5)
        except: info["proc"].kill()

def _sid(handle):
    if isinstance(handle, str) and handle.startswith("img_"):
        s = handle[4:]
        if s in _sessions: return s
    return None

# ── Tool implementations ───────────────────────────────────────────────

def tool_create_canvas(**kw):
    sid = f"cp-{uuid.uuid4().hex[:8]}"
    _start_gimp(sid)
    r = _send_cmd(sid, {"cmd":"create_canvas","width":kw.get("width",800),"height":kw.get("height",600),
                         "bg":[kw.get("bg_r",0.05),kw.get("bg_g",0.1),kw.get("bg_b",0.2)]})
    if r.get("ok"): r["handle"] = f"img_{sid}"
    return r

def tool_new_layer(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Invalid handle"} if not s else
        _send_cmd(s, {"cmd":"new_layer","name":kw.get("name","Layer")}))

def tool_add_text(**kw):
    s = _sid(kw.get("target","") or kw.get("image","")); return ({"error":"Invalid handle"} if not s else
        _send_cmd(s, {"cmd":"add_text","text":kw["text"],"x":kw.get("x",60),"y":kw.get("y",160),
                       "size":kw.get("size",20),"color":[kw.get("r",1),kw.get("g",1),kw.get("b",1)],
                       "layer":kw.get("layer",-1)}))

def tool_draw_ellipse(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Invalid handle"} if not s else
        _send_cmd(s, {"cmd":"draw_ellipse","cx":kw["cx"],"cy":kw["cy"],"rx":kw["rx"],"ry":kw["ry"],
                       "fill":[kw.get("fill_r",0.78),kw.get("fill_g",0.52),kw.get("fill_b",0.29)],
                       "layer":kw.get("layer",-1)}))

def tool_draw_rect(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Invalid handle"} if not s else
        _send_cmd(s, {"cmd":"draw_rect","x":kw["x"],"y":kw["y"],"w":kw["w"],"h":kw["h"],
                       "fill":[kw.get("fill_r",0.5),kw.get("fill_g",0.5),kw.get("fill_b",0.5)],
                       "layer":kw.get("layer",-1)}))

def tool_export(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Invalid handle"} if not s else
        _send_cmd(s, {"cmd":"export","path":str(Path("/home/ekl/Documents/Programming/cave-painter/tests/output") / kw.get("path","export.png"))}))

def tool_export_done(**kw):
    s = _sid(kw.get("image",""))
    if not s: return {"error":"Invalid handle"}
    r = _send_cmd(s, {"cmd":"export","path":str(Path("/home/ekl/Documents/Programming/cave-painter/tests/output") / kw.get("path","export.png"))})
    _cleanup(s); r["released"] = True; return r

def tool_done(**kw):
    s = _sid(kw.get("image",""))
    if not s: return {"error":"Invalid handle"}
    _cleanup(s); return {"ok":True,"released":True}

def tool_status(**kw):
    version = "unknown"
    try:
        for line in open(DAEMON):
            if line.startswith("VERSION"):
                version = line.split('"')[1]
                break
    except: pass
    return {"ok":True,"sessions":len(_sessions),"handles":[f"img_{s}" for s in _sessions],"version":version}

def tool_list_brushes(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Need image"} if not s else _send_cmd(s, {"cmd":"list_brushes"}))

def tool_new_brush(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Need image"} if not s else
        _send_cmd(s, {k:v for k,v in {"cmd":"new_brush","brush_name":kw.get("brush_name"),
            "size":kw.get("size"),"hardness":kw.get("hardness"),"aspect_ratio":kw.get("aspect_ratio"),
            "angle":kw.get("angle"),"spacing":kw.get("spacing"),"force":kw.get("force")}.items() if v is not None}))

def tool_paint_stroke(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Invalid handle"} if not s else
        _send_cmd(s, {"cmd":"paint_stroke","brush":kw["brush"],"strokes":kw["strokes"],
                       "color":[kw.get("color_r",0),kw.get("color_g",0),kw.get("color_b",0)],
                       "layer":kw.get("layer",-1)}))

def tool_paint_dab(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Invalid handle"} if not s else
        _send_cmd(s, {k:v for k,v in {"cmd":"paint_dab","brush":kw["brush"],"x":kw["x"],"y":kw["y"],
            "color":[kw.get("color_r",0),kw.get("color_g",0),kw.get("color_b",0)],
            "size":kw.get("size")}.items() if v is not None}))

def tool_drop_brush(**kw):
    s = _sid(kw.get("image","")); return ({"error":"Need image"} if not s else
        _send_cmd(s, {"cmd":"drop_brush","brush":kw["brush"]}))

# ── MCP server ─────────────────────────────────────────────────────────

app = Server("cave-painter")

@app.list_tools()
async def list_tools():
    return [
        Tool(name="create_canvas",description="Create blank canvas. Returns handle like img_abc123.",
             inputSchema={"type":"object","properties":{"width":{"type":"integer","default":800},"height":{"type":"integer","default":600},"bg_r":{"type":"number","default":0.05},"bg_g":{"type":"number","default":0.1},"bg_b":{"type":"number","default":0.2}}}),
        Tool(name="new_layer",description="Create transparent layer on image.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"name":{"type":"string","default":"Layer"}},"required":["image"]}),
        Tool(name="add_text",description="Add text to image or layer.",
             inputSchema={"type":"object","properties":{"target":{"type":"string"},"text":{"type":"string"},"x":{"type":"integer","default":60},"y":{"type":"integer","default":160},"size":{"type":"integer","default":20},"r":{"type":"number","default":1},"g":{"type":"number","default":1},"b":{"type":"number","default":1}},"required":["target","text"]}),
        Tool(name="draw_ellipse",description="Draw filled ellipse on image.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"cx":{"type":"number"},"cy":{"type":"number"},"rx":{"type":"number"},"ry":{"type":"number"},"fill_r":{"type":"number","default":0.78},"fill_g":{"type":"number","default":0.52},"fill_b":{"type":"number","default":0.29}},"required":["image","cx","cy","rx","ry"]}),
        Tool(name="draw_rect",description="Draw filled rectangle on image.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"x":{"type":"number"},"y":{"type":"number"},"w":{"type":"number"},"h":{"type":"number"},"fill_r":{"type":"number","default":0.5},"fill_g":{"type":"number","default":0.5},"fill_b":{"type":"number","default":0.5}},"required":["image","x","y","w","h"]}),
        Tool(name="export",description="Save PNG (keeps GIMP alive).",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"path":{"type":"string","default":"export.png"}},"required":["image"]}),
        Tool(name="export_done",description="Save PNG and release GIMP.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"path":{"type":"string","default":"export.png"}},"required":["image"]}),
        Tool(name="done",description="Release GIMP without saving.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"}},"required":["image"]}),
        Tool(name="status",description="Show active sessions.",
             inputSchema={"type":"object","properties":{}}),
        Tool(name="list_brushes",description="List 58 available GIMP brushes.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"}},"required":["image"]}),
        Tool(name="new_brush",description="Create brush preset. Returns brush_0001. Pass to paint_stroke/dab.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"brush_name":{"type":"string","default":"2. Hardness 100"},"size":{"type":"number"},"hardness":{"type":"number","description":"0.0-1.0"},"aspect_ratio":{"type":"number"},"angle":{"type":"number"},"spacing":{"type":"number"},"force":{"type":"number","description":"0.0-1.0"}},"required":["image"]}),
        Tool(name="paint_stroke",description="Paint a path with a brush. Same stroke format as draw_bezier.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"brush":{"type":"string"},"strokes":{"type":"array","items":{"type":"object"}},"color_r":{"type":"number","default":0},"color_g":{"type":"number","default":0},"color_b":{"type":"number","default":0}},"required":["image","brush","strokes"]}),
        Tool(name="paint_dab",description="Single brush dab at (x,y).",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"brush":{"type":"string"},"x":{"type":"number"},"y":{"type":"number"},"color_r":{"type":"number","default":0},"color_g":{"type":"number","default":0},"color_b":{"type":"number","default":0},"size":{"type":"number"}},"required":["image","brush","x","y"]}),
        Tool(name="drop_brush",description="Release brush preset.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"brush":{"type":"string"}},"required":["image","brush"]}),
    ]

HANDLERS = {
    "create_canvas": tool_create_canvas, "new_layer": tool_new_layer,
    "add_text": tool_add_text, "draw_ellipse": tool_draw_ellipse,
    "draw_rect": tool_draw_rect, "export": tool_export,
    "export_done": tool_export_done, "done": tool_done, "status": tool_status,
    "list_brushes": tool_list_brushes, "new_brush": tool_new_brush,
    "paint_stroke": tool_paint_stroke, "paint_dab": tool_paint_dab,
    "drop_brush": tool_drop_brush,
}

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    fn = HANDLERS.get(name)
    if not fn: result = {"error": f"Unknown tool: {name}"}
    else:
        try: result = fn(**arguments)
        except Exception as e: result = {"error": f"{type(e).__name__}: {e}"}
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    async with stdio_server() as (rs, ws):
        await app.run(rs, ws, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
