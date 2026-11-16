'use strict';
document.querySelector('#lock-workroom').addEventListener('click',async()=>{
 const button=document.querySelector('#lock-workroom');button.disabled=true;
 try{
  const response=await fetch('/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',credentials:'same-origin'});
  if(!response.ok)throw Error('logout');
  location.replace('/unlock');
 }catch{button.disabled=false;button.textContent='잠금 재시도';}
});
