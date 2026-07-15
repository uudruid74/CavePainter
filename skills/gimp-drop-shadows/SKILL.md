---
name: gimp-drop-shadows
description: GIMP 3.x Drop Shadow and Glow Effects — GEGL plug-in for soft glows, inner shadows, and layer effects with context management
category: cave-painter
trigger: When adding drop shadows, soft glows, and inner shadows to text or objects in Cave Painter
---

## GIMP Drop Shadow & Glow Effects

### Overview

This skill covers the GEGL drop shadow plug-in for creating soft glows, inner shadows, and various layer effects. The drop shadow filter is a GEGL-based effect that works best with alpha channels and is essential for professional-looking composites.

**Key Features:**
- Soft glow effects (via blur radius)
- Inner shadows
- Customizable color and opacity
- Proper context management for color consistency
- Works with text, selections, or complete images

### API Reference

| Method | Purpose | Parameters | Notes |
|---|---|---|---|
| `Gimp.get_pdb().lookup_procedure("gimp-edit-dropshadow")` | Perform drop shadow effect | `layer, x_offset, y_offset, blur_radius, grow_radius, color_name, opacity` | Requires alpha channel |
| `Gimp.context_set_foreground()` | Set shadow color | `color_object` | Use after context_push() for safety |
| `Gimp.context_set_background()` | Set background | `color_object` | For contrast layers |
| `Gimp.Displays.flush()` | Force UI update | | Critical for daemon mode |
| `Gimp.context_push()/pop()` | Save/restore context | | Prevents color leakage |

### Code Examples

#### Basic Drop Shadow

```python
from gi.repository import Gimp, Gegl

def apply_drop_shadow(img, layer_name="Drop Shadow", x_offset=20, y_offset=20, blur_radius=10, grow_radius=0, color_name="black", opacity=0.5):
    """Apply a professional drop shadow with context management"""
    if not img.get_layers():
        return

    # Create shadow layer with transparency
    shadow_layer = Gimp.Layer.new(img, layer_name, img.get_width(), img.get_height(), Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    
    # Fill with transparent color
    bg_color = Gegl.Color.new("transparent")
    Gimp.context_set_background(bg_color)
    Gimp.Drawable.edit_fill(shadow_layer, Gimp.FillType.BACKGROUND)
    
    # Move shadow to top for editing
    img.add_layer(shadow_layer, -1)
    
    # Apply drop shadow with context management
    Gimp.context_push()
    try:
        # Set shadow color using PDB procedure for reliability
        shadow_color = Gegl.Color.new(color_name)
        Gimp.context_set_foreground(shadow_color)
        
        # Apply drop shadow using PDB (more reliable than direct API)
        pdb = Gimp.get_pdb()
        drop_shadow_proc = pdb.lookup_procedure("gimp-edit-dropshadow")
        if drop_shadow_proc:
            cfg = drop_shadow_proc.create_config()
            cfg.set_property("layer", shadow_layer)
            cfg.set_property("x-offset", x_offset)
            cfg.set_property("y-offset", y_offset)
            cfg.set_property("blur-radius", blur_radius)
            cfg.set_property("grow-radius", grow_radius)
            cfg.set_property("color", shadow_color)
            cfg.set_property("opacity", opacity)
            drop_shadow_proc.run(cfg)
            
    finally:
        Gimp.context_pop()
        Gimp.displays_flush()

# Usage:
# apply_drop_shadow(current_image, x_offset=15, y_offset=15, blur_radius=8, color_name="#808080", opacity=0.4)
```

#### Soft Glow Effect (Multiple Layers)

```python
def apply_soft_glow(img, layer_name="Glow Layer", blur_radius=15, opacity=0.3, color_name="#ffffff"):
    """Create a soft glow effect with multiple layers"""
    if not img.get_layers():
        return

    # Create glow layer
    glow_layer = Gimp.Layer.new(img, layer_name, img.get_width(), img.get_height(), Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.ADD)
    
    # Fill with semi-transparent color
    glow_color = Gegl.Color.new(color_name)
    Gimp.context_set_foreground(glow_color)
    Gimp.Drawable.edit_fill(glow_layer, Gimp.FillType.FOREGROUND)
    
    # Set layer opacity
    glow_layer.set_opacity(int(100.0 * opacity))
    
    # Add layer to image
    img.add_layer(glow_layer, -1)
    
    # Apply Gaussian blur to glow
    Gimp.Image.undo_group_start(img)
    try:
        Gimp.filter_image(img, "gaussian-blur", {"radius": blur_radius, "sigma": blur_radius / 3.0})
    finally:
        Gimp.Image.undo_group_end(img)
        Gimp.displays_flush()
```

#### Text with Drop Shadow

