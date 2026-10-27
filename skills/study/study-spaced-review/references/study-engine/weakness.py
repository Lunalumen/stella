"""Evidence-bound local diagnosis. No model calls; no causal inference from one error."""
import copy
import hashlib
import json
import re
from collections import Counter

CAUSES={'unknown':'원인 미확인','concept':'개념 부족','memory':'암기 부족','interpretation':'문제 해석','mistake':'계산·코딩 실수'}
TARGET_TYPES={'mc','short','essay','coding'}
ASSESSED={'correct','incorrect','partial'}

RULES={
 'java':[
  (r'형변환|캐스팅|\(int\)','형변환'),
  (r'배열|\.length\b|new\s+\w+\s*\[','배열과 인덱스'),
  (r'증감|\+\+|--','증감 연산자'),
  (r'\bfor\b|\bwhile\b|반복|\bbreak\b|\bcontinue\b','반복문과 종료 조건'),
  (r'논리|&&|\|\|','논리 연산'),
  (r'\bif\b|\bswitch\b|조건문|삼항','조건 분기'),
  (r'상속|\bextends\b|오버라이','상속과 재정의'),
  (r'생성자|\bnew\b|객체|클래스|\bthis\b','클래스와 객체'),
  (r'메서드|\breturn\b|매개변수|인자|\bvoid\b','메서드와 반환'),
  (r'문자열|\bString\b|println|\bprint\b','출력과 문자열'),
  (r'자료형|변수|\bbyte\b|\bdouble\b|\bboolean\b','변수와 자료형'),
 ],
 'algorithms':[
  (r'복잡도|빅오|\bO\s*\(|점근','복잡도 분석'),
  (r'재귀|호출|종료 조건','재귀와 종료 조건'),
  (r'정렬|sort','정렬'),
  (r'탐색|search','탐색'),
  (r'그리디|탐욕|최적','탐욕 선택과 최적성'),
  (r'분할|병합|merge','분할 정복'),
 ],
 'windows':[
  (r'OnTimer|SetTimer|타이머','타이머와 메시지 처리'),
  (r'OnDraw|Invalidate|그리기','그리기와 화면 갱신'),
  (r'CString|문자열|Format','문자열과 출력 형식'),
  (r'메시지|핸들러|이벤트','메시지와 이벤트'),
 ],
 'chemistry':[
  (r'결합|전자|원자','원자·전자·결합'),
  (r'물 분자|극성|수소 결합','물의 구조와 성질'),
  (r'단백질|아미노산|효소','단백질과 효소'),
  (r'산성|염기|양성자|pH','산·염기와 조건'),
 ],
 'aesthetics':[
  (r'플라톤|이데아|모방','플라톤·모방·지식'),
  (r'아리스토텔레스|보편|카타르','아리스토텔레스의 예술관'),
  (r'고대 그리스|칼론|테크네|심메트리아|하르모니아','고대 그리스의 미·예술 용어'),
 ],
 'history20':[
  (r'계급|노동|마르크스','계급과 사회주의'),
  (r'감시|규율|인식 체계','감시·규율·이데올로기'),
  (r'민족|제국|식민','민족주의와 제국주의'),
  (r'전쟁|슐리펜|참호|병력','세계대전의 원인과 전개'),
  (r'러시아|차르|레닌|소비에트','러시아 혁명의 흐름'),
 ]
}

def concept_key(q,course):
    identity=[course,q.get('topic') or ' '.join(q.get('prompt','').split()),sorted(q.get('source_ids',[]))]
    return hashlib.sha256(json.dumps(identity,ensure_ascii=False).encode()).hexdigest()[:24]

def tags_for(q,course,scopes=()):
    if q.get('conceptTags'):
        return list(q['conceptTags']),q.get('tagOrigin','문항 등록 기준')
    matches=[tag for pattern,tag in RULES.get(course,[]) if re.search(pattern,q.get('prompt',''),re.I)]
    if matches:
        return list(dict.fromkeys(matches))[:2],'지문 기준 자동 분류 · 확인 필요'
    scope=q.get('scope') or (scopes[0] if len(scopes)==1 else None)
    topic=q.get('topic','')
    if scope:
        return [scope],'등록 범위 기준'
    if topic and not re.fullmatch(r'[a-z]+[-_]?\d+',topic,re.I):
        return [topic],'등록 주제 기준'
    return ['개념 분류 미확인'],'분류 미확인'

def annotate(q,course,scopes=()):
    tags,origin=tags_for(q,course,scopes)
    q['conceptTags']=tags
    q['tagOrigin']=origin
    q['conceptKey']=concept_key(q,course)
    return q

