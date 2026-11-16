'use strict';
(() => {
 const symbols={'NASDAQ:GOOGL':'USD','NASDAQ:INTC':'USD','KRX:005930':'KRW','NASDAQ:AAPL':'USD','NASDAQ:TSLA':'USD','AMEX:SPY':'USD'};
 const q=s=>document.querySelector(s);
 let symbol='NASDAQ:GOOGL',interval='D',opened=true,loadVersion=0;
 function mount(){
  const version=++loadVersion;
  q('#market-symbol').textContent=`${symbol} · ${symbols[symbol]}`;
  q('#chart-external').href=`https://www.tradingview.com/chart/?symbol=${encodeURIComponent(symbol)}`;
  document.querySelectorAll('[data-symbol]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.symbol===symbol)));
  if(symbol==='KRX:005930'){
   const notice=document.createElement('div');notice.className='chart-unavailable';
   const heading=document.createElement('h3');heading.textContent='삼성전자는 원본 차트에서 확인해요';
   const text=document.createElement('p');text.textContent='2026-10-30 확인 시 이 무료 위젯에서는 삼성전자 차트를 제공하지 않았어요. 아래 링크에서 TradingView 원본 페이지를 열 수 있어요.';
   const link=document.createElement('a');link.textContent='삼성전자 차트 열기 ↗';link.href=q('#chart-external').href;link.target='_blank';link.rel='noopener noreferrer';
   notice.append(heading,text,link);q('#chart-mount').replaceChildren(notice);q('#chart-status').textContent='KRX:005930 · 무료 임베드 제공 제한. 가격 데이터는 표시하지 않아요.';return;
  }
  const frame=document.createElement('iframe');
  frame.title=`TradingView ${symbol} ${interval==='W'?'주봉':'일봉'} 차트`;
  frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox');
  frame.referrerPolicy='no-referrer';
  const settings=new URLSearchParams({symbol,interval});
  document.querySelectorAll('[data-indicator]').forEach(input=>settings.set(input.dataset.indicator,input.checked?'1':'0'));
  frame.src='chart.html?'+settings.toString();
  q('#chart-mount').replaceChildren(frame);
  q('#chart-status').textContent='외부 차트를 불러오는 중 · AI 분석은 실행하지 않아요.';
  // A loaded frame is not proof that market prices were received.
  frame.addEventListener('load',()=>{if(version!==loadVersion)return;q('#chart-status').textContent=`화면 요청 ${new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date())} KST · 가격 기준 시각 아님. 빈 화면이면 TradingView에서 열어 보세요.`;});
 }
 document.querySelectorAll('[data-symbol]').forEach(button=>button.addEventListener('click',()=>{if(button.dataset.symbol===symbol)return;symbol=button.dataset.symbol;mount();}));
 q('#chart-interval').addEventListener('change',e=>{interval=e.target.value;mount();});
 document.querySelectorAll('[data-indicator]').forEach(input=>input.addEventListener('change',()=>{if(opened)mount();}));
 q('#chart-reload').addEventListener('click',mount);
 q('#chart-toggle').addEventListener('click',()=>{opened=!opened;q('#market-body').hidden=!opened;q('#chart-toggle').setAttribute('aria-expanded',String(opened));q('#chart-toggle').textContent=opened?'차트 닫기':'차트 열기';if(opened)mount();else{loadVersion++;q('#chart-mount').replaceChildren();}});
 const watchItems=[['구글','NASDAQ:GOOGL'],['인텔','NASDAQ:INTC'],['애플','NASDAQ:AAPL'],['테슬라','NASDAQ:TSLA'],['미국 시장 ETF','AMEX:SPY']];
 let watchOpen=true;
 function renderWatch(){
  const grid=q('#watch-cards');grid.replaceChildren();
  for(const [name,ticker] of watchItems){
   const card=document.createElement('article');card.className='watch-card';
   const label=document.createElement('div');label.className='watch-card-header';
   const title=document.createElement('strong');title.textContent=name;
   const detail=document.createElement('button');detail.type='button';detail.textContent='상세 차트 ↗';detail.setAttribute('aria-label',name+' 상세 차트 보기');
   detail.onclick=()=>{if(!opened)q('#chart-toggle').click();symbol=ticker;mount();q('#market-title').scrollIntoView({behavior:'smooth',block:'start'});};
   label.append(title,detail);
   const frame=document.createElement('iframe');frame.title=name+' 시세 카드 · TradingView';frame.loading='lazy';frame.referrerPolicy='no-referrer';frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox');frame.src='chart.html?mode=mini&symbol='+encodeURIComponent(ticker);
   card.append(label,frame);grid.append(card);
  }
  const kr=document.createElement('article');kr.className='watch-card watch-kr';
  const h=document.createElement('strong');h.textContent='삼성전자 · 005930';
  const p=document.createElement('p');p.textContent='무료 위젯 제공 제한으로 가격을 표시할 수 없어요.';
  const a=document.createElement('a');a.textContent='원본 차트 열기 ↗';a.href='https://www.tradingview.com/chart/?symbol=KRX%3A005930';a.target='_blank';a.rel='noopener noreferrer';
  kr.append(h,p,a);grid.append(kr);
 }
 q('#watch-toggle').addEventListener('click',()=>{watchOpen=!watchOpen;q('#watch-body').hidden=!watchOpen;q('#watch-toggle').setAttribute('aria-expanded',String(watchOpen));q('#watch-toggle').textContent=watchOpen?'상황판 접기':'상황판 열기';if(watchOpen)renderWatch();else q('#watch-cards').replaceChildren();});
 renderWatch();
 mount();
})();
