"""GIMP adapter: implements DrawingEngine from the MCP server's own process.

GIMP's Python API only exists inside GIMP's own interpreter, so this adapter
launches a `gimp --batch-interpreter python-fu-eval` subprocess per canvas
(daemon.py runs inside it) and talks to it over a Unix socket (or TCP on
older Windows). The subprocess/IPC management is an implementation detail
of *this* adapter; nothing above the DrawingEngine port needs to know about it.
"""
import json
import os
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path

from cave_painter import config
from cave_painter.adapters.gimp.discovery import discover_gimp_bin
from cave_painter.domain.engine import DrawingEngine
from cave_painter.domain.types import BrushHandle, BrushSpec, CanvasHandle, Color, LayerHandle, PathSegment

_gimp_bin_cache: str | None = None


def _resolve_gimp_bin() -> str:
    global _gimp_bin_cache
    if config.GIMP_BIN:
        return config.GIMP_BIN
    if _gimp_bin_cache is None:
        _gimp_bin_cache = discover_gimp_bin()
    return _gimp_bin_cache


def _segment_to_dict(seg: PathSegment) -> dict:
    kind = seg.kind
    p = seg.points
    if kind == "moveto":
        return {"type": "moveto", "x": p[0], "y": p[1]}
    if kind == "lineto":
        return {"type": "lineto", "x0": p[0], "y0": p[1]}
    if kind == "conicto":
        return {"type": "conicto", "x0": p[0], "y0": p[1], "x1": p[2], "y1": p[3]}
    if kind == "cubicto":
        return {"type": "cubicto", "x0": p[0], "y0": p[1], "x1": p[2], "y1": p[3], "x2": p[4], "y2": p[5]}
    if kind == "close":
        return {"type": "close"}
    raise ValueError(f"Unknown path segment kind: {kind}")


def _brush_to_dict(spec: BrushSpec) -> dict:
    return {k: v for k, v in {
        "brush_name": spec.name, "size": spec.size, "hardness": spec.hardness,
        "aspect_ratio": spec.aspect_ratio, "angle": spec.angle,
        "spacing": spec.spacing, "force": spec.force,
    }.items() if v is not None}


