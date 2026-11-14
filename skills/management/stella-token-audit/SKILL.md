---
name: stella-token-audit
description: Compare supplied text token counts or exported whole-task usage before and after an optimization, while checking scope and required content. Use to assess claimed token savings, not to shorten prompts or infer hidden ChatGPT usage.
---
# 토큰 절감 평가

scripts/token_audit.py를 실행한다. 사용자가 --counter claude를 선택한 경우의 토큰 계산 요청 외에는 AI API를 호출하지 않으며, 로그 전체 수집·사용자 계정 조회는 하지 않는다. 필요한 파일만 지정받고 원자료·로그·키는 GitHub에 올리지 않는다.

- text: 같은 계산기로 두 텍스트를 계산한다. 기본 --counter tiktoken은 ChatGPT 계열 기준으로, 명시적으로 준비한 캐시만 쓰고 자동 다운로드하지 않는다. Claude에서 쓸 스킬은 --counter claude --model <모델ID>로 Anthropic count_tokens(생성 없음, 네트워크 필요)를 쓴다. 두 수치는 서로 바꿔 쓰지 않는다. --required의 필수 표현 보존은 문자열 검사일 뿐 의미 정확성을 검증하지 않는다.
- usage: 준비·검색·압축·생성·재시도를 포함한 whole_task 단위의 제공된 사용량을 합산한다. task_id·model·config_id가 같고 complete=true, scope=whole_task와 품질 통과 근거가 있을 때만 제공 로그에서 감소했다고 표시한다. 누락·설정 차이·품질 실패·합성 로그이면 판정 자료 부족이다.
- cached_tokens는 input, reasoning_tokens는 output의 부분집합이므로 더하지 않는다. 비용·구독료 절감을 토큰 감소로 추정하지 않는다.
- 실제 로그가 없으면 실제 총토큰은 미측정이다. text 결과를 전체 ChatGPT·Codex 소비량이라고 표시하지 않는다. 한 번의 비교를 일반 절감률로 확장하지 않는다.

실행 형식과 기록 양식은 필요할 때만 [references/USAGE.md](references/USAGE.md)를 읽는다. 판정은 결과 / 비교 범위 / 전후 수치 / 품질·누락 / 한계 순으로 짧게 보고한다. JSON의 보고자 진술만으로 로그 진위·완전성을 독립 검증했다고 하지 않는다.
