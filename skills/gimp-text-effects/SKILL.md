---
name: gimp-text-effects
description: GIMP 3.x Text Effects — Bevel, emboss, shadow, and text along path using gimp-text-fontname and GEGL filters with context management
category: cave-painter
trigger: When adding bevel, emboss, and shadow effects to text or creating text along paths in Cave Painter
---

## GIMP Text Effects & Manipulation

### Overview

This skill covers advanced text effects in GIMP 3.x, including bevel, emboss, shadow effects, and text along path manipulation. It uses the PDB `gimp-text-fontname` for reliable text creation and GEGL filters for professional text styling.

**Key Features:**
- Bevel and emboss effects using GEGL filters
- Drop shadow for text
- Text along path manipulation
- Context-safe color and layer management
- Integration with `gimp-mcp-patterns` for proper workflow

### API Reference

| Method | Purpose | Parameters | Notes |
|---|---|---|---|
| `Gimp.get_pdb().lookup_procedure("gimp-text-fontname")` | Create text layer with font | `drawable, font_name, size, attributes, text, angle` | Reliable PDB-based text creation |
| `Gimp.get_pdb().lookup_procedure("gimp-edit-dropshadow")` | Apply drop shadow | `layer, x_offset, y_offset, blur_radius, color, opacity` | Works with alpha channels |
| `Gimp.get_pdb().lookup_procedure("gimp-edit-bevel")` | Apply bevel effect | `layer, bevel_type, radius, elevation, depth` | Chamfer or Bump bevel |
| `Gimp.Image.select_path()` | Create text along path | `path, operation, offset_x, offset_y` | Convert path to selection |
| `Gimp.context_set_foreground()/background()` | Set text/shadow colors | `color_object` | Use with context_push() for safety |
| `Gimp.Drawable.edit_fill()` | Fill text layers | `fill_type` | Uses context colors |
| `Gimp.context_push()/pop()` | Context management | | Prevents color leakage |

### Code Examples

#### Basic Text Creation with PDB

```python
from gi.repository import Gimp, Gegl

def create_text_layer(img, font_name="Arial", font_size=24, text="Sample Text", angle=0, x=50, y=50):
    """Create a text layer using PDB for reliability"""
    Gimp.context_push()
    try:
        # Create text using PDB procedure (more reliable than direct API)
        pdb = Gimp.get_pdb()
        text_proc = pdb.lookup_procedure("gimp-text-fontname")
        if not text_proc:
            raise Exception("gimp-text-fontname PDB procedure not found")
            
        cfg = text_proc.create_config()
        cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
        cfg.set_property("drawable", img)
        cfg.set_property("font-name", font_name)
        cfg.set_property("size", font_size)
        cfg.set_property("attributes", Gimp.TextAttributes.NORMAL)
        cfg.set_property("text", text)
        cfg.set_property("angle", angle)
        cfg.set_property("x", x)
        cfg.set_property("y", y)
        
        text_proc.run(cfg)
        
        # Get the created text layer
        layers = img.get_layers()
        if layers:
            text_layer = layers[-1]  # Last layer created should be the text
            return text_layer
            
    finally:
        Gimp.context_pop()
        Gimp.displays_flush()
```

#### Apply Bevel & Emboss to Text

```python
def apply_text_bevel(img, text_layer, bevel_type="chamfer", radius=5.0, elevation=45.0, depth=2.0, color_name="#808080"):
    """Apply professional bevel and emboss effects to text layers"""
    Gimp.context_push()
    try:
        # Map bevel types to GEGL enum values
        if bevel_type.lower() == "bump":
            bevel_type_enum = "bump"
        else:
            bevel_type_enum = "chamfer"
            
        # Set bevel color using context
        bevel_color = Gegl.Color.new(color_name)
        Gimp.context_set_foreground(bevel_color)
        
        # Apply bevel using PDB (more reliable)
        pdb = Gimp.get_pdb()
        bevel_proc = pdb.lookup_procedure("gimp-edit-bevel")
        if not bevel_proc:
            raise Exception("gimp-edit-bevel PDB procedure not found")
            
        cfg = bevel_proc.create_config()
        cfg.set_property("layer", text_layer)
        cfg.set_property("bevel-type", bevel_type_enum)
        cfg.set_property("radius", radius)
        cfg.set_property("elevation", elevation)
        cfg.set_property("depth", depth)
        cfg.set_property("color", bevel_color)
        
        bevel_proc.run(cfg)
        
    finally:
        Gimp.context_pop()
        Gimp.displays_flush()
```

#### Add Drop Shadow to Text

