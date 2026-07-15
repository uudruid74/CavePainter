#!/usr/bin/env python3
"""Quick test of the daemon text/stroke/dab fixes via file protocol."""
import json, os, subprocess, sys, time, uuid
from pathlib import Path

DAEMON = "/home/ekl/Documents/Programming/cave-painter/src/cave_painter_daemon.py"
SID = f"test-{uuid.uuid4().hex[:8]}"
BASE = Path(f"/tmp/gopher-daemon/{SID}")
CMD_DIR = BASE / "commands"
RES_DIR = BASE / "results"
OUTPUT = Path("/home/ekl/Documents/Programming/cave-painter/tests/output/fix-test.png")

os.makedirs(CMD_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

# Start GIMP headless
proc = subprocess.Popen(
    ["gimp", "--no-interface", "--batch-interpreter", "python-fu-eval",
     "-b", f"exec(open('{DAEMON}').read())"],
    env={**os.environ, "GDB_SESSION_ID": SID, "HOME": "/home/ekl",
         "GIMP2_DIRECTORY": "/home/ekl/.config/GIMP/3.0"},
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
time.sleep(3)  # GIMP startup

def send_cmd(seq, cmd):
    path = CMD_DIR / f"{seq:04d}_{cmd['cmd']}.json"
    path.write_text(json.dumps(cmd))
    res_path = RES_DIR / f"{seq:04d}_result.json"
    start = time.time()
    while time.time() - start < 30:
        if res_path.exists():
            return json.loads(res_path.read_text())
        time.sleep(0.05)
    return {"error": f"Timeout on seq {seq}"}

results = []

# 1. Create canvas
r = send_cmd(1, {"cmd": "create_canvas", "width": 400, "height": 300, "bg": [0.05, 0.1, 0.2]})
results.append(("create_canvas", r.get("ok", False)))

# 2. Add text
r = send_cmd(2, {"cmd": "add_text", "text": "FIXED!", "x": 60, "y": 140, "size": 32, "color": [1.0, 0.0, 0.0]})
results.append(("add_text", r.get("ok", False)))

# 3. New brush + paint stroke
r = send_cmd(3, {"cmd": "new_brush", "brush_name": "2. Hardness 100", "size": 30})
brush_handle = r.get("handle", "")
results.append(("new_brush", r.get("ok", False)))

# 4. Paint stroke with brush
r = send_cmd(4, {"cmd": "paint_stroke", "brush": brush_handle, "color": [0.0, 1.0, 0.0],
    "strokes": [
        {"type": "moveto", "x": 50, "y": 250},
        {"type": "lineto", "x0": 350, "y0": 250},
    ]})
results.append(("paint_stroke", r.get("ok", False)))

# 5. Paint dab
r = send_cmd(5, {"cmd": "paint_dab", "brush": brush_handle, "x": 200, "y": 200, "color": [1.0, 1.0, 0.0], "size": 40})
results.append(("paint_dab", r.get("ok", False)))

# 6. Export
r = send_cmd(6, {"cmd": "export", "path": str(OUTPUT)})
results.append(("export", r.get("ok", False)))

# 7. Done
send_cmd(7, {"cmd": "done", "path": str(OUTPUT)})

# Wait for GIMP to exit
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.kill()

# Report
print("=== Cave Painter Daemon Fix Test ===")
all_pass = True
for name, ok in results:
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  {status}: {name}")

if OUTPUT.exists():
    size = OUTPUT.stat().st_size
    print(f"  Output: {OUTPUT} ({size} bytes)")
    if size < 1000:
        print(f"  WARNING: output suspiciously small")
        all_pass = False
else:
    print(f"  NO output file at {OUTPUT}")
    all_pass = False

print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
sys.exit(0 if all_pass else 1)
