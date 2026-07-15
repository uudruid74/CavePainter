---
name: cave-painter-wiki
description: Update the Cave Painter wiki checklist — append items and flip checkboxes only, NEVER overwrite the entire file
category: cave-painter
trigger: When a kanban worker completes a task and needs to mark [x] in the wiki
---

## Wiki Structure

The wiki lives at `/home/ekl/vault/wiki/`. It has two top-level directory types:

| Directory | Purpose | Example |
|-----------|---------|---------|
| `entities/` | Per-project wiki pages | `entities/hermes-agent-fork/`, `entities/clearview/` |
| `projects/` | Task checklists and progress tracking | `projects/cave-painter/index.md` |

The `projects/cave-painter/index.md` checklist is the specific file this skill was originally built for. The same patch-based editing rules apply to ALL wiki files.

### CRITICAL RULE: NEVER use write_file on the wiki

`write_file` **overwrites the entire file**. This destroys all existing content. You ALWAYS use `patch` for targeted edits.

### Workflow

#### Step 1 — Read first
```
read_file(path="/home/ekl/vault/wiki/projects/cave-painter/index.md")
```
This loads the current state. Study the structure before changing anything.

#### Step 2 — Use patch for checkboxes
To mark an item complete, match the exact line:
```
patch(
    path="/home/ekl/vault/wiki/projects/cave-painter/index.md",
    old_string="- [ ] GIMP Quickies — beginner shortcuts",
    new_string="- [x] GIMP Quickies — beginner shortcuts (by Zephyr 🦊)"
)
```
Include enough surrounding text to make the match unique. The `patch` tool uses fuzzy matching — a few words are fine.

#### Step 3 — Add new items (not replace)
To add a NEW unchecked item, find a nearby anchor line and insert:
```
patch(
    path="/home/ekl/vault/wiki/projects/cave-painter/index.md",
    old_string="- [ ] Clone & healing tool — spot removal (from playlist)\n\n### Add as discovered",
    new_string="- [ ] Clone & healing tool — spot removal (from playlist)\n- [ ] Drop shadows and glow effects\n- [ ] Font effects and typography\n\n### Add as discovered"
)
```

#### Step 4 — Verify
After patching, verify your change:
```
read_file(path="/home/ekl/vault/wiki/projects/cave-painter/index.md", offset=168)
```
Confirm only your targeted lines changed and nothing else was touched.

#### Step 5 — Create new wiki pages
To create a NEW wiki page for an existing entity:
1. Verify the entity directory exists: `ls /home/ekl/vault/wiki/entities/<entity>/`
2. Write the new page: `write_file(path="/home/ekl/vault/wiki/entities/<entity>/<page-name>.md")`
3. Since the page is NEW (not editing existing), write_file is safe — it creates a new file
4. Add a wikilink from the entity Home page: patch the Home.md with `[[entity/page-name]]`
5. Log the page to fabric for agent awareness

Example (from 2026-07-13):
```
write_file(path="/home/ekl/vault/wiki/entities/hermes-agent-fork/kanban-notification-architecture.md")
patch(path="...Home.md", old_string="## Related", new_string="Notification architecture: [[hermes-agent-fork/kanban-notification-architecture]]\\n\\n## Related")
fabric_write(summary="Wiki: new page on topic")
```

### Create, then link, then log: these three steps guarantee the new page is discoverable by agents and humans.

### Anti-Patterns — DO NOT

| ❌ Bad | ✅ Good |
|---|---|
| `write_file(path="...index.md", content="# Entire new file")` | `patch(path, old_string="- [ ]", new_string="- [x]")` |
| Reformatting the whole page | Only changing the specific line |
| Adding a new section by rewriting | Using patch to insert between existing lines |
| Removing existing content | Leaving everything intact |

### When in doubt
- Use `patch` with replace_all=False (default) — it errors if the match isn't unique
- If patch fails, re-read the file and try a longer `old_string` match
- Include surrounding context lines to make the match unique

### Real-world caution
See `references/wiki-nuking-incident.md` — a kanban worker once replaced the entire wiki instead of editing it. Don't be that worker.
