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

## 개인 공부 검색

한국어 띄어쓰기 차이를 허용하며 서로 다른 검색어가 함께 등장하는 구간을 먼저 반환한다. 단어 반복 횟수만으로 우선순위를 정하지 않는다. 동의어·의미 검색은 아니다.

앞뒤 정의·조건·예외가 필요하면 search --context-sections 1 --max-total-chars 3600을 사용한다. PDF 페이지·PPT 슬라이드 문맥만 추가하며 모든 발췌가 같은 본문 문자 예산을 공유한다. JSON 메타데이터와 토큰 수는 별도다. truncated와 context_omitted_for_budget을 확인하고 필요할 때만 read로 확대한다.

과목·시험별 course를 분리하고 지정 등록한 자료만 사용한다. 이전 시험 자료를 새 범위로 자동 등록하지 않는다. 원본의 그림·수식과 학습 완료는 별도 확인한다.

## 설명 본문과 중복 발췌

검색어 일치 정도가 같으면 짧은 과제형 질문보다 설명 본문을 우선하는 휴리스틱이다. 같은 원본에서 반환된 텍스트에 완전히 포함되는 미절단 발췌만 생략하고 위치를 included_locations·duplicate_count로 남긴다. 다른 원본·부분 중복·별도 예외·잘린 텍스트는 보존한다. 생략한 자리에는 추가 자료를 채우지 않으며 필요하면 read로 원문을 확인한다. 설명 우선으로 길이가 늘 수도 있어 토큰 절감으로 단정하지 않는다.
