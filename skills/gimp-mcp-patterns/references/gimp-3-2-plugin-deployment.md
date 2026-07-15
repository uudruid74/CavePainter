# GIMP 3.2 Plugin Deployment Debugging Chain

Full debugging chain from the 2026-07-12 session where Prometheus 
wouldn't load in GIMP 3.2.4.

## The Problem

Plugin file in `/home/ekl/.config/GIMP/3.0/plug-ins/prometheus.py` 
would not appear in Tools menu. Even a minimal test plugin with 
just `class TestPlugin(Gimp.PlugIn)` didn't load.

## Step-by-Step Diagnosis

### Step 1: Check Python-Fu Console sys.path
```python
import sys
print([p for p in sys.path])
```
GIMP's plug-ins directory is NOT in sys.path — that's normal. 
GIMP executes plugin files during startup, it doesn't import them.

### Step 2: Check for `Gimp.directory_plugins()`
```python
from gi.repository import Gimp
# Gimp.directory_plugins() DOES NOT EXIST in GIMP 3.2
# AttributeError: 'gi.repository.Gimp' object has no attribute 'directory_plugins'
```

### Step 3: Find the REAL plug-ins directory
```python
import os
os.path.expanduser("~/.config/GIMP")  # → /home/ekl/.config/GIMP
```
Then `ls ~/.config/GIMP/` to see version directories.
GIMP 3.2.4 uses `3.2/` not `3.0/`.

### Step 4: Check plugin structure requirements
GIMP 3.x Python plugins must be in a **subdirectory** matching 
the plugin name, NOT flat `.py` files in the root:

```
❌ Wrong:
~/.config/GIMP/3.2/plug-ins/prometheus.py

✅ Correct:
~/.config/GIMP/3.2/plug-ins/prometheus/prometheus.py
```

This matches the system plugin pattern:
`/usr/lib/gimp/3.0/plug-ins/python-console/python-console.py`

### Step 5: Verify file requirements
- Shebang: `#!/usr/bin/python3.14`
- gi.require_version: `gi.require_version('Gimp', '3.0')`
- Executable: `chmod +x` (700 or 755)

### Step 6: Test with minimal plugin
```python
#!/usr/bin/python3.14
import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, GLib

class TestPlugin(Gimp.PlugIn):
    def do_query_procedures(self):
        return ["test-hello"]
    def do_create_procedure(self, name):
        p = Gimp.ImageProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, self.run, None)
        p.set_image_types("*")
        p.set_menu_label("Test _Hello")
        p.add_menu_path("<Image>/Tools/")
        return p
    def run(self, proc, mode, img, drawables, config, data):
        Gimp.message("Hello!")
        return proc.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

Gimp.main(TestPlugin.__gtype__, sys.argv)
```

### Step 7: Check menu after restart
Full restart required — Filters → Tools reload is not enough.

## What NOT To Do

- **DO NOT** `exec()` the plugin file from Python-Fu Console to test it.
  The `Gimp.main()` call at the bottom is for startup, not interactive 
  execution. It will crash with "Plug-in crashed: python-console.py" 
  and corrupt GIMP state. Save work and restart.
- **DO NOT** check for `Gimp.directory_plugins()` — doesn't exist.
- **DO NOT** check sys.path for plug-ins dir — it won't be there.

## Root Cause Summary

| Attempt | Symptom | Root Cause |
|---|---|---|
| Flat .py in 3.0/plug-ins/ | Not in menu | Wrong version dir (3.0 vs 3.2) |
| Flat .py in 3.2/plug-ins/ | Not in menu | GIMP 3 needs subdirectory structure |
| Subdir in 3.2/plug-ins/ | ✅ In menu! | Correct structure |
| exec() from console to test | Crashed GIMP | Gimp.main() not for interactive use |
| File-save in run handler | Worked ✅ | Gimp.file_save(run_mode, image, gfile, None) works in both batch and GUI |
| Configured subdir + restart | ✅ Full success | Plugin loads in Tools menu |
