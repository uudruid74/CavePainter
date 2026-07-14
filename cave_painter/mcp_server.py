"""Cave Painter MCP server — tool registry.
Depends only on cave_painter.domain.engine.DrawingEngine.
GIMP-specific process/IPC management lives entirely in adapters/gimp/client.py.
"""
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from cave_painter.domain.engine import DrawingEngine
from cave_painter.domain.types import BrushSpec, Color, PathSegment


def engine_factory() -> DrawingEngine:
    from cave_painter.adapters.gimp.client import GimpEngine
    return GimpEngine()

ENGINE: DrawingEngine = engine_factory()


def _segments_from_json(raw: list[dict]) -> list[PathSegment]:
    out = []
    for s in raw:
        kind = s["type"]
        if kind == "moveto":
            pts = (s["x"], s["y"])
        elif kind == "lineto":
            pts = (s["x0"], s["y0"])
        elif kind == "conicto":
            pts = (s["x0"], s["y0"], s["x1"], s["y1"])
        elif kind == "cubicto":
            pts = (s["x0"], s["y0"], s["x1"], s["y1"], s["x2"], s["y2"])
        elif kind == "close":
            pts = ()
        else:
            raise ValueError(f"Unknown stroke type: {kind}")
        out.append(PathSegment(kind=kind, points=pts))
    return out


# -- Tool implementations ------------------------------------------------

def tool_create_canvas(**kw):
    handle = ENGINE.create_canvas(
        width=kw.get("width", 800), height=kw.get("height", 600),
        bg=Color(kw.get("bg_r", 0.05), kw.get("bg_g", 0.1), kw.get("bg_b", 0.2)),
    )
    return {"ok": True, "handle": handle}

def tool_new_layer(**kw):
    handle = ENGINE.new_layer(kw["image"], kw.get("name", "Layer"))
    return {"ok": True, "handle": handle}

def tool_add_text(**kw):
    ENGINE.add_text(
        kw.get("target") or kw["image"], kw["text"], kw.get("x", 60), kw.get("y", 160),
        kw.get("size", 20), Color(kw.get("r", 1), kw.get("g", 1), kw.get("b", 1)),
        font=kw.get("font"),
    )
    return {"ok": True}

def tool_draw_ellipse(**kw):
    ENGINE.draw_ellipse(
        kw["image"], kw["cx"], kw["cy"], kw["rx"], kw["ry"],
        Color(kw.get("fill_r", 0.78), kw.get("fill_g", 0.52), kw.get("fill_b", 0.29)),
    )
    return {"ok": True}

def tool_draw_rect(**kw):
    ENGINE.draw_rect(
        kw["image"], kw["x"], kw["y"], kw["w"], kw["h"],
        Color(kw.get("fill_r", 0.5), kw.get("fill_g", 0.5), kw.get("fill_b", 0.5)),
    )
    return {"ok": True}

def tool_draw_bezier(**kw):
    fill_color = None
    if kw.get("fill"):
        fc = kw.get("fill_color", [kw.get("r", 1.0), kw.get("g", 0.2), kw.get("b", 0.2)])
        fill_color = Color(*fc)
    stroke_color = Color(kw.get("r", 1.0), kw.get("g", 0.2), kw.get("b", 0.2))
    ENGINE.draw_path(
        kw["image"], _segments_from_json(kw["strokes"]), stroke_color,
        kw.get("stroke_width", 3.0), fill_color,
    )
    return {"ok": True}

def tool_draw_gradient(**kw):
    ENGINE.draw_gradient(
        kw["image"], Color(*kw.get("fg", [0.0, 0.5, 0.8])),
        Color(*kw.get("bg", [0.08, 0.05, 0.15])),
        "radial" if kw.get("style", 0) == 1 else "linear",
    )
    return {"ok": True}

def tool_export(**kw):
    size = ENGINE.export(kw["image"], kw.get("path", "export.png"))
    return {"ok": True, "size_bytes": size}

def tool_export_done(**kw):
    size = ENGINE.export(kw["image"], kw.get("path", "export.png"))
    ENGINE.close(kw["image"])
    return {"ok": True, "size_bytes": size, "released": True}

def tool_done(**kw):
    ENGINE.close(kw["image"])
    return {"ok": True, "released": True}

def tool_status(**kw):
    sessions = getattr(ENGINE, "_sessions", {})
    return {"ok": True, "sessions": len(sessions), "handles": [f"img_{s}" for s in sessions]}

def tool_list_brushes(**kw):
    return {"ok": True, "brushes": ENGINE.list_brushes(kw["image"])}

def tool_new_brush(**kw):
    spec = BrushSpec(
        name=kw.get("brush_name", "2. Hardness 100"), size=kw.get("size"),
        hardness=kw.get("hardness"), aspect_ratio=kw.get("aspect_ratio"),
        angle=kw.get("angle"), spacing=kw.get("spacing"), force=kw.get("force"),
    )
    handle = ENGINE.register_brush(kw["image"], spec)
    return {"ok": True, "handle": handle}

def tool_paint_stroke(**kw):
    color = Color(kw.get("color_r", 0), kw.get("color_g", 0), kw.get("color_b", 0))
    ENGINE.paint_stroke(kw["image"], kw["brush"], _segments_from_json(kw["strokes"]), color)
    return {"ok": True}

def tool_paint_dab(**kw):
    color = Color(kw.get("color_r", 0), kw.get("color_g", 0), kw.get("color_b", 0))
    ENGINE.paint_dab(kw["image"], kw["brush"], kw["x"], kw["y"], color, size=kw.get("size"))
    return {"ok": True}

