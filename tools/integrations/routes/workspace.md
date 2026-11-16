# Google 자료
현재 Google Drive 플러그인이 파일 탐색의 시작점이다. Gmail과 Calendar는 해당 요청일 때만 선택한다. 현재 연결 상태를 확인하고 지정한 자료의 메타데이터 → 필요한 구간 순서로 읽는다. 같은 자료는 기존 study-cache/stella-read에 저장된 버전·해시와 대조해 재사용한다.
명월 자료를 자동 일괄 수집하지 않는다. 새 노트/메일/일정 쓰기는 별도 사용자 요청 범위에서 한다. 주식 자료를 Google에 자동 업로드하지 않는다.
`../upstream/workspace`는 외부 개발자의 MIT 소스이며 현재 Google 플러그인의 내부 구현이라고 주장하지 않는다. 로컬 실행은 Python 의존성·Google OAuth client 설정·사용자 로그인이 필요하다. 플러그인 인증과 로컬 OAuth는 서로 별개다.
