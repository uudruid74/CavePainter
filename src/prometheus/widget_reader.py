"""
Prometheus GTK Dialog Widget Reader — P0 Component 1.

Scans Gtk.Window.list_toplevels() for visible dialogs, walks the widget
tree, and reads all parameter values from supported widget types.

Key constraint: GIMP 3.x embedded Python — gi.repository only, no external deps.

Widgets supported:
  Gtk.SpinButton   → value, min, max, step
  Gtk.ComboBoxText → selected text, all options
  Gtk.CheckButton  → active state
  Gtk.Scale        → current value
  Gtk.ColorButton  → RGBA [r,g,b,a]
  Gtk.Entry        → text content
  Gtk.Label        → label text (context, not a parameter)

The values are read directly from in-process GTK widgets — no screen
scraping, no C code, no sandbox escape.
"""

import json
from gi.repository import Gtk


def read_spin_button(widget):
    """Read SpinButton: value, range, step."""
    adj = widget.get_adjustment()
    return {
        "type": "spin",
        "value": widget.get_value(),
        "min": adj.get_lower() if adj else None,
        "max": adj.get_upper() if adj else None,
        "step": adj.get_step_increment() if adj else None,
    }


def read_combo_box(widget):
    """Read ComboBoxText: selected text + all option strings."""
    result = {
        "type": "combo",
        "value": widget.get_active_text(),
        "options": [],
    }
    model = widget.get_model()
    if model is not None:
        for i in range(model.get_n_items()):
            result["options"].append(model.get_string(i))
    return result


def read_check_button(widget):
    """Read CheckButton: active state."""
    return {"type": "check", "value": widget.get_active()}


def read_scale(widget):
    """Read Scale (slider): current value."""
    return {"type": "scale", "value": widget.get_value()}


def read_color_button(widget):
    """Read ColorButton: RGBA float tuple [r, g, b, a]."""
    rgba = widget.get_rgba()
    return {
        "type": "color",
        "value": [rgba.red, rgba.green, rgba.blue, rgba.alpha],
    }


def read_entry(widget):
    """Read Entry: text content."""
    return {"type": "entry", "value": widget.get_text()}


def read_label(widget):
    """Read Label: text — useful for parameter names in filter dialogs."""
    return {"type": "label", "value": widget.get_label()}


# Widget-type → reader dispatch table
_WIDGET_READERS = {
    Gtk.SpinButton: read_spin_button,
    Gtk.ComboBoxText: read_combo_box,
    Gtk.CheckButton: read_check_button,
    Gtk.Scale: read_scale,
    Gtk.ColorButton: read_color_button,
    Gtk.Entry: read_entry,
    Gtk.Label: read_label,
}


def walk_widget_tree(widget, depth=0):
    """Recursively walk a GTK widget tree and extract all readable values.

    Returns a dict keyed by a widget identifier: its GtkBuildable ID,
    tooltip text, or generated name. Labels are included as 'label_N'
    entries — they provide parameter-name context for adjacent controls.

    Args:
        widget: A Gtk.Widget at the root of the subtree.
        depth: Internal recursion guard (capped at 32).

    Returns:
        dict of {widget_id: {type, value, ...}}
    """
    if depth > 32:
        return {}

    result = {}

    # Identify this widget
    name = None
    try:
        # Prefer GtkBuildable ID (set in .ui files)
        name = widget.get_name()
    except Exception:
        pass
    if not name:
        try:
            name = widget.get_tooltip_text()
        except Exception:
            pass
    if not name:
        name = widget.__class__.__name__

    # Read value if supported
    for wtype, reader in _WIDGET_READERS.items():
        if isinstance(widget, wtype):
            try:
                data = reader(widget)
                # Disambiguate duplicate names
                key = name
                suffix = 0
                while key in result:
                    suffix += 1
                    key = f"{name}_{suffix}"
                result[key] = data
            except Exception:
                pass
            break

    # Recurse into container children
    try:
        children = widget.get_children()
    except Exception:
        children = []

    for child in children:
        result.update(walk_widget_tree(child, depth + 1))

    return result


def scan_dialogs(title_filter=None):
    """Scan all visible toplevel Gtk windows for filter dialogs.

    Each window that is visible and has a non-empty title is treated as
    a potential filter dialog.  The entire widget tree is walked.

    Args:
        title_filter: If set, only windows whose title contains this
                      string (case-insensitive) are included.  Useful
                      for matching specific filters like "Gaussian".

    Returns:
        list of dicts: [{"title": str, "params": {...}}, ...]
    """
    dialogs = []
    toplevels = Gtk.Window.list_toplevels()

    for window in toplevels:
        try:
            if not window.get_visible():
                continue
        except Exception:
            continue

        try:
            title = window.get_title() or ""
        except Exception:
            title = ""

        if not title:
            continue

        if title_filter and title_filter.lower() not in title.lower():
            continue

        params = walk_widget_tree(window)
        dialogs.append({"title": title, "params": params})

    return dialogs


def scan_dialogs_json(title_filter=None):
    """Convenience: scan_dialogs() → JSON string."""
    return json.dumps(scan_dialogs(title_filter), indent=2)


# ── Known filter dialog title patterns ──────────────────────────────────
# Used by the plugin to auto-detect what filter was applied.
FILTER_PATTERNS = {
    "gaussian": "GEGL Gaussian Blur",
    "blur": "Blur",
    "levels": "Levels",
    "curves": "Curves",
    "brightness": "Brightness-Contrast",
    "contrast": "Brightness-Contrast",
    "hue": "Hue-Saturation",
    "saturation": "Hue-Saturation",
    "sharpen": "Sharpen",
    "unsharp": "Unsharp Mask",
    "noise": "Noise",
    "dropshadow": "Drop Shadow",
    "edge": "Edge",
    "neon": "Neon",
    "glow": "Soft Glow",
    "threshold": "Threshold",
    "posterize": "Posterize",
    "colorize": "Colorize",
    "invert": "Invert",
    "scale": "Scale",
    "rotate": "Rotate",
    "crop": "Crop",
    "resize": "Resize",
}


def identify_filter(title):
    """Guess filter/operation name from dialog title.

    Returns the PDB-style operation name or None.
    """
    t = title.lower()
    for pattern, name in FILTER_PATTERNS.items():
        if pattern in t:
            return name
    return None
