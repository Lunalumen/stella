'use strict';
const $=s=>document.querySelector(s);
const members=[
 {name:'루미',role:'자료 수집',color:'#c2ed99',symbol:'↗',home:[24,43],note:'공식 공시와 기업 IR을 먼저 확인해요. 같은 자료는 팀에 한 번만 전달해요.'},
 {name:'노아',role:'기업 분석',color:'#9cc7e2',symbol:'⌁',home:[76,43],note:'사업과 숫자를 연결해요. 회계상 이익과 실제 현금흐름을 구분해요.'},
 {name:'이브',role:'반론 검토',color:'#edb382',symbol:'◇',home:[24,87],note:'국가의 금리·환율·경기와 기업의 위험, 반대 근거를 확인해요.'},
 {name:'모아',role:'결과 정리',color:'#c8afe4',symbol:'≡',home:[76,87],note:'상승과 하락 조건을 근거와 함께 정리해요.'},
 {name:'다온',role:'뉴스·경쟁사',color:'#f1bb8d',symbol:'▤',home:[12,43],note:'뉴스와 경쟁사 자료를 살펴보고 출처를 공유해요.'},
 {name:'하린',role:'시세·가치',color:'#a7c9e6',symbol:'◈',home:[88,43],note:'주가 움직임과 가치평가를 살펴봐요.'},
 {name:'지안',role:'애널리스트',color:'#e4b6c7',symbol:'✦',home:[50,48],note:'자료에 근거한 의견과 판단을 바꿀 조건을 정리해요.'},
 {name:'세온',role:'시장·정책 조사',color:'#e6c58e',symbol:'◎',home:[10,66],note:'금리·정책·경제와 사회 변화를 살피고 관련 기업에 미칠 경로와 출처를 함께 전달해요.'}
];
const stages=[
 {name:'자료 회의',pair:[7,0,4,1,6],station:0,duration:11000,speech:['시장과 정책 상황을 살펴볼게요','기업 공시도 함께 확인해요'],event:'세온이 시장과 정책 자료를 팀원들과 나눠요.',state:'자료 회의 중'},
 {name:'분석 회의',pair:[1,5,6,0,4],station:1,duration:11000,speech:['기업의 이익을 살펴봤어요','가격과 가치를 함께 볼게요'],event:'다섯 명이 기업 분석과 가치평가를 함께 살펴봐요.',state:'분석 회의 중'},
 {name:'의견 검토 회의',pair:[7,2,6,1,5],station:2,duration:11000,speech:['정책이 기업에 미칠 영향을 살펴요','반대 근거와 시행 여부도 확인할게요'],event:'애널리스트와 팀원들이 의견과 반대 근거를 함께 검토해요.',state:'의견 검토 중'},
 {name:'보고서 회의',pair:[2,3,6,1,4],station:3,duration:11000,speech:['빠진 위험은 없는지 확인했어요','상승과 하락 조건을 정리할게요'],event:'팀원들이 위험과 상승·하락 조건을 함께 정리해요.',state:'보고서 회의 중'}
];
const total=stages.reduce((s,x)=>s+x.duration,0);
let running=false,paused=false,speed=1,elapsed=0,last=0,currentStage=-1,selected=0,question='',events=0;
members.forEach((m,i)=>{
 const a=document.createElement('button');a.className='agent';a.style.setProperty('--color',m.color);a.setAttribute('aria-label',`${m.name} · ${m.role} 상세 보기`);
 a.innerHTML='<span class="speech" hidden></span><span class="avatar"><span class="hair"></span><span class="head"></span><span class="body"></span><span class="legs"></span></span><span class="agent-name"></span>';
 a.querySelector('.agent-name').textContent=`${m.name} · ${m.role}`;a.onclick=()=>select(i);$('#agents').append(a);m.el=a;
 const row=document.createElement('button');row.className='team-row';row.style.setProperty('--color',m.color);row.innerHTML='<span class="portrait"></span><span class="who"><b></b><small></small></span><span class="team-state">대기</span>';
 row.querySelector('.portrait').textContent=m.symbol;row.querySelector('b').textContent=m.name;row.querySelector('small').textContent=m.role;row.onclick=()=>select(i);$('#team').append(row);m.row=row;position(i,m.home);
});
function position(i,p){members[i].el.style.left=p[0]+'%';members[i].el.style.top=p[1]+'%';}
function select(i){selected=i;members.forEach((m,j)=>{m.el.classList.toggle('selected',j===i);m.row.classList.toggle('selected',j===i)});const m=members[i];$('#agent-detail p').textContent=`${m.name} · ${m.note}`;}
function addEvent(text,color){const e=document.createElement('div');e.className='event';e.style.setProperty('--color',color||'#c2ed99');const content=document.createElement('span');content.textContent=text;const time=document.createElement('small');time.textContent=`DEMO · ${format(elapsed)}`;e.append(content,time);$('#feed').append(e);$('#feed').scrollTop=$('#feed').scrollHeight;$('#event-count').textContent=++events+' EVENTS';}
function format(ms){const s=Math.floor(ms/1000);return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function enter(index){const stage=stages[index];currentStage=index;members.forEach((m,i)=>{m.el.classList.remove('walking','meeting-left','meeting-right');m.el.querySelector('.speech').hidden=true;const active=stage.pair.includes(i);if(active&&stage.pair.indexOf(i)<2)m.el.classList.add(stage.pair[0]===i?'meeting-left':'meeting-right');m.row.classList.toggle('busy',active);m.row.querySelector('.team-state').textContent=active?stage.state:'대기';});document.querySelectorAll('.station').forEach((el,i)=>el.classList.toggle('active',i===stage.station));$('#station-'+stage.station).textContent=stage.state;select(stage.pair[0]);addEvent(stage.event,members[stage.pair[0]].color);$('#scene-status').textContent=stage.pair.map(i=>members[i].name).join(' · ')+' / '+stage.state;$('#phase-label').textContent=stage.name;$('#active-route').style.opacity=0;$('#handoff').hidden=true;}
function pointOn(path,t){const lengths=path.slice(1).map((p,i)=>Math.hypot(p[0]-path[i][0],p[1]-path[i][1]));const length=lengths.reduce((s,x)=>s+x,0);if(!length)return path[0];let remaining=t*length;for(let i=0;i<lengths.length;i++){if(remaining<=lengths[i]||i===lengths.length-1){const u=lengths[i]?Math.min(1,remaining/lengths[i]):1;return[path[i][0]+(path[i+1][0]-path[i][0])*u,path[i][1]+(path[i+1][1]-path[i][1])*u]}remaining-=lengths[i]}return path.at(-1);}
function draw(){let start=0,index=0;while(index<stages.length-1&&elapsed>=start+stages[index].duration){start+=stages[index].duration;index++;}if(index!==currentStage)enter(index);const stage=stages[index],t=Math.min(1,(elapsed-start)/stage.duration);stage.pair.forEach((memberId,j)=>{const m=members[memberId],destination=[[27,58],[38,67],[50,70],[62,67],[73,58]][j];let fraction=t<.35?t/.35:t<.65?1:Math.max(0,(1-t)/.35);position(memberId,[m.home[0]+(destination[0]-m.home[0])*fraction,m.home[1]+(destination[1]-m.home[1])*fraction]);m.el.classList.toggle('walking',!paused&&(t<.35||t>=.65));const speech=m.el.querySelector('.speech');speech.textContent=stage.speech[j]||'';speech.hidden=!(j<2&&t>=.35&&t<.65);});$('#progress').style.width=(elapsed/total*100)+'%';$('#elapsed').textContent=format(elapsed);const completed=elapsed>=total?4:index;$('#progress-label').textContent=completed+' / 4';document.querySelectorAll('.steps span').forEach((e,i)=>e.classList.toggle('done',i<completed));}
function finish(){running=false;draw();members.forEach((m,i)=>{position(i,m.home);m.el.classList.remove('walking');m.el.querySelector('.speech').hidden=true;m.row.classList.remove('busy');m.row.querySelector('.team-state').textContent='완료';});document.querySelectorAll('.station').forEach((el,i)=>{el.classList.remove('active');$('#station-'+i).textContent='완료'});$('#handoff').hidden=true;$('#active-route').style.opacity=0;$('#scene-status').textContent='데모 완료 / 예시 보고서를 확인하세요';$('#phase-label').textContent='작업 흐름 완료';$('#open-report').disabled=false;$('#open-report').textContent='예시 보고서 보기 ↗';$('#start').textContent='다시 실행 ↗';$('#pause').disabled=true;addEvent('팀의 작업 흐름이 완료됐어요. 실제 기업 분석은 수행하지 않았어요.');}
function clear(){running=false;paused=false;elapsed=0;currentStage=-1;events=0;$('#feed').replaceChildren();$('#event-count').textContent='0 EVENTS';$('#office').classList.remove('paused');$('#pause').textContent='Ⅱ 일시정지';$('#pause').disabled=true;$('#progress').style.width='0%';$('#progress-label').textContent='0 / 4';$('#phase-label').textContent='작업 준비';$('#elapsed').textContent='00:00';$('#scene-status').textContent='질문을 입력하고 작업을 시작하세요';$('#open-report').disabled=true;$('#open-report').textContent='완료 후 예시 보고서 보기 ↗';$('#start').textContent='작업 시작 ↗';$('#handoff').hidden=true;$('#active-route').style.opacity=0;members.forEach((m,i)=>{position(i,m.home);m.el.classList.remove('walking');m.el.querySelector('.speech').hidden=true;m.row.classList.remove('busy');m.row.querySelector('.team-state').textContent='대기'});document.querySelectorAll('.station').forEach((el,i)=>{el.classList.remove('active');$('#station-'+i).textContent='대기 중'});document.querySelectorAll('.steps span').forEach(el=>el.classList.remove('done'));select(selected);}
function begin(){if(!$('#question').value.trim())return;clear();question=$('#question').value.trim();$('#report-question').textContent=question;running=true;last=performance.now();$('#pause').disabled=false;$('#start').textContent='처음부터 다시 ↗';addEvent(`질문 접수: ${question}`);draw();}
function tick(now){const delta=Math.min(now-last,120);last=now;if(running&&!paused){elapsed=Math.min(total,elapsed+delta*speed);draw();if(elapsed>=total)finish();}requestAnimationFrame(tick);}
$('#request-form').addEventListener('submit',e=>{e.preventDefault();begin()});$('#pause').onclick=()=>{if(!running)return;paused=!paused;$('#office').classList.toggle('paused',paused);$('#pause').textContent=paused?'▶ 이어하기':'Ⅱ 일시정지';members.forEach(m=>{if(paused)m.el.classList.remove('walking')});};$('#speed').onclick=()=>{speed=speed===1?2:speed===2?.5:1;$('#speed').textContent=speed+'×'};$('#reset').onclick=clear;$('#open-report').onclick=()=>$('#report-dialog').showModal();$('#close-report').onclick=()=>$('#report-dialog').close();$('#report-dialog').addEventListener('click',e=>{if(e.target===$('#report-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close()}});
function clock(){ $('#clock').textContent=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date())}clock();setInterval(clock,1000);select(0);clear();requestAnimationFrame(tick);

// 저장된 결과: 실시간 AI 실행과 분리. 공식 페이지 확인일 2026-11-02.
(()=>{
 const issuer='https://www.schwabassetmanagement.com/products/schd';
 const holdings='https://www.schwabassetmanagement.com/allholdings/schd';
 const rows=[['TXN','텍사스 인스트루먼트',4.80,'아날로그·임베디드 반도체'],['CVX','셰브런',4.27,'통합 에너지'],['COP','코노코필립스',4.26,'석유·가스 개발'],['QCOM','퀄컴',4.26,'통신 반도체·특허'],['PG','P&G',4.25,'생활용품'],['KO','코카콜라',4.11,'음료'],['AMGN','암젠',4.06,'바이오 의약품'],['HD','홈디포',4.03,'주택 보수용품 유통'],['UNH','유나이티드헬스',4.01,'건강보험·의료 서비스'],['MRK','머크',3.77,'의약품']];
 const panel=document.querySelector('#result-content');let chartsOpen=true;
 function render(){
  panel.innerHTML=`<h3>SCHD · Schwab U.S. Dividend Equity ETF</h3><p class="result-meta">확인일 2026-11-02 · 미국 NYSE Arca · USD · 저장된 공식 자료 요약 · 재무제표 기반 기업가치 평가 아님</p>
  <p><b>사실:</b> 미국 배당주 지수를 따라가는 ETF예요. ETF는 여러 자산을 묶어 주식처럼 거래하는 상품이에요. 연간 총보수는 0.060%예요. <a href="${issuer}" target="_blank" rel="noopener noreferrer">운용사 공식 자료 ↗</a></p>
  <div class="result-metrics"><div><strong>3.24%</strong><span>최근 12개월 분배수익률 · 2026-09-30</span></div><div><strong>3.09%</strong><span>30일 SEC 수익률 · 2026-10-29</span></div><div><strong>102</strong><span>전체 보유 항목 수 · 2026-10-29</span></div></div>
  <p>ETF에서는 배당금을 보통 ‘분배금’이라 불러요. 최근 12개월 분배수익률은 과거 분배금에 기반한 값이며 미래 지급률이 아니에요. 30일 SEC 수익률은 최근 수익을 표준 방식으로 연율화한 별도 지표예요. 두 수치를 섞어 계산하지 않아요. <a href="${issuer}" target="_blank" rel="noopener noreferrer">수익률·정의 확인 ↗</a></p>
  <div class="result-charts" id="etf-result-charts"></div>
  <p>차트는 TradingView의 가격 흐름이며 분배금 재투자 총수익률이 아니에요. 공급자 조정 방식·시세 시점·지연 여부는 차트 내부를 확인하세요. 저장된 수익률 자료와 차트의 기준일은 달라요. 연결 실패 시 <a href="https://www.tradingview.com/symbols/AMEX-SCHD/" target="_blank" rel="noopener noreferrer">원본 차트 ↗</a>를 이용하세요.</p>
  <h3>주요 편입 기업 10개</h3><p>비중 기준일 2026-10-29 · <a href="${holdings}" target="_blank" rel="noopener noreferrer">전체 보유 목록 ↗</a> · 업종 설명은 이해를 돕는 요약이에요.</p>
  <div class="result-table"><table><thead><tr><th>기업</th><th>비중</th><th>사업 요약</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r[1]} <small>${r[0]}</small></td><td>${r[2].toFixed(2)}%</td><td>${r[3]}</td></tr>`).join('')}</tbody></table></div><p>상위 10개 합계 ${rows.reduce((a,r)=>a+Math.round(r[2]*100),0)/100}% · 개별 비중은 반올림 값이며 전체 102개 중 일부예요.</p>
  <h3>판단할 때 볼 점</h3><p><b>분석 의견:</b> 여러 배당 기업을 함께 보유하는 장점이 있지만 상위 종목과 특정 업종의 영향을 크게 받을 수 있어요. 배당주라는 이유로 가격 하락이 막히지는 않아요. 한국 투자자의 원화 수익은 달러 환율에도 영향을 받아요.</p>
  <p><b>판단 한계:</b> 이 결과만으로 현재 가격이 싸다고 판단할 근거는 부족해요. 분배금 이력·지급 일정, 동일 시점의 경쟁 ETF 비교, 세금과 환전 비용은 추가 확인이 필요해요. 가격 상승과 분배금을 합친 총수익을 함께 보세요.</p>
  <p class="result-meta">공식 페이지는 별도 발표일이 표시되지 않은 동적 자료예요. 위 항목별 기준일을 따르며 자동 최신화하지 않아요. 같은 결과를 다시 열면 저장된 요약을 재사용하며 모델·검색 호출이 추가되지 않아요. 차트는 외부 제공 서비스예요.</p>`;
  mountCharts();
 }
 function mountCharts(){const mount=document.querySelector('#etf-result-charts');mount.replaceChildren();if(!chartsOpen)return;for(const years of [1,5]){const wrap=document.createElement('div');const title=document.createElement('h3');title.textContent=`최근 ${years}년 가격 그래프`;const frame=document.createElement('iframe');frame.title=`SCHD 최근 ${years}년 가격 차트`;frame.src=`chart.html?mode=etf&symbol=AMEX%3ASCHD&years=${years}`;frame.loading='lazy';wrap.append(title,frame);mount.append(wrap);}}
 document.querySelector('#show-result').onclick=()=>{if(!panel.children.length)render();document.querySelector('#research-results').scrollIntoView({behavior:'smooth'});};
 document.querySelector('#hide-result-charts').onclick=e=>{chartsOpen=!chartsOpen;e.target.textContent=chartsOpen?'차트 접기':'차트 펼치기';mountCharts();};
 document.querySelector('#request-form').addEventListener('submit',()=>{const q=document.querySelector('#question').value.trim();document.querySelector('#result-request-status').textContent=/\bSCHD\b/i.test(q)?'SCHD 저장 결과를 아래에 표시합니다. 새 조사를 실행한 결과는 아니에요.':`“${q}”의 새 분석은 아직 연결되지 않았어요. 아래는 별도로 확인한 SCHD 결과이며 입력한 종목의 결과가 아니에요.`;});
 render();
})();
