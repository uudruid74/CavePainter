# Vaughanwj Fork — Cross-Platform Hexagonal Restructure

Vaughn (github.com/Vaughanwj) forked CavePainter on 2026-07-13 and did a
major restructure adding cross-platform Windows support, hexagonal
architecture, and three bug fixes — two of which reproduce in our codebase.

## Architecture

### Ports-and-adapters (hexagonal)

```
cave_painter/
├── __init__.py          # Package root
├── config.py            # Environment-driven paths — NO hardcoded machine paths
├── mcp_server.py        # MCP tool registry — depends only on the domain port
├── domain/
│   ├── __init__.py
│   ├── engine.py        # DrawingEngine ABC — backend-agnostic interface
│   └── types.py         # Color, PathSegment, BrushSpec — pure value types
└── adapters/
    ├── __init__.py
    └── gimp/
        ├── __init__.py
        ├── client.py    # Host-side: subprocess/IPC management
        ├── daemon.py    # Inside GIMP: command processor (poll-driven)
        └── discovery.py # Auto-find GIMP on Windows/macOS/Linux
```

The MCP server (`mcp_server.py`) depends only on the `DrawingEngine` interface.
Swapping backends (Cairo, Pillow, etc.) means writing a new adapter, not
rewriting the whole codebase.

### Environment-Driven Config (config.py)

| Env Var | Default | Purpose |
|---|---|---|
| `CAVE_PAINTER_OUTPUT_DIR` | `PROJECT_ROOT/output/` | Where exports land |
| `CAVE_PAINTER_RUNTIME_DIR` | `tempfile.gettempdir()/cave-painter/` | Command/result IPC scratch space |
| `CAVE_PAINTER_GIMP_BIN` | auto-discover | Path to gimp/gimp-console executable |
| `CAVE_PAINTER_GIMP_HOME` | inherit current HOME | Optional HOME override for GIMP subprocess |
| `CAVE_PAINTER_STARTUP_SECONDS` | 2.5 | GIMP boot wait |
| `CAVE_PAINTER_COMMAND_TIMEOUT` | 30 | Per-command timeout |

### Auto-Discovery (discovery.py)

Cross-platform GIMP binary finder. Searches in order:

- **Windows:** `%LOCALAPPDATA%\Programs\GIMP*\bin\gimp-console-*.exe`,
  then `gimp-*.exe` — prefers console build over GUI build
- **macOS:** `/Applications/GIMP*.app/Contents/MacOS/gimp-console`
- **Linux:** `shutil.which("gimp-console")`, then `shutil.which("gimp")`,
  then fallback paths (`/usr/bin/gimp`, `/snap/bin/gimp`)

Returns bare `"gimp"` if nothing found (lets the subprocess fail loudly
with a useful error instead of failing quietly at discovery time).

## File-Based IPC (Commands/Results Protocol)

Instead of Unix domain sockets, Vaughn uses a **file-based command/result
protocol** under `RUNTIME_DIR/<session_id>/`:

```
/tmp/cave-painter/<session_id>/
  commands/              ← MCP server writes numbered JSON here
    0001_create_canvas.json
    0002_draw_ellipse.json
  results/               ← GIMP daemon writes numbered JSON here
    0001_result.json
    0002_result.json
```

GIMP daemon (`daemon.py`) polls `commands/` in a tight loop (100ms sleep),
processes commands synchronously, writes results, marks files as "processed"
by tracking seen filenames in a set.

**Advantages over Unix sockets:**
- Works identically on Linux, macOS, and Windows (no socket API dependency)
- Debuggable — files are just JSON, inspectable with `cat`
- Survives disconnects — GIMP crash doesn't lose the command queue
- No listener process needed — the daemon owns its own polling loop

**Disadvantages vs sockets:**
- Polling adds 100ms latency per command (vs immediate wakeup on socket)
- Filesystem I/O is heavier than in-memory socket buffers
- Requires cleanup of stale command/result files

## Three Bugs Fixed (All Affect Our Code)

### 1. Path Traversal in export()

**Vulnerability:** Agent-supplied `filename` like `"../../.env"` was joined
onto the output directory with no check — could write outside the intended
output directory.

**Fix (config.py):**
```python
def resolve_output_path(filename: str) -> Path:
    candidate = (OUTPUT_DIR / filename).resolve()
    if candidate != OUTPUT_DIR and OUTPUT_DIR not in candidate.parents:
        raise ValueError(
            f"path {filename!r} escapes the output directory ({OUTPUT_DIR})"
        )
    return candidate
```

Applied in both the client (before sending the command) and the daemon
(defense-in-depth before touching disk).

### 2. Layer Opacity Scale (0-100 vs 0.0-1.0)

**Bug:** `Gimp.Layer.new(img, name, W, H, type, **1.0**, mode)` with
opacity=1.0 makes the layer at 1% opacity in GIMP 3.x's PDB (expects 0-100).
Every layer drawn was ~1% opaque.

**Fix:** Use `100.0` for full opacity. Already documented in our codebase
as a known trap — Vaughn independently discovered and fixed it.

**Diagnosis:** `identify output.png` shows `sRGB` but histogram shows
alpha=2-5 on all pixels (e.g. `srgba(12,25,51,0.0117647)`).

### 3. Selection-Ignoring fill() (edit_fill vs fill)

**Bug:** `drawable.fill(Gimp.FillType.FOREGROUND)` fills the ENTIRE layer
regardless of any active selection. `draw_ellipse` and `draw_rect` create
a selection with `select_ellipse()` / `select_rectangle()`, then call
`fill()` — which fills the whole canvas, not the selected shape.

**Fix:** Use `drawable.edit_fill(Gimp.FillType.FOREGROUND)` instead, which
respects the active selection (the actual "Edit > Fill" PDB equivalent).

Already documented in our codebase — Vaughn independently discovered and
fixed it.

## Windows Compatibility Summary

| Component | Linux | Windows | macOS |
|---|---|---|---|
| GIMP auto-discover | gimp-console, gimp via PATH | Registry + Programs/GIMP* | .app/Contents/MacOS |
| File-based IPC | ✅ (native) | ✅ (no socket needed) | ✅ |
| `gimp --no-interface` | ✅ | Use `gimp-console` | ✅ |
| `python-fu-eval` batch | ✅ | ✅ | ✅ |
| Env var config | ✅ | ✅ | ✅ |
| Unix domain sockets | ✅ | Python 3.12+ (Win 10 17063+) | ✅ |

**Bottom line:** Vaughn's file-based IPC approach works on all three
platforms with zero platform-specific code. If we need cross-platform
support, adopt the file-based IPC pattern and ditch Unix sockets.

See: https://github.com/Vaughanwj/CavePainter (branch `main`,
commit `190eb7b`)
