# 자료 보고 읽기

파일이 지정된 요청은 [stella-read](stella-read/SKILL.md) 하나에서 시작합니다.

```text
stella-read/
├─ references/pdf/READ.md
│  ├─ text.md    텍스트 추출·재사용
│  ├─ scan.md    스캔·OCR 필요 판단
│  └─ visual.md  표·그림·수식 확인
├─ references/ppt/READ.md
├─ references/document/READ.md
└─ scripts/read_source.py
```

하위 가지는 필요할 때만 읽는 내부 모듈입니다. 별도 에이전트나 독립 스킬을 매번 호출하지 않습니다. 이미 아는 파일은 바로 처리하고 반환된 자료 ID로 이어갑니다. 기존 study-cache를 재사용하며 지정 파일 안에서만 검색합니다. 같은 파일은 재추출하지 않습니다.

## 보조 기능

- [stella-kb-retriever](stella-kb-retriever/SKILL.md): 대상 파일을 모를 때 지정 과목 캐시에서 찾기
- [study-cache](study-cache/SKILL.md): 공통 추출·저장·변경 확인 엔진
- [read-and-summarize](read-and-summarize/SKILL.md): 자료 이해·요약 기준
- [qmd](qmd/SKILL.md): 선택형 고급 검색
- [ppt2word](ppt2word/SKILL.md): Word 산출물이 필요할 때
- [notebooklm](notebooklm/SKILL.md): 사용자가 해당 서비스를 선택했을 때
- [stella-markitdown](stella-markitdown/SKILL.md) · [stella-mineru-document-explorer](stella-mineru-document-explorer/SKILL.md): 기본 도구로 해결되지 않는 추가 변환·탐색의 선택 참고
- [stella-concise-prompt](stella-concise-prompt/SKILL.md): 프롬프트 축약 요청 때만

[공통 프롬프트 작성법](PROMPT_GUIDE.md) · [원본 출처](STELLA_IMPORTS.json) · [전체 분야](../README.md)

폴더 계층만으로 실제 모델 토큰 절감이 보장되지는 않습니다. 원본 지침·라이선스·기존 기능은 보존했습니다.
