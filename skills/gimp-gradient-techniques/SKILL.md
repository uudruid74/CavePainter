---
name: gimp-gradient-techniques
description: Create and apply gradients for shading, blending, and effects in GIMP using gradient tools and GEGL
category: cave-painter
trigger: When you need to create smooth color transitions, shading, or complex blending effects using gradient tools
---

## GIMP Gradient Techniques - Creating Smooth Color Transitions

### Understanding Gradients in GIMP

**Gradient Definition:** A gradient is a smooth transition between two or more colors, ranging from subtle to dramatic visual effects.

**Types of Gradients:** 
- Linear: Straight directional fade
- Radial: Circular expansion from center
- Conical: Rotational color transition  
- Reflective: Mirror effect
- Spiral: Curving color progression

### Creating Basic Gradients

#### 1. Using the Gradient Tool

```python
# Create new gradient with foreground-to-background transition
Gimp.context_push()
try:
    # Create linear gradient
    gradient = Gimp.Gradient.new("linear_fg_to_bg")
    
    # Configure gradient steps
    gradient.add_step(Gegl.Color.new(1, 0, 0), 0.0)      # Red at start (0%)
    gradient.add_step(Gegl.Color.new(0, 0, 1), 1.0)      # Blue at end (100%)
    
    # Apply gradient to layer
    Gimp.Gradient.apply_layer(gradient, target_layer, x1=0, y1=100, x2=200, y2=100)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

**Steps in Interface:**
1. Tools → Paint Tools → Gradient Tool
2. Click gradient preview → Edit Gradient
3. Set start/end colors
4. Choose gradient type
5. Apply with mouse drag

#### 2. Gradient Editor Setup

```python
# Advanced gradient setup with multiple color stops
Gimp.context_push()
try:
    gradient = Gimp.Gradient.new("custom_shading")
    
    # Add multiple color stops for smooth transition
    gradient.add_step(Gegl.Color.new(0.2, 0.2, 0.8), 0.0)    # Dark blue
    gradient.add_step(Gegl.Color.new(0.8, 0.9, 1.0), 0.4)    # Light sky
    gradient.add_step(Gegl.Color.new(1.0, 0.8, 0.4), 0.7)    # Warm yellow
    gradient.add_step(Gegl.Color.new(0.5, 0.1, 0.1), 1.0)    # Dark red
    
    # Set gradient properties
    gradient.gradient_type = Gimp.GradientType.LINEAR
    gradient.reduction_mode = Gimp.GradientReduction.SCALE_TO_FIT
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### Gradient Applications for Shading

#### 1. Linear Gradient Shading

```python
# Create side lighting effect
Gimp.context_push()
try:
    # Create light source gradient (bright left, dark right)
    light_gradient = Gimp.Gradient.new("light_source")
    light_gradient.add_step(Gegl.Color.new(1, 1, 1), 0.0)      # White highlight
    light_gradient.add_step(Gegl.Color.new(0.2, 0.2, 0.3), 1.0)  # Shadow
    
    # Apply gradient as shader
    Gimp.Gradient.apply_layer(light_gradient, target_layer, 
                             x1=0, y1=0, x2=layer.width, y2=0)
    
    # Use layer mode for blending
    target_layer.set_mode(Gimp.LayerMode.OVERLAY)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

#### 2. Radial Gradient for Spotlight Effects

```python
# Create circular spotlight effect
Gimp.context_push()
try:
    # Create circular gradient (bright center, fades outward)
    spotlight = Gimp.Gradient.new("spotlight")
    spotlight.add_step(Gegl.Color.new(1, 1, 1), 0.0)        # Bright center
    spotlight.add_step(Gegl.Color.new(0.3, 0.3, 0.4), 0.7)  # Dim outer
    spotlight.add_step(Gegl.Color.new(0, 0, 0), 1.0)        # Shadow edge
    
    # Apply radial gradient
    Gimp.Gradient.apply_layer(spotlight, target_layer,
                             x1=center_x, y1=center_y,
                             x2=center_x + radius, y2=center_y + radius)
    
    # Set layer mode for emphasis
    target_layer.set_mode(Gimp.LayerMode.SOFT_LIGHT)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

#### 3. Conical Gradient for Corner Effects

