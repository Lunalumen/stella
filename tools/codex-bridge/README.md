# Optional Codex CLI MCP bridge

A small stdio MCP server exposing an explicit `ask_chatgpt` call through a separately installed Codex CLI. Start with `python server.py` only when configuring a trusted MCP host. It accepts JSON-RPC on stdin/stdout; it is not an HTTP server. Authentication and official CLI installation must be performed separately by the user.

The wrapper removes selected API environment variables and defaults requests to a read-only sandbox. It accepts a working directory and sandbox mode from its trusted host: do not expose this tool to untrusted callers or treat read-only defaults as an immutable authorization boundary. No private credentials, model weights, conversation history or CLI binary is included.

Account usage limits and charges can still apply. Each request starts a CLI task; this implementation does not guarantee continuity with earlier desktop conversations. Logs are private and excluded. This source is retained as an optional compatibility feature, not an instruction to involve Claude in development. No model call or MCP host connection was verified for this export.
