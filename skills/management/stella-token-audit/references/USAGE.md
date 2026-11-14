# 실행과 근거 양식

text BEFORE.txt AFTER.txt --encoding o200k_base --runtime <tiktoken설치폴더> --cache-dir <준비된캐시> --required facts.json
text BEFORE.txt AFTER.txt --counter claude --model claude-opus-5-5 --required facts.json
usage BEFORE.json AFTER.json

--counter claude는 anthropic 패키지와 자격 증명(ANTHROPIC_API_KEY 또는 `ant auth login` 프로필)이 필요하다. 키를 명령줄·파일·저장소에 적지 않는다. count_tokens는 입력 토큰만 세고 답변을 생성하지 않는다. 메시지 포장에 따른 소량의 고정 토큰이 포함되지만 전후 차이에서는 상쇄된다. 모델이 다르면 토크나이저가 다를 수 있으므로 실제 사용할 모델 ID를 지정한다. tiktoken 수치는 Claude 토큰보다 적게 나오는 경향이 있으므로 Claude 결과로 표시하지 않는다.

scripts/token_audit.py 앞에 사용할 Python 경로를 붙인다. --output은 하위 명령 앞에 둔다. 입력을 덮어쓰지 않고 기존 결과 파일도 덮어쓰지 않는다. encoding은 실제 대상에 맞게 지정하며 모델을 추측하지 않는다. o200k_base는 이번 비교용 기준이지 현재 채팅 모델의 내부 토큰화라고 주장하지 않는다.

usage 입력은 templates/run.json을 따른다. calls에는 개별 요청 usage만 한 번씩 넣고 누적 session total과 섞지 않는다. call id를 고유하게 쓰고 Responses 형식 input_tokens/output_tokens로 명시적으로 정규화한다. Chat Completions나 Codex의 다른 로그 포맷을 그대로 넣지 않는다. 수집 도구의 cached input 포함 기준을 확인하고 모델 설정이 같음을 config_id에 기록한다. 완전한 내보내기를 확보하지 못하면 complete=false로 둔다.

quality_passed와 quality_basis는 외부의 검토 결과다. 필수 사실·정확성·근거·재질문을 비교하고, 단순 문자열 포함을 의미 평가 통과로 바꾸지 않는다. 합성 사용량은 origin=synthetic_test로 표시하며 실제 절감 판정을 내리지 않는다.

로컬 사용량 모드는 Python 표준 라이브러리만 필요하다. 텍스트 모드는 무료 MIT tiktoken을 선택 의존성으로 사용한다. 이 프로젝트의 준비 환경은 external-tools/stella-work/runtime/token-audit, 캐시는 external-tools/stella-work/runtime/token-cache다. 설치 파일과 캐시를 배포하거나 전역 설정을 바꾸지 않는다. 새 컴퓨터에서는 별도 준비가 필요하다. 자동 설치·API 호출은 없다.

공식 근거:
- https://developers.openai.com/api/docs/guides/token-counting
- https://github.com/openai/tiktoken (MIT)
- https://platform.claude.com/docs/en/build-with-claude/token-counting

텍스트 수치에는 숨은 문맥·도구 포장·이미지·실제 출력·추론·준비 요청·재시도가 없다. 실제 출력 토큰은 화면상 답변 토큰보다 많을 수 있다. 비용 평가는 별도 요금표와 사용량 세부 정보가 필요하며 본 스킬은 비용을 계산하지 않는다.