```python
def apply_text_shadow(img, text_layer, x_offset=5, y_offset=5, blur_radius=5, color_name="black", opacity=0.6):
    """Apply drop shadow to text layers"""
    Gimp.context_push()
    try:
        # Ensure text layer has alpha channel for shadow
        if not text_layer.have_alpha():
            Gimp.Layer.set_mode(text_layer, Gimp.LayerMode.HOMOGEN_ALPHA)
            
        # Set shadow color
        shadow_color = Gegl.Color.new(color_name)
        Gimp.context_set_foreground(shadow_color)
        
        # Create shadow layer
        shadow_width = text_layer.get_width()
        shadow_height = text_layer.get_height()
        shadow_layer = Gimp.Layer.new(img, f"{text_layer.get_name()} Shadow",
                                      shadow_width, shadow_height,
                                      Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.OVERLAY)
        
        # Fill shadow with semi-transparent black
        Gimp.Drawable.edit_fill(shadow_layer, Gimp.FillType.BACKGROUND)
        
        # Apply drop shadow effect
        pdb = Gimp.get_pdb()
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
            
        # Add shadow layer to image
        img.add_layer(shadow_layer, -1)
        
    finally:
        Gimp.context_pop()
        Gimp.displays_flush()
```

#### Text Along Path

```python
def create_text_along_path(img, path, font_name="Arial", font_size=24, text="Text Along Path"):
    """Create text that follows a path curve"""
    Gimp.context_push()
    try:
        # First create the text
        pdb = Gimp.get_pdb()
        text_proc = pdb.lookup_procedure("gimp-text-fontname")
        if not text_proc:
            raise Exception("gimp-text-fontname PDB procedure not found")
            
        cfg = text_proc.create_config()
        cfg.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
        cfg.set_property("drawable", img)
        cfg.set_property("font-name", font_name)
        cfg.set_property("size", font_size)
        cfg.set_property("attributes", Gimp.TextAttributes.NORMAL)
        cfg.set_property("text", text)
        
        text_proc.run(cfg)
        
        # Get text layer
        layers = img.get_layers()
        if not layers:
            return None
            
        text_layer = layers[-1]
        
        # Apply path constraint
        path_proc = pdb.lookup_procedure("gimp-image-select-path")
        if path_proc:
            cfg = path_proc.create_config()
            cfg.set_property("image", img)
            cfg.set_property("path", path)
            cfg.set_property("operation", Gimp.ChannelOps.REPLACE)
            cfg.set_property("inherit", True)
            path_proc.run(cfg)
            
        # Deselect
        pdb = Gimp.get_pdb()
        none_proc = pdb.lookup_procedure("gimp-selection-none")
        if none_proc:
            cfg = none_proc.create_config()
            cfg.set_property("image", img)
            none_proc.run(cfg)
            
        Gimp.displays_flush()
        return text_layer
        
    finally:
        Gimp.context_pop()
```

#### Complete Text Effect Composition

```python
def create_advanced_text_effect(img, font_name="Arial Black", font_size=48, main_text="EFFECTIVE
TEXT",
                                 shadow_color="#333333", shadow_opacity=0.7, shadow_blur=8,
                                 bevel_type="bump", bevel_radius=3.0, bevel_elevation=30.0,
                                 text_color="#FFFFFF", x=100, y=100):
    """Create a comprehensive text effect with shadow, bevel, and glow"""
    Gimp.Image.undo_group_start(img)
    try:
        # Create base text layer
        text_layer = create_text_layer(img, font_name, font_size, main_text, 0, x, y)
        
        # Set text color (this applies to the layer)
        text_color_obj = Gegl.Color.new(text_color)
        Gimp.context_push()
        try:
            Gimp.context_set_foreground(text_color_obj)
            # Apply text color
            Gimp.Drawable.edit_fill(text_layer, Gimp.FillType.FOREGROUND)
        finally:
            Gimp.context_pop()
            
        # Apply drop shadow
        apply_text_shadow(img, text_layer, x_offset=4, y_offset=4, 
                         blur_radius=shadow_blur, color_name=shadow_color,
                         opacity=shadow_opacity)
                         
        # Apply bevel and emboss
        apply_text_bevel(img, text_layer, bevel_type=bevel_type, 
                         radius=bevel_radius, elevation=bevel_elevation,
                         depth=2.0, color_name="#666666")
                         
        Gimp.displays_flush()
        return text_layer
        
    finally:
        Gimp.Image.undo_group_end(img)
```

### Common Pitfalls & Solutions

#### Pitfall 1: Text Not Visible
**Problem:** Text layer created but not visible or empty.

**Solution:**
```python
# Ensure proper font handling - try common system fonts if Arial fails
common_fonts = ["Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"]
for font in common_fonts:
    try:
        text_layer = create_text_layer(img, font, 24, "Test")
        if text_layer and text_layer.get_width() > 0:
            return text_layer
    except:
        continue
raise Exception(f"Could not create text with any of {common_fonts}")
```

