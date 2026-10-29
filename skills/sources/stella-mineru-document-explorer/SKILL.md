---
name: stella-mineru-document-explorer
description: Navigate large documents by section or page and inspect relevant tables and figures.
---
# Stella mineru-document-explorer

긴 문서는 목차·검색으로 위치를 먼저 찾고 해당 페이지·절만 읽는다. 표·수식·그림이 답에 영향을 주면 원본을 시각 확인한다. MinerU 실행 환경이 확인된 경우에만 해당 도구를 사용한다. 없으면 기존 PDF·문서 도구로 같은 흐름을 수행하고 미연결 상태를 밝힌다. 위키 생성·모델 설치·자동 색인은 별도 요청이 있을 때만 한다.

## 선택형 원본 참고

원본은 references/upstream/에 보존했다. 현재 작업에서 필요한 구간만 참고하고 원본의 설치·전체 색인·외부 호출 지시를 자동 실행하지 않는다. 이 스킬은 외부 런타임 설치나 연결 완료를 뜻하지 않는다.

## 프롬프트 작성에 연결

사용자가 프롬프트 작성·축약을 요청했을 때만 [stella-concise-prompt](../stella-concise-prompt/SKILL.md)를 사용한다. 자료 확인만 요청됐으면 프롬프트를 자동 추가하지 않는다. 필요한 자료·근거만 넘기며 다른 두 검색 스킬을 연쇄 호출하지 않는다.
