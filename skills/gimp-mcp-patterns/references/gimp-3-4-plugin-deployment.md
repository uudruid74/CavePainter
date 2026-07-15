# GIMP 3.2.4 Python Plugin Deployment (CachyOS/Arch)

## Discovery Session (2026-07-12 — corrected)

System: CachyOS (Arch-based), GIMP 3.2.4, Python 3.14.6

## ⚠️ CRITICAL: Version Directory Mismatch

**GIMP 3.2.4 uses `~/.config/GIMP/3.2/` NOT `~/.config/GIMP/3.0/`.**

This was the root cause of an entire session's worth of debugging. Every plugin file was placed in `/home/ekl/.config/GIMP/3.0/plug-ins/` when GIMP was looking at `/home/ekl/.config/GIMP/3.2/plug-ins/`.

**Check your GIMP version before deploying plugins:**
```python
# In Python-Fu Console:
from gi.repository import Gimp
print(Gimp.MAJOR_VERSION, Gimp.MINOR_VERSION, Gimp.MICRO_VERSION)
```

Then map to the config directory:
- GIMP 3.0.x → `~/.config/GIMP/3.0/`
- GIMP 3.2.x → `~/.config/GIMP/3.2/`
- GIMP 3.4.x → `~/.config/GIMP/3.4/`

## Working Plugin Directory

```
~/.config/GIMP/3.2/plug-ins/{plugin-name}/
    {plugin-name}.py    ← Main entry with Gimp.main() + Gimp.PlugIn subclass
    (supporting files)
```

## What Was Actually Tested (and What Failed vs What Worked)

| Structure | Location | Result | Root Cause |
|---|---|---|---|
| Flat `.py` in plug-ins | `3.0/` | ❌ | Wrong directory |
| Subdirectory plugin | `3.0/` | ❌ | Wrong directory |
| **Subdirectory plugin** | **`3.2/`** | **✅ Menu appeared!** | **Correct directory** |

## How to Test Plugin Registration

```python
pdb = Gimp.get_pdb()
proc = pdb.lookup_procedure("prometheus-record")
print("Found!" if proc else "Not found")
```

DO NOT run `exec(open('plugin.py').read())` — `Gimp.main()` at the bottom of the plugin file is designed for startup. It crashes the console plugin and corrupts GIMP's internal state.

## Plugin File Template

```python
#!/usr/bin/python3.14
import sys, os, json, time
import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, GLib, Gtk, Gdk, Gio

class MyPlugin(Gimp.PlugIn):
    def do_query_procedures(self):
        return ["my-procedure"]
    def do_create_procedure(self, name):
        p = Gimp.ImageProcedure.new(self, name, Gimp.PDBProcType.PLUGIN,
                                     self.run, None)
        p.set_image_types("*")
        p.set_menu_label("_My Label")
        p.add_menu_path("<Image>/Tools/")
        return p
    def run(self, proc, mode, img, drawables, config, data):
        try:
            Gimp.message("Hello!")
        except Exception as e:
            Gimp.message(f"Error: {e}")
        return proc.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

Gimp.main(MyPlugin.__gtype__, sys.argv)
```

## Key Files

- Prometheus plugin: `/home/ekl/.config/GIMP/3.2/plug-ins/prometheus/prometheus.py`
- Cave Painter source: `/home/ekl/Documents/Programming/cave-painter/src/`

## Still Unanswered

- Does the `.py` filename inside the subdirectory need to match the directory name?
- Do plugins need execute permissions? (ours is 755, works)
- Is 3.2 vs 3.0 split standard or system-specific?
