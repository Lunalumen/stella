# GitHub
현재 연결된 GitHub 플러그인을 기본으로 사용한다. 저장소·파일 범위를 지정하고 해당 파일/변경만 읽는다. 원본 코드는 `../upstream/github`, 고정 커밋은 `../upstream-lock.json`에 있다. 사용자 수정은 별도 어댑터에 둔다.
내 스킬 저장소는 실제 연결로 확인한 `Lunalumen/stella`. 주식 연결 지침은 `skills/research/stock-research/SKILL.md`. 공개 배포본에는 개인 경로·자료·토큰을 넣지 않는다. 스킬 저장소의 연결 지침과 로컬 수집기 전체를 구분한다.
로컬 GitHub MCP 실행은 공식 바이너리와 별도 OAuth/PAT가 필요하다. 기존 플러그인 인증을 꺼내거나 복제하지 않는다. 파일 변경 요청이 있을 때만 원격에 쓴다. 이번 도입은 원격 저장소 수정·새 fork 공개를 자동 수행하지 않는다.
