# Task conversations between Codex and Claude

Use one explicit dispatcher for the two existing CLI wrappers. A task keeps one **separate session per provider**. This is not shared model memory or synchronization of existing desktop chat windows. No model is contacted by downloading these files.

## CLI use

Create a UTF-8 `question.txt` inside the chosen project folder. From the repository root:

```text
python tools/bridge.py --root <project-folder> claude status
python tools/bridge.py --root <project-folder> codex status
python tools/bridge.py --root <project-folder> claude ask --task example-001 --question-file question.txt
python tools/bridge.py --root <project-folder> codex ask --task example-001 --question-file question.txt
```

Edit the question and repeat **the same target, project root and task name** for the next turn. Add `--context notes.md` for an explicitly selected reference. `history --task example-001` shows turn metadata without session IDs or prompt text. Use `--new-session` only when deliberately starting over; it preserves earlier turn files.

The selected context is the only file content the dispatcher forwards. At most four `.md`/`.txt` references, 20,000 reference characters and 12,000 question characters are accepted; the Codex combined prompt is bounded too. Dotfiles and configuration/session/private/log/credential directories are not accepted. Do not put secrets in a question or reference file.

Codex defaults to `read-only`. An explicitly requested edit may use `--sandbox workspace-write` within the operator-selected root. Changing cwd, sandbox or model on a resumed Codex task is refused: use a separate task or explicitly start a new session. This guard is not an OS read-access boundary.

## Runtime requirements and privacy

Install official CLIs and log in through the user's own subscription account. The wrappers verify account mode; a configured chat subscription still has usage limits and is not unlimited/free. There is no API-key fallback in this workflow. Codex additionally pins the built-in provider and ChatGPT login policy for the invocation and bypasses ambient user configuration; authentication still uses the user's normal CLI account store. Unknown or unsupported status/help output fails closed.

Use `CODEX_EXE` for an explicitly chosen native executable; an operator can instead select `CODEX_JS` and `NODE_EXE` for an npm installation. A Windows npm shim is resolved to its entry point without a shell. No package is installed automatically. `CODEX_EXE` must point to a trusted official executable; versioned installation paths may need refreshing after an app update.

Each provider's private task state lives under the selected root's ignored `.bridge/` directory: Claude keeps its compatible `.bridge/tasks/`, while Codex uses `.bridge/codex/tasks/`. Requests, visible final answers, session IDs and usage metadata are stored locally in plaintext. Do not publish these files, enter secrets, or claim encrypted memory. Numeric usage records are not proof of token savings.

Failed/inflight turns block implicit continuation; there is no automatic retry. A lock left by a killed process is not automatically removed, even with `--new-session`. Inspect the PID/time in `turn.lock`, verify that no request is running, preserve the task records, and remove only that verified stale lock manually. If uncertain, use a different task. Do not delete all state as a repair step. A failed new Codex session retains the previous state in that turn's `previous-state.json`; recovery is manual, not automatic reuse of an uncertain session.

Timeout/output-limit cleanup targets the active CLI process tree. Already-detached descendants after a parent exits, OS-specific races, and arbitrary background work are not a guaranteed containment boundary. These bridges are for trusted local users, not untrusted remote clients. Keep background work and recursive model calls disabled. No sandbox or hook-trust bypass is added.

## Related files

- [Codex MCP wrapper](codex-bridge/README.md)
- [Claude wrapper](claude-bridge/README.md)
- [Review workflow](../docs/BRIDGE_WORKFLOW.md)
- [Verification boundaries](../docs/BRIDGE_VALIDATION_2026-11-17.md)

The CLI resume behavior and account policy are checked against [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference), and [Claude programmatic conversations](https://code.claude.com/docs/en/headless). These are compatibility references, not permission to install, sign in, spend money or run another AI.
