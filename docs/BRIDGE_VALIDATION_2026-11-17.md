# User-edition bridge verification — 2026-11-17

## Scope

This report concerns the distributed connection code and user workflow, not any individual's computer, accounts, private directories or security configuration. Reviewed the two CLI wrappers, task state, common dispatcher, legacy MCP entry compatibility and explicit reference handling. This was not an audit of every other Stella application or a comprehensive security assessment.

Baseline: Stella at `8aac3ea3909c74b34c2af2d2a192900b6c202423`. The old Codex MCP wrapper always started a new `codex exec`; the existing Claude wrapper already had exact-session continuation. The change preserves Claude's continuation and adds a common entry point plus task-scoped Codex resume.

## Actual model exchange

The user authorized one focused Claude review and one follow-up. Codex supplied only the proposal, selected public connection source and implementation/verification notes. Two real Claude subscription replies were received through the existing bridge. The second turn resumed the same session and recalled a synthetic review marker that was not resent. Claude reported source observations and CLI assumptions; it did not execute tests or write implementation files. Its follow-up explicitly did **not** give blanket approval. No further automatic exchange was started.

Codex independently performed two real synthetic ChatGPT-subscription CLI turns through the new dispatcher. The first established a random marker; the second resumed the exact captured UUID and returned that marker without it being resent. Both answers matched. The session's own turn-context metadata recorded `read-only` for both turns. This is metadata evidence of the configured policy, not a filesystem-escape or deliberate write-denial test.

No API-key provider, payment, new subscription, private course source or actual memory database was used. Account usage was consumed. Raw prompts/replies, session IDs, account metadata and CLI session files are not published. Neither CLI session is claimed to be an existing desktop chat.

## Changes supported by evidence

- Exact task UUID persistence, explicit new-session behavior, provider-separated records, task locks and atomic writes.
- Codex cwd/sandbox/model fingerprints prevent silently resuming under different settings. Failed/inflight turns block implicit continuation; previous state is preserved before new turns.
- Installed official CLI help and account mode were checked; execution pins ChatGPT login policy and the built-in provider rather than assuming that deleting an API environment variable guarantees subscription mode. Unknown formats/unsupported flags fail closed.
- Windows shim resolution avoids shell fallback. Child environment values are allowlisted; request/stream/answer limits and active-process timeout cleanup are enforced.
- Raw provider stderr and reasoning events are not saved or returned by the wrapper. Public error surfaces normalize exceptions. History omits session IDs, prompts and absolute paths.
- Shared dispatcher routes only explicitly selected, bounded question/reference files. Existing Claude task-state layout remains compatible.

## Offline tests and integration checks

41 deterministic tests passed: 25 Codex wrapper tests, 13 Claude wrapper tests and 3 dispatcher tests. Synthetic subprocesses exercise event parsing, exact-session resume, timeout/output limits and stdio protocol without real model calls. Tests cover configuration mismatch, failed-turn blocking, old-state preservation, account refusal, path/input validation, private error redaction and MCP task routing.

Commands from the repository root:

```text
python -B -X utf8 tools/codex-bridge/test_server.py -v
python -B -X utf8 tools/claude-bridge/test_bridge.py -v
python -B -X utf8 tools/test_bridge_dispatcher.py -v
```

The compatibility entry initialized over stdio as server version 0.2.0 and listed three tools; `ask_chatgpt` requires `task_id`. The installed legacy entry and common dispatcher were checked without changing authentication records. Existing task records and original sources were preserved. A running Claude host was not forcibly restarted; it must reconnect to refresh the server process/tool schema. Readiness/stdio initialization is not proof that an already-running host has adopted the upgrade.

## Review disposition and limitations

Claude's review prompted cwd/permission fingerprints, account enforcement, bounded events, private error normalization, lock metadata and previous-state preservation. Codex verified the supplied source and current CLI help; it did not treat Claude's version assumptions as confirmed behavior. Auth-policy/resume references: [OpenAI non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), [Claude programmatic conversations](https://code.claude.com/docs/en/headless).

Unknown CLI versions, non-Windows live model execution, corporate proxy/custom account homes, host cancellation/progress notifications, and concurrent host behavior remain unverified. The updated Claude wrapper received offline tests; its actual review exchange used the existing compatible wrapper rather than claiming a newly reloaded desktop host.

Stale locks require explicit operator inspection and manual recovery; there is no automatic unlock. Local task records contain plaintext selected prompts and final answers and must remain private. Active-process timeout cleanup is tested; already-detached descendants after parent exit are not a guaranteed containment boundary. Same-user programs can access local records. Reconnection does not grant blanket authority for future model calls or edits. Token/cost savings for the combined workflow are unmeasured.
