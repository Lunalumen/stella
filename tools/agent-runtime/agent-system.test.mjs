import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { join, resolve, sep } from 'node:path';
import { runtimeDirectory, loadRegistry, validateTask, workerPrompt, executionPlan, executeTask, usageSummary, createRunStore } from './agent-system.mjs';
import { codeToolConfig } from './code-tools.mjs';

const registry = await loadRegistry();
const task = {goal:'알고리즘 역할만 확인하고 강의자료는 읽지 마.', agents:['algorithms'], sources:{}};
const result = text=>({text, usage:{input_tokens:100,cached_input_tokens:40,output_tokens:20,reasoning_output_tokens:5},sdkThreadId:'sdk-only-test'});

test('총괄·관리자·7개 과목·선택 검증 역할의 상위 연결 확인',()=>{
  assert.equal(registry.agents.length,11);
  assert.equal(registry.agents.filter(a=>a.parent === null).length,1);
  assert.equal(registry.agents.filter(a=>a.kind === 'specialist').length,7);
  assert.equal(registry.agents.filter(a=>a.kind === 'reviewer').length,1);
});
test('코드 검색 도구는 기본 미연결이며 한 제공자만 연결',()=>{
  assert.deepEqual(codeToolConfig('none'),{});
  const graft=codeToolConfig('graft',{checkInstalled:false});
  assert.deepEqual(Object.keys(graft.mcp_servers),['myeongwol_graft']);
  assert.equal(graft.mcp_servers.myeongwol_graft.env.DO_NOT_TRACK,'1');
  assert.equal(graft.mcp_servers.myeongwol_graft.args.at(-1),runtimeDirectory);
  const cbm=codeToolConfig('codebase-memory',{checkInstalled:false}).mcp_servers.myeongwol_codebase_memory;
  assert.equal(cbm.env.CBM_ALLOWED_ROOT,runtimeDirectory);
  assert.ok(!cbm.enabled_tools.includes('index_repository'));
  assert.throws(()=>validateTask({...task,codeTools:'all'},registry));
});
test('배정 호출에는 코드 도구를 전달하지 않고 실제 담당에만 전달',async()=>{
  const providers=[];
  const record=await executeTask({...task,codeTools:'graft'},registry,{managed:true,call:async(a,p,options)=>{
    providers.push(options.codeTools);
    return result(a.id === 'myeongwol' ? JSON.stringify({targets:['algorithms'],reason:'코드 검토'}) : '보고');
  }});
  assert.equal(record.status,'completed');
  assert.deepEqual(providers,['none','graft']);
});
test('agency 기준은 짧은 지침으로 적용하고 선택 검증을 자동 호출하지 않음',async()=>{
  assert.ok(registry.agents.find(a=>a.id === 'myeongwol').instructions.includes('완료 기준'));
  assert.ok(registry.agents.find(a=>a.id === 'reality-checker').instructions.includes('근거가 충분하면 인정'));
  const seen=[];
  await executeTask(task,registry,{call:async a=>{seen.push(a.id);return result('보고');}});
  assert.deepEqual(seen,['algorithms']);
});
test('직접 작업은 담당 1명만 호출하고 타 프로젝트 출처를 제외',async()=>{
  const scoped = {...task,agents:['algorithms','java'],sources:{algorithms:['algo.pptx 2쪽'],java:['private-java-reference']}};
  assert.ok(!workerPrompt(registry.agents.find(a=>a.id === 'algorithms'),scoped).includes('private-java-reference'));
  const seen=[];
  const record=await executeTask(task,registry,{call:async a=>{seen.push(a.id);return result('보고');}});
  assert.deepEqual(seen,['algorithms']);
  assert.equal(record.status,'completed');
  assert.equal(record.plan.desktopChatsControlled,false);
});
test('총괄은 필요한 하위 담당만 선택하고 중간 관리자를 추가 호출하지 않음',async()=>{
  const seen=[];
  const record=await executeTask({...task,agents:['algorithms','java']},registry,{managed:true,call:async a=>{
    seen.push(a.id);
    return result(a.id === 'myeongwol' ? JSON.stringify({targets:['algorithms'],reason:'알고리즘 요청'}) : '보고');
  }});
  assert.equal(record.status,'completed');
  assert.deepEqual(seen,['myeongwol','algorithms']);
  assert.equal(record.usage.totals.input_tokens,200);
});
test('미등록·중복·호출 상한 초과 배정은 담당 실행 전 차단',async()=>{
  assert.throws(()=>validateTask({...task,agents:['missing']},registry));
  assert.throws(()=>validateTask({...task,agents:['algorithms','algorithms']},registry));
  assert.throws(()=>executionPlan({...task,agents:['algorithms','java']},registry,{maxCalls:1}));
  for (const targets of [['chemistry'],['algorithms','algorithms'],['algorithms','java']]) {
    let calls=0;
    const record=await executeTask({...task,agents:['algorithms','java']},registry,{managed:true,maxCalls:2,call:async()=>{
      calls++;return result(JSON.stringify({targets,reason:'시험'}));
    }});
    assert.equal(record.status,'failed');
    assert.equal(calls,1);
  }
});
test('프로젝트 관리자는 자기 하위만 선택하고 모호한 요청은 추가 정보 상태로 종료',async()=>{
  const record=await executeTask(task,registry,{managed:true,manager:'major',call:async()=>result(JSON.stringify({targets:[],reason:'작업 확인 필요'}))});
  assert.equal(record.status,'needs-input');
  assert.equal(record.calls.length,1);
  assert.ok(record.finishedAt);
  assert.throws(()=>executionPlan(task,registry,{managed:true,manager:'liberal-arts'}));
});
test('실패 시 완료 결과 보존·자동 재시도 없음·취소 후 실행 없음',async()=>{
  const writes=[];
  const record=await executeTask({...task,agents:['algorithms','java']},registry,{persist:async r=>writes.push(structuredClone(r)),call:async a=>{
    if(a.id === 'java') throw new Error('모의 연결 오류');
    return result('완료 결과');
  }});
  assert.equal(record.status,'failed');
  assert.equal(record.calls.length,2);
  assert.equal(record.results.length,1);
  assert.equal(writes.at(-1).calls.at(-1).status,'failed');
  const controller=new AbortController(); controller.abort();
  const cancelled=await executeTask(task,registry,{signal:controller.signal,call:async()=>assert.fail('호출하면 안 됨')});
  assert.equal(cancelled.status,'cancelled');
});
test('미측정 usage는 0으로 표시하지 않고 캐시·추론 토큰 중복 합산 방지',()=>{
  assert.equal(usageSummary([{usage:null}]).totals,null);
  const summary=usageSummary([{usage:result('').usage},{usage:null}]);
  assert.equal(summary.measuredCalls,1);
  assert.equal(summary.unmeasuredCalls,1);
  assert.equal(summary.totals.input_tokens,100);
  assert.equal(summary.totals.output_tokens,20);
  assert.equal(summary.savingsPercent,null);
});
test('실행별 독립 폴더와 원자적 스냅샷으로 최종 상태 저장',async()=>{
  const base=await mkdtemp(join(runtimeDirectory,'myeongwol-test-'));
  try {
    const first=await createRunStore(base);
    const second=await createRunStore(base);
    assert.notEqual(first.file,second.file);
    await first.persist({status:'running'});
    await first.persist({status:'completed'});
    assert.equal(JSON.parse(await readFile(first.file,'utf8')).status,'completed');
  } finally {
    assert.ok(resolve(base).startsWith(runtimeDirectory + sep));
    await rm(base,{recursive:true,force:true});
  }
});
