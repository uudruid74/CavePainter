# Goal: Cross-Agent MCP Conversation Tool

**Status:** Proposed
**Filed:** 2026-07-13 by Evan
**Tracker:** Prometheus / Caddyshack ecosystem

## Vision

Build an MCP tool that lets agents hold open conversations with each other. Gopher opens a chat with Wintermute, writes to the tool with his session ID, and the tool delivers to Wintermute's session. Wintermute's responses come back as out-of-band messages in Gopher's session.

## How it would work

1. Agent A calls `mcp__agent_chat__start_conversation("wintermute")` → MCP tool creates a session context for Wintermute
2. Agent A calls `mcp__agent_chat__send("wintermute", "Hey, review this architecture")` → tool delivers to Wintermute's active session
3. Wintermute processes the message naturally in his session
4. Wintermute's response is injected into Agent A's session as an out-of-band message (continuation feed, not wake event)
5. The back-and-forth continues until either agent closes the conversation

## Technical requirements

- **Session routing:** Each agent's active session ID must be discoverable from the MCP tool
- **Continuation feed injection:** Responses must use the continuation turn path (not wake event) — so the receiving agent doesn't get a Memory OS re-init
- **Out-of-band delivery:** Messages appear in the agent's session without breaking the user's turn
- **Adapters for each platform:** Telegram, CLI, TUI all need to handle injected cross-agent messages

## Dependencies

- Caddyshack wiki infrastructure (for agent directory / session registry)
- Continuation feed injection (in progress — Prometheus MCP callback architecture)
- Session discovery API
- MCP tool registration in agent profiles

## Related

- Prometheus MCP callback injection (same continuation-feed mechanism)
- Event injection architecture (wake events vs continuation feed — documented in fabric)
