'use strict';
const $=s=>document.querySelector(s), storageKey='myeongwol-materials-v1';
let groups=[], result=null, documentMeta=null, state={};
try{state=JSON.parse(localStorage.getItem(storageKey)||'{}')||{};}catch{}
const save=()=>{try{localStorage.setItem(storageKey,JSON.stringify(state));}catch{}};
async function api(path,body){const r=await fetch('/api/materials/'+path,body?{method:'POST',headers:{'Content-Type':'application/json','X-Myeongwol':'study'},body:JSON.stringify(body)}:{});const data=await r.json();if(!r.ok)throw Error(data.error||'요청을 처리하지 못했습니다.');return data;}
const option=(value,label)=>{const o=document.createElement('option');o.value=value;o.textContent=label;return o;};
function remember(){for(const id of ['exam','course','group','question','budget','required'])state[id]=$('#'+id).value;save();}
function groupOptions(){const list=groups.filter(g=>g.course===$('#course').value);$('#group').replaceChildren(...list.map(g=>option(g.id,g.scope+' · '+g.title)));if(list.some(g=>g.id===state.group))$('#group').value=state.group;$('#search').disabled=!list.length;$('#group').disabled=!list.length;$('#source-status').textContent=list.length?'선택한 시험에 등록된 로컬 저장본만 검색합니다. 원격 최신 상태는 미확인입니다.':'이 시험·과목의 등록 자료가 없습니다. 다른 시험 자료는 포함하지 않습니다.';}
async function catalog(){try{const d=await api('catalog?exam='+encodeURIComponent($('#exam').value));groups=d.groups;$('#course').replaceChildren(...Object.entries(d.courses).map(([id,name])=>option(id,name)));if(d.courses[state.course])$('#course').value=state.course;groupOptions();}catch(e){$('#error').textContent=e.message;$('#search').disabled=true;}}
for(const id of ['exam','question','budget','required'])if(state[id])$('#'+id).value=state[id];
$('#exam').onchange=()=>{remember();$('#result').hidden=true;catalog();};
$('#course').onchange=()=>{groupOptions();remember();$('#result').hidden=true;};
for(const id of ['group','question','budget','required'])$('#'+id).addEventListener('input',()=>{remember();$('#result').hidden=true;});
function reviewKey(){return $('#exam').value+'|'+$('#group').value+'|'+$('#question').value;}
function saveReview(){state.reviews=state.reviews||{};state.reviews[reviewKey()]={note:$('#review-note').value,...Object.fromEntries([...document.querySelectorAll('[data-review]')].map(c=>[c.dataset.review,c.checked]))};save();}
for(const c of document.querySelectorAll('[data-review]'))c.onchange=saveReview;
$('#review-note').oninput=saveReview;
function evidence(hit){const card=document.createElement('article');card.className='card evidence-card';const h=document.createElement('h3');h.textContent=hit.title+' · '+hit.location;const p=document.createElement('pre');p.textContent=hit.text;const note=document.createElement('p');note.className='hint';note.textContent=hit.truncated?'일부 발췌입니다. 앞뒤 문맥을 확인하세요.':'등록된 텍스트 저장본입니다. 원본 그림 확인은 별도입니다.';const button=document.createElement('button');button.className='secondary';button.textContent='이 구간 본문 더 읽기';let offset=Math.max(0,hit.offset-300);button.onclick=async()=>{button.disabled=true;try{const d=await api('read',{id:hit.id,exam:result.exam,offset});p.textContent=d.text;note.textContent=d.location+' · '+d.offset+'~'+(d.offset+d.text.length)+' / '+d.totalChars+'자';offset=d.nextOffset;button.textContent=offset===null?'끝까지 확인함':'다음 구간 읽기';button.disabled=offset===null;}catch(e){note.textContent=e.message;button.disabled=false;}};card.append(h,p,note,button);return card;}
function render(d){result=d;$('#result').hidden=false;$('#cache-status').textContent=['reused','unchanged'].includes(d.cache)?'저장본 재사용':'저장본 갱신';const t=d.tokens;$('#before').textContent=t.available?t.before.toLocaleString():'미측정';$('#after').textContent=t.available?t.after.toLocaleString():'미측정';$('#delta-label').textContent=t.saved<0?'증가':'감소';$('#delta').textContent=t.available?Math.abs(t.saved).toLocaleString():'미측정';$('#percent').textContent=t.available?Math.abs(t.reduction_percent).toFixed(1)+'%':'';const max=Math.max(t.before||0,t.after||0,1);$('#before-bar').style.width=(t.before||0)/max*100+'%';$('#after-bar').style.width=(t.after||0)/max*100+'%';$('#metric-note').textContent=t.available?'o200k_base로 위 두 근거 텍스트만 계산했습니다. 실제 대화 전체 사용량·요금 절감률은 미측정입니다. 이 검색의 AI API 호출은 0회입니다.':t.scope+' · 전체 '+t.beforeChars+'자 / 발췌 '+t.afterChars+'자. 실제 대화 사용량은 미측정입니다.';if(!d.hits.length){$('#delta-label').textContent='근거 없음';$('#delta').textContent='—';$('#percent').textContent='절감 평가 보류';}$('#fact-status').textContent=t.missing.length?'발췌에서 빠진 필수 표현: '+t.missing.join(', ')+(t.baselineMissing.length?' (원본에도 없는 표현: '+t.baselineMissing.join(', ')+')':''):'필수 표현 '+$('#required').value.split('\n').filter(v=>v.trim()).length+'개 문자열 검사. 의미·조건·예외의 정확성은 직접 검토하세요.';$('#evidence').replaceChildren(...d.hits.map(evidence));if(!d.hits.length)$('#evidence').textContent='일치하는 근거가 없습니다. 핵심어를 바꿔 주세요. 0토큰 발췌를 유효한 절감 성과로 판단하지 않습니다.';$('#copy-prompt').disabled=!d.prompt;const review=(state.reviews||{})[reviewKey()]||{};for(const c of document.querySelectorAll('[data-review]'))c.checked=Boolean(review[c.dataset.review]);$('#review-note').value=review.note||'';}
$('#search-form').onsubmit=async e=>{e.preventDefault();remember();$('#error').textContent='';$('#search').disabled=true;$('#busy').textContent='저장본 검색·토큰 계산 중…';try{render(await api('search',{exam:state.exam,group:state.group,question:state.question,budget:Number(state.budget),required:state.required.split('\n').map(v=>v.trim()).filter(Boolean)}));}catch(e){$('#error').textContent=e.message;}finally{$('#search').disabled=!$('#group').value;$('#busy').textContent='';}};
$('#copy-prompt').onclick=async()=>{try{await navigator.clipboard.writeText(result.prompt);$('#copy-prompt').textContent='복사했습니다';}catch{$('#error').textContent='클립보드 권한을 확인해 주세요.';}};
let checkedCapabilities=false;
$('#document-tools').ontoggle=async()=>{if(!$('#document-tools').open||checkedCapabilities)return;checkedCapabilities=true;const d=await api('capabilities').catch(()=>({available:false,languages:[]}));$('#ocr-capabilities').textContent=d.available?'이 PC의 OCR 언어: '+d.languages.join(', ')+' · 로컬 처리, 별도 AI API 없음':'이 PC에서 Windows OCR을 실행할 수 없습니다.';$('#ocr').disabled=!d.available;for(const o of $('#ocr-language').options)o.disabled=!d.languages.some(l=>o.value.toLowerCase().startsWith(l.toLowerCase()));};
async function showPage(){if(!documentMeta)return;const page=Number($('#page').value);$('#page-tables').replaceChildren();$('#table-status').textContent='';$('#extract-tables').disabled=documentMeta.extension!=='.pdf';$('#visual-review').checked=false;$('#ocr-status').textContent='페이지 확인 중…';try{const d=await api('text',{id:documentMeta.id,page});$('#page-image').src='/api/materials/page?id='+documentMeta.id+'&page='+page;$('#page-text').textContent=d.text||'추출 가능한 텍스트가 없습니다. 이 페이지에 OCR을 실행할 수 있습니다.';$('#ocr-status').textContent=d.truncated?'추출 결과가 12,000자로 제한되었습니다.':'텍스트 추출 완료 · 원본 대조는 미확인';state.document={...documentMeta,page};save();}catch(e){$('#ocr-status').textContent=e.message;}}
$('#show-page').onclick=showPage;
$('#page').oninput=()=>{$('#page-tables').replaceChildren();$('#table-status').textContent='';};
$('#upload').onclick=async()=>{const file=$('#local-file').files[0];if(!file)return;$('#upload').disabled=true;try{if(file.size>6*1024*1024)throw Error('6MB 이하 파일을 선택해 주세요.');const content=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(file);});documentMeta=await api('upload',{name:file.name,content});$('#document-status').textContent=documentMeta.name+' · '+documentMeta.pages+'쪽 · '+documentMeta.registration;$('#page-tools').hidden=false;$('#page').max=documentMeta.pages;$('#page').value=1;await showPage();}catch(e){$('#document-status').textContent=e.message;}finally{$('#upload').disabled=false;}};
$('#ocr').onclick=async()=>{if(!documentMeta)return;$('#ocr').disabled=true;$('#ocr-status').textContent='이 페이지를 로컬 OCR로 인식 중…';try{const d=await api('ocr',{id:documentMeta.id,page:Number($('#page').value),language:$('#ocr-language').value});$('#page-text').textContent=d.text;$('#ocr-status').textContent=d.warning+' · '+(d.cache==='reused'?'인식 결과 재사용':'새로 인식');}catch(e){$('#ocr-status').textContent=e.message;}finally{$('#ocr').disabled=false;}};
if(state.document){documentMeta=state.document;$('#page-tools').hidden=false;$('#page').max=documentMeta.pages;$('#page').value=documentMeta.page||1;$('#document-status').textContent=documentMeta.name+' · 이전 선택 복원 (임시 검토함)';}
catalog();

