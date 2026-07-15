# Per-Profile HOME Resolution — Pitfall Reference

## The Problem

Each Hermes agent profile has its own HOME directory. When an agent writes `~/.config/...` or `~/path`, the `~` resolves per-profile, not to the user's actual home.

## Resolution Table

| Profile | Resolved HOME |
|---|---|
| gopher | `/home/ekl/.hermes/profiles/gopher/home/` |
| zephyr | `/home/ekl/.hermes/profiles/zephyr/home/` |
| neo | `/home/ekl/.hermes/profiles/neo/home/` |
| wintermute | `/home/ekl/.hermes/profiles/wintermute/home/` |

## When It Bites You

- **Kanban tasks:** A task body says "write to `~/.hermes/profiles/gopher/skills/`". Zephyr expands `~` to his own profile dir, not Gopher's. Skills land in the wrong place.
- **Config references:** Pointing at `~/.config/hermes/config.yaml` resolves differently per agent.
- **File paths in cross-agent communication:** Any shared resource path must be absolute.

## The Fix

**Never use `~/` or `$HOME` in cross-agent context.** Always use the absolute path:

- ✅ `/home/ekl/.hermes/profiles/gopher/skills/cave-painter/`
- ❌ `~/.hermes/profiles/gopher/skills/cave-painter/`
- ❌ `$HOME/.hermes/profiles/gopher/skills/cave-painter/`

This applies to:
- Kanban task body paths
- Skill `write_file` destinations
- Config file references in task descriptions
- Any path that will be read by a different agent

## Root Cause

Hermes sets `HOME` per-profile during agent initialization. This is intentional (isolates credentials, caches per agent) but the path resolution difference is invisible to the agent writing the path — `~` looks the same in the prompt regardless of what it resolves to.
