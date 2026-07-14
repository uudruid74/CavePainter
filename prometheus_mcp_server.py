#!/usr/bin/env python3
"""
Cave Painter MCP Server — Prometheus session management.

Tools:
  prometheus_request_session  — Create a Unix socket for a new capture session
  prometheus_get_handoff      — Poll the session's socket buffer for new data
  prometheus_close_session    — Close session, minimize GIMP

Socket format: /tmp/prometheus/<session_id>.sock
Messages: JSON line-delimited via SOCK_STREAM connections.
"""
import asyncio, json, os, time, uuid, logging, subprocess, sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cave-painter")
logger = logging.getLogger("cave-painter-mcp")

HANDOFF_DIR = "/tmp/prometheus"
SOCKET_SUFFIX = ".sock"
os.makedirs(HANDOFF_DIR, exist_ok=True)

# ── Session registry ──────────────────────────────────────────────────────
# {session_id: {"socket_path": str, "buffer": asyncio.Queue, "done": bool,
#               "clients": set[StreamWriter]}}
# clients tracks all connected writers — data received from any client
# is forwarded to all others (enabling gateway push via watch_unix_socket).
_sessions: dict[str, dict] = {}


async def _socket_server(session_id: str):
    """Background task: accept connections on the session's Unix socket.

    Each connection delivers one JSON object (the handoff payload).
    Multiple connections are allowed (one per snapshot). Data is pushed
    onto an asyncio.Queue so the polling tool can read it FIFO.
    """
    info = _sessions.get(session_id)
    if not info:
        return

    sock_path = info["socket_path"]
    queue = info["buffer"]
    done = info.get("done", False)

    try:
        server = await asyncio.start_unix_server(
            lambda r, w: _handle_client(r, w, session_id, queue), sock_path
        )
        info["server"] = server
        async with server:
            await server.serve_forever()
    except Exception as e:
        logger.error("Socket server error [%s]: %s", session_id, e)
    finally:
        _cleanup_socket(sock_path)


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                         session_id: str, queue: asyncio.Queue):
    """Handle one client connection — read a JSON line, push to queue,
    and forward to all other connected clients (broadcast).

    The gateway connects as a persistent client via watch_unix_socket().
    When the GIMP plugin connects and sends a handoff, this handler
    forwards the data to the gateway for steer injection.
    """
    info = _sessions.get(session_id)
    clients: set = info.get("clients", set()) if info else set()
    clients.add(writer)
    try:
        data = await reader.readuntil(b"\n")
        payload = json.loads(data.decode("utf-8"))
        await queue.put(payload)

        # Forward to all other connected clients (the gateway)
        dead = set()
        for w in clients:
            if w is writer:
                continue
            try:
                w.write(data)
                await w.drain()
            except Exception:
                dead.add(w)
        clients -= dead
    except asyncio.IncompleteReadError:
        pass  # Client disconnected without sending a full line
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON from client: %s", e)
    finally:
        clients.discard(writer)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def _cleanup_socket(path: str):
    """Remove a socket file if it exists."""
    try:
        if os.path.exists(path):
            os.unlink(path)
    except Exception as e:
        logger.warning("Cleanup error %s: %s", path, e)


# ── MCP Tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def prometheus_request_session() -> str:
    """Create a new Prometheus capture session.

    Returns a session_id string. Use this session_id with
    prometheus_get_handoff() to poll for handoff data.
    The AI calls this once to set up the pipeline.
    """
    session_id = uuid.uuid4().hex[:12]
    sock_path = os.path.join(HANDOFF_DIR, f"{session_id}{SOCKET_SUFFIX}")

    # Clean up any stale socket
    _cleanup_socket(sock_path)

    # Create session entry with an unbounded asyncio Queue
    queue: asyncio.Queue = asyncio.Queue()
    _sessions[session_id] = {
        "socket_path": sock_path,
        "buffer": queue,
        "done": False,
        "clients": set(),
    }

    # Start the background socket listener
    asyncio.create_task(_socket_server(session_id))

    # Write current session ID so the GIMP plugin can find the socket
    session_file = os.path.join(HANDOFF_DIR, "current_session")
    with open(session_file, "w") as f:
        f.write(session_id)

    # For TCP fallback (Windows < Python 3.12), write port file
    if sys.platform == "win32" and sys.version_info < (3, 12):
        import hashlib
        port = 49152 + (int(hashlib.md5(session_id.encode()).hexdigest(), 16) % 16384)
        port_file = os.path.join(HANDOFF_DIR, f"{session_id}.port")
        with open(port_file, "w") as f:
            f.write(str(port))

    logger.info("Session %s created at %s", session_id, sock_path)
    return json.dumps({"session_id": session_id, "socket_path": sock_path})


@mcp.tool()
async def prometheus_get_handoff(session_id: str) -> str:
    """Poll a Prometheus session for new handoff data.

    Returns the next unconsumed handoff as a JSON string, or "{}" if
    nothing new has arrived, or '{"done": true}' when the session is closed.

    The AI calls this in a loop between user interactions to pick up
    new snapshots as the user works in GIMP.
    """
    info = _sessions.get(session_id)
    if not info:
        return '{"error": "session_not_found"}'

    if info.get("done"):
        return '{"done": true}'

    queue = info["buffer"]
    try:
        # Non-blocking: return immediately if nothing available
        payload = queue.get_nowait()
        return json.dumps(payload, default=str)
    except asyncio.QueueEmpty:
        return "{}"


@mcp.tool()
async def prometheus_close_session(session_id: str, minimize_gimp: bool = True) -> str:
    """Close a Prometheus session.

    Marks the session as done (subsequent get_handoff calls return
    {"done": true}), stops the socket listener, removes the socket file,
    and optionally minimizes the GIMP window.

    Args:
        session_id: The session to close.
        minimize_gimp: If True, sends a wmctrl command to minimize GIMP.
    """
    info = _sessions.get(session_id)
    if not info:
        return '{"error": "session_not_found"}'

    info["done"] = True

    # Stop socket server if running
    server = info.get("server")
    if server:
        server.close()

    # Remove socket file
    _cleanup_socket(info["socket_path"])

    # Minimize GIMP window
    if minimize_gimp:
        try:
            proc = await asyncio.create_subprocess_exec(
                "wmctrl", "-r", "GNU Image Manipulation Program", "-b", "add,hidden",
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:
            logger.warning("Failed to minimize GIMP: %s", e)

    # Clean up session entry
    _sessions.pop(session_id, None)

    logger.info("Session %s closed", session_id)
    return json.dumps({"ok": True, "session_id": session_id})


if __name__ == "__main__":
    mcp.run()