def tool_drop_brush(**kw):
    ENGINE.release_brush(kw["image"], kw["brush"])
    return {"ok": True, "released": kw["brush"]}


# -- MCP server ----------------------------------------------------------

app = Server("cave-painter")

@app.list_tools()
async def list_tools():
    return [
        Tool(name="create_canvas", description="Create blank canvas. Returns handle like img_abc123.",
             inputSchema={"type":"object","properties":{"width":{"type":"integer","default":800},"height":{"type":"integer","default":600},"bg_r":{"type":"number","default":0.05},"bg_g":{"type":"number","default":0.1},"bg_b":{"type":"number","default":0.2}}}),
        Tool(name="new_layer", description="Create transparent layer on image.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"name":{"type":"string","default":"Layer"}},"required":["image"]}),
        Tool(name="add_text", description="Add text to image or layer.",
             inputSchema={"type":"object","properties":{"target":{"type":"string"},"image":{"type":"string"},"text":{"type":"string"},"x":{"type":"integer","default":60},"y":{"type":"integer","default":160},"size":{"type":"integer","default":20},"r":{"type":"number","default":1},"g":{"type":"number","default":1},"b":{"type":"number","default":1},"font":{"type":"string"}},"required":["text"]}),
        Tool(name="draw_ellipse", description="Draw filled ellipse on image.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"cx":{"type":"number"},"cy":{"type":"number"},"rx":{"type":"number"},"ry":{"type":"number"},"fill_r":{"type":"number","default":0.78},"fill_g":{"type":"number","default":0.52},"fill_b":{"type":"number","default":0.29}},"required":["image","cx","cy","rx","ry"]}),
        Tool(name="draw_rect", description="Draw filled rectangle on image.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"x":{"type":"number"},"y":{"type":"number"},"w":{"type":"number"},"h":{"type":"number"},"fill_r":{"type":"number","default":0.5},"fill_g":{"type":"number","default":0.5},"fill_b":{"type":"number","default":0.5}},"required":["image","x","y","w","h"]}),
        Tool(name="draw_bezier", description="Draw/stroke a bezier vector path, optionally filled.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"strokes":{"type":"array","items":{"type":"object"}},"r":{"type":"number","default":1.0},"g":{"type":"number","default":0.2},"b":{"type":"number","default":0.2},"stroke_width":{"type":"number","default":3.0},"fill":{"type":"boolean","default":False},"fill_color":{"type":"array","items":{"type":"number"}}},"required":["image","strokes"]}),
        Tool(name="draw_gradient", description="Fill a new layer with a linear or radial gradient.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"fg":{"type":"array","items":{"type":"number"}},"bg":{"type":"array","items":{"type":"number"}},"style":{"type":"integer","default":0,"description":"0=linear, 1=radial"}},"required":["image"]}),
        Tool(name="export", description="Save PNG (keeps GIMP alive).",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"path":{"type":"string","default":"export.png"}},"required":["image"]}),
        Tool(name="export_done", description="Save PNG and release GIMP.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"path":{"type":"string","default":"export.png"}},"required":["image"]}),
        Tool(name="done", description="Release GIMP without saving.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"}},"required":["image"]}),
        Tool(name="status", description="Show active sessions.",
             inputSchema={"type":"object","properties":{}}),
        Tool(name="list_brushes", description="List available GIMP brushes.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"}},"required":["image"]}),
        Tool(name="new_brush", description="Create brush preset. Returns brush_0001.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"brush_name":{"type":"string","default":"2. Hardness 100"},"size":{"type":"number"},"hardness":{"type":"number"},"aspect_ratio":{"type":"number"},"angle":{"type":"number"},"spacing":{"type":"number"},"force":{"type":"number"}},"required":["image"]}),
        Tool(name="paint_stroke", description="Paint a path with a brush.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"brush":{"type":"string"},"strokes":{"type":"array","items":{"type":"object"}},"color_r":{"type":"number","default":0},"color_g":{"type":"number","default":0},"color_b":{"type":"number","default":0}},"required":["image","brush","strokes"]}),
        Tool(name="paint_dab", description="Single brush dab at (x,y).",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"brush":{"type":"string"},"x":{"type":"number"},"y":{"type":"number"},"color_r":{"type":"number","default":0},"color_g":{"type":"number","default":0},"color_b":{"type":"number","default":0},"size":{"type":"number"}},"required":["image","brush","x","y"]}),
        Tool(name="drop_brush", description="Release brush preset.",
             inputSchema={"type":"object","properties":{"image":{"type":"string"},"brush":{"type":"string"}},"required":["image","brush"]}),
    ]

HANDLERS = {
    "create_canvas": tool_create_canvas, "new_layer": tool_new_layer,
    "add_text": tool_add_text, "draw_ellipse": tool_draw_ellipse,
    "draw_rect": tool_draw_rect, "draw_bezier": tool_draw_bezier,
    "draw_gradient": tool_draw_gradient, "export": tool_export,
    "export_done": tool_export_done, "done": tool_done, "status": tool_status,
    "list_brushes": tool_list_brushes, "new_brush": tool_new_brush,
    "paint_stroke": tool_paint_stroke, "paint_dab": tool_paint_dab,
    "drop_brush": tool_drop_brush,
}

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    fn = HANDLERS.get(name)
    if not fn:
        result = {"error": f"Unknown tool: {name}"}
    else:
        try:
            result = fn(**arguments)
        except Exception as e:
            result = {"error": f"{type(e).__name__}: {e}"}
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    async with stdio_server() as (rs, ws):
        await app.run(rs, ws, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
