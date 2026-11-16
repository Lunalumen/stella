# Security and private data

This is a source and skill-instruction repository. Never commit real memory databases, chat transcripts, exports, course documents, authentication files, API keys, or machine-specific configuration. Use synthetic fixtures in tests. `.gitignore` is a guardrail, not a secret detector: it does not remove files already committed or historical copies.

## Stella Memory local UI

The management server is experimental, intended for one trusted local OS user. It binds to `127.0.0.1` only. Do not expose it through a reverse proxy, tunnel, public host, or port forwarding. Project names separate work inside a database; they do not provide tenant authorization or OS isolation.

The source implements per-start API tokens, Host and Origin checks, JSON-only POST operations, fixed static-file routes, restrictive response headers, and text rendering for imported memory content. These controls do not protect against other programs running as the same OS user. The token is present in the local page HTML. Memory is stored in ordinary SQLite files without application-level encryption. Protect those files and backups using OS permissions and appropriate storage protection.

Retiring a memory is not deletion. Deletion is not guaranteed secure erasure of SQLite pages, exports, snapshots, or backups. Never store credentials or highly sensitive records in this tool.

## Reporting

Do not disclose credentials, real records, or exploit details in a public issue. Use the repository's **Security → Report a vulnerability** option if it is available. If private reporting is unavailable, ask the maintainer for a private reporting channel without posting the sensitive material.

If a credential is exposed, revoke or rotate it with its provider. Removing the current file or switching the repository back to private does not revoke credentials or recall downloaded copies.

Third-party source keeps its original license and attribution. Publishing source does not make third-party services, subscriptions, or API calls free.
