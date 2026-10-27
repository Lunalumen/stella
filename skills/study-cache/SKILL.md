---
name: study-cache
description: Reuse supplied study material by storing source text with slide or section locations, checking changes, and retrieving bounded relevant passages. Use for repeated lecture-source lookup, not automatic whole-folder ingestion or learning-completion claims.
---
# Reuse study sources

The AI agent chooses the task; this skill provides its internal retrieval algorithm. Follow the [reuse rules](../study-cache/references/reuse-rules.md).

Use `scripts/study_cache.py` with a designated local input. It supports PPTX, DOCX, UTF-8 TXT/MD and a saved native Google Docs API JSON response. Run `--help` only when syntax is unfamiliar.

```text
python scripts/study_cache.py --db <private-cache>/sources.sqlite ingest <file> --course <course>
python scripts/study_cache.py --db <private-cache>/sources.sqlite search <keywords> --course <course> --limit 3 --max-chars 1200
python scripts/study_cache.py --db <private-cache>/sources.sqlite read <source-id> <section-number> --offset 0 --max-chars 2500
```

- Use the existing cache before importing again. `ingest` compares content hashes and skips unchanged extraction. Search/read omit local sources whose bytes have changed or disappeared.
- A remote snapshot also needs `--remote-id <Drive-id> --revision <observed-version>`. Before using its result, check current Drive metadata with the existing connector and compare to the returned revision. The helper cannot authenticate or check remote freshness.
- Resolve an existing source by ID/recorded path; do not rerun broad Drive discovery. Save only the requested document response locally. Read its relevant sections rather than sending the full response into the conversation again.
- A new remote revision replaces the old source's cache. Passing the same remote revision with different content is a conflict, not a fresh cache. Preserve the original; resolve with a new metadata read.
- Search is lexical (SQLite candidate filtering and bounded excerpts), without embeddings or model calls. Korean substring matching handles common inflected terms; no match warrants one query refinement or source inspection.
- Section numbers preserve PPT presentation order and Google Docs tab/paragraph location. Empty or graphical slide text is not evidence that the slide has no content. The helper reports visual content as unverified.
- Do not infer formulas, chemical models, diagrams, emphasis, or lecture meaning from extraction alone. Inspect relevant source visuals when needed.
- Read outputs include offsets and a truncation flag. Fetch the next slice only when the task needs it. Never present a truncated passage as the complete source.
- The helper's parsing/search tests are infrastructure checks; they do not mean the user's course materials have been read, summarized, or learned. No corpus is ingested automatically.

