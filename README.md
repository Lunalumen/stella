# Stella

Reusable AI skills and source-code tools for local study, document reuse, memory, and research.

Maintained by [Lunalumen](https://github.com/Lunalumen). Documentation entry points are in English; existing skills, interfaces, and examples include Korean. This repository contains source code, not a hosted service or a copy of the maintainer's private data.

## Programs and technologies

| Component | Purpose | Entry point |
|---|---|---|
| Study Room | Local question bank, grading helpers, spaced review, source library, PDF/image review | [apps/study-room](apps/study-room/README.md) |
| Korea/US Stock Research | Official-source retrieval, document imports, caching, bounded research workflows | [apps/stock-research](apps/stock-research/README.md) |
| Stock Workroom | Local animated workflow demonstration and optional market chart | [workroom](apps/stock-research/workroom/README.md) |
| Agent Runtime | Explicit Codex SDK task planning, selected roles, bounded execution and usage records | [tools/agent-runtime](tools/agent-runtime/README.md) |
| CLI Bridges | Explicit task conversations with separate saved sessions for Claude/Codex | [unified bridge guide](tools/BRIDGE_README.md), [review workflow](docs/BRIDGE_WORKFLOW.md) |
| Integration Router | Select the relevant GitHub, Workspace, Firecrawl, Context7, Notion or stock branch | [tools/integrations](tools/integrations/README.md) |
| Stella Memory | Project-scoped local SQLite memory and experimental management UI | [memory skill](skills/management/stella-memory/SKILL.md) |
| Skills | Document reading, cache/retrieval, concise prompts, token audit, study, research, Java packaging | [skill catalog](skills/README.md) |

## Skills and provenance

The repository contains 26 skill entry points: 4 management, 10 source-reading/reuse, 3 summary, 6 study/review, 2 research/security, and 1 development/Java-packaging skill. Keep each `SKILL.md` with its referenced scripts, templates and license files. Read only the skill and reference sections needed for the task; copying files does not install a skill or connect an external service.

The original skill reorganization came from `Lunalumen/-` at commit `2b524f08161c16c399d58742c361301110fec0c3`; imported-source licenses and [upstream-lock.json](upstream-lock.json) are preserved. `upstream-SKILL.md` files are provenance snapshots, not execution entry points. See [concise prompt preparation](skills/sources/stella-concise-prompt/SKILL.md) and [token audit](skills/management/stella-token-audit/SKILL.md) for bounded text and usage comparisons.

## Start here

Clone or download the repository and follow the selected component's README. Python components target Python 3.12 or newer. The two private desktop web interfaces use Windows account-bound access; the study-room launcher uses Windows PowerShell. The agent runtime needs Node.js and its pinned npm dependency for model execution. Optional tools have their own requirements.

Local storage, cache lookup, the synthetic study demo, and mock research tests do not require model API calls. AI CLI/SDK execution consumes the configured account's usage and may incur charges. Hosted connectors and data providers have separate account requirements and limits. The Study Room paid API branch is disabled unless the user explicitly enables it. No installation, sign-in, paid service, or AI call runs just by downloading this repository.

## Privacy, provenance and readiness

Keep actual databases, source documents, chat history, credentials, exports, runtime installations and logs outside version control. See [SECURITY.md](SECURITY.md), [third-party notices](THIRD_PARTY_NOTICES.md), and [program export verification](docs/PROGRAM_EXPORT_2026-11-16.md).

The source export received syntax, configuration and private-reference checks. Most applications have not received a fresh end-to-end runtime test in the publication environment; the separately tested bridge sessions and remaining host-refresh limits are recorded in [bridge verification](docs/BRIDGE_VALIDATION_2026-11-17.md). Treat the programs as experimental; source preservation, successful syntax checks, live service connection, and measured token savings are different claims. Token/cost savings for the whole task have not been measured.

