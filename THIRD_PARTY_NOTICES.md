# Sources and third-party components

The original source programs remain in their local projects; this repository holds a source-only public adaptation with portable paths and no private runtime state. Existing `skills/**` upstream license files and the root `upstream-lock.json` remain authoritative for the previously imported skills. Do not claim all linked projects as original Stella work or override a third-party license with this document.

- Agent Runtime uses `@openai/codex-sdk` as a pinned dependency. It is not vendored. Coordination profile adaptations refer to [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents); the retained MIT license is [here](tools/agent-runtime/THIRD_PARTY_LICENSES/agency-agents.LICENSE).
- Graft and codebase-memory-mcp are optional external installations, not included binaries or indexed data.
- Stock research references [anthropics/financial-services](https://github.com/anthropics/financial-services) and [obra/superpowers](https://github.com/obra/superpowers) in its research policy; full external skill archives and private source-review reports are not included in this program export.
- The integration registry links [github/github-mcp-server](https://github.com/github/github-mcp-server), [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp), [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl), [upstash/context7](https://github.com/upstash/context7), and [makenotion/notion-mcp-server](https://github.com/makenotion/notion-mcp-server). Linked repositories retain their own licenses; Firecrawl includes AGPL components. These server sources and binaries are not vendored by this export.
- Optional PDF/image libraries and Poppler are separately installed and retain their own licenses. TradingView chart embedding is an optional external service governed by the provider's terms, not a bundled chart engine or market-data license.
- Official Claude and Codex CLIs, accounts and subscriptions are not distributed here. Their usage limits and commercial terms are independent of the wrapper source.

Do not infer unlimited free operation, ownership of upstream code, or permission to redistribute private course documents from source availability. No license grant for another party's material is made by this notice.
