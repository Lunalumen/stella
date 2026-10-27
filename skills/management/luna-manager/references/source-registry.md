# 로컬 원자료 변경 확인

자료 버전이 의심되거나 기존 요약을 재사용할 때만 `scripts/source_registry.py`를 실행한다. Python 표준 라이브러리만 사용하며 지정 파일의 SHA-256을 계산한다. 내용을 채팅에 읽어 들이거나 외부로 보내지 않는다. PDF 본문 읽기·OCR·코드 실행·학습 완료 검증 기능이 아니다.

## 사용

처음 등록할 파일의 절대 경로를 JSON 문자열 배열로 로컬 `paths.json`에 둔다. 사용자가 지정한 자료만 포함하며 폴더 전체를 자동 등록하지 않는다.

```text
python scripts/source_registry.py register --registry <local-registry.json> --project <subject> --paths-json <paths.json>
python scripts/source_registry.py check --registry <local-registry.json> --project <subject>
```

- 등록은 대표 원본 파일의 바이트 기준선을 저장한다. 이미 등록한 프로젝트은 기본으로 덮어쓰지 않는다.
- 확인은 해당 프로젝트만 읽고 변경·누락·오류·동일 바이트 파일을 출력한다. 기준선은 변경하지 않는다. 종료 코드 0은 변화 없음, 1은 변경·누락·확인 오류, 2는 실행/입력 오류다.
- 변화 없음은 같은 파일 바이트라는 뜻일 뿐, 내용이 정확하거나 이전 요약이 충분하다는 뜻은 아니다. 미독 구간은 계속 미독이다.
- 변경되면 영향받은 요약·코드·문항의 출처 구간을 실제로 확인하고 기록한다. 그 뒤 명시적으로 `register ... --refresh`하여 기준선을 갱신한다. 변경 탐지 직후 자동 갱신하지 않는다.
- 중복은 삭제 제안의 근거가 아니라 대표본을 선택할 참고 정보다. 파일을 자동 삭제하지 않는다.
- 원격 Google 문서는 이 도구에 포함하지 않는다. 수정 시각·대상 탭·결과 텍스트를 기존 커넥터로 확인한다.
- `paths.json`과 실제 자료 경로·해시가 들어간 레지스트리는 개인 상태다. 공용 GitHub 스킬에는 스크립트와 사용법만 저장한다.
- 단일 관리자가 갱신한다. 여러 채팅이 동시에 쓸 때는 수정 담당을 하나로 정하고 최신 기준을 확인한다.

## 참고한 설계

- OpenAI 공식 스킬 카탈로그: https://github.com/openai/skills
- 반복 작업은 스크립트로 분리하고 상세 참고는 필요할 때 읽는 방식: https://developers.openai.com/blog/skills-agents-sdk

이 스크립트는 루나의 파일 관리에 맞춰 새로 작성했다. 외부 스킬 코드를 복사하거나 설치한 것은 아니다.
