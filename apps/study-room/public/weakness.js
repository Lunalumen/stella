'use strict';
(()=>{
 const causes={unknown:'원인 미확인',concept:'개념 부족',memory:'암기 부족',interpretation:'문제 해석',mistake:'계산·코딩 실수'};
 let selectedCourse='all';
 const nav=document.createElement('button');nav.id='nav-weakness';nav.className='nav';nav.textContent='약점 분석';
 $('#nav-info').before(nav);
 nav.onclick=async()=>{if(busy)return;try{if(view==='quiz')await flushSave();await showWeakness();}catch(err){toast(err.message);}};
 async function showWeakness(){
  setView('weakness');$('#app').innerHTML='<div class="loading">제출한 답안의 개념별 기록을 확인하고 있어요…</div>';
  try{
   const query=selectedCourse==='all'?'':'?course='+encodeURIComponent(selectedCourse);
   const [report,review]=await Promise.all([api('/api/weakness'+query),api('/api/review'+query)]);
   const courses=meta.courses.filter(c=>c.id!=='demo');
   $('#app').innerHTML=`<section class="hero"><div><p class="eyebrow">KNOW WHAT TO PRACTICE NEXT</p><h1>틀린 곳에서, 다음 공부를.</h1><p>문법·개념별 오답과 복습 변화를 모아 봅니다.</p></div><button class="secondary" id="weakness-home">문제 만들기</button></section><div class="weakness-toolbar"><label class="field">과목<select id="weakness-course"><option value="all">영어 제외 전체 과목</option>${courses.map(c=>`<option value="${e(c.id)}" ${selectedCourse===c.id?'selected':''}>${e(c.name)}${c.bankCount===0?' · 자료 등록 필요':''}</option>`).join('')}</select></label><span class="pill">단답형 · 5지선다 · 서술형 중심</span></div><div class="notice">${e(report.note)}<br>${e(report.threshold)}</div><div class="weakness-metrics"><div class="card"><strong>${report.groups.length}</strong><span>기록이 있는 개념</span></div><div class="card"><strong>${report.groups.filter(g=>g.label==='반복 오답 관찰').length}</strong><span>반복 오답이 관찰된 개념</span></div><div class="card"><strong>${report.pending['검토 필요']||0}</strong><span>검토 보류 · 약점 판정 제외</span></div></div><div class="weakness-formats">${Object.entries(report.formats).map(([kind,n])=>`<span>${e(kind)} <b>${n}</b>회</span>`).join('')}<small>풀이 횟수에는 재풀이가 포함됩니다.</small></div><div class="weakness-groups">${report.groups.length?report.groups.map((g,i)=>`<article class="card weakness-group"><div class="row"><span class="pill">${e(g.courseName)}</span><span class="result-label ${g.label==='반복 오답 관찰'?'status-incorrect':g.currentWrong?'status-partial':'status-correct'}">${e(g.label)}</span></div><h2>${e(g.tag)}</h2><p class="hint">${e(g.tagOrigin)}</p><div class="weakness-progress"><div><small>첫 풀이 정답</small><b>${g.firstCorrect} / ${g.distinctQuestions}</b></div><span>→</span><div><small>최근 채점 정답</small><b>${g.latestCorrect} / ${g.distinctQuestions}</b></div><div><small>오답 후 정답 관찰</small><b>${g.recovered}문항</b></div></div><p class="reason">${e(g.evidence)}</p><p class="hint">지속된 오답의 실제 원인은 자기평가나 풀이 과정을 확인하기 전까지 미확인입니다.</p>${g.sample.length?`<details class="weakness-samples"><summary>확인할 문항 ${g.currentWrong}개 중 예시</summary>${g.sample.map(s=>`<p>${e(s.prompt)}</p>`).join('')}</details>`:''}<div class="actions"><button class="secondary" data-weak-review="${i}" ${g.reviewable?'':'disabled'}>이 개념 오답 ${Math.min(10,g.reviewable)}개 다시 풀기 →</button></div></article>`).join(''):'<section class="card empty"><h2>아직 판단할 답안이 없어요.</h2><p>문제를 풀고 전체 제출하면 이곳에 기록됩니다.<br>검토가 보류된 서술형을 오답으로 단정하지 않아요.</p></section>'}</div><section class="card weakness-causes"><h2>내가 기록한 오류 원인</h2><p class="hint">채점 결과의 ‘내가 느낀 원인’에서 선택한 자기평가입니다. 자동 진단으로 확정한 원인이 아닙니다.</p>${Object.keys(report.selfCauses).length?`<div class="weakness-formats">${Object.entries(report.selfCauses).map(([cause,n])=>`<span>${e(cause)} <b>${n}</b>회</span>`).join('')}</div>`:'<p class="hint">아직 원인을 기록하지 않았어요.</p>'}</section><div id="weakness-error"></div>`;
   $('#weakness-home').onclick=home;
   const reviewBox=document.createElement('section');reviewBox.className='card spaced-review';
   const dueCourses=[...new Set(review.items.filter(i=>i.dueNow).map(i=>i.course))];
   reviewBox.innerHTML=`<h2>오늘의 오답 복습</h2><p><b>${review.dueCount}문항</b> 복습 예정 · 전체 ${review.scheduledCount}문항 관리 중 · ${e(review.today)} 한국 시간</p><p class="hint">${e(review.note)}</p><div class="actions">${dueCourses.map(id=>{const items=review.items.filter(i=>i.course===id&&i.dueNow);return `<button class="secondary" data-spaced-course="${e(id)}">${e(items[0].courseName)} ${Math.min(10,items.length)}문항 복습 →</button>`;}).join('')||'<span class="hint">지금 복습할 문항은 없어요. 예정일이 되면 여기에 다시 표시돼요.</span>'}</div>${review.items.length?`<details><summary>오답 복습 일정 보기 (${review.items.length})</summary>${review.items.map(i=>`<p><b>${e(new Date(i.due).toLocaleString("ko-KR",{timeZone:"Asia/Seoul"}))} · ${e(i.courseName)}${i.dueNow?' · 복습할 차례':''}</b><br>${e(i.prompt)}<br><small>${i.intervalHours}시간 간격 · ${e(i.dateBasis)}</small></p>`).join('')}</details>`:''}<div id="spaced-error"></div>`;
   $('.weakness-toolbar').after(reviewBox);
   $$('[data-spaced-course]').forEach(button=>button.onclick=async()=>{if(busy)return;busy=true;button.disabled=true;const id=button.dataset.spacedCourse;try{attempt=await api('/api/review/retry',{course:id,count:Math.min(10,review.items.filter(i=>i.course===id&&i.dueNow).length)});index=0;resultFilter='all';quiz();window.scrollTo(0,0);}catch(err){showError(err,$('#spaced-error'),()=>button.click());}finally{busy=false;button.disabled=false;}});
   $('#weakness-course').onchange=()=>{selectedCourse=$('#weakness-course').value;showWeakness();};
   $$('[data-weak-review]').forEach(button=>button.onclick=async()=>{if(busy)return;const g=report.groups[Number(button.dataset.weakReview)];busy=true;button.disabled=true;try{attempt=await api('/api/weakness/retry',{course:g.course,tag:g.tag,count:Math.min(10,g.reviewable)});index=0;resultFilter='all';quiz();window.scrollTo(0,0);}catch(err){showError(err,$('#weakness-error'),()=>button.click());}finally{busy=false;if(view==='weakness')button.disabled=false;}});
  }catch(err){showError(err,$('#app'),showWeakness);}
 }
 function addResultDiagnosis(){
  if(view!=='results'||!attempt?.result)return;
  const aid=attempt.id;
  const rows=attempt.result.rows.filter(r=>resultFilter==='all'||r.status!=='correct');
  $$('.result-card').forEach((card,i)=>{
   const row=rows[i];if(!row||!['mc','short','essay'].includes(row.type)||$('.diagnosis-meta',card))return;
   const box=document.createElement('div');box.className='diagnosis-meta';
   box.innerHTML=`<div class="concept-tags">${(row.conceptTags||['개념 분류 미확인']).map(tag=>`<span>${e(tag)}</span>`).join('')}</div><p class="hint">${e(row.tagOrigin||'분류 미확인')}</p>${row.status!=='correct'?`<label class="cause-editor">내가 느낀 원인 <select aria-label="문제 ${row.number} 오류 원인">${Object.entries(causes).map(([value,label])=>`<option value="${value}" ${row.selfCause===value?'selected':''}>${label}</option>`).join('')}</select><small class="cause-state">자기평가 · 확실하지 않으면 미확인</small></label>`:''}`;
   card.append(box);
   const select=$('select',box);
   if(select)select.onchange=async()=>{select.disabled=true;try{const saved=await api(`/api/attempt/${aid}/cause`,{questionId:row.id,cause:select.value});row.selfCause=saved.cause;$('.cause-state',box).textContent='저장됨 · '+saved.source;}catch(err){select.value=row.selfCause||'unknown';toast(err.message);}finally{select.disabled=false;}};
   if(['short','essay'].includes(row.type)&&row.status!=='unanswered'){
    const review=document.createElement('details');review.className='self-assessment';
    const rubric=row.type==='essay'?row.rubric:[{criterion:'핵심 용어·의미 일치',points:10}];
    review.innerHTML=`<summary>표현이 달라도 의미가 맞나요? 근거를 보고 직접 채점하기</summary><p class="hint">모범 답안과 문장을 똑같이 쓸 필요는 없어요. 핵심 개념·조건·인과관계가 맞고 모순이 없는지 확인하세요. 단순히 키워드가 들어간 것만으로 정답을 주지 마세요. 아래 점수는 자동 의미 판정이 아닌 본인의 자기채점으로 표시됩니다.</p>${rubric.map((r,j)=>`<label class="cause-editor">${e(r.criterion)} <select data-self-score="${j}" aria-label="문제 ${row.number} ${e(r.criterion)} 점수">${(row.type==='short'?[0,10]:Array.from({length:r.points+1},(_,k)=>k)).map(n=>`<option value="${n}" ${n===(row.criteria[j]?.earned||0)?'selected':''}>${n} / ${r.points}점</option>`).join('')}</select></label>`).join('')}<label class="field">인정·감점 근거<textarea class="self-reason" maxlength="1000" placeholder="핵심 개념과 논리가 어떻게 맞는지, 무엇이 빠졌는지 적어주세요."></textarea></label><label><input type="checkbox" class="self-confirm"> 원자료·해설과 비교해 의미·논리·빠진 조건을 확인했어요.</label><p class="hint">자기채점 결과는 점수·오답 복습·약점 기록에 반영됩니다. 원래 자동 채점 결과도 보관합니다.</p><button type="button" class="secondary self-save">자기채점 반영</button><p class="self-error" role="status"></p>`;
    box.append(review);
    $('.self-save',review).onclick=async()=>{if(busy)return;const button=$('.self-save',review);button.disabled=true;busy=true;try{attempt=await api(`/api/attempt/${aid}/self-assess`,{questionId:row.id,scores:$$('[data-self-score]',review).map(s=>Number(s.value)),reason:$('.self-reason',review).value,confirmed:$('.self-confirm',review).checked});results();toast('자기채점 결과를 반영했어요.');}catch(err){$('.self-error',review).textContent=err.message;}finally{busy=false;button.disabled=false;}};
   }
  });
 }
 new MutationObserver(addResultDiagnosis).observe($('#app'),{childList:true,subtree:true});
})();

