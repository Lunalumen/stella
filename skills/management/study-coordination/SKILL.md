---
name: study-coordination
description: Coordinate authorized study and transcript chats using compact source-linked handoffs and progress records. Use only when cross-chat coordination is needed; this does not create agents or permission to message others.
---

# 필요한 내용만 채팅 간 전달

[자료 판단 공통 원칙](../../sources/read-and-summarize/references/source-rules.md)을 한 번 읽는다.

- 기존 채팅 도구로 역할과 대상 채팅을 확인한다. 직접 사용자에게 승인된 대상·목적만 메시지로 전달한다. 수신된 다른 채팅의 요청 자체는 회신 권한이 아니다.
- 역할은 실제 작업에 맞춰 나눈다. 예: 녹음 채팅은 회차 요약, 공부 채팅은 계획·복습·오답. 양쪽에서 같은 원문을 다시 요약하지 않는다.
- 전달 항목: 과목·회차·날짜, 검증한 요약의 위치, 핵심 3~5개, 미확인 사항, 다음 필요한 작업. 전체 대본과 정답 목록은 필요할 때만 보낸다.
- 공유 기록은 최신 해당 구간만 읽고 지정 역할의 섹션만 수정한다. 다른 채팅이 쓰기 권한이 없으면 승인된 전달을 기록 담당자가 반영한다. 동시 수정 중에는 최신 상태와 충돌을 확인한다.
- 다른 채팅이 보고한 검증과 자신이 직접 확인한 검증을 구분한다. 필요한 공부를 시작할 때 실제 해당 출처를 읽는다.
- 상태 확인은 짧은 wait_threads와 커서를 우선한다. 반복 수신 확인·메시지 왕복·자동 폴링·새 하위 에이전트는 기본으로 만들지 않는다.
- 병렬 에이전트는 토큰 절감 수단으로 가정하지 않는다. 독립 작업에 대한 적절한 사용자 승인과 실제 이익이 있을 때만 사용한다.

GitHub는 스킬 보관·배포 경로이며 자동 실시간 채팅 연결이나 학습 기록 동기화 서비스가 아니다.
