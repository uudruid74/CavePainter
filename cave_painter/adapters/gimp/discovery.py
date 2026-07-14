"""Locate a usable GIMP executable when CAVE_PAINTER_GIMP_BIN isn't set.
Prefers the console build (gimp-console*) over the GUI build (gimp*) since
this project always launches with --no-interface.
"""
import os
import platform
import re
import shutil
from pathlib import Path

_WINDOWS_CONSOLE_RE = re.compile(r"^gimp-console(-[\d.]+)?\.exe$", re.IGNORECASE)
_WINDOWS_GUI_RE = re.compile(r"^gimp(-[\d.]+)?\.exe$", re.IGNORECASE)


def _find_windows() -> str | None:
    roots = [Path(v) for var in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432") if (v := os.environ.get(var))]
    bases = [b for root in roots for b in (root / "Programs", root)]
    gimp_dirs = sorted(
        {d for base in bases if base.is_dir() for d in base.glob("GIMP*") if d.is_dir()},
        key=lambda p: p.name, reverse=True,
    )
    for gdir in gimp_dirs:
        bin_dir = gdir / "bin"
        if not bin_dir.is_dir():
            continue
        for pattern in (_WINDOWS_CONSOLE_RE, _WINDOWS_GUI_RE):
            matches = sorted(f for f in bin_dir.iterdir() if f.is_file() and pattern.match(f.name))
            if matches:
                return str(matches[-1])
    return None


def _find_macos() -> str | None:
    for app_dir in Path("/Applications").glob("GIMP*.app"):
        for name in ("gimp-console", "gimp"):
            candidate = app_dir / "Contents" / "MacOS" / name
            if candidate.exists():
                return str(candidate)
    return _find_unix()


def _find_unix() -> str | None:
    for name in ("gimp-console", "gimp"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in ("/usr/bin/gimp-console", "/usr/bin/gimp", "/usr/local/bin/gimp", "/snap/bin/gimp"):
        if Path(candidate).exists():
            return candidate
    return None


def discover_gimp_bin() -> str:
    system = platform.system()
    if system == "Windows":
        found = _find_windows()
    elif system == "Darwin":
        found = _find_macos()
    else:
        found = _find_unix()
    return found or "gimp"
