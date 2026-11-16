# Study Room

A local study application with server-side answers, question-bank sessions, objective/short-answer grading helpers, essay review states, retry history, weakness tagging, spaced review, source-bounded material lookup, and optional local document previews. The existing interface is primarily Korean.

## Windows quick start

From this directory, run `python -B -X utf8 setup_demo.py`, then `powershell -NoProfile -File start.ps1`. The launcher also runs the non-overwriting demo setup. It starts the server on `127.0.0.1:8765` and opens a short-lived account-bound unlock link. Python 3.12+ is recommended. The lock uses Windows DPAPI and the launcher restricts its local state directory to the current user and SYSTEM.

Setup creates only missing empty source/bank JSON registries in `private/`. The server supplies twelve clearly synthetic demo items. Existing local registries are preserved. Personal course sources, professor material, textbook exercise archives and real question banks are not bundled. The Java viewer contains a synthetic Hello example only.

For PDF/image functions, install the optional packages in `requirements-optional.txt` in your own environment. Poppler tools on PATH are needed for PDF rendering; local Windows OCR depends on installed OS language support. Source-cache and token-audit code is reused from `../../skills/`. Tokenizer files/runtime can be selected through `STELLA_TOKEN_AUDIT_RUNTIME` and `STELLA_TOKEN_CACHE`; no tokenizer package or model is bundled.

## Costs and limits

Question-bank/demo functions do not call an AI API. The optional OpenAI generation/grading branch is disabled unless `STELLA_ENABLE_PAID_API=1` is explicitly set along with `OPENAI_API_KEY` and `OPENAI_MODEL`. API usage can be billed separately from a chat subscription. Do not enable it unintentionally; the public export was not tested with an AI API.

This is a single-machine application, not a public learning-management service. Keep the loopback bind and account lock. Attempts, imported materials and caches remain local until the user removes them; clearing a browser cookie does not erase server data or backups. The default web port is also used by the Memory UI, so run one at a time or select a different port when starting a server manually. Fresh runtime/browser/DPAPI verification of this exported layout remains pending.
