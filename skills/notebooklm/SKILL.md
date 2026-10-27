---
name: notebooklm
description: Use NotebookLM for source-grounded questions, flashcards or quizzes when the user chooses NotebookLM. Ordinary Google Drive reading uses the existing Drive connector.
---
# Optional NotebookLM workflow

- Follow the [reuse rules](../study-cache/references/reuse-rules.md).
- Check whether a NotebookLM MCP tool or `nlm` CLI is available. Skill installation alone does not provide a runtime, account login or an authenticated source connection.
- Prefer the existing Drive connector plus local study cache for ordinary source reading. Do not add a second login or service to answer a simple source question.
- For an explicit NotebookLM task, read only the relevant part of [command reference](references/command_reference.md) or [workflows](references/workflows.md). Read [upstream instructions](references/upstream-SKILL.md) only if those do not resolve the operation; do not call `nlm --ai` by default.
- Use only designated sources. Never start web research, bulk imports, audio/video generation, public sharing or source deletion merely because they are available.
- User-owned account login remains interactive if required; do not extract another browser's credentials. Existing read authorization does not require repeated conversational confirmation.
- Check source revision/sync status; unknown freshness is not current. Present source-backed findings separately from generated interpretation.
- During practice, show the question first and reveal the answer after the student responds.

