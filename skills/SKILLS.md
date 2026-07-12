# Cave Painter Skills Library

Skills are reusable GIMP drawing recipes that any Hermes agent can call through the Cave Painter MCP server. Each skill is a JSON recipe with metadata.

## Structure
```
skills/
├── font-effects/   # Text effects: neon, chrome, 3D, glass
├── lighting/       # Lighting: drop shadow, glow, lens flare
├── composites/     # Layer compositing: green screen, double exposure
├── abstracts/      # Generative art: fractals, geometric patterns
├── characters/     # Character templates: gopher, neo, wintermute
├── templates/      # Canvas templates: logo, banner, diagram
└── SKILLS.md       # This file
```

## Adding Skills
1. Create a recipe JSON in the appropriate category
2. Test it with `gopher_draw_recipe`
3. The MCP server auto-discovers new skills

## Use Cases
- 🎨 Logo design (zero copyright liability)
- 📊 Diagrams and infographics
- 🖼️ Web design assets
- 📝 Social media graphics
- 🐹 Character portraits (Plato's Cave experiment)