```python
def apply_text_drop_shadow(img, text_layer, x_offset=5, y_offset=5, blur_radius=5, color_name="black", opacity=0.6):
    """Apply drop shadow to a text layer"""
    Gimp.context_push()
    try:
        # Create shadow for text
        shadow_color = Gegl.Color.new(color_name)
        Gimp.context_set_foreground(shadow_color)
        
        # Create shadow layer
        shadow_layer = Gimp.Layer.new(img, f"{text_layer.get_name()} Shadow", 
                                      text_layer.get_width(), text_layer.get_height(),
                                      Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.OVERLAY)
        
        # Copy text layer content to shadow
        pdb = Gimp.get_pdb()
        copy_proc = pdb.lookup_procedure("gimp-edit-layer-copy")
        if copy_proc:
            cfg = copy_proc.create_config()
            cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
            copy_proc.run(cfg)
            
        # Apply drop shadow
        drop_shadow_proc = pdb.lookup_procedure("gimp-edit-dropshadow")
        if drop_shadow_proc:
            cfg = drop_shadow_proc.create_config()
            cfg.set_property("layer", shadow_layer)
            cfg.set_property("x-offset", x_offset)
            cfg.set_property("y-offset", y_offset)
            cfg.set_property("blur-radius", blur_radius)
            cfg.set_property("grow-radius", 0)
            cfg.set_property("color", shadow_color)
            cfg.set_property("opacity", opacity)
            drop_shadow_proc.run(cfg)
            
    finally:
        Gimp.context_pop()
        Gimp.displays_flush()
```

### Common Pitfalls & Solutions

#### Pitfall 1: Alpha Channel Required
**Problem:** Drop shadow filter is disabled when image lacks an alpha channel.

**Solution:**
```python
# Check for alpha channel
if not img.have_alpha():
    # Add alpha channel to image or layer
    Gimp.Layer.set_mode(layer, Gimp.LayerMode.HOMOGEN_ALPHA)
```

#### Pitfall 2: Context Color Leakage
**Problem:** Foreground color changes don't persist between operations due to brush context snapshots.

**Solution:** Use context_push/pop() consistently:
```python
Gimp.context_push()
try:
    Gimp.context_set_foreground(shadow_color)
    # Apply shadow effect
    Gimp.Drawable.edit_fill(shadow_layer, Gimp.FillType.FOREGROUND)
finally:
    Gimp.context_pop()
```

#### Pitfall 3: Layer Order Issues
**Problem:** Drop shadow appears behind main content instead of in front.

**Solution:** Ensure shadow layers are above the base layer:
```python
img.add_layer(shadow_layer, -1)  # -1 adds to top
```

### Advanced Techniques

#### Multiple Shadow Layers for Realism

```python
def create_multi_shadow(img, base_layer, shadow_color="#000000", shadow_opacity=0.4, blur_amount=15):
    """Create multiple shadow layers for depth and realism"""
    # Main drop shadow
    apply_drop_shadow(img, layer_name="Main Shadow", color_name=shadow_color, 
                      opacity=shadow_opacity, blur_radius=blur_amount)
    
    # Secondary softer shadow
    apply_drop_shadow(img, layer_name="Secondary Shadow", x_offset=10, y_offset=10,
                      blur_radius=blur_amount * 1.5, opacity=shadow_opacity * 0.5,
                      color_name=shadow_color)
    
    # Edge highlight (optional)
    # Can add subtle edge highlight for surface sheen
```

### Canvas Flush Requirements

**CRITICAL:** Always call `Gimp.displays_flush()` after GIMP operations that modify the image:

```python
Gimp.displays_flush()
```

This is especially important in daemon mode where UI updates might not auto-refresh.

### Integration with gimp-mcp-patterns

This skill follows the patterns from `gimp-mcp-patterns`:

1. **Context Management:** Uses `context_push()`/`context_pop()` for color safety
2. **Class Methods:** Uses `Gimp.Drawable.edit_fill()` class syntax
3. **Undo Groups:** Wraps multi-layer operations in undo groups
4. **Canvas Flush:** Calls `Gimp.displays_flush()` after modifications
5. **PDB Fallbacks:** Uses PDB procedures when direct API fails

### Performance Tips

- Use `undo_group_start/end()` for multi-step operations
- Batch similar shadows together
- Consider layer masks for complex shadow blending
- Use the `grow-radius` parameter to avoid additional blur steps

### Further Reading


- [GEGL Drop Shadow Documentation](https://docs.gimp.org/3.0/en/gimp-filter-drop-shadow.html)
- [GEGL Bevel Documentation](https://docs.gimp.org/3.0/en/gegl-bevel.html)
- [GEGL Styles Documentation](https://docs.gimp.org/3.0/en/gegl-styles.html)