#### Pitfall 2: Bevel/Emboss Not Working
**Problem:** Bevel effects appear invisible or don't apply correctly.

**Solution:**
```python
# Ensure alpha channel for text before applying bevel
if not text_layer.have_alpha():
    Gimp.Layer.set_mode(text_layer, Gimp.LayerMode.HOMOGEN_ALPHA)
    
# Check if bevel procedure exists before using
pdb = Gimp.get_pdb()
bevel_proc = pdb.lookup_procedure("gimp-edit-bevel")
if not bevel_proc:
    # Fallback to GEGL filter
    Gimp.filter_image(img, "gegl-bevel", {"radius": 5.0, "elevation": 45.0})
```

#### Pitfall 3: Shadow Overflows Text Bounds
**Problem:** Drop shadow extends beyond text boundaries.

**Solution:**
```python
# Clip shadow to text bounds
grow_proc = pdb.lookup_procedure("gimp-selection-grow")
if grow_proc:
    cfg = grow_proc.create_config()
    cfg.set_property("radius", 1)
    cfg.set_property("invert", False)
    grow_proc.run(cfg)
```

### Advanced Techniques

#### Multiple Text Layers for Depth

```python
def create_text_depth_effect(img, font_name="Arial", font_size=48, text="DEPTH EFFECT"):
    """Create text with layered depth effect"""
    depth_layers = []
    
    # Create base text
    base_layer = create_text_layer(img, font_name, font_size, text)
    depth_layers.append(base_layer)
    
    # Add shadow layer
    apply_text_shadow(img, base_layer, x_offset=3, y_offset=3, 
                     blur_radius=6, color_name="#000000", opacity=0.5)
    
    # Add highlight/glow effect
    Gimp.context_push()
    try:
        highlight_color = Gegl.Color.new("#FFFFFF")
        Gimp.context_set_foreground(highlight_color)
        
        highlight_layer = Gimp.Layer.new(img, f"{font_name} Highlight",
                                        img.get_width(), img.get_height(),
                                        Gimp.ImageType.RGBA_IMAGE, 50.0, Gimp.LayerMode.ADD)
        
        Gimp.Drawable.edit_fill(highlight_layer, Gimp.FillType.FOREGROUND)
        img.add_layer(highlight_layer, -1)
        depth_layers.append(highlight_layer)
        
    finally:
        Gimp.context_pop()
        
    return depth_layers
```

#### Text with 3D Extrusion Effect

```python
def create_text_3d_effect(img, font_name="Arial", font_size=72, text="3D TEXT"):
    """Create 3D extrusion text effect"""
    Gimp.Image.undo_group_start(img)
    try:
        # Create main text layer
        main_layer = create_text_layer(img, font_name, font_size, text)
        
        # Apply base bevel
        apply_text_bevel(img, main_layer, bevel_type="bump", radius=8.0, 
                         elevation=45.0, depth=3.0, color_name="#444444")
        
        # Add secondary bevel for depth
        apply_text_bevel(img, main_layer, bevel_type="chamfer", radius=4.0,
                         elevation=135.0, depth=2.0, color_name="#888888")
        
        # Add subtle shadow
        apply_text_shadow(img, main_layer, x_offset=2, y_offset=2,
                         blur_radius=10, color_name="#000000", opacity=0.4)
        
        Gimp.displays_flush()
        return main_layer
        
    finally:
        Gimp.Image.undo_group_end(img)
```

### Integration with gimp-mcp-patterns

This skill follows established patterns from `gimp-mcp-patterns`:

1. **Context Management:** Uses `context_push()`/`context_pop()` for color safety
2. **PDB Procedures:** Uses reliable PDB procedures instead of direct API calls
3. **Undo Groups:** Wraps complex text operations in undo groups
4. **Canvas Flush:** Calls `Gimp.displays_flush()` after modifications
5. **Selection Management:** Proper use of `Gimp.Selection.none()` to clear selections

### Performance Tips

- Use undo groups (`undo_group_start/end()`) for multi-step text operations
- Batch text creation operations when possible
- Limit the number of bevel/shadow effects on complex text
- Consider using layer masks for precise text masking
- Use PDB procedures for reliability over direct API calls

### Further Reading


- [GEGL Bevel Documentation](https://docs.gimp.org/3.0/en/gegl-bevel.html)
- [GEGL Styles Documentation](https://docs.gimp.org/3.0/en/gegl-styles.html)
- [GEGL Drop Shadow Documentation](https://docs.gimp.org/3.0/en/gimp-filter-drop-shadow.html)
- [GIMP Text Tool Guide](https://docs.gimp.org/3.0/en/gimp-tool-text.html)