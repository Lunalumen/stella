# 로컬 관리 화면

## 실행
```text
python scripts/ui_server.py --db <DB 경로> [--port 8765] [--actor user]
```
- 주소: `http://127.0.0.1:8765/` (또는 `http://localhost:8765/`). **127.0.0.1에만 연결**하며 바꾸는 옵션은 없다.
- DB 파일이 없으면 화면에서 첫 작업을 할 때 만들어진다. 실제 기억용 DB(`<local-data>/…`)를 처음 만드는 것은 사용자가 직접 한다.
- 종료: 터미널에서 Ctrl+C.
- 화면 상단에 사용 중인 DB 경로·상태, 선택한 프로젝트, AI 연결 상태(현재 "연결 안 됨")가 항상 보인다.

## 기능 (모두 `memory.Store` 호출, 화면 전용 저장·충돌 로직 없음)
| 탭 | 하는 일 | 사용하는 Store 기능 |
|---|---|---|
| 기억 목록 | 프로젝트의 기억, 선택 시 대체됨·보관 중지 포함 | `show()` |
| 검색 | 키워드 검색, 부분 결과·충돌 경고 표시, 다음/이전 페이지 | `search(offset, max_response_chars)` |
| 추가 | 저장 전 미리보기(실제 결과: 새 기억/충돌 후보/중복/보관 중 재활성화) → 저장 | `add(dry_run)` → `add()` |
| 상세 | 필드, 개정 이력, 수정(미리보기·예상 개정 확인), 보관 중지, 삭제 | `show(include_all)`, `update(dry_run)`, `retire()`, `delete(confirm)` |
| 충돌 | 미해결 그룹과 후보, 사용자가 고른 후보만 유지 | `open_conflicts()`, `resolve()` |
| 가져오기 | JSONL 미리보기 → 오류 0개일 때만 적용(전부 성공 또는 전부 취소). 미리보기 뒤 파일 내용이 바뀌면 거부 | `import_jsonl()` |
| 내보내기 | JSONL·전달문을 브라우저 다운로드로 받음(서버에 파일을 남기지 않음) | `export()` |
| 작업 기록 | 원문 없는 감사 기록 | `audit_log()` |

## 보안 설계
- 서버 시작마다 새 임의 토큰을 만들고 페이지에만 넣는다. 모든 API는 `X-Stella-Token` 헤더가 맞아야 한다. 다른 사이트는 이 페이지를 읽을 수 없으므로 토큰을 얻지 못한다.
- `Host`는 `127.0.0.1:<port>`/`localhost:<port>`만 허용(DNS 리바인딩 방어). `Origin`·`Sec-Fetch-Site`가 오면 같은 출처여야 한다.
- API는 POST + `application/json`만. CORS 허용 헤더를 보내지 않으며 OPTIONS는 거부한다.
- CSP `default-src 'none'; script-src 'self'; …; frame-ancestors 'none'`, `nosniff`, `no-store`.
- 기억 내용·가져온 파일은 신뢰하지 않는 데이터로 다룬다. 화면은 `textContent`로만 그리고 HTML로 해석하지 않는다. 파일 안의 작성자·검증 표시는 무시한다.

## 한계
- 같은 PC의 다른 프로그램(같은 사용자 권한)은 막지 않는다. 토큰은 서버 콘솔에 출력하지 않지만 페이지 HTML에는 들어 있다.
- 오류 문구 일부는 `memory.py`의 영어 메시지를 그대로 보여 준다.
- 여러 프로세스가 동시에 쓰는 상황은 SQLite 잠금(5초 대기)에 맡기며, 다중 프로세스 동시성 시험은 하지 않았다.
- ChatGPT·Claude가 이 화면이나 DB에서 기억을 자동으로 불러오는 연결은 없다.
