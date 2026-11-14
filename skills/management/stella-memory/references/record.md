# 기억 기록 구조

SQLite 단일 파일. 표 5개. 모든 시각은 ISO 8601 UTC(`Z`). `project`·`key`·`actor`는 `^[a-z0-9][a-z0-9._-]{0,63}$`, `text`는 2,000자 이하. SQL 값은 전부 매개변수 바인딩.

## memories — 기억 1건의 안정 ID와 현재 상태
| 필드 | 뜻 |
|---|---|
| memory_id | UUID4. 내용과 무관하므로 같은 문장을 다른 project/key에 저장해도 ID가 다르다 |
| project | `global` 또는 프로젝트 이름 |
| key | 대체 가능한 사실 단위의 주제 키. 생략 시 `unclassified.<id 앞 8자>` |
| key_provisional | 1이면 임시 키. 임시 키끼리는 충돌 후보를 만들지 않는다 |
| kind | preference / constraint / decision / open_question |
| status | active / conflict / superseded / retired |
| created, current_rev | 생성 시각, 현재 개정 번호 |

## revisions — 내용의 개정 이력
| 필드 | 뜻 |
|---|---|
| memory_id, rev | 개정 번호는 1부터 |
| text | 원문. NFC 정규화 + 앞뒤 공백 제거만. 대소문자·내부 공백 보존 |
| content_hash | sha256(정규화 text). 중복 비교 전용, ID 아님 |
| actor | 명령을 실행한 주체 |
| requested_by | 저장을 요청한 주체(기본 user). 파일 import 시 파일 내용이 아니라 명령줄 인자 |
| source_note | 짧은 출처 메모. 채팅 ID·개인 경로 금지 |
| source_verified | 기본 0. 실행자가 발언·파일 원문을 직접 확인했을 때만 1 |
| superseded_by | `<memory_id>:<rev>`. 새 개정 또는 충돌 해소로 대체된 경우 |

## conflicts / conflict_members — 같은 (project, key)의 상충 후보 그룹
status: open → resolved(사용자가 `resolve`) 또는 dissolved(retire/delete로 후보가 1개 이하로 남음). `resolved_memory/rev/by/at`에 선택 이력. 멤버는 (memory_id, rev).

## audit — 작업 메타만
op(add/update/update_rejected/conflict_candidate/resolve/retire/reactivate/delete/export), memory_id, project, key, revs, actor, at. **text·content_hash는 저장하지 않는다.** key는 사용자가 정한 짧은 라벨이라 남긴다(사용자 결정 2026-11-14).

## tombstones — 삭제된 memory_id
삭제된 ID의 재import는 기본 거부, `--allow-resurrect` 명시 시만 허용.

## 상태 전이
```
add ──► active ──(같은 key 다른 내용)──► conflict ──resolve(선택)──► active
                                              └──resolve(비선택)──► superseded
active/conflict ──retire──► retired ──add --reactivate──► active
any ──delete --confirm──► (행 삭제) + tombstone
update: current_rev == expect_rev 일 때만 rev+1, 아니면 stale_revision(변경 없음)
```

## 중복 판정
같은 (project, key)에서 content_hash **와 정규화 문자열이 모두** 같을 때만 동일 내용으로 본다(해시 일치만으로 합치지 않음). active/conflict면 `unchanged`, retired면 `retired_exists`. 다른 project나 key면 새 기억. 지문 일치 = 같은 문자열이지 같은 의미라는 뜻은 아니다.

## 재활성화 (`add --reactivate`)
retired 기억을 active로 되돌릴 때도 새 저장과 같은 충돌 검사를 거친다. 같은 key에 다른 live 기억이 있으면 열린 충돌 그룹에 합류하고 `reactivated_conflict_candidate`를 돌려준다. 재활성화 요청은 다른 후보와의 모순을 자동 해소하라는 뜻이 아니다.

## import 정책
- 적용은 **전체 성공 또는 전체 무변경**(한 트랜잭션). 어느 행이든 실패하면 모두 되돌리고 `rejected_no_changes`.
- 미리보기(`--dry-run` 기본)에서 거부: 필수 필드 누락, project 불일치, 파일 안 `memory_id` 중복, 저장소에 이미 있는 `memory_id`(import는 덮어쓰지 않음, `update` 사용), tombstone에 있는 `memory_id`(`--allow-resurrect` 없을 때).
- `memory_id`는 삭제·유실된 기억을 되돌릴 때만 넣는다. 파일 크기 5 MB 이하.

## 삭제 후 충돌 이력
`delete`는 열린 그룹에서는 멤버를 빼고 후보가 1개 이하면 그룹을 `dissolved`로 닫는다. resolved/dissolved 그룹의 멤버 행은 이력으로 남고, `show --conflict`는 삭제된 멤버를 `status: deleted, deleted_at, text: null`로 설명한다(`resolved_memory_deleted` 플래그 포함). 삭제된 원문은 어디에도 돌려주지 않는다.
