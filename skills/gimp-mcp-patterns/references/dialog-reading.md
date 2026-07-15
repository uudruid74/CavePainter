# GIMP Dialog Reading Architecture

## Origin

Discovered 2026-07-12 during Prometheus plugin architecture design. Goal was capturing user's GIMP filter settings for AI training without spying on pixel operations.

## Key Insight

GIMP 3.x runs its own Python process. Filter dialogs are Gtk windows in the same process space. Python can enumerate all Gtk toplevel windows and read every widget's value via standard PyGObject introspection. No C extensions, no vision API, no external calls.

## What We Tried That Didn't Work

- **Xvfb headless**: Virtual framebuffer can't show user dialogs. Only useful for unattended tests.
- **Batch-mode Python-Fu**: `exec(open(...).read())` inside `--batch-interpreter python-fu-eval` doesn't produce stdout or file writes reliably. Use a proper plugin registration instead.
- **Vision screenshot**: Works but burns tokens and adds latency for data already available in-process.

## What We Didn't Prove But Know Is True

The GTK introspection API (`Gtk.Window.list_toplevels()`) is the same API used by every GIMP 3.x Python plugin that shows custom dialogs. It is confirmed working by:
- Multiple gimp-mcp projects (maorcc, martinduartemore) that implement VNC-based remote access
- Official GIMP 3.x plugin examples using `Gimp.PlugIn.create_procedure()` which runs inside the same Python interpreter
- The GIMP 3.x Python-Fu console where `from gi.repository import Gtk, Gdk` works directly

## Test Plan (for when GIMP is open on a real display)

1. Open GIMP normally with a display
2. Open any image
3. Open Filters → Blur → Gaussian Blur (or any filter dialog that has SpinButtons)
4. Run a plugin that calls `Gtk.Window.list_toplevels()` and walks widgets
5. Verify: all widget values readable, including range limits from `Gtk.Adjustment`

Unproven: whether GIMP 3.x's GTK theme or custom widgets (GimpSpinScale, etc.) break the standard Gtk widget type checks in a walk function.

## Integration with Prometheus

- Prometheus registers as a GIMP plugin via `Gimp.PlugIn.create_procedure()`
- On "Record" button click: finds topmost dialog → walks widget tree → dumps JSON
- JSON payload sent over existing file-based command protocol to Cave Painter daemon
- Daemon stores training pair: {tool_name, params, before_canvas} in fabric

## Cross-reference

- `gimp-mcp-patterns/SKILL.md` — dialog reading section
- `gopher-kanban-flow/SKILL.md` — Creating a Kanban Worker Profile section (Zephyr pattern)
- Fabric entries: Wintermute's architecture review (3 GIMP API blockers)