class GimpEngine(DrawingEngine):
    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._layer_counts: dict[str, int] = {}

    # -- session plumbing (Unix socket) --------------------------------

    def _start_session(self, sid: str) -> dict:
        sock_path = config.socket_path_for_session(sid)

        if config.USE_TCP_FALLBACK:
            host, port_str = sock_path.split(":")
            port = int(port_str)
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((host, port))
            server_sock.listen(1)
            server_sock.settimeout(config.GIMP_STARTUP_SECONDS + 5)
        else:
            # Clean up stale socket file
            try:
                os.unlink(sock_path)
            except FileNotFoundError:
                pass
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(sock_path)
            server_sock.listen(1)
            server_sock.settimeout(config.GIMP_STARTUP_SECONDS + 5)

        env = {**os.environ,
               "CAVE_PAINTER_SESSION_ID": sid,
               "CAVE_PAINTER_SOCKET_PATH": sock_path,
               "CAVE_PAINTER_ROOT": str(config.PROJECT_ROOT)}
        if config.GIMP_HOME:
            env["HOME"] = config.GIMP_HOME

        gimp_bin = _resolve_gimp_bin()
        try:
            proc = subprocess.Popen(
                [gimp_bin, "--no-interface", "--batch-interpreter", "python-fu-eval",
                 "-b", f"exec(open({str(config.DAEMON_SCRIPT)!r}).read())"],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            server_sock.close()
            raise RuntimeError(
                f"Couldn't launch GIMP (tried {gimp_bin!r}): {e}. "
                "Set CAVE_PAINTER_GIMP_BIN to the full path of your gimp/gimp-console executable."
            ) from e

        # Accept the daemon's connection (blocks up to startup timeout)
        try:
            conn, _ = server_sock.accept()
        except socket.timeout:
            proc.kill()
            server_sock.close()
            raise RuntimeError(f"GIMP daemon did not connect within {config.GIMP_STARTUP_SECONDS}s")
        finally:
            server_sock.close()  # we only need one connection

        conn.settimeout(config.COMMAND_TIMEOUT_SECONDS)
        info = {"proc": proc, "conn": conn, "sock_path": sock_path}
        self._sessions[sid] = info
        return info

    def _send(self, sid: str, cmd: dict, timeout: float | None = None) -> dict:
        info = self._sessions.get(sid)
        if not info:
            return {"error": f"Session not found: {sid}"}
        conn = info["conn"]
        msg = (json.dumps(cmd) + "\n").encode("utf-8")
        try:
            conn.sendall(msg)
            # Read response (newline-delimited)
            old_timeout = conn.gettimeout()
            if timeout is not None:
                conn.settimeout(timeout)
            buf = b""
            while b"\n" not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    return {"error": "Daemon closed connection"}
                buf += chunk
            if timeout is not None:
                conn.settimeout(old_timeout)
            line, _, _ = buf.partition(b"\n")
            return json.loads(line.decode("utf-8"))
        except socket.timeout:
            return {"error": f"Timeout (cmd={cmd.get('cmd', '?')})"}
        except (ConnectionError, json.JSONDecodeError) as e:
            return {"error": f"Socket error: {e}"}

    def _sid(self, canvas: CanvasHandle) -> str:
        if not canvas.startswith("img_"):
            raise ValueError(f"Invalid canvas handle: {canvas}")
        sid = canvas[4:]
        if sid not in self._sessions:
            raise ValueError(f"Unknown canvas: {canvas}")
        return sid

    def _raise_if_error(self, result: dict) -> dict:
        if "error" in result:
            raise RuntimeError(result["error"])
        return result

    # -- DrawingEngine -------------------------------------------------

    def create_canvas(self, width, height, bg):
        sid = f"cp-{uuid.uuid4().hex[:8]}"
        self._start_session(sid)
        self._layer_counts[sid] = 0
        self._raise_if_error(self._send(sid, {
            "cmd": "create_canvas", "width": width, "height": height, "bg": bg.as_list(),
        }))
        return f"img_{sid}"

    def close(self, canvas):
        sid = self._sid(canvas)
        info = self._sessions.pop(sid, None)
        self._layer_counts.pop(sid, None)
        if info:
            try:
                info["conn"].close()
            except Exception:
                pass
            try:
                info["proc"].terminate()
                info["proc"].wait(timeout=5)
            except Exception:
                info["proc"].kill()

    def new_layer(self, canvas, name):
        sid = self._sid(canvas)
        r = self._raise_if_error(self._send(sid, {"cmd": "new_layer", "name": name}))
        idx = r["layer_index"]
        self._layer_counts[sid] = idx + 1
        return f"layer_{idx}"

    def _layer_index(self, layer: LayerHandle | None) -> int:
        if layer is None:
            return -1
        if not layer.startswith("layer_"):
            raise ValueError(f"Invalid layer handle: {layer}")
        return int(layer.split("_", 1)[1])

    def draw_ellipse(self, canvas, cx, cy, rx, ry, fill, layer=None):
        sid = self._sid(canvas)
        self._raise_if_error(self._send(sid, {
            "cmd": "draw_ellipse", "cx": cx, "cy": cy, "rx": rx, "ry": ry,
            "fill": fill.as_list(), "layer": self._layer_index(layer),
        }))

    def draw_rect(self, canvas, x, y, w, h, fill, layer=None):
        sid = self._sid(canvas)
        self._raise_if_error(self._send(sid, {
            "cmd": "draw_rect", "x": x, "y": y, "w": w, "h": h,
            "fill": fill.as_list(), "layer": self._layer_index(layer),
        }))

    def draw_path(self, canvas, segments, stroke_color, stroke_width, fill_color, layer=None):
        sid = self._sid(canvas)
        self._raise_if_error(self._send(sid, {
            "cmd": "draw_bezier",
            "strokes": [_segment_to_dict(s) for s in segments],
            "color": (stroke_color or Color(0, 0, 0)).as_list(),
            "stroke_width": stroke_width,
            "fill": fill_color is not None,
            "fill_color": (fill_color or Color(0, 0, 0)).as_list(),
        }))

    def draw_gradient(self, canvas, fg, bg, style="linear", layer=None):
        sid = self._sid(canvas)
        self._raise_if_error(self._send(sid, {
            "cmd": "draw_gradient", "fg": fg.as_list(), "bg": bg.as_list(),
            "style": 1 if style == "radial" else 0,
        }))

    def add_text(self, canvas, text, x, y, size, color, font=None, layer=None):
        sid = self._sid(canvas)
        self._raise_if_error(self._send(sid, {
            "cmd": "add_text", "text": text, "x": x, "y": y, "size": size,
            "color": color.as_list(), "font": font or "", "layer": self._layer_index(layer),
        }))

    def list_brushes(self, canvas):
        sid = self._sid(canvas)
        r = self._raise_if_error(self._send(sid, {"cmd": "list_brushes"}))
        return r["brushes"]

    def register_brush(self, canvas, spec):
        sid = self._sid(canvas)
        r = self._raise_if_error(self._send(sid, {"cmd": "new_brush", **_brush_to_dict(spec)}))
        return r["handle"]

    def release_brush(self, canvas, brush):
        sid = self._sid(canvas)
        self._raise_if_error(self._send(sid, {"cmd": "drop_brush", "brush": brush}))

    def paint_stroke(self, canvas, brush, segments, color, layer=None):
        sid = self._sid(canvas)
        self._raise_if_error(self._send(sid, {
            "cmd": "paint_stroke", "brush": brush,
            "strokes": [_segment_to_dict(s) for s in segments],
            "color": color.as_list(), "layer": self._layer_index(layer),
        }))

    def paint_dab(self, canvas, brush, x, y, color, size=None):
        sid = self._sid(canvas)
        cmd = {"cmd": "paint_dab", "brush": brush, "x": x, "y": y, "color": color.as_list()}
        if size is not None:
            cmd["size"] = size
        self._raise_if_error(self._send(sid, cmd))

    def export(self, canvas, filename):
        sid = self._sid(canvas)
        resolved = config.resolve_output_path(filename)
        r = self._raise_if_error(self._send(sid, {"cmd": "export", "path": str(resolved)}))
        return r["size_bytes"]
