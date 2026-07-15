# GIMP 3.2.4 File-Save API (Two Working Approaches)

GIMP 3.2.4 supports **two** approaches to PNG export from Python plugins. 
Both were confirmed working in GUI plugin context (July 2026).

## Approach 1: Direct Function Call (Simpler)

```python
from gi.repository import Gimp, GLib, Gio

path = "/tmp/output.png"
gfile = Gio.File.new_for_path(path)
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, gfile, None)
```

**Confirmed:** This works in both headless batch mode AND GUI plugin context.
Tested with Prometheus plugin in GIMP 3.2.4 GUI mode (produced valid 413KB PNGs).

## Approach 2: Config-Based PDB Procedure (More Control)

```python
from gi.repository import Gimp, GLib, Gio

pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-file-save")

config = proc.create_config()
config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
config.set_property("image", image)
config.set_property("file", Gio.File.new_for_path("/path/to/output.png"))

# Export options — create PNG-specific export options
export_options = Gimp.ExportOptions.new()
# For PNG: set save-background, save-alpha, etc.
config.set_property("export-options", export_options)

result = proc.run(config)
```

## How to Discover Arguments for Any PDB Procedure

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("gimp-file-save")
for i, arg in enumerate(proc.get_arguments()):
    print(i, type(arg).__name__, arg)
```

For `gimp-file-save` in GIMP 3.2.4, this returns:
- 0: `GParamEnum` — run-mode (INTERACTIVE/NONINTERACTIVE)
- 1: `GimpParamImage` — the image object
- 2: `GParamObject` — a `Gio.File` for the output path
- 3: `GimpParamExportOptions` — export format options

## Headless vs GUI Plugin Notes

GIMP 3.x headless batch mode (`--batch-interpreter python-fu-eval`) 
may still accept the old API patterns because the batch interpreter 
wraps them differently than GUI plugin execution.

**Always test both modes** — a save that works headless may crash in GUI.

## Verification

After saving, check the file exists and has content:

```python
import os
path = "/tmp/prometheus/test.png"
exists = os.path.exists(path) and os.path.getsize(path) > 0
print(f"File saved: {exists} ({os.path.getsize(path)} bytes)" if exists else "FAILED")
```
