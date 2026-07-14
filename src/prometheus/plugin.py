"""
Prometheus GIMP Plugin — GIMP 3.x entry point.

Registers two PDB procedures:
  prometheus-snapshot  — Capture before-canvas state.
  prometheus-record    — Scan dialogs + export diff + write handoff.

Installation: copy prometheus/ directory into GIMP's plug-ins path
  ~/.config/GIMP/3.0/plug-ins/prometheus/

Or run from any location — GIMP auto-discovers Python plugins.
"""

import sys
import os
import logging

logger = logging.getLogger("prometheus-plugin")

# Ensure the parent directory is on sys.path so 'import prometheus' works
# when GIMP executes this file directly.
_src_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_src_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from gi.repository import Gimp, GLib
from prometheus.widget_reader import scan_dialogs, identify_filter
from prometheus.canvas_exporter import export_full_png, export_diff
from prometheus.undo_monitor import record_action, resolve_pdb_name, reset, current_sequence
from prometheus.handoff import full_handoff, write_handoff_socket


# ── Plugin state ────────────────────────────────────────────────────────
# Persists across invocations within a GIMP session.
_snapshot_path = None   # Path to before-canvas PNG


class PrometheusPlugin(Gimp.PlugIn):
    """GIMP 3.x plugin: Prometheus dialog reader + canvas handoff."""

    def do_query_procedures(self):
        return ["prometheus-snapshot", "prometheus-record"]

    def do_create_procedure(self, name):
        if name == "prometheus-snapshot":
            return self._create_snapshot_proc()
        elif name == "prometheus-record":
            return self._create_record_proc()
        return None

    def _create_snapshot_proc(self):
        procedure = Gimp.ImageProcedure.new(
            self, "prometheus-snapshot",
            Gimp.PDBProcType.PLUGIN,
            self.run_snapshot, None,
        )
        procedure.set_image_types("*")
        procedure.set_menu_label("_Prometheus Snapshot")
        procedure.add_menu_path("<Image>/Tools/")
        procedure.set_documentation(
            "Capture before-canvas state for Prometheus handoff",
            "Exports the current image (flattened) as a before-snapshot "
            "PNG to /tmp/prometheus/. Call this before applying a filter.",
            "prometheus-snapshot",
        )
        procedure.set_attribution("Neo", "Neo", "2026")
        return procedure

    def _create_record_proc(self):
        procedure = Gimp.ImageProcedure.new(
            self, "prometheus-record",
            Gimp.PDBProcType.PLUGIN,
            self.run_record, None,
        )
        procedure.set_image_types("*")
        procedure.set_menu_label("_Prometheus Record")
        procedure.add_menu_path("<Image>/Tools/")
        procedure.set_documentation(
            "Record filter dialogs + canvas diff and write handoff",
            "Scans visible GTK filter dialogs, exports current canvas, "
            "computes bounding-rect diff from snapshot, and writes the "
            "structured payload to /tmp/prometheus/handoff_NNN.json.",
            "prometheus-record",
        )
        procedure.set_attribution("Neo", "Neo", "2026")
        return procedure

    # ── Procedure handlers ──────────────────────────────────────────

    def run_snapshot(self, procedure, run_mode, image, drawables,
                     config, run_data):
        """Capture before-canvas PNG."""
        global _snapshot_path

        if run_mode == Gimp.RunMode.INTERACTIVE:
            Gimp.progress_init("Prometheus: capturing snapshot...")

        path = export_full_png(image, "before")
        if path:
            _snapshot_path = path
            Gimp.message(f"Prometheus snapshot saved: {path}")
        else:
            Gimp.message("Prometheus: failed to export snapshot.")

        return procedure.new_return_values(
            Gimp.PDBStatusType.SUCCESS, GLib.Error()
        )

    def run_record(self, procedure, run_mode, image, drawables,
                   config, run_data):
        """Record dialogs, export canvas, write handoff."""
        global _snapshot_path

        if run_mode == Gimp.RunMode.INTERACTIVE:
            Gimp.progress_init("Prometheus: recording...")

        # ── Step 1: Scan visible dialogs ────────────────────────────
        dialogs = scan_dialogs()
        action_names = []
        all_params = {}

        for dlg in dialogs:
            title = dlg.get("title", "")
            op_name = identify_filter(title)
            if op_name:
                action_names.append(op_name)
            # Merge params (widget values keyed by widget ID)
            all_params[title] = dlg.get("params", {})

        # Fallback: if no dialog identified, record as generic action
        if not action_names:
            action_names.append("unknown-filter")
        if not all_params:
            all_params["no-dialogs"] = {"note": "No visible filter dialogs found"}

        # ── Step 2: Export current canvas ───────────────────────────
        current_png = export_full_png(image, "current")
        if not current_png:
            Gimp.message("Prometheus: failed to export current canvas.")
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error()
            )

        # ── Step 3: Compute diff (if snapshot exists) ───────────────
        after_png = current_png  # default: use full current as "after"
        diff_rect = None

        if _snapshot_path and os.path.exists(_snapshot_path):
            rect, cropped = export_diff(_snapshot_path, current_png)
            if rect and cropped:
                diff_rect = rect
                after_png = cropped  # cropped-to-changes version

        # ── Step 4: Record action sequence ──────────────────────────
        pdb_names = []
        for name in action_names:
            pdb = resolve_pdb_name(name)
            if pdb:
                pdb_names.append(pdb)
            record_action(name)

        # ── Step 5: Assemble and write handoff ──────────────────────
        seq = current_sequence()
        payload, handoff_path = full_handoff(
            sequence=seq,
            action_names=action_names,
            dialog_params=all_params,
            before_png=_snapshot_path,
            after_png=after_png,
            current_png=current_png,
            diff_rect=diff_rect,
        )

        Gimp.message(
            f"Prometheus recorded — seq {seq}: "
            f"{', '.join(action_names) if action_names else 'no dialog'}\n"
            f"Handoff: {handoff_path}"
        )

        # Also push to the Unix socket for real-time steer injection.
        # Best-effort — if the socket isn't ready, the file handoff
        # above still works for polling via prometheus_get_handoff.
        if write_handoff_socket(payload):
            logger.info("Socket handoff sent for seq %d", seq)
        else:
            logger.debug("Socket handoff skipped (no active session)")

        return procedure.new_return_values(
            Gimp.PDBStatusType.SUCCESS, GLib.Error()
        )


# ── GIMP entry point ────────────────────────────────────────────────────
Gimp.main(PrometheusPlugin.__gtype__, sys.argv)
