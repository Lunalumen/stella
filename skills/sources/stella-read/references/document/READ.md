# 문서 읽기

DOCX는 문단, TXT·MD는 줄 구간, 저장된 Docs JSON은 탭·문단을 유지한다. 물리적 페이지를 추정하지 않는다. 원격 Docs 저장본은 --remote-id와 --revision을 함께 주며 현재 원격 revision은 기존 연결로 별도 확인한다. JSON은 native Docs API 저장본만 지원하며 임의 자료 목록 JSON은 직접 처리하지 않는다.
