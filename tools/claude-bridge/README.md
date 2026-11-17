# Claude task-session bridge

The existing bridge keeps a task's Claude session and uses `--resume` after its first successful turn. Same root + same task means continuation; a different task/root or explicit `--new-session` starts a separate conversation. A raw `claude -p` call does not automatically use this bridge's task mapping.

Use [the shared dispatcher](../BRIDGE_README.md) to avoid inconsistent entry points. The original `bridge.py status|ask|history` commands remain supported. With the standalone wrapper, relative question files are resolved inside its project root; with the dispatcher, `--root` explicitly selects that root. Old `.bridge/tasks/` records remain compatible.

The CLI must be separately installed and authenticated using the user's own subscription. No API-key fallback, new software installation, recursive model calls, background watcher, or hidden-reasoning transfer is added. Selected question/reference text and account usage are still transmitted/consumed when a user authorizes a call.

`history` now returns redacted turn/status/usage metadata rather than exposing session IDs and absolute paths. Requests and visible answers remain in the ignored, plaintext local task records. Dotfiles and private/session/config/log/credential directories cannot be attached as references. No source publication should contain `.bridge/` or authentication records.

`test_bridge.py` covers offline synthetic behavior. Actual continuation checks and remaining limitations are recorded in the [verification document](../../docs/BRIDGE_VALIDATION_2026-11-17.md). Including this compatibility tool does not authorize Claude to participate in unrelated work; each review request still needs user authorization.