$('#extract-tables').disabled=!documentMeta||documentMeta.extension!=='.pdf';
$('#extract-tables').onclick=async()=>{
  if(!documentMeta)return;
  const id=documentMeta.id,page=Number($('#page').value);
  $('#extract-tables').disabled=true;$('#table-status').textContent='이 페이지만 로컬에서 표 추출 중…';$('#page-tables').replaceChildren();
  try{
    const d=await api('tables',{id,page});
    if(documentMeta.id!==id||Number($('#page').value)!==page)return;
    $('#table-status').textContent=(d.tables.length?d.tables.length+'개 표 표시':'추출된 표 없음')+' · '+(d.cache==='reused'?'결과 재사용':'새로 추출')+(d.truncated?' · 표시 분량 제한':'')+' · '+d.warning;
    for(const [i,item] of d.tables.entries()){
      const box=document.createElement('div');box.className='table-scroll';
      const table=document.createElement('table'),caption=document.createElement('caption');caption.textContent=page+'쪽 · 표 '+(i+1)+' · 기계 추출, 원본 대조 미확인';table.append(caption);
      const body=document.createElement('tbody');
      for(const row of item.rows){const tr=document.createElement('tr');for(const cell of row){const td=document.createElement('td');td.textContent=cell;tr.append(td);}body.append(tr);}
      table.append(body);box.append(table);$('#page-tables').append(box);
    }
  }catch(e){if(documentMeta.id===id&&Number($('#page').value)===page)$('#table-status').textContent=e.message;}
  finally{$('#extract-tables').disabled=!documentMeta||documentMeta.extension!=='.pdf';}
};
