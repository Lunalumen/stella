---
name: qmd
description: Search previously saved local study sources with QMD; retrieve only relevant cited sections. Use for indexed material lookup, not live Google Drive access or ordinary tutoring.
---
# Local source retrieval

- Follow the [reuse rules](../study-cache/references/reuse-rules.md).
- Search the requested course only. Start with exact terms using `qmd search ... -c <collection> -n 3`; read a bounded matching window using `qmd get <id>:<line>:40` before making claims.
- If QMD is not installed, use the parent's `study-cache` helper. Do not install models or run a semantic pipeline for a simple lookup.
- Use semantic search only after one lexical refinement fails and conceptual matching would help. Check runtime availability first; embedding/model setup is a separate setup action.
- QMD does not access Drive itself. Remote snapshots require source ID, revision and a current metadata check. A local match is not proof that Drive is unchanged.
- Index only designated sources; update changed documents only. Use the current user authorization for maintaining designated local caches; this package grants no additional permissions.
- Read [upstream reference](references/upstream-SKILL.md) only for unfamiliar advanced QMD commands. Do not follow its full-document or hybrid-search defaults when a relevant source window suffices.

