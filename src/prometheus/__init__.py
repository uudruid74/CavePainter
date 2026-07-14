"""Prometheus — GIMP 3.x Plugin for AI collaborative editing.

Records filter dialog parameters and canvas state, then hands off
structured data to AI agents via native vision (DeepSeek V4-Flash).

Components:
  widget_reader  — GTK dialog widget tree scanner (requires gi.repository)
  canvas_exporter — Flatten → PNG → bounding-rect diff (requires gi.repository)
  undo_monitor  — Internal sequence counter + PDB name resolution (pure Python)
  handoff       — Payload assembly + JSON file write (pure Python)
  plugin        — GIMP 3.x plugin entry point (requires gi.repository)

Workflow:
  1. User clicks "Prometheus Snapshot" → captures before-canvas
  2. User applies a filter (e.g. Gaussian Blur) — GIMP shows dialog
  3. User clicks "Prometheus Record" →
     a. Scans visible dialogs via GTK introspection
     b. Exports after-canvas (full + diff crop)
     c. Writes handoff payload to /tmp/prometheus/

Architecture: Native vision — no auxiliary vision pipeline needed.
DeepSeek V4-Flash sees inline PNGs at ~$0.000013/image.
"""

# Lazy imports — gi.repository only resolves inside GIMP's Python.
# Individual modules are imported directly by plugin.py.
