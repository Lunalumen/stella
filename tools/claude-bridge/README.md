# Explicit Claude CLI bridge

Optional compatibility source for sending one user-authorized question to a separately installed official Claude CLI. It saves the visible request/answer and session metadata locally in `.bridge/`, supports explicit session continuation, and has task locks and bounded timeouts. It does not copy hidden reasoning, wake existing desktop chats, or start an automatic conversation loop.

Inspect `python bridge.py --help` before use. Install and authenticate the CLI yourself. The implementation checks the CLI/account path and removes selected API-routing environment variables; it does not include credentials or grant an account. Existing subscription usage and limits still apply. No Claude call was made for this export, and including this tool does not appoint Claude as a developer or authorize future calls.

For an explicitly authorized request after local setup: `python bridge.py ask --task example-001 --question-file ./question.txt --timeout 120`. Reusing that task continues its saved bridge session; `--new-session` explicitly starts again. `python bridge.py history --task example-001` reads the local visible history. These commands can transmit the selected question/context and consume account usage; they are examples, not commands run during publication.

Never publish `.bridge/`, prompts containing private data, authentication files or results. `test_bridge.py` contains synthetic subprocess mocks; a fresh test run and real CLI connection were not performed in this publication check.
