---
name: stella-markitdown
description: Prepare user-designated documents as searchable text while preserving source locations.
---
# Stella markitdown

기존 추출본과 변경 여부부터 확인한다. 필요한 형식의 변환기만 사용한다. MarkItDown이 있으면 지정 문서만 변환하고 없으면 현재 이용 가능한 형식별 도구를 쓴다. 변환 결과에 원본명과 페이지·절 위치를 연결한다. 페이지 대응이 유실되면 확인 필요로 표시한다. 스캔은 OCR 필요 여부를 확인하고 외부 업로드·유료 OCR은 자동 실행하지 않는다. 변환 성공을 그림·수식 검증 완료로 간주하지 않는다.

## 선택형 원본 참고

원본은 references/upstream/에 보존했다. 현재 작업에서 필요한 구간만 참고하고 원본의 설치·전체 색인·외부 호출 지시를 자동 실행하지 않는다. 이 스킬은 외부 런타임 설치나 연결 완료를 뜻하지 않는다.

## 프롬프트 작성에 연결

사용자가 프롬프트 작성·축약을 요청했을 때만 [stella-concise-prompt](../stella-concise-prompt/SKILL.md)를 사용한다. 자료 확인만 요청됐으면 프롬프트를 자동 추가하지 않는다. 필요한 자료·근거만 넘기며 다른 두 검색 스킬을 연쇄 호출하지 않는다.
