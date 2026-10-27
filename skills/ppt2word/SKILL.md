---
name: ppt2word
description: Convert a supplied PPTX into Word when a document is requested. For repeated study lookup, reuse slide-numbered cached text instead of generating Word each time.
---
# PPT reuse and optional Word conversion

- Follow the [reuse rules](../study-cache/references/reuse-rules.md).
- For studying, first check the existing source cache and version. Use `study-cache` for slide-numbered text extraction; do not generate DOCX merely to answer a question.
- A text extraction does not validate illustrations, chemical models, formulas or diagrams. Inspect the relevant original slide when these affect the answer.
- Only for requested PPT-to-Word conversion, read [conversion reference](references/upstream-SKILL.md), then inspect the applicable bundled script before execution. Dependencies are installed only when needed.
- Preserve Korean UTF-8. Do not apply the upstream's unconditional gb18030 decoding. Determine slide count and order from the file; do not copy its hard-coded 93-slide example.
- Do not discard failed images silently or treat the template's company/title fields as user content. Report unsupported content and verify the requested output.

