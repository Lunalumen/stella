# Stella

자료 이해·요약·학습·리서치를 위한 AI 스킬 23개를 목적별로 모았습니다.

## 분야별로 찾기

| 분야 | 포함 내용 | 스킬 수 |
|---|---|---:|
| [프로젝트 관리](skills/management/README.md) | 프로젝트 상태 관리와 채팅 간 작업 전달에 사용합니다. | 2 |
| [자료 읽기·재사용](skills/sources/README.md) | 자료를 읽고, 필요한 구간을 찾고, 저장본을 재사용할 때 선택합니다. | 5 |
| [강의 요약](skills/summaries/README.md) | 강의 자료와 필기를 과목과 자료 형태에 맞춰 정리합니다. | 3 |
| [학습·복습](skills/study/README.md) | 실제 문제 풀이, 답안 피드백, 계획과 오답 복습에 사용합니다. | 6 |
| [리서치·보안](skills/research/README.md) | 기업 조사나 보안 검토가 요청됐을 때만 선택합니다. | 2 |

## 폴더 구조

```text
skills/
├─ management/  프로젝트 관리·채팅 전달
├─ sources/     자료 읽기·검색·저장본 재사용
├─ summaries/   강의 요약·대본 정리
├─ study/       문제 풀이·계획·오답 복습
└─ research/    기업 리서치·보안 검토
```

각 스킬 폴더의 SKILL.md가 진입점입니다. 필요한 references/·scripts/·라이선스는 그 스킬과 함께 보관합니다. 오답 복습 도우미는 study/study-spaced-review/references/study-engine/에 있습니다.

## 사용 기준

- 목적에 맞는 스킬부터 읽고 필요한 보조 자료만 확인합니다.
- 저장소 안에서 참조할 때는 이 폴더 구조를 유지합니다. 다른 위치에 개별 설치할 때는 공통 스킬 의존성과 상대 경로를 함께 조정해야 합니다.
- 이번 정리는 GitHub 보관 구조 변경입니다. 로컬 설치나 선택형 외부 서비스 연결을 수행하지 않습니다.
- 개인 문서·공부 기록·계정 정보·캐시·로그는 포함하지 않습니다. 실제 토큰 절감률은 측정 전까지 미확인입니다.

## 출처와 라이선스

Lunalumen/-의 커밋 2b524f08161c16c399d58742c361301110fec0c3에서 가져온 스킬을 분야별로 재배치했습니다. 외부 유래 스킬의 라이선스와 [upstream-lock.json](upstream-lock.json)을 보존합니다. upstream-SKILL.md는 원본 기록이며 실행 진입점이 아닙니다. 기존 원본 저장소는 수정하지 않습니다.

## Stella 자료 검색·프롬프트 정리

[자료 읽기·재사용](skills/sources/README.md)에 Stella 전용 스킬 3개를 추가했습니다. 중복을 줄이면서 목표·조건·숫자·출처를 보존합니다. 외부 런타임은 미설치·미검증이며 실제 토큰 절감률은 미측정입니다.

짧은 프롬프트 작성: [stella-concise-prompt](skills/sources/stella-concise-prompt/SKILL.md).
