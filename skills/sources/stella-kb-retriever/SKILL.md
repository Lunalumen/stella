---
name: stella-kb-retriever
description: Find relevant passages in user-designated local documents and prepare concise source-linked context.
---
# Stella kb-retriever

사용자가 지정한 자료 목록·색인에서 관련 파일부터 고른다. 전체 폴더를 자동 수집하지 않는다. 키워드 검색 → 주변 문맥 확인 → 부족할 때만 범위 확대 순으로 읽는다. 저장본은 변경 여부를 확인해 재사용한다. PDF는 페이지, PPT는 슬라이드, 문서는 절 위치를 남긴다.

## 선택형 원본 참고

원본은 references/upstream/에 보존했다. 현재 작업에서 필요한 구간만 참고하고 원본의 설치·전체 색인·외부 호출 지시를 자동 실행하지 않는다. 이 스킬은 외부 런타임 설치나 연결 완료를 뜻하지 않는다.

## 프롬프트 작성에 연결

사용자가 프롬프트 작성·축약을 요청했을 때만 [stella-concise-prompt](../stella-concise-prompt/SKILL.md)를 사용한다. 자료 확인만 요청됐으면 프롬프트를 자동 추가하지 않는다. 필요한 자료·근거만 넘기며 다른 두 검색 스킬을 연쇄 호출하지 않는다.