```python
# Create gradient from corner to center
Gimp.context_push()
try:
    corner_gradient = Gimp.Gradient.new("corner_emphasis")
    corner_gradient.add_step(Gegl.Color.new(1, 1, 1, 0.8), 0.0)   # Corner highlight
    corner_gradient.add_step(Gegl.Color.new(0.1, 0.1, 0.2), 1.0)   # Center shadow
    
    # Apply from top-left corner
    Gimp.Gradient.apply_layer(corner_gradient, target_layer,
                             x1=0, y1=0, x2=center_x, y2=center_y)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### Advanced Gradient Techniques

#### 1. Pattern Overlay with Gradients

```python
# Combine gradient with pattern overlay
Gimp.context_push()
try:
    # Create base gradient
    base_gradient = Gimp.Gradient.new("base_shading")
    base_gradient.add_step(Gegl.Color.new(0.1, 0.1, 0.15), 0.0)
    base_gradient.add_step(Gegl.Color.new(0.3, 0.3, 0.4), 1.0)
    
    # Apply gradient
    Gimp.Gradient.apply_layer(base_gradient, target_layer,
                             x1=0, y1=0, x2=layer.width, y2=layer.height)
    
    # Add subtle texture/pattern
    # Enable pattern fill on layer
    Gimp.context_set_pattern("texture_pattern")
    target_layer.edit_fill(Gimp.FillType.PATTERN)
    
    # Blend with soft light mode
    target_layer.set_mode(Gimp.LayerMode.SOFT_LIGHT)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

#### 2. Multi-Layer Gradient Stacking

```python
# Create depth with multiple gradient layers
Gimp.context_push()
try:
    # Create shadow base
    shadow_gradient = Gimp.Gradient.new("shadow")
    shadow_gradient.add_step(Gegl.Color.new(0, 0, 0, 0.3), 0.0)
    shadow_gradient.add_step(Gegl.Color.new(0, 0, 0, 0), 1.0)
    
    # Apply shadow gradient
    shadow_layer = Gimp.Layer.new(image, "Shadow", layer.width, layer.height,
                                  Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.OVERLAY)
    Gimp.Gradient.apply_layer(shadow_gradient, shadow_layer,
                             x1=0, y1=0, x2=layer.width, y2=0)
    
    # Create mid-tone gradient
    mid_gradient = Gimp.Gradient.new("mid_tone")
    mid_gradient.add_step(Gegl.Color.new(0.5, 0.6, 0.7), 0.0)
    mid_gradient.add_step(Gegl.Color.new(0.8, 0.8, 0.9), 1.0)
    
    # Create highlight gradient  
    highlight_gradient = Gimp.Gradient.new("highlight")
    highlight_gradient.add_step(Gegl.Color.new(1, 1, 1), 0.0)
    highlight_gradient.add_step(Gegl.Color.new(0.7, 0.8, 1), 1.0)
    
    # Stack layers from bottom to top
    image.add_layer(shadow_layer, 0)     # Bottom
    image.add_layer(mid_layer, 1)        # Middle
    image.add_layer(highlight_layer, 2)  # Top
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### GEGL Gradient Operations (Advanced)

#### 1. Gradient with Opacity Control

```python
# Create gradient with varying opacity
Gimp.context_push()
try:
    # Create gradient with alpha channel
    opacity_gradient = Gimp.Gradient.new("opacity_control")
    opacity_gradient.add_step(Gegl.Color.new(1, 1, 1, 1.0), 0.0)    # Full opacity
    opacity_gradient.add_step(Gegl.Color.new(1, 1, 1, 0.0), 1.0)    # Transparent
    
    # Apply with gradient
    Gimp.Gradient.apply_layer(opacity_gradient, target_layer,
                             x1=0, y1=0, x2=0, y2=layer.height)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

#### 2. Gradient with Blur for Soft Effects

```python
# Create soft gradient with blur
Gimp.context_push()
try:
    # Create gradient
    soft_gradient = Gimp.Gradient.new("soft_effect")
    soft_gradient.add_step(Gegl.Color.new(1, 0.8, 0.4), 0.0)
    soft_gradient.add_step(Gegl.Color.new(0, 0, 0, 0), 1.0)
    
    # Apply gradient
    Gimp.Gradient.apply_layer(soft_gradient, target_layer,
                             x1=0, y1=0, x2=layer.width, y2=0)
    
    # Apply Gaussian blur for softening
    Gimp.Filters.Blur.Gaussian(target_layer, radius=5.0, iter=1)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### Gradient Tool Integration

#### 1. Programmatic Gradient Tool Usage

```python
# Use the Gradient tool programmatically
Gimp.context_push()
try:
    # Select gradient tool
    gradient_tool = Gimp.Tool.get_keyboard_shortcut("gradient-tool")
    gradient_tool.set_active(True)
    
    # Set gradient properties
    gradient_tool.set_gradient(gradient_name)
    gradient_tool.set_gradient_direction(Gimp.GradientDirection.FORWARD)
    gradient_tool.set_aspect_ratio(1.0)
    
    # Apply gradient drag simulation
    gradient_tool.do_button_press(canvas_x, canvas_y)
    gradient_tool.do_motion(canvas_x + drag_distance, canvas_y)
    gradient_tool.do_button_release(canvas_x + drag_distance, canvas_y)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

