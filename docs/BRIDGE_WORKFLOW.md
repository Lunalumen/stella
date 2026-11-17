# User-authorized code review conversations

This workflow is optional. It does not start either CLI, install tools or grant a second model authority. Start it only for a user-authorized task. Use one focused review and one follow-up; stop further automatic exchanges and report unresolved disagreements.

1. Codex reads the current task state and the necessary source, checks the installed tool's help/version and relevant official documentation, and identifies observable defects. Do not label code defective merely because it is old or uses a different style.
2. Prepare an explicit question and only the necessary source excerpts using [the question template](../tools/bridge-templates/review-question.md). Use one stable project root and task ID when asking Claude through the bridge. Do not forward whole chats, logs, authentication records or unrelated user files.
3. Record the actual received answer as a model response. A saved file is not proof that the other model wrote files, tested code, consented, or read more than the supplied references. Codex decides which suggestions are supported by source and current documentation.
4. Replace only the demonstrated defect: unsupported CLI flags, missing continuation/state, incorrect paths, unbounded inputs, unsafe diagnostics, or a testable behavior mismatch. Preserve working originals, public interfaces where practical, user data and third-party attribution. Document intentional interface changes.
5. Run focused offline tests and, only when authorized, minimal synthetic subscription calls. Record mocked tests, CLI readiness, real model replies, session continuation, host reconnection and file changes separately. Do not equate them or infer cost savings from shorter output.
6. Send one concise implementation note using [the follow-up template](../tools/bridge-templates/implementation-note.md) through the same task session. Keep each provider's session independent. Finish with observed results, remaining limitations and any user action needed to refresh a host.

If a current CLI/documentation fact is unclear, mark it unverified instead of inventing a flag or silently upgrading dependencies. A replacement should have a concrete trigger, expected result, evidence and smallest effective change. Do not remove controls, trust hooks automatically, retry endlessly or switch to a paid API to make a demonstration pass.
