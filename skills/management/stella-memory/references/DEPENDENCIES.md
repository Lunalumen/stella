# 의존성

## 실행 (memory.py, test_memory.py)
Python 3.10+ 표준 라이브러리만: `sqlite3`, `hashlib`, `json`, `re`, `unicodedata`, `uuid`. 검증 환경: Python 3.13.17, SQLite 3.50.4 (Windows 11). 외부 패키지·AI API·네트워크 없음.

## 관리 화면 (ui_server.py, ui/, test_ui_server.py)
같은 표준 라이브러리 + `http.server`, `secrets`, `hmac`, `tempfile`. 화면은 정적 HTML/CSS/JS(프레임워크·CDN·빌드 도구 없음). 브라우저 확인: Claude 데스크톱 앱 내장 브라우저(Chromium 계열)에서만 시험.

## 측정 (선택, 실행과 분리)
검색 전후 텍스트 비교는 `stella-token-audit/scripts/token_audit.py text`를 쓴다. 오프라인 tiktoken 모드는 `tiktoken` 패키지와 미리 준비한 인코딩 캐시(`--cache-dir`)가 필요하다. `--counter claude`는 anthropic 패키지와 API 자격 증명이 필요하며 이번 버전 검증에서는 실행하지 않았다.

## 데이터 위치
`<local-data>/`(DB, exports/, inbox/)는 skills 저장소 밖에 둔다. 다른 저장소·수동 업로드에 포함되지 않는지는 별도로 확인한다.

## 출처
한국어 띄어쓰기 무시 매칭 `study_pattern`은 같은 저장소 `skills/sources/study-cache/scripts/study_cache.py`에서 가져왔다. 외부 코드 없음.
