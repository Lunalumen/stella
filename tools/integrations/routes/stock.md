# 한국·미국 상장기업
`../registry.json`의 stock.root와 기존 stock-research 스킬을 사용한다. `../luna.py stock status` / `stock resolve 삼성전자` / `stock request "애플 기업 분석"`으로 기존 모듈에 직접 전달한다. 학교 자료·문제은행·공부용 담당을 불러오지 않는다.
GitHub 연결은 `Lunalumen/stella`의 `skills/research/stock-research/SKILL.md`에서 확인됐다. 배포 스킬은 연결 지침이며 수집기 전체가 아니다. 기존 로컬 모듈의 financial-services/superpowers 선별 원본과 라이선스를 그대로 재사용한다.
한국 DART/KRX·KIND/IR, 미국 SEC/IR을 우선한다. SEC 식별자와 무료 DART 키 설정 여부를 확인하고 없으면 가능한 공개 IR/로컬 자료 경로와 한계를 표시한다. 키·개인 연락처를 대화에 요구하거나 임의로 채우지 않는다.
request는 작은 근거 패킷을 준비하며 AI 분석 완료가 아니다. 그 context만 읽고 현재 대화에서 분석 후 기존 complete 검증/저장 절차를 쓴다. PDF·표·차트의 숫자는 실제 원본·단위·기간 대조 전 확정하지 않는다. 최신 시세·공시 확인 전 현재 데이터처럼 말하지 않는다.
주문·유료 모델 API·자동 감시는 연결하지 않는다. Firecrawl은 이 프로젝트의 기존 무료 단일 페이지 정책을 따르고, GitHub/Notion/Google로 투자 자료를 자동 전송하지 않는다.
