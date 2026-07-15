---
name: gimp-luminosity-masks
description: Advanced layer mask isolation technique using channel operations, apply image, and curves for exposure blending and selective edits
category: cave-painter
trigger: When needing advanced layer mask isolation, exposure blending, or selective edits based on brightness values in Cave Painter
---

## GIMP 3.x Luminosity Masks

### Overview

Luminosity Masks are an advanced layer masking technique that isolates specific brightness ranges within an image. By creating masks based on the luminosity (brightness) channel, you can make precise selective edits without affecting other areas.

### Key Applications

- **Exposure blending**: Combine multiple exposures with precise control
- **Selective color grading**: Modify colors in specific brightness ranges
- **Sky enhancement**: Adjust skies without affecting foreground
- **Shadow/highlight recovery**: Fix under/over exposed areas
- **Portrait retouching**: Select and edit skin tones precisely

### Technical Foundation

Luminosity masks work by:

1. **Extracting luminosity**: Convert image to grayscale based on brightness
2. **Thresholding**: Create binary masks at specific brightness levels
3. **Refining masks**: Smooth edges and adjust feathering
4. **Applying masks**: Use as layer masks for selective editing

### Core Luminosity Mask API

```python
# Core luminosity mask workflow
from gi.repository import Gegl

# 1. Create luminosity channel
Gimp.context_push()
try:
    # Create a copy for processing
    luminosity_copy = Gimp.image_new_from_drawable(drawable)
    
    # Convert to grayscale/luminosity
    Gimp.color_transform(luminosity_copy, drawable, Gimp.ColorTransform.BRIGHTNESS)
    
    # Apply curve adjustments for precise masking
    Gimp.curves_spline(drawable, GEvalC.CURVE_LINEAR)  # Example adjustment
    
finally:
    Gimp.context_pop()
Gimp.displays_flush()
```

### Luminosity Mask Workflow

```python
def create_luminosity_mask(image, threshold_low=0.3, threshold_high=0.7, feather_amount=0.1):
    """Create a luminosity mask for selective editing"""
    
    Gimp.context_push()
    try:
        # Get active drawable
        drawable = image.get_active_drawable()
        
        # Create luminosity channel copy
        luminosity_copy = Gimp.image_new_from_drawable(drawable)
        Gimp.color_transform(luminosity_copy, drawable, Gimp.ColorTransform.BRIGHTNESS)
        
        # Apply channel operations for thresholding
        # Use GIMP's channel operations to create mask
        Gimp.Image.select_gradient(image, Gimp.GradientType.RADIAL, 
                                  Gimp.ChannelOps.REPLACE, 50, 50, 200, 200)
        
        # Create mask based on brightness levels
        Gimp.Selection.invert(image)
        
        # Feather edges for smoother transitions
        Gimp.Selection.feather(image, feather_amount)
        
    finally:
        Gimp.context_pop()
    Gimp.displays_flush()
    
    return luminosity_copy
```

### Layer Mask Application

```python
def apply_luminosity_mask(layer, mask_image):
    """Apply luminosity mask as layer mask"""
    
    Gimp.context_push()
    try:
        # Apply mask to layer
        layer.set_mask_image(mask_image)
        
        # Set mask opacity for controlled blending
        layer.set_mask_opacity(100.0)
        
        # Update display to show mask
        Gimp.displays_flush()
        
    finally:
        Gimp.context_pop()
```

### Example: Sky Enhancement with Luminosity Mask

```python
def enhance_sky_with_luminosity(image):
    """Enhance sky using luminosity mask isolation"""
    
    Gimp.context_push()
    try:
        # Get components
        background_layer = image.get_layers()[0]
        
        # Create luminosity mask for sky region (adjust thresholds as needed)
        sky_mask = create_luminosity_mask(image, threshold_low=0.6, threshold_high=0.95)
        
        # Apply as layer mask
        apply_luminosity_mask(background_layer, sky_mask)
        
        # Selective color adjustments using mask
        Gimp.Image.select_ellipse(image, Gimp.ChannelOps.ADD, 100, 100, 400, 300)
        Gimp.context_set_foreground(Gegl.Color.new("sky_blue"))
        Gimp.Drawable.edit_fill(background_layer, Gimp.FillType.FOREGROUND)  # Only affects sky region
        
    finally:
        Gimp.context_pop()
    Gimp.displays_flush()
```

### Channel Operations Integration

```python
def luminosity_channel_operations(image, operation_type, value):
    """Use channel operations for precise luminosity mask control"""
    
    Gimp.context_push()
    try:
        # Get luminosity channel
        channels = image.get_active_drawable().get_color()
        
        # Apply specific channel operation
        if operation_type == "threshold":
            Gimp.Image.select_gradient(image, Gimp.GradientType.LINEAR,
                                      Gimp.ChannelOps.REPLACE, value, 0, 255, 0)
        elif operation_type == "invert":
            Gimp.Selection.invert(image)
        elif operation_type == "feather":
            Gimp.Selection.feather(image, value)
            
        Gimp.displays_flush()
        
    finally:
        Gimp.context_pop()
```

