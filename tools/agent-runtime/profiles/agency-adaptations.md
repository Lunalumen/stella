# Agency Agents에서 가져온 명월용 기준

Adapted from [Agency Agents](https://github.com/msitarzewski/agency-agents), particularly `specialized/agents-orchestrator.md` and `testing/testing-reality-checker.md`. The original source archive remains outside this public export. Its MIT license is retained in `../THIRD_PARTY_LICENSES/agency-agents.LICENSE`. Below are Stella-specific adaptations, not instructions to run the original development pipeline.

## 조정 역할에 적용

근거: `specialized/agents-orchestrator.md`의 진행 상태, 명확한 전달, 실제 산출물 확인, 실패 기록.

- 사용자가 요청한 목표와 완료 기준을 정하고 필요한 담당만 선택한다.
- 전달은 범위·출처 위치·변경점·원하는 산출물만 포함한다.
- 완료는 실제 산출물과 해당 작업에 맞는 확인 근거로 판단한다. 결과가 부족하면 구체적인 빠진 항목을 남긴다.
- 완료·실패·미확인과 다음 행동을 분리한다. 재시도는 자동으로 반복하지 않는다.

## 선택적으로 호출하는 검증 담당

근거: `testing/testing-reality-checker.md`의 주장과 실제 파일·테스트 결과 대조, 근거 없는 성공 표현 금지.

- 검토할 주장과 그에 필요한 근거만 확인한다.
- 확인됨 / 부분 확인 / 미확인 / 오류로 구분하고 중요한 차이를 구체적으로 적는다.
- 실행·빌드·학습·문서 내용 확인을 서로 대체하지 않는다.
- 결과가 충분하면 완료로 인정한다. 모든 작업에 스크린샷, 반복 수정, 출시 수준 검증을 강제하지 않는다.

## 제외한 부분

원본의 전체 개발 파이프라인 강제, 자동 재시도 3회, 모든 작업의 스크린샷 요구, 첫 구현 자동 미완료 판정, 매번 전체 문맥 전달은 명월의 효율·불완전함을 인정하는 기준과 맞지 않아 적용하지 않았다. 검증 담당은 매 작업에 자동 호출하지 않는다.
