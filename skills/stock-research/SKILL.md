---
name: stock-research
description: Route company research to an explicitly configured source-linked research module and reuse its relevant cached context. Use for company analysis, not orders or automatic monitoring.
---

# 선택형 주식 리서치 연결

이 스킬은 모듈 연결 지침이며 수집기·거래 API·분석 모델 자체를 포함하지 않는다. 개인 경로·로그인·계좌 정보는 배포하지 않는다.

- 사용자가 지정한 리서치 모듈의 SKILL.md와 실행 안내를 필요한 때만 읽는다. 모듈 경로가 설정되지 않았거나 필요한 도구가 없으면 미연결이라고 알리고 무엇이 필요한지 설명한다. 설치만으로 연동 성공을 주장하지 않는다.
- 해당 요청의 종목·질문·기준일에 필요한 근거와 변경 구간만 읽는다. 수집 준비·AI 해석·근거 검증 완료를 구분하고 최신성이 필요한 주장에는 현재 출처를 확인한다.
- 리서치는 현재 대화에서 수행한다. 공부 담당·전체 스킬·별도 모델을 매번 불러오지 않는다. 모듈이 제공하는 검토/저장 절차가 있으면 그 범위 안에서 사용한다.
- 주문·유료 API·예약 감시 권한을 만들지 않는다. 실제 사용량 없이 비용/토큰 절감을 수치화하지 않는다.
