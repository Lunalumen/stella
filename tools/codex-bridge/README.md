# Codex task-session MCP bridge

`server.py` is a local stdio MCP wrapper for the official Codex CLI. Version 0.2 adds explicit task sessions. The previous one-shot wrapper's tool calls must be updated: **`ask_chatgpt` now requires `task_id` as well as `prompt`**. Refresh/reconnect the MCP host so it reads the new tool schema; an already running server is not replaced just by editing a file.

```json
{"task_id":"review-001","prompt":"Review the selected implementation","sandbox":"read-only","timeout_sec":120}
```

Repeat the same task ID to resume its exact stored UUID. Never use `--last` to guess which conversation belongs to a task. `new_session: true` explicitly starts another session. The additional tools are `codex_bridge_status` (no model request) and `codex_bridge_history` (redacted task metadata). Model calls are synchronous; configure a trusted host timeout compatible with the selected 10–180-second operation timeout. Cancellation/progress notifications and a multi-client remote service are not implemented.

Set `STELLA_CODEX_ROOT` in the **operator's MCP configuration** to the intended project root. A request's cwd must resolve inside that root. The default is this wrapper directory; it does not grant access to arbitrary requested workspaces. [Generic configuration example](mcp.example.json) contains placeholders only, not a usable account or personal path.

The wrapper checks ChatGPT account mode, forces that login method and the built-in OpenAI provider per execution, strips non-allowlisted child environment variables, and ignores ambient user config. API-key mode or unsupported CLI flags cause refusal. Subscription usage and limits still apply. Custom providers/proxies/CODEX_HOME are intentionally not inherited. Corporate network setups needing those features are unverified and require a separately reviewed configuration.

Only the final answer file, task state and selected numeric usage are retained. Reasoning, raw event streams and raw provider stderr are not persisted or returned by this wrapper. Public errors use controlled identifiers. The underlying official CLI may maintain its own private sessions/logs; this wrapper does not erase or publish them.

Run `python -B -X utf8 test_server.py -v` for synthetic offline tests. For the unified CLI use [tools/bridge.py](../BRIDGE_README.md). Refer to the shared guide for plaintext local state, manual stale-lock recovery, partial process-lifetime guarantees and other limitations. No desktop chat is automatically resumed by this bridge.
