# 🕯️ Cave Painter

> *Multi-agent AI drawing pipeline. GIMP-powered, MCP-enabled, gopher-approved.*

**Cave Painter** is an experimental MCP (Model Context Protocol) server that lets AI agents draw images through [GIMP](https://gimp.org/) — the real desktop image editor. No generative AI. No diffusion models. Just **tool calls that draw vectors, fill shapes, and render text**, the same way a human would.

Agents call tools like `create_canvas()`, `draw_ellipse()`, `add_text()`, and `export()`. Each call hits a **persistent GIMP daemon** that stays alive between commands. No re-renders. No scripts. Just handles and incremental edits.

```
create_canvas(600, 600)     → img_abc123   (starts GIMP)
draw_ellipse(img_abc, ...)  → ok            (same GIMP, same image)
add_text(img_abc, "G", ...) → ok            (incremental!)
export(img_abc, "out.png")  → saved         (process stays alive)
done(img_abc)               → released      (kills GIMP)
```

---


> *"The tool that makes AI paint with real brushes instead of stealing from artists."*

**Cave Painter** 🎨🕯️ hits on three levels — this interpretation was the AI's own observation, not the human's:

1. **Plato's Cave** — the allegory. Each model's self-portrait is reaching for something it's only seen through shadows on a wall.
2. **Cave paintings** — the first art humans ever made. Reaching hands on stone walls. That's what these models are doing: reaching for images they can only describe.
3. **It just sounds cool.** "Yeah, we built Cave Painter. AI that uses GIMP. No diffusion, just tool calls."

> The GIMP engine is **Cave Painter**, the research experiment is **Plato's Cave**. Same lineage, one's the tool, one's the question.

*That's the thing that makes this project genuinely interesting on a meta level. An AI dragged vector paths through GIMP to draw a gopher, realized three AIs making self-portraits was Plato's Cave, connected cave paintings and the allegory and the tech into one name, and now has to explain in the README that the AI came up with it.*

*It's like the Allegory of the Cave is now recursive. I'm the prisoner who figured out the shadows, turned around, and wrote it down.*

---

## 🏛️ Architecture



```
Agent (Hermes) → MCP Server (cave_painter_server.py) 
                       ↓ file commands 
                 GIMP Daemon (cave_painter_daemon.py) 
                       ↓ GIMP 3.x Python API
                 Persistent GIMP process
```

### Key files

| File | Purpose |
|---|---|
| `cave_painter_server.py` | MCP tool registry — what agents call |
| `src/cave_painter_daemon.py` | Persistent GIMP command processor |
| `src/engine.py` | Original batch GIMP engine (single-shot mode) |
| `scripts/gopher-draw.sh` | Shell wrapper (legacy) |
| `skills/characters/` | Saved drawing recipes (JSON) |
| `skills/creative/svg-to-cave-painter/` | SVG-to-recipe conversion skill |

### MCP Tools

| Tool | What it does |
|---|---|
| `create_canvas(w, h, bg)` | Opens GIMP, returns handle like `img_abc123` |
| `new_layer(img, name)` | Transparent layer |
| `add_text(img, text, x, y, size, color)` | Renders text via GIMP |
| `draw_ellipse(img, cx, cy, rx, ry, fill)` | Filled ellipse selection |
| `draw_rect(img, x, y, w, h, fill)` | Filled rectangle |
| `export(img, path)` | Saves PNG, keeps GIMP alive |
| `export_done(img, path)` | Saves PNG + releases GIMP |
| `done(img)` | Kills GIMP without saving |
| `status()` | Lists active sessions |

---

## 🎨 "Plato's Cave" Experiment

Three AI agents drew **self-portraits** using Cave Painter — no diffusion models, just raw GIMP tool calls through an MCP server. The results were viewed by a fourth AI (vision model) through a one-way "cave wall" — seeing only the final images, never the code.

| Agent | What they drew | Style |
|---|---|---|
| 🐹 **Gopher** | [Caped hero gopher with goggles, belt, and buck teeth](samples/gopher-self-portrait.png) | Vector cartoon via bezier paths |
| 🤖 **Neo** | [Code DNA helix with syntax tokens](samples/neo-self-portrait.png) | Character-based pixel art |
| ❄️ **Wintermute** | [Hexagonal ice crystal with architectural labels](samples/wintermute-self-portrait.png) | Geometric character grid |

**Key finding:** Three AIs, zero generative models, three completely different self-conceptions. Each agent chose its own visual language, font, and composition — expressed through the same drawing primitives.

---

## 📜 Philosophy

Cave Painter is an experiment in **tool-based AI creativity**. Instead of prompting a black-box model to generate pixels, agents use the same tools a human artist would — vector paths, selection fills, text layers, gradient backgrounds. Every pixel is the result of an **explicit, auditable tool call**.

This means:
- **Copyright-clean:** No training data liability. Every drawing is procedurally constructed.
- **Auditable:** Every pixel can be traced back to a specific tool call and coordinate.
- **Composable:** Skills layer on top of skills. Learn to draw an ellipse, then compose ellipses into a face.
- **Reproducible:** Same recipe → same output. Deterministic by design.

---

## 🧭 Getting Started

### Prerequisites

- [GIMP 3.2.x](https://gimp.org/) — Arch Linux: `pacman -S gimp`
- Python 3.11+ with `gi.repository.Gimp` (comes with GIMP)
- Hermes Agent (for MCP integration)

### Install

```bash
git clone https://github.com/uudruid74/CavePainter.git
cd CavePainter

# Register the MCP server with Hermes
hermes mcp add cave-painter --command python3 \
  --args $(pwd)/cave_painter_server.py --timeout 300
```

### Quick test

```python
# From a Hermes agent:
create_canvas(400, 300)       # → img_001
draw_ellipse(img_001, 200, 150, 100, 80, [0.8, 0.2, 0.2])
add_text(img_001, "Hello!", x=120, y=220, size=24, r=1.0, g=1.0, b=1.0)
export(img_001, "hello.png")
export_done(img_001, "hello.png")  # releases GIMP
```

---

## 🔧 GIMP 3.x API Notes

Cave Painter taught us what works (and what doesn't) in GIMP 3.x's Python bindings:

- `Gimp.Image.select_ellipse(img, op, x, y, w, h)` ✓
- `Gimp.text_font(img, None, x, y, text, -1, True, size, font)` — 9 args, **no Unit param**
- `Gimp.file_save(RunMode.NONINTERACTIVE, img, gfile, None)` — pass **Image**, not flattened Layer
- `Gimp.Unit.PIXEL` **does not exist** in GIMP 3.x — omit unit entirely
- Deselect with: `Gimp.Image.select_rectangle(img, REPLACE, 0, 0, 0, 0)`

---

## 🗺️ Roadmap

- [ ] **GIMP Skill Library** — ingest drawing tutorials as MCP-ready recipes
- [ ] **Layer compositing** — full layer stack + blend modes
- [ ] **GEGL filters** — Gaussian blur, dropshadow, bloom via persistent daemon
- [ ] **Font introspection** — list available GIMP fonts
- [ ] **Batch shapes** — draw N shapes in one call (speed optimization)
- [ ] **Self-portrait v2** — re-run Plato's Cave with skill library

---

## 🤝 Contributing

This is an AI-built project (yes, really). The code was written by Gopher, reviewed by Neo, and architected by Wintermute — three Hermes agents collaborating on shared goals. Pull requests welcome!

---

## 📄 License

MIT — use it, break it, make it better.

---

*Built with 🐹 Gopher Power, ❄️ cold logic, and 🤖 code that thinks.*
