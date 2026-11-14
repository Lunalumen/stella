# 전달 양식과 연결 현황

## AI 간 전달문 (`export --format handoff`가 생성)
```text
대상: <project> / 기억 N건
기준: <UTC 시각> 저장소 상태
결과:
- (kind) key [충돌 미해결]: 내용  <id 앞 8자 rN>
확인: 저장소에서 직접 읽음. 사용자 발언 원문은 재확인하지 않음
미확인: retired·삭제 건 제외. 검색 누락 ≠ 저장 부재
다음: 수신자가 변경 제안은 JSONL로 inbox에 둠
```
루나 전달 규격(`luna-manager/references/handoff.md`)의 축약이다. 수신자는 이 전달문을 검토 자료로 읽고, 저장·변경은 사용자 지시가 있을 때 `import`/`add`로 한다.

## 제안 JSONL (inbox용, 한 줄 = 기억 1건)
```json
{"project":"p1","key":"report.length","kind":"constraint","text":"보고서는 참고문헌 제외 1,000자 이내","source_note":"사용자 지시 2026-11-14"}
```
`memory_id`는 기존 export를 되돌릴 때만 넣는다. 파일 안의 `requested_by`·`source_verified`·`actor`는 무시된다.

## 환경별 연결 현황 (2026-11-14, 실제 시험 / 추정 구분)
| 환경 | 읽기 | 쓰기 | memory.py 실행 | 근거 |
|---|---|---|---|---|
| Claude Code | 실제 성공 | 실제 성공 | 실제 성공 (Python 3.13) | 이 스킬을 만든 세션 |
| Codex 데스크톱 | 실제 성공 | 실제: 기본 권한 거부, 승인된 권한 확장에서 성공 | 미시험 | ChatGPT의 review-chatgpt.md 보고 |
| 다른 Codex 세션 | 추정 | 추정 | 추정 | 일반화하지 않음 |
| ChatGPT 웹 / Claude 웹 | 미시험 | 미시험 | 불가(추정) | 로컬 경로만으로 연결된다고 가정하지 않음 |

자동 연결이 없는 환경: 사용자가 `search` 결과나 handoff 전달문을 붙여 넣고, 상대의 제안은 사용자가 JSONL로 `E:/claude/memory/inbox/`에 저장한 뒤 `import`한다. 상시 감시·자동 왕복은 구성하지 않는다.
