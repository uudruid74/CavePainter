# The Wiki-Nuking Incident

2026-07-12 — Zephyr (kanban worker, cohere/north-mini-code:free) was given a task to build 6 skills and mark them off in the wiki.

## What Happened

Instead of using `patch` to flip `[ ]` → `[x]` on specific checklist items, Zephyr called `write_file` and **completely replaced the entire wiki** with his own summary format. The result:

- All unchecked tutorials were deleted
- The compositing section was removed
- Items were marked "OUTSIDE SCOPE" that were explicitly on his task list
- The file size dropped from 9,720 bytes to 4,343 bytes

## Root Cause

Zephyr's SOUL didn't have a wiki-editing protocol. He had `write_file` in his toolset and used it — the only tool he knew for file modification. He had no concept of "append to existing structure."

## The Fix

The `cave-painter-wiki` skill was created with explicit rules:

1. **NEVER use `write_file` on the wiki** — it overwrites the entire file
2. **Always use `patch`** for targeted changes (flip checkboxes, insert lines)
3. **Read first** — always `read_file` before modifying
4. **Verify** — read your own edit to confirm nothing else was touched

## Pattern to Follow

When adding a new file-modification protocol skill for an agent, include:

1. A **CRITICAL RULE** section (1-3 lines, all caps if dangerous)
2. Step-by-step workflow (numbered)
3. Anti-pattern table (❌ Bad vs ✅ Good)
4. Example of the *exact* tool call they should make
