# 자료 읽기·재사용

자료를 읽고, 필요한 구간을 찾고, 저장본을 재사용할 때 선택합니다.

| 스킬 | 용도 |
|---|---|
| [read-and-summarize](read-and-summarize/SKILL.md) | 자료 확인·이해·핵심 요약 |
| [study-cache](study-cache/SKILL.md) | 자료 변경 확인과 저장본 재사용 |
| [qmd](qmd/SKILL.md) | 저장된 자료의 관련 구간 검색 |
| [ppt2word](ppt2word/SKILL.md) | PPT 자료 재사용과 Word 변환 |
| [notebooklm](notebooklm/SKILL.md) | 선택형 NotebookLM 연결 |

[전체 분야](../README.md) · [Stella 홈](../../README.md)

## Stella 프롬프트·자료 처리

- [stella-kb-retriever](stella-kb-retriever/SKILL.md): Find relevant passages in user-designated local documents and prepare concise source-linked context.
- [stella-mineru-document-explorer](stella-mineru-document-explorer/SKILL.md): Navigate large documents by section or page and inspect relevant tables and figures.
- [stella-markitdown](stella-markitdown/SKILL.md): Prepare user-designated documents as searchable text while preserving source locations.

필요한 스킬 하나부터 선택합니다. 3개를 매번 함께 읽지 않습니다. 원본 지침·라이선스는 각 references/upstream/에 보존하고 출처 커밋은 [STELLA_IMPORTS.json](STELLA_IMPORTS.json)에 기록합니다.

## 프롬프트 만들기

[공통 프롬프트 작성법](PROMPT_GUIDE.md): 검색한 자료를 목표·근거·조건·원하는 결과로 정리하고 중요한 정보가 보존됐는지 확인합니다.

- [stella-concise-prompt](stella-concise-prompt/SKILL.md): 중요한 요구사항을 보존하고 완성된 짧은 프롬프트 하나만 출력합니다.
