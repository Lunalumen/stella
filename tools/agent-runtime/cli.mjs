import { readFile } from 'node:fs/promises';
import { loadRegistry, executionPlan, executeTask, createRunStore } from './agent-system.mjs';

const args = process.argv.slice(2);
const [command, file, ...flags] = args;
try {
  const registry = await loadRegistry();
  if (command === 'list') {
    console.log(JSON.stringify(registry,null,2));
  } else if (['plan','run'].includes(command) && file) {
    const options = {managed:false, manager:registry.root, maxCalls:4};
    for (let i=0; i<flags.length; i++) {
      if (flags[i] === '--managed') options.managed = true;
      else if (flags[i] === '--manager') options.manager = flags[++i];
      else if (flags[i] === '--max-calls') options.maxCalls = Number(flags[++i]);
      else throw new Error(`알 수 없는 옵션: ${flags[i]}`);
    }
    const task = JSON.parse((await readFile(file,'utf8')).replace(/^\uFEFF/,''));
    const plan = executionPlan(task,registry,options);
    if (command === 'plan') console.log(JSON.stringify(plan,null,2));
    else {
      const controller = new AbortController();
      const cancel = ()=>controller.abort();
      process.once('SIGINT', cancel);
      process.once('SIGTERM', cancel);
      const store = await createRunStore();
      console.error(`실행 기록 폴더: ${store.directory}`);
      try {
        const record = await executeTask(task,registry,{...options,persist:store.persist,signal:controller.signal,progress:p=>console.error(`${p.agent}: ${p.status}`)});
        console.log(JSON.stringify(record,null,2));
        console.error(`최종 기록: ${store.file}`);
        process.exitCode = record.status === 'completed' ? 0 : 1;
      } finally {
        process.removeListener('SIGINT',cancel);
        process.removeListener('SIGTERM',cancel);
      }
    }
  } else throw new Error('사용: node cli.mjs list | plan 작업.json [--managed] [--manager ID] [--max-calls N] | run 작업.json [동일 옵션]');
} catch(error) {
  console.error(error.message);
  process.exitCode = 1;
}
