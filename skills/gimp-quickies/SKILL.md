---
name: gimp-quickies
description: Quick GIMP tips for common tasks - scaling, cropping, rotating, exporting, and basic image modifications
category: cave-painter
trigger: When you need simple but practical GIMP operations without learning full workflows
---

## GIMP Quickies - Practical Tips for Common Tasks

### Scaling Images

#### Reduce Image Size for Web/Email

**Problem:** Image too large (1225×1280) for certain uses
**Solution:** Use Scale Image dialog

```python
# Scale image to web dimensions
image.scale(width=600, height=627, quality=LOHALO)
Gimp.displays_flush()
```

**Steps:**
1. Image → Scale Image…
2. Enter new Width/Height (chain keeps aspect ratio)
3. Choose interpolation (LoHalo for best quality)
4. Export or Overwrite

**Key Points:**
- Use LoHalo interpolation for best quality
- Chain maintains aspect ratio
- Export to preserve original

### Cropping Images

#### Remove Borders or Focus on Details

**Method 1 - Crop Tool:**
```python
# Using Crop tool
gimp_tool_crop.start()
drag_selection()
press_enter_to_commit()
```

**Method 2 - Crop to Selection:**
```python
# Select region first
Gimp.Image.select_rectangle(img, Gimp.ChannelOps.REPLACE, x, y, width, height)
Gimp.Image.crop_to_selection(img)
Gimp.displays_flush()
```

**Steps:**
1. Use Crop Tool or Rectangle Select Tool
2. Fine-tune selection handles
3. Press Enter to commit crop
4. Image → Crop to Selection (for rectangle method)

### Rotating and Flipping

#### Rotate 90° Increments

```python
# Rotate entire image
Gimp.Image.transform_rotate_90CW(image)
Gimp.displays_flush()
```

**Steps:**
1. Image → Transform
2. Choose Rotate 90° CW/CW/CCW or 180°
3. Note: Arbitrary rotations work per-layer only

#### Flip Image

```python
# Mirror along axis
Gimp.Image.transform_flip_horizontal(image)
Gimp.displays_flush()
```

**Steps:**
1. Image → Transform
2. Choose Flip Horizontally or Vertically

### Image Size (Filesize) - JPEG Compression

#### Reduce File Size for Web

**Problem:** Large filesize despite small dimensions
**Solution:** Use JPEG export compression

```python
# Export with compression settings
Gimp.File.export(img, "filename.jpg", quality=80)
Gimp.displays_flush()
```

**Steps:**
1. File → Export…
2. Enter filename (.jpg extension)
3. Choose quality (80 shows size preview)
4. Export with desired quality

**Quality Levels:**
- 90-100: Best quality, larger files
- 70-85: Good balance, common web use
- 50-60: Smallest files, visible compression

### Quick Color Adjustments

#### Change Foreground/Background Colors

```python
# Set foreground color
Gimp.context_push()
try:
    color = Gegl.Color.new(0.8, 0.2, 0.2)  # RGB values 0.0-1.0
    Gimp.context_set_foreground(color)
    # Use color in fill operations
    layer.edit_fill(Gimp.FillType.FOREGROUND)
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

#### Swap Colors Quickly

```python
# Keyboard shortcut: X key
Gimp.context_set_foreground(Gimp.context_get_background())
Gimp.context_set_background(Gimp.context_get_foreground())
```

### Fill with Color

#### Quick Background Fill

```python
# Fill layer with color
Gimp.context_push()
try:
    Gimp.context_set_foreground(Gegl.Color.new(0, 0, 0))  # Black
    # For selection-aware fill, ensure selection exists first
    Gimp.Drawable.edit_fill(layer, Gimp.FillType.FOREGROUND)
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### Common Workflow Integration

```python
# Complete workflow: Create, scale, crop, export
Gimp.context_push()
try:
    # Create new image
    image = Gimp.Image.new(256, 128, Gimp.ImageBaseType.RGB)
    bg_layer = Gimp.Layer.new(image, "Background", 256, 128, 
                              Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.NORMAL)
    
    # Fill with background color
    Gimp.context_set_background(Gegl.Color.new(0, 0, 0))  # Black
    Gimp.Drawable.edit_fill(bg_layer, Gimp.FillType.BACKGROUND)
    
    # Scale if needed
    Gimp.Image.scale(image, 600, 314, Gimp.InterpolationType.LOHALO)
    
    # Crop to desired area
    Gimp.Image.crop_to_selection(image)  # Uses current selection
    
    # Export
    Gimp.File.export(image, "output.jpg", quality=80)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### Tips and Tricks

- **Zoom View:** Use magnifying glass tool to check pixel dimensions at top of window
- **Export vs Save:** Export creates new file, Save overwrites
- **Size Units:** Click px spinner to use percentage (50 for half size)
- **Quick Swap:** X key swaps foreground/background colors
- **Selection Management:** Use `Gimp.Selection.none(image)` to clear selections
- **Undo:** Use Ctrl+Z or Edit → Undo

### When to Use

- **Quick modifications:** Scaling, cropping, rotating
- **Web optimization:** File size reduction
- **Batch processing:** For multiple similar images
- **Learning foundation:** Builds understanding for advanced workflows

### Recommended Learning Path

1. Start with these quickies
2. Build on with detailed tutorials
3. Master layer masks and effects
4. Learn advanced filters and GEGL operations
5. Create custom workflows and tools