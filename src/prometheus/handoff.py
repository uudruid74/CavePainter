"""
Prometheus Handoff Coordinator — P0 Component 4.

Assembles the structured payload from all three data sources:
  1. Dialog parameters (widget_reader)
  2. Canvas exports (canvas_exporter)
  3. Action metadata (undo_monitor)

Writes the payload as JSON to /tmp/prometheus/handoff_NNN.json for
consumption by the Hermes agent / cave-painter daemon.

Handoff payload structure:
  {
    "sequence": int,
    "action_names": [str],
    "dialog_params_json": str,    # JSON-encoded dialog tree
    "before_PNG": "/absolute/path",
    "after_PNG": "/absolute/path",
    "current_PNG": "/absolute/path",
    "diff_rect": {"x","y","width","height"} | null
  }
"""

import json
import os
import time

HANDOFF_DIR = "/tmp/prometheus"
os.makedirs(HANDOFF_DIR, exist_ok=True)


def assemble_payload(sequence, action_names, dialog_params,
                     before_png, after_png, current_png,
                     diff_rect=None):
    """Assemble the full Prometheus handoff payload.

    Args:
        sequence: int — undo_monitor sequence number.
        action_names: list of str — operation names detected.
        dialog_params: dict — widget_reader scan results.
        before_png: str — absolute path to before-snapshot PNG.
        after_png: str — absolute path to cropped diff PNG (or full after).
        current_png: str — absolute path to current full-canvas PNG.
        diff_rect: dict or None — bounding rect from canvas_exporter.

    Returns:
        dict ready for JSON serialization.
    """
    return {
        "sequence": sequence,
        "action_names": action_names,
        "dialog_params_json": json.dumps(dialog_params, indent=2),
        "before_PNG": before_png,
        "after_PNG": after_png,
        "current_PNG": current_png,
        "diff_rect": diff_rect,
        "timestamp_utc": time.time(),
    }


def write_handoff(payload, seq=None):
    """Write the assembled payload to /tmp/prometheus/handoff_NNN.json.

    Args:
        payload: dict from assemble_payload().
        seq: Optional sequence override for filename (uses payload seq if None).

    Returns:
        Absolute path to the written handoff file.
    """
    seq_num = seq if seq is not None else payload.get("sequence", 0)
    fname = f"handoff_{seq_num:04d}.json"
    path = os.path.join(HANDOFF_DIR, fname)

    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

    # Also write a symlink to "latest" for easy polling
    latest = os.path.join(HANDOFF_DIR, "latest.json")
    try:
        if os.path.islink(latest) or os.path.exists(latest):
            os.remove(latest)
        os.symlink(fname, latest)
    except OSError:
        pass  # symlink is best-effort

    return path


def write_handoff_socket(payload: dict) -> bool:
    """Write the payload to the active session's Unix socket.

    Reads /tmp/prometheus/current_session to find the session ID,
    connects to /tmp/prometheus/<session_id>.sock, sends one JSON
    line, and disconnects.  The MCP server's socket handler receives
    the data and broadcasts to all connected clients — including the
    gateway's persistent watch_unix_socket connection.

    Returns:
        True if the write succeeded, False otherwise.
    """
    session_file = os.path.join(HANDOFF_DIR, "current_session")
    try:
        with open(session_file, "r") as f:
            session_id = f.read().strip()
    except Exception:
        return False

    if not session_id:
        return False

    sock_path = os.path.join(HANDOFF_DIR, f"{session_id}.sock")
    if not os.path.exists(sock_path):
        return False

    try:
        import socket as _socket
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(sock_path)
        data = json.dumps(payload) + "\n"
        sock.sendall(data.encode("utf-8"))
        sock.close()
        return True
    except Exception:
        return False


def full_handoff(sequence, action_names, dialog_params,
                 before_png, after_png, current_png,
                 diff_rect=None):
    """Convenience: assemble + write in one call.

    Returns:
        (payload dict, handoff_path)
    """
    payload = assemble_payload(
        sequence, action_names, dialog_params,
        before_png, after_png, current_png, diff_rect
    )
    path = write_handoff(payload, sequence)
    return payload, path
