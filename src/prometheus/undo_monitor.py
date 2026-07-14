"""
Prometheus Undo Monitor — P0 Component 3.

GIMP 3.x has NO undo stack introspection API.  The undo history is
internal to the GIMP core and not exposed to Python plugins.

Strategy:
  - Internal sequence counter — incremented on each recorded action.
  - Operation name derived from dialog title (via widget_reader.identify_filter).
  - For v1, PDB procedure names are inferred from the filter dialog title,
    not read from the undo stack (which is impossible).

This approach captures the WHAT (which filter was applied, with what
parameters) even though we cannot read the WHEN from GIMP's undo system.
"""

# Simple module-level counters — one per plugin lifetime (one GIMP session).
# These are reset on each new image, tracked via image_id.

_state = {
    "counter": 0,
    "current_image_id": None,
    "action_log": [],  # list of (seq, action_name) tuples
}


def reset(image_id=None):
    """Reset the counter. Call when starting a new image or session."""
    _state["counter"] = 0
    _state["current_image_id"] = image_id
    _state["action_log"] = []


def next_sequence(image_id=None):
    """Increment and return the next sequence number.

    If image_id changes (new image opened), auto-resets.
    """
    if image_id is not None and image_id != _state["current_image_id"]:
        reset(image_id)

    _state["counter"] += 1
    if image_id is not None:
        _state["current_image_id"] = image_id

    return _state["counter"]


def record_action(action_name):
    """Append an action to the log. Returns the sequence number.

    Args:
        action_name: Human-readable operation name (e.g. "GEGL Gaussian Blur").

    Returns:
        (sequence_number, action_name)
    """
    seq = next_sequence()
    _state["action_log"].append((seq, action_name))
    return seq, action_name


def current_sequence():
    """Return the current sequence number without incrementing."""
    return _state["counter"]


def get_action_log():
    """Return a copy of the full action log.

    Returns:
        list of {"seq": int, "action": str} dicts.
    """
    return [{"seq": s, "action": a} for s, a in _state["action_log"]]


# ── Known PDB procedure names for common GIMP filters ──────────────────
# These map dialog title patterns → GIMP PDB procedure names.
# Used when the plugin can't read undo stack (which is always in GIMP 3.x).

PDB_FILTER_MAP = {
    "gaussian blur": "plug-in-gauss",
    "blur": "plug-in-gauss",
    "levels": "gimp-levels",
    "curves": "gimp-curves-spline",
    "brightness": "gimp-brightness-contrast",
    "contrast": "gimp-brightness-contrast",
    "hue": "gimp-hue-saturation",
    "saturation": "gimp-hue-saturation",
    "sharpen": "plug-in-sharpen",
    "unsharp mask": "plug-in-unsharp-mask",
    "noise": "plug-in-rgb-noise",
    "drop shadow": "plug-in-dropshadow",
    "edge": "plug-in-edge",
    "neon": "plug-in-neon",
    "soft glow": "plug-in-softglow",
    "threshold": "gimp-threshold",
    "posterize": "gimp-posterize",
    "colorize": "gimp-colorize",
    "invert": "gimp-invert",
    "scale image": "gimp-image-scale",
    "scale layer": "gimp-layer-scale",
    "rotate": "gimp-image-rotate",
    "crop": "plug-in-crop",
}


def resolve_pdb_name(action_name):
    """Map a human-readable action name to a GIMP PDB procedure name.

    Args:
        action_name: e.g. "GEGL Gaussian Blur"

    Returns:
        PDB name (e.g. "plug-in-gauss") or None.
    """
    name_lower = action_name.lower().replace("gegl ", "")
    for pattern, pdb_name in PDB_FILTER_MAP.items():
        if pattern in name_lower:
            return pdb_name
    return None
