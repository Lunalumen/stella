---
name: study-cache
description: Reuse supplied study material by storing source text with slide or section locations, checking changes, and retrieving bounded relevant passages. Use for repeated lecture-source lookup, not automatic whole-folder ingestion or learning-completion claims.
---
# Reuse study sources

The AI agent chooses the task; this skill provides its internal retrieval algorithm. Follow the [reuse rules](references/reuse-rules.md).

Use `scripts/study_cache.py` with a designated local input. It supports PDF (optional pypdf), PPTX, DOCX, UTF-8 TXT/MD and a saved native Google Docs API JSON response. Run `--help` only when syntax is unfamiliar.

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


## PDF 페이지 캐시

PDF는 물리적 페이지 순서를 section 번호로 저장한다. 인쇄된 쪽번호와 다를 수 있다. pypdf가 설치된 환경에서만 추출하며 자동 설치·OCR·외부 업로드는 하지 않는다. 빈 페이지는 OCR/원본 확인 필요 표시를 남기고, 전체가 비어 있으면 기존 캐시를 보존한 채 실패한다. 추출 텍스트는 표·수식·그림·읽기 순서를 검증하지 않는다. 관련 원본을 확인한다. 검색 발췌가 잘리면 필요한 다음 구간이나 read로 문맥을 확대한다. 파일 변경 시 재등록 전까지 오래된 캐시를 사용하지 않는다.

기본 DB는 현재 작업 폴더의 .study-cache/sources.sqlite다. 공유 저장소에서는 --db로 개인 캐시 위치를 지정하고 원자료·DB를 커밋하지 않는다.

작은 합성 PDF 실험과 한계는 [PDF_BENCHMARK.md](PDF_BENCHMARK.md)에 있다. 재현 검사가 필요할 때만 확인한다.

## 개인 공부 검색

한국어 띄어쓰기 차이를 허용하며 서로 다른 검색어가 함께 등장하는 구간을 먼저 반환한다. 단어 반복 횟수만으로 우선순위를 정하지 않는다. 동의어·의미 검색은 아니다.

앞뒤 정의·조건·예외가 필요하면 search --context-sections 1 --max-total-chars 3600을 사용한다. PDF 페이지·PPT 슬라이드 문맥만 추가하며 모든 발췌가 같은 본문 문자 예산을 공유한다. JSON 메타데이터와 토큰 수는 별도다. truncated와 context_omitted_for_budget을 확인하고 필요할 때만 read로 확대한다.

과목·시험별 course를 분리하고 지정 등록한 자료만 사용한다. 이전 시험 자료를 새 범위로 자동 등록하지 않는다. 원본의 그림·수식과 학습 완료는 별도 확인한다.