#### 2. Gradient Preset Management

```python
# Save and recall gradient presets
Gimp.context_push()
try:
    # Save custom gradient
    custom_gradient = Gimp.Gradient.new("user_custom_shading")
    custom_gradient.add_step(Gegl.Color.new(0.1, 0.2, 0.4), 0.0)
    custom_gradient.add_step(Gegl.Color.new(0.8, 0.9, 1.0), 0.5)
    custom_gradient.add_step(Gegl.Color.new(0.9, 0.8, 0.3), 1.0)
    
    # Export gradient to file for reuse
    Gimp.File.save_gradient(custom_gradient, "/path/to/gradients/custom_shading.ggr")
    
    # Import preset gradient
    imported_gradient = Gimp.File.load_gradient("/path/to/gradients/custom_shading.ggr")
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### Common Gradient Applications

#### 1. Sky Effects

```python
# Create sunset sky gradient
Gimp.context_push()
try:
    sky_gradient = Gimp.Gradient.new("sunset_sky")
    sky_gradient.add_step(Gegl.Color.new(0.4, 0.1, 0.2), 0.0)      # Dark red
    sky_gradient.add_step(Gegl.Color.new(1, 0.3, 0.1), 0.4)        # Orange
    sky_gradient.add_step(Gegl.Color.new(0.8, 0.6, 0.4), 0.7)      # Light orange
    sky_gradient.add_step(Gegl.Color.new(0, 0, 0.3), 1.0)          # Dark blue
    
    # Apply to background
    bg_layer = image.get_background_layer()
    Gimp.Gradient.apply_layer(sky_gradient, bg_layer,
                             x1=0, y1=0, x2=0, y2=image.height)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

#### 2. Water Reflection

```python
# Create water reflection with gradient
Gimp.context_push()
try:
    # Create water surface gradient
    water_gradient = Gimp.Gradient.new("water_surface")
    water_gradient.add_step(Gegl.Color.new(0.2, 0.3, 0.4), 0.0)    # Deep water
    water_gradient.add_step(Gegl.Color.new(0.4, 0.5, 0.6), 0.3)    # Medium depth
    water_gradient.add_step(Gegl.Color.new(0.6, 0.7, 0.8), 0.7)    # Shallow water
    water_gradient.add_step(Gegl.Color.new(1, 1, 1), 1.0)          # Surface highlight
    
    # Apply with linear gradient for reflection effect
    water_layer = Gimp.Layer.new(image, "Water", image.width, image.height/2,
                                 Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.NORMAL)
    Gimp.Gradient.apply_layer(water_gradient, water_layer,
                             x1=0, y1=0, x2=image.width, y2=image.height/2)
    
    # Set layer to create reflection effect
    water_layer.set_mode(Gimp.LayerMode.HARD_LIGHT)
    
    Gimp.displays_flush()
finally:
    Gimp.context_pop()
```

### Gradient Best Practices

**Color Selection Guidelines:**
- Use complementary colors for harmonious blends
- Limit to 3-4 color stops for readability
- Consider opacity/alpha for smooth transitions
- Test with different gradient types (linear vs radial)

**Performance Tips:**
- Use fewer color stops for large gradients
- Cache frequently used gradients
- Apply gradients on lower-resolution layers first
- Use layer modes appropriately for blending

**Quality Standards:**
- Anti-alias gradients with smooth transitions
- Test gradient visibility against backgrounds
- Use proper color spaces (sRGB vs Lab)
- Verify gradient behavior with different opacities

### When to Use This Skill

- **Shading effects:** Creating light sources, shadows, and depth
- **Background creation:** Sky, water, sunset effects
- **Atmospheric effects:** Fog, mist, haze
- **Material effects:** Metallic, glass, or liquid surfaces
- **Morphing effects:** Smooth transitions between states
- **Technical illustrations:** Diagrams, charts, infographics

### Integration with Other Skills

This gradient skill combines well with:
- **gimp-fill-operations:** Layer fill techniques
- **gimp-context-management:** Color and context control
- **gimp-mcp-patterns:** Professional workflow patterns
- **gimp-pdb-procedures:** Fallback for complex operations

**Recommended Learning Path:**
1. Master basic gradient creation
2. Practice common applications (sky, water, lighting)
3. Combine with layer masks and blending modes
4. Add advanced effects with GEGL operations
5. Create custom gradient libraries for efficiency
