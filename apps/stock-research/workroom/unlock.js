'use strict';
(async()=>{
 const key=new URLSearchParams(location.hash.slice(1)).get('key');
 // Fragments never reach HTTP logs/referrers; remove before any further request.
 history.replaceState(null,'','/unlock');
 if(!key)return;
 const status=document.querySelector('#unlock-status');
 status.textContent='이 브라우저의 접근 권한을 확인하고 있어요…';
 try{
  const response=await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key}),credentials:'same-origin'});
  if(!response.ok)throw new Error('locked');
  location.replace('/');
 }catch{status.textContent='접속 권한을 확인하지 못했어요. 잠시 후 현재 Windows 계정에서 workroom\\open.ps1을 다시 실행해 주세요.';}
})();
