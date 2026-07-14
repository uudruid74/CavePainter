"""Environment-driven configuration. No machine-specific paths live in code.
Everything here has a sane default under the system temp dir / project dir,
and can be overridden with CAVE_PAINTER_* environment variables for a given install.
"""
import os
import sys
import platform
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Where exported PNGs are allowed to land. export() rejects any path
# that would resolve outside this directory (see resolve_output_path).
OUTPUT_DIR = Path(os.environ.get(
    "CAVE_PAINTER_OUTPUT_DIR", PROJECT_ROOT / "output"
)).resolve()

# Scratch space for Unix socket files — one socket per GIMP daemon session.
SOCKET_DIR = Path(os.environ.get(
    "CAVE_PAINTER_SOCKET_DIR", Path(tempfile.gettempdir()) / "cave-painter"
)).resolve()

# Prometheus session sockets live here.
PROMETHEUS_DIR = Path(os.environ.get(
    "CAVE_PAINTER_PROMETHEUS_DIR", Path(tempfile.gettempdir()) / "prometheus"
)).resolve()

# The `gimp` executable to launch. Leave unset to auto-discover.
GIMP_BIN = os.environ.get("CAVE_PAINTER_GIMP_BIN")

# Optional HOME override for the GIMP subprocess.
GIMP_HOME = os.environ.get("CAVE_PAINTER_GIMP_HOME")

# The daemon script GIMP's python-fu-eval interpreter loads and execs.
DAEMON_SCRIPT = Path(__file__).resolve().parent / "adapters" / "gimp" / "daemon.py"

# How long to wait for GIMP subprocess to boot and for each command to come back.
GIMP_STARTUP_SECONDS = float(os.environ.get("CAVE_PAINTER_GIMP_STARTUP_SECONDS", "2.5"))
COMMAND_TIMEOUT_SECONDS = float(os.environ.get("CAVE_PAINTER_COMMAND_TIMEOUT_SECONDS", "30"))

# Socket fallback: on Windows < Python 3.12, use TCP localhost instead of Unix sockets.
# Python 3.12+ on Windows 10 build 17063+ supports Unix domain sockets natively.
def _needs_tcp_fallback() -> bool:
    if platform.system() != "Windows":
        return False
    if sys.version_info >= (3, 12):
        return False  # Unix sockets supported natively
    return True

USE_TCP_FALLBACK = _needs_tcp_fallback()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SOCKET_DIR.mkdir(parents=True, exist_ok=True)
PROMETHEUS_DIR.mkdir(parents=True, exist_ok=True)


def resolve_output_path(filename: str) -> Path:
    """Join `filename` onto OUTPUT_DIR and refuse to escape it.
    `filename` comes straight from an MCP tool call, i.e. it's agent-controlled input.
    Without this check, a "../../.." path segment lets export() write an arbitrary
    file anywhere the process has permissions — this is the fix for that path-traversal bug.
    """
    candidate = (OUTPUT_DIR / filename).resolve()
    if candidate != OUTPUT_DIR and OUTPUT_DIR not in candidate.parents:
        raise ValueError(
            f"path {filename!r} escapes the output directory ({OUTPUT_DIR})"
        )
    return candidate


def socket_path_for_session(session_id: str) -> str:
    """Return the socket path (or TCP port string) for a given session ID."""
    if USE_TCP_FALLBACK:
        # Derive a deterministic port from the session_id hash (49152-65535 range)
        port = 49152 + (hash(session_id) % 16384)
        return f"127.0.0.1:{port}"
    return str(SOCKET_DIR / f"{session_id}.sock")
