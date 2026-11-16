# User-edition publication check — 2026-11-16

## Audience and privacy

This report describes the distributed source and checks relevant to users of Stella. It does not describe an individual's computer, accounts, active services, or personal security configuration. Paths in usage examples are repository-relative or generic placeholders. No user is being asked to disclose credentials or private records.

## Scope and outcome

Reviewed the distributed Stella Memory source, tests, and UI documentation against the source baseline at `5f9c0d2906f05d5e4c3c72f6d73f073f4de5dab9`. Included the hash-match string verification fix together with the UI and search-response changes. No production database, memory export, chat log, authentication file, or personal course document is included.

The reviewed source snapshot had 142 tracked files. Pattern scanning of tracked text and the Git patch history available to this publication check found no matching GitHub/AI/AWS key patterns, private-key headers, user-home paths, or the selected personal identifiers. Historical file names contained no matching database, JSONL, environment, or course-document files. This is a bounded pattern check, not proof that every possible secret is absent. Remote-only references, Actions logs, releases, issues, and attachments were not inspected.

The 11 Memory files were selected as explicit source-file entries. Existing machine-specific database path examples in changed documentation were replaced with generic local-data placeholders. Existing upstream source licenses and attribution remain untouched. Git commit-author metadata may remain visible in repository history. Editing the current documentation does not remove historical copies.

## Source review

- The UI binds to IPv4 loopback only; there is no public-bind option.
- API requests require the per-start token and JSON content type; Host, Origin, and Fetch Metadata are checked. Static routes use a fixed allowlist.
- User memory text is rendered as text rather than HTML. No external CDN or model endpoint is added by this UI.
- Core reads and writes use the project-scoped store; imports retain preview and atomic-apply checks. The source includes tests for wrong tokens/origins/hosts, project separation, import rejection, and CRUD flows.
- Search-response limits are character limits, not measured model-token savings. Source notes above 500 characters are rejected rather than silently truncated.

## Validation actually performed

Parsed the four uploaded Python source/test files using Python's AST parser without importing or running them. Checked the browser JavaScript with Node's syntax checker. Inspected source, selected tests, file paths, and secret-pattern matches. No AI API was called and no actual user memory store was created.

Runtime unit tests, HTTP tests, browser interaction tests, and multi-process concurrency tests were **not run in this publication check**. Follow-up runtime validation requires an isolated disposable environment with network isolation, an allowlisted environment, read-only source/toolchain, scratch-only writes, and resource limits. No claim about any user's current computer or security controls is made by this source-only check. Do not interpret syntax checks or test-source presence as passing runtime tests.

For follow-up validation, use a disposable isolated environment with synthetic data and temporary storage only, then run `python -B -X utf8 scripts/test_memory.py -v` and `python -B -X utf8 scripts/test_ui_server.py -v` from the Memory skill directory. Keep the UI local and treat this version as experimental until those checks complete.

## Remaining boundaries

Same-user local programs can read the UI and database. Projects are not security tenants. SQLite storage is not encrypted by this application, and deletion is not secure erasure. No ChatGPT/Claude automatic memory connection or unlimited/free model usage is claimed. No formal comprehensive penetration test was performed.