def build_report(records,courses,course_filter=None):
    groups={}
    courses_seen=Counter()
    pending=Counter()
    causes=Counter()
    formats=Counter()
    examples={}
    # Ascending time makes first attempt and latest graded attempt explicit.
    for record in sorted(records,key=lambda r:(r['created'],r['id'])):
        course=record['course']
        if course not in courses or course=='demo' or (course_filter and course!=course_filter):
            continue
        payload=json.loads(record['payload'])
        result=json.loads(record['result']) if record['result'] else {}
        questions={q['id']:q for q in payload['questions']}
        for row in result.get('rows',[]):
            q=questions.get(row['id'])
            if not q or q['type'] not in TARGET_TYPES:
                continue
            courses_seen[course]+=1
            fmt='5지선다' if q['type']=='mc' and len(q.get('options',[]))==5 else '4지선다' if q['type']=='mc' else '단답형' if q['type']=='short' else '서술형'
            formats[fmt]+=1
            status=row['status']
            cause=row.get('selfCause','unknown')
            if cause!='unknown' and cause in CAUSES:
                causes[CAUSES[cause]]+=1
            if row.get('needsReview') or status not in ASSESSED:
                pending['검토 필요' if row.get('needsReview') or status=='review' else '미응답']+=1
                continue
            tags,origin=tags_for(q,course,payload.get('scopes',[]))
            key=concept_key(q,course)
            for tag in tags:
                identity=(course,tag)
                group=groups.setdefault(identity,{'course':course,'courseName':courses[course]['name'],'tag':tag,'tagOrigin':origin,'items':{},'events':0,'wrongEvents':0})
                item=group['items'].setdefault(key,{'first':status,'latest':status,'everWrong':False,'latestQuestion':q,'latestPayload':payload,'latestAttempt':record['id']})
                item.update(latest=status,latestQuestion=q,latestPayload=payload,latestAttempt=record['id'])
                item['everWrong']=item['everWrong'] or status in ('incorrect','partial')
                group['events']+=1
                group['wrongEvents']+=int(status in ('incorrect','partial'))
    output=[]
    for group in groups.values():
        items=list(group.pop('items').values())
        n=len(items)
        first_correct=sum(i['first']=='correct' for i in items)
        latest_correct=sum(i['latest']=='correct' for i in items)
        wrong=[i for i in items if i['latest'] in ('incorrect','partial')]
        recovered=sum(i['everWrong'] and i['latest']=='correct' for i in items)
        label='반복 오답 관찰' if n>=3 and len(wrong)>=2 else '추가 진단 필요' if wrong else '복습 후 정답 관찰' if recovered else '현재 정답 관찰'
        output.append({**group,'distinctQuestions':n,'firstCorrect':first_correct,'latestCorrect':latest_correct,'firstAccuracy':round(first_correct/n*100),'latestAccuracy':round(latest_correct/n*100),'currentWrong':len(wrong),'recovered':recovered,'label':label,'evidence':f'서로 다른 {n}문항 · 현재 오답/부분 정답 {len(wrong)}문항 · 재풀이 포함 오답 {group["wrongEvents"]}회','reviewable':len(wrong),'sample':[{'prompt':i['latestQuestion']['prompt'],'status':i['latest'],'attemptId':i['latestAttempt']} for i in wrong[:3]]})
    output.sort(key=lambda g:(g['label']!='반복 오답 관찰',-g['currentWrong'],g['courseName'],g['tag']))
    return {'groups':output,'pending':dict(pending),'selfCauses':dict(causes),'formats':dict(formats),'courseEvents':dict(courses_seen),'note':'같은 문항의 재풀이는 새로운 독립 문항으로 세지 않습니다. 검토 필요 서술형·미응답·OX는 약점 판단에서 제외합니다. 자동 개념 분류와 오류 원인 확정은 다릅니다. 4지선다는 기존 시험 기준을 보존해 별도 표시합니다.','threshold':'서로 다른 채점 문항 3개 이상 중 현재 오답/부분 정답 2개 이상이면 반복 오답 관찰로 표시합니다. 정답 관찰을 완전 숙달로 단정하지 않습니다.'}

def review_questions(records,course,tag):
    latest={}
    for record in sorted(records,key=lambda r:(r['created'],r['id'])):
        if record['course']!=course:
            continue
        payload=json.loads(record['payload'])
        result=json.loads(record['result']) if record['result'] else {}
        qs={q['id']:q for q in payload['questions']}
        for row in result.get('rows',[]):
            q=qs.get(row['id'])
            if not q or q['type'] not in TARGET_TYPES or row.get('needsReview') or row['status'] not in ASSESSED:
                continue
            tags,_=tags_for(q,course,payload.get('scopes',[]))
            if tag in tags:
                latest[concept_key(q,course)]=(q,payload,row['status'])
    return [(copy.deepcopy(q),copy.deepcopy(p)) for q,p,status in latest.values() if status in ('incorrect','partial')]
