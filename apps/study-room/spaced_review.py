"""Exam-period error review: two hours from the latest assessed submission."""
import copy
import json
from datetime import datetime, timedelta, timezone
import weakness

KST=timezone(timedelta(hours=9))
INTERVAL_HOURS=2
COMPLETED_COURSES={'history20','java','algorithms','windows','aesthetics','chemistry'}

def schedule(records,courses,course_filter=None,now=None):
    current=(now or datetime.now(KST)).astimezone(KST)
    items={}
    for record in sorted(records,key=lambda r:((json.loads(r['result']) if r['result'] else {}).get('submittedAt') or r['created'],r['id'])):
        course=record['course']
        if course not in courses or course in ('demo','english','china') or (course_filter and course!=course_filter):
            continue
        payload=json.loads(record['payload'])
        if course in COMPLETED_COURSES and payload.get('exam')=='중간고사':
            continue
        result=json.loads(record['result']) if record['result'] else {}
        qs={q['id']:q for q in payload['questions']}
        stamp=result.get('submittedAt') or record['created']
        try:
            submitted=datetime.fromisoformat(stamp.replace('Z','+00:00'))
            if submitted.tzinfo is None:
                submitted=submitted.replace(tzinfo=timezone.utc)
            submitted=submitted.astimezone(KST)
        except (ValueError,TypeError):
            continue
        for row in result.get('rows',[]):
            q=qs.get(row['id'])
            if not q or q['type'] not in weakness.TARGET_TYPES or row.get('needsReview') or row['status'] not in weakness.ASSESSED:
                continue
            key=weakness.concept_key(q,course)
            if row['status']=='correct' and key not in items:
                continue
            items[key]={'key':key,'course':course,'question':copy.deepcopy(q),'payload':copy.deepcopy(payload),
                        'due':submitted+timedelta(hours=INTERVAL_HOURS),'fallback':not bool(result.get('submittedAt'))}
    return sorted(items.values(),key=lambda i:(i['due'],i['course'],i['key'])),current

def report(records,courses,course_filter=None,now=None):
    items,current=schedule(records,courses,course_filter,now)
    return {'dueCount':sum(i['due']<=current for i in items),'scheduledCount':len(items),'today':current.date().isoformat(),'asOf':current.isoformat(),
            'items':[{'key':i['key'],'course':i['course'],'courseName':courses[i['course']]['name'],
                      'prompt':i['question']['prompt'],'due':i['due'].isoformat(),'dueNow':i['due']<=current,
                      'intervalHours':INTERVAL_HOURS,'dateBasis':'기존 기록의 시험 생성 시각 기준' if i['fallback'] else '제출 시각 기준'} for i in items],
            'note':'중간고사는 전체 완료로 예정 복습에서 제외하고 기록은 보관합니다. 기말 문항은 이전 오답의 마지막 채점 제출 시각부터 2시간 뒤 복습합니다. 한국 시간 기준. 검토 보류·미응답·OX 제외. 자동 알림 없이 이 화면을 열거나 새로고침할 때 확인합니다.'}
