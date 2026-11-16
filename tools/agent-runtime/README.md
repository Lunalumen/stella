# Agent Runtime

An explicit task runner built around the Codex SDK, with a local role registry, selected worker prompts, task validation, optional managerial plans, bounded call counts, progress states and run records. It does not control or synchronize desktop chat histories.

From this directory use `node cli.mjs list` to inspect roles and `node cli.mjs plan examples/algorithm-task.json` to inspect a plan. Model execution requires installing the pinned dependency in `package.json` (`npm install --ignore-scripts`) and configuring the user's own CLI/account. `node cli.mjs run examples/algorithm-task.json --max-calls 1` is a real model execution, consumes usage, and may incur charges. No model execution was performed for this export.

`codeTools` defaults to `none`. Graft and codebase-memory-mcp are optional, separately installed providers; no binaries, indexes or package caches are bundled. If needed, set `STELLA_CODE_TOOLS_ROOT` to the directory containing `graft-cli/` or `codebase-memory-mcp/`. Graft configurations set `DO_NOT_TRACK=1`. Never treat a graph's token estimate as measured whole-task savings.

Run records under `state/` are private and ignored. Examples use synthetic tasks and do not include real study documents. `node --test agent-system.test.mjs` is the included unit-test command; the current publication check performed syntax checks only. Adapted coordination guidance keeps its upstream Agency Agents attribution and MIT license in `THIRD_PARTY_LICENSES/`.
