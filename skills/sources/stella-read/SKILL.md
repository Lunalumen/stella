---
name: stella-read
description: Read a designated PDF, PPTX, DOCX, text file or saved Docs snapshot through one entry point, reusing the existing cache and following only the needed format branch. Use when a file or cached source is known, not for open-ended discovery.
---
# 자료 보고 읽기

파일이 지정되면 다시 찾지 말고 scripts/read_source.py를 실행한다. 새 파일은 등록·조회가 한 번에 처리되고 다음 요청은 반환된 source_id로 바로 이어간다. 기존 study-cache를 재사용한다. 등록·추출은 읽기 검증·학습 완료와 구분한다.

형식 처리가 필요할 때 아래 가지 하나만 읽는다. 이미 같은 가지를 확인했고 조건이 같으면 다시 읽지 않는다.
- PDF: [PDF 읽기](references/pdf/READ.md)
- PPTX: [PPT 읽기](references/ppt/READ.md)
- DOCX·TXT·MD·저장된 Docs JSON: [문서 읽기](references/document/READ.md)

--db <개인DB> --course <과목·시험> <파일> --query <핵심어>
--db <개인DB> --course <과목·시험> --source-id <ID> --query <핵심어>
--db <개인DB> --course <과목·시험> --source-id <ID> --section <번호>

Python을 앞에 붙여 scripts/read_source.py에 전달한다. --max-chars는 구간 한도, --max-total-chars는 문맥 포함 본문 합계다. 전체 JSON·모델 토큰 수는 아니다. 필요할 때만 --context-sections 1을 쓴다.

검색은 지정 파일 안에서만 한다. 못 찾으면 검색어를 한 번 보완하거나 원문의 필요한 절을 읽고, 충분하면 종료한다. 전체 요약 요청은 일부 검색 결과로 대체하지 않는다. 경로가 없거나 바뀌면 그 대상만 확인하고 전체 폴더 검색으로 확대하지 않는다.

반복 지침·다른 스킬·원본 안내를 연쇄 로딩하지 않는다. 외부 변환 도구는 기존 도구로 해결되지 않을 때만 선택한다. 네트워크·유료 API·자동 OCR·자동 설치는 없다. 토큰 평가는 요청됐을 때만 별도로 한다.