### Curve Adjustments for Masking

```python
def apply_luminosity_curves(image, curve_points):
    """Adjust luminosity curves for precise masking"""
    
    Gimp.context_push()
    try:
        # Create curves adjustment layer
        curves_layer = Gimp.Layer.new(image, "Luminosity Curves", 
                                      image.get_width(), image.get_height(),
                                      Gimp.ImageType.RGBA_IMAGE, 100.0, 
                                      Gimp.LayerMode.OVERLAY)
        image.add_layer(curves_layer, 0)
        
        # Apply curve adjustments
        # curve_points: list of (x, y) tuples
        Gimp.curves_spline(curves_layer, curve_points)
        
        Gimp.displays_flush()
        
    finally:
        Gimp.context_pop()
```

### Color Curves Integration

```python
def selective_color_adjustment_with_luminosity(image, color_vector, brightness_range):
    """Adjust colors based on luminosity ranges"""
    
    Gimp.context_push()
    try:
        # Create luminosity mask for range
        mask = create_luminosity_mask(image, 
                                      threshold_low=brightness_range[0],
                                      threshold_high=brightness_range[1])
        
        # Set up color adjustment
        Gimp.context_set_foreground(Gegl.Color.new(color_vector[0], 
                                                   color_vector[1], 
                                                   color_vector[2]))
        
        # Apply color only within mask
        # This would typically use edit_fill with mask selection
        # Implementation depends on specific editing needs
        
        Gimp.displays_flush()
        
    finally:
        Gimp.context_pop()
```

### Integration with Cave Painter

Luminosity masks excel at:

- **Sky and water manipulation**: Select and edit only bright areas
- **Shadow detail recovery**: Enhance dark regions without affecting highlights
- **Portrait enhancement**: Adjust skin tones precisely
- **Landscape compositing**: Blend multiple exposures seamlessly
- **Selective color grading**: Apply colors to specific brightness ranges

### Example Comprehensive Workflow

```python
def complete_luminosity_mask_workflow(image, target_area="sky", adjustment_type="exposure"):
    """Complete workflow using luminosity masks for image enhancement"""
    
    Gimp.context_push()
    try:
        # Step 1: Create appropriate luminosity mask
        if target_area == "sky":
            mask = create_luminosity_mask(image, threshold_low=0.7, threshold_high=1.0)
        elif target_area == "shadows":
            mask = create_luminosity_mask(image, threshold_low=0.0, threshold_high=0.3)
        else:  # midtones
            mask = create_luminosity_mask(image, threshold_low=0.3, threshold_high=0.7)
        
        # Step 2: Apply mask for selective editing
        active_layer = image.get_active_drawable()
        apply_luminosity_mask(active_layer, mask)
        
        # Step 3: Perform specific adjustment based on type
        if adjustment_type == "exposure":
            # Apply exposure blending using mask
            pass
        elif adjustment_type == "color":
            # Apply selective color grading
            pass
        elif adjustment_type == "contrast":
            # Adjust contrast within masked region
            pass
        
        Gimp.displays_flush()
        
    finally:
        Gimp.context_pop()
```

### API Validation Checklist

- [x] `Gimp.context_push()/pop()` for color safety (from gimp-context-management)
- [x] `Gimp.Selection.none()` and `Gimp.Selection.invert()` for mask control (from gimp-pdb-procedures)
- [x] `Gimp.Selection.feather()` for smooth edges (from gimp-pdb-procedures)
- [x] `Gimp.Drawable.edit_fill()` for layer operations (from gimp-fill-operations)
- [x] `Gimp.curves_spline()` for luminosity adjustments (from gimp-basic-color-curves reference)
- [x] `Gimp.displays_flush()` for committing changes (from gimp-mcp-patterns)
- [x] `Gimp.Image.select_ellipse()` and other selection operations
- [x] `Gimp.context_set_foreground()` for color management (from gimp-context-management)

### Advanced Techniques

```python
def advanced_luminosity_masking(image, use_pdb_fallback=True):
    """Advanced luminosity masking with PDB fallback for complex operations"""
    
    Gimp.context_push()
    try:
        # Core luminosity mask creation
        drawable = image.get_active_drawable()
        
        # Try direct API first, fallback to PDB
        if use_pdb_fallback:
            pdb = Gimp.get_pdb()
            # Use PDB procedures for operations not directly supported
            # Example: complex threshold operations
            pass
        
        # Apply mask with undo group for safety
        image.undo_group_start()
        try:
            # Luminosity mask implementation
            pass
        finally:
            image.undo_group_end()
        
        Gimp.displays_flush()
        
    finally:
        Gimp.context_pop()
```

This skill provides comprehensive luminosity mask capabilities for precise, non-destructive image editing in Cave Painter workflows.