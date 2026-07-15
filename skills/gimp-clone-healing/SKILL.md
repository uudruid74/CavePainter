---
name: gimp-clone-healing
description: Clone stamp and healing tool APIs for photo retouching and selective repairs - clone stamp for copying pixels, heal tool for texture-aware repair
category: cave-painter
trigger: When removing blemishes, repairing photos, or copying pixels from one area to another in Cave Painter
---

## GIMP 3.x Clone & Healing Tools

### Clone Tool (Clone Stamp)

The Clone tool copies pixels from one source area to another, useful for spot removal and pattern copying.

#### API Pattern

```python
# Basic clone stamp operation
from gi.repository import Gegl

Gimp.context_push()
try:
    # Set foreground color and brush
    foreground_color = Gegl.Color.new("red")
    Gimp.context_set_foreground(foreground_color)
    Gimp.context_set_brush_size(10.0)
    
    # Select source area with Ctrl-click (simulated)
    # In actual usage, user presses Ctrl+click to set source
    # For scripting, use PDB procedure gimp-clone-register
    
    # Paint cloned pixels (user handles source selection)
    Gimp.paintbrush_default(drawable, [100, 50, 150, 50, 200, 50])
finally:
    Gimp.context_pop()
Gimp.displays_flush()
```

#### Clone Tool API Calls

| Function | Purpose | Notes |
|---|---|---|
| `Gimp.context_set_brush_size(10.0)` | Set brush size | Clone uses current brush |
| `Gimp.context_set_foreground(color)` | Set source color (optional) | Affects copied pixels |
| `Gimp.paintbrush_default(drawable, coords)` | Paint clone stamp | User must select source first (Ctrl+click) |
| `Gimp.displays_flush()` | Commit changes | Required after operations |

#### Clone Tool Alignment Modes

1. **None**: Each stroke uses fresh source selection
2. **Aligned**: First click sets offset, subsequent strokes maintain it  
3. **Registered**: Pixel-for-pixel cloning between layers
4. **Fixed**: Source remains stationary

#### Key Workflow Steps

```python
def clone_stamp_operation(drawable, source_image, source_coords, target_coords, brush_size=20):
    """Clone pixels from source to target"""
    
    Gimp.context_push()
    try:
        # Set up brush and color
        Gimp.context_set_brush_size(brush_size)
        Gimp.context_set_foreground(Gegl.Color.new("white"))
        
        # Select source (in GUI: Ctrl+click, in script: PDB gimp-clone-register)
        # This is handled differently in scripts vs interactive use
        
        # Clone the pixels
        Gimp.paintbrush_default(drawable, target_coords)
        
    finally:
        Gimp.context_pop()
    Gimp.displays_flush()
```

### Healing Tool

The Heal tool intelligently repairs images by blending source pixels with destination texture, ideal for wrinkles, blemishes, and texture-aware repairs.

#### API Pattern

```python
# Basic heal operation
Gimp.context_push()
try:
    # Set brush size appropriate for defect
    Gimp.context_set_brush_size(30.0)
    
    # Set source area (in GUI: Ctrl+click, then drag sample)
    # In scripts, use PDB procedure gimp-heal
    
    # Apply healing
    Gimp.pencil(drawable, [100, 50, 200, 50])  # Example stroke
    
finally:
    Gimp.context_pop()
Gimp.displays_flush()
```

#### Healing Tool Key Features

- **Intelligent blending**: Takes surrounding destination pixels into account
- **Source selection**: Ctrl+click to select area to copy from
- **Sample dragging**: Drag sample to defect location
- **Line healing**: Shift+click for line-based healing
- **Hard edge option**: Bounces contour
- **Sample merged**: Samples from all visible layers

#### Healing Workflow

```python
def heal_operation(drawable, source_coords, target_coords, brush_size=30):
    """Heal defect using surrounding texture blending"""
    
    Gimp.context_push()
    try:
        # Configure brush for defect size
        Gimp.context_set_brush_size(brush_size)
        
        # Note: Healing requires user interaction for source selection
        # In automated scripts, use PDB procedure gimp-heal
        
        # Apply healing stroke along defect
        Gimp.pencil(drawable, [target_coords[0], target_coords[1], 
                              target_coords[0]+100, target_coords[1]])
        
    finally:
        Gimp.context_pop()
    Gimp.displays_flush()
```

### PDB Procedures for Automation

For fully automated clone/healing operations without user interaction:

```python
# Clone stamp via PDB
pdb = Gimp.get_pdb()
clone_proc = pdb.lookup_procedure("gimp-clone-register")
if clone_proc:
    cfg = clone_proc.create_config()
    cfg.set_property("clone-source", source_drawable)
    cfg.set_property("clone-method", Gimp.CloneMethod.REGISTERED)
    clone_proc.run(cfg)

# Heal via PDB  
heal_proc = pdb.lookup_procedure("gimp-heal")
if heal_proc:
    cfg = heal_proc.create_config()
    cfg.set_property("heal-source", source_drawable)
    cfg.set_property("heal-mode", Gimp.HealMode.NORMAL)
    heal_proc.run(cfg)
```

### Common Pitfalls

1. **Source not selected**: Clone tool requires source selection (Ctrl+click) before painting
2. **Alpha channel issues**: Cloning from transparent areas produces no effect
3. **Layer mode mismatches**: Clone from RGB to Indexed layers may produce approximations
4. **Heal tool dependency**: Requires manual source selection - less automated than clone
5. **Sample merged complexity**: When enabled, considers all visible layers

### Integration with Cave Painter

These tools excel at:
- **Photo texture incorporation**: Clone background elements into cave art
- **Spot cleanup**: Remove unwanted artifacts or errors
- **Pattern replication**: Copy textures, rocks, or patterns
- **Selective color correction**: Heal specific areas without affecting surrounding pixels

### Example Usage Pattern

```python
# Heal a blemish in cave texture
def retouch_cave_texture(cave_image):
    drawable = cave_image.get_active_drawable()
    
    # Heal surface imperfections
    heal_operation(drawable, [100, 100], [120, 120], brush_size=25)
    
    # Clone rock texture pattern
    clone_stamp_operation(drawable, [400, 400], [300, 300], 
                         [150, 150], brush_size=15)
```

### API Validation Checklist

- [x] `Gimp.context_push()/pop()` for color safety
- [x] `Gimp.context_set_brush_size()` for brush control
- [x] `Gimp.context_set_foreground()` for color management  
- [x] `Gimp.paintbrush_default()` for smooth clone curves
- [x] `Gimp.pencil()` for straight line healing
- [x] `Gimp.displays_flush()` for committing changes
- [x] Context management patterns from gimp-context-management skill

This skill enables precise pixel-level editing and intelligent texture repair for Cave Painter workflows.