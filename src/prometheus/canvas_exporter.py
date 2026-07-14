"""
Prometheus Canvas Exporter — P0 Component 2.

Flattens the GIMP image, exports as PNG, and computes a bounding-rect
crop of changed pixels between two snapshots.

Key constraints:
  - GIMP 3.x embedded Python — stdlib only (no PIL/numpy/OpenCV).
  - Pixel diff via GdkPixbuf byte comparison.
  - Cropping via GdkPixbuf.Pixbuf.new_subpixbuf().

Architecture note:
  DeepSeek V4-Flash has native vision.  The cropped 'after' PNG is
  attached inline as MEDIA: path — no auxiliary vision pipeline needed.
  Cost: ~$0.000013/image at 90 KV entries.
"""

import os
import uuid
from gi.repository import Gimp, Gio, GdkPixbuf


EXPORT_DIR = "/tmp/prometheus"
os.makedirs(EXPORT_DIR, exist_ok=True)


def export_full_png(image, label="snapshot"):
    """Flatten image, export as full-canvas PNG to /tmp/prometheus/.

    Works on a duplicate so the original image is not modified.

    Args:
        image: Gimp.Image to export.
        label: Prefix for the generated filename.

    Returns:
        Absolute path to the saved PNG, or None on failure.
    """
    dup = image.duplicate()
    try:
        # Flatten merges all visible layers onto a single background
        dup.flatten()

        fname = f"{label}_{uuid.uuid4().hex[:8]}.png"
        path = os.path.join(EXPORT_DIR, fname)
        gfile = Gio.File.new_for_path(path)
        result = Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, dup, gfile, None)

        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
        return None
    finally:
        dup.delete()


def _pixbuf_from_png(path):
    """Load a PNG file into a GdkPixbuf.Pixbuf."""
    return GdkPixbuf.Pixbuf.new_from_file(path)


def _pixels_differ(a, b, x, y, n_channels):
    """Compare one pixel at (x, y) between two pixbufs.

    Args:
        a, b: GdkPixbuf.Pixbuf instances of identical dimensions.
        x, y: Pixel coordinate.
        n_channels: 3 (RGB) or 4 (RGBA).

    Returns:
        True if any channel differs.
    """
    rowstride = a.get_rowstride()
    offset = y * rowstride + x * n_channels
    a_pixels = a.get_pixels()
    b_pixels = b.get_pixels()
    for c in range(n_channels):
        if a_pixels[offset + c] != b_pixels[offset + c]:
            return True
    return False


def compute_diff_rect(before_path, after_path):
    """Compute the bounding rectangle of changed pixels between two PNGs.

    Reads raw pixel bytes via GdkPixbuf — no PIL/numpy needed.
    Compare byte-by-byte row by row.

    Args:
        before_path: Path to "before" PNG.
        after_path: Path to "after" PNG.

    Returns:
        dict with keys x, y, width, height of the bounding rect,
        or None if the images are identical or dimensions mismatch.
    """
    a = _pixbuf_from_png(after_path)
    b = _pixbuf_from_png(before_path)

    if a.get_width() != b.get_width() or a.get_height() != b.get_height():
        return None  # Dimension mismatch — shouldn't happen for same canvas

    w = a.get_width()
    h = a.get_height()
    nch = a.get_n_channels()

    min_x, min_y = w, h
    max_x, max_y = -1, -1

    for y in range(h):
        row_has_change = False
        for x in range(w):
            if _pixels_differ(a, b, x, y, nch):
                row_has_change = True
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
        if row_has_change:
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y

    if max_x < 0:  # No changes found
        return None

    # Add a small margin (2px) to ensure edge changes aren't clipped
    margin = 2
    min_x = max(0, min_x - margin)
    min_y = max(0, min_y - margin)
    max_x = min(w - 1, max_x + margin)
    max_y = min(h - 1, max_y + margin)

    return {
        "x": min_x,
        "y": min_y,
        "width": max_x - min_x + 1,
        "height": max_y - min_y + 1,
    }


def crop_png(source_path, rect, output_label="diff"):
    """Crop a PNG to a bounding rectangle.

    Args:
        source_path: Path to the full PNG.
        rect: {"x", "y", "width", "height"} from compute_diff_rect().
        output_label: Prefix for the output filename.

    Returns:
        Absolute path to cropped PNG, or None on failure.
    """
    pixbuf = _pixbuf_from_png(source_path)
    cropped = GdkPixbuf.Pixbuf.new_subpixbuf(
        pixbuf, rect["x"], rect["y"], rect["width"], rect["height"]
    )

    fname = f"{output_label}_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(EXPORT_DIR, fname)
    cropped.savev(path, "png", [], [])
    return path if os.path.exists(path) else None


def export_diff(before_path, after_path):
    """Full diff pipeline: compute rect, crop after image to changed region.

    Args:
        before_path: Path to before snapshot PNG.
        after_path: Path to after snapshot PNG.

    Returns:
        (diff_rect dict, cropped_png_path) or (None, None) on no change/failure.
    """
    rect = compute_diff_rect(before_path, after_path)
    if rect is None:
        return None, None

    cropped = crop_png(after_path, rect, "diff")
    return rect, cropped
