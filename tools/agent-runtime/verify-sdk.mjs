import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { Codex } from '@openai/codex-sdk';

const installed = JSON.parse(readFileSync(new URL('./node_modules/@openai/codex-sdk/package.json', import.meta.url), 'utf8'));
const expected = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')).dependencies['@openai/codex-sdk'];
assert.equal(installed.version, expected);
const codex = new Codex();
assert.equal(typeof codex.startThread, 'function');
assert.equal(typeof codex.resumeThread, 'function');
// SDK thread construction is lazy: no thread.run(), subprocess, authentication,
// model request, or access to the user's existing desktop conversations here.
const draft = codex.startThread();
assert.equal(typeof draft.run, 'function');
assert.equal(typeof draft.runStreamed, 'function');
const sdkRequire = createRequire(import.meta.resolve('@openai/codex-sdk'));
const cliManifestPath = sdkRequire.resolve('@openai/codex/package.json');
const cliManifest = JSON.parse(readFileSync(cliManifestPath, 'utf8'));
const cliEntry = resolve(dirname(cliManifestPath), cliManifest.bin.codex);
const cliVersion = execFileSync(process.execPath, [cliEntry, '--version'], {
  encoding: 'utf8', timeout: 15000, windowsHide: true
}).trim();
assert.match(cliVersion, /codex/i);
console.log(JSON.stringify({
  package: installed.name,
  version: installed.version,
  importVerified: true,
  threadApiVerified: true,
  cliVersion,
  modelCalled: false,
  desktopChatsControlled: false
}, null, 2));
