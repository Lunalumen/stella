"""Offline synthetic tests only; no provider credentials, network or real model calls."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('codex_bridge', Path(__file__).with_name('server.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeClient:
    def __init__(self):
        self.calls = []
        self.fail = False

    def ask(self, prompt, session, cwd, sandbox, model, timeout):
        self.calls.append({'session': session, 'cwd': cwd, 'sandbox': sandbox})
        if self.fail:
            raise ValueError('synthetic_failure')
        return {'session_id': session or str(uuid.uuid4()), 'answer': 'Synthetic answer', 'usage': {'input_tokens': 1}}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.client = FakeClient()
        self.bridge = module.Bridge(self.root, self.client)

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_resume_and_redacted_history(self):
        first = self.bridge.ask('a', 'first')
        sid = json.loads((self.bridge.task_dir('a')/'state.json').read_text('utf-8'))['session_id']
        second = self.bridge.ask('a', 'second')
        self.assertFalse(first['resumed'])
        self.assertTrue(second['resumed'])
        self.assertEqual(self.client.calls[1]['session'], sid)
        history = json.dumps(self.bridge.history('a'))
        self.assertNotIn(sid, history)
        self.assertNotIn('first', history)

    def test_tasks_do_not_share_sessions(self):
        self.bridge.ask('a', 'first')
        self.bridge.ask('b', 'second')
        self.assertIsNone(self.client.calls[1]['session'])

    def test_configuration_change_refused_then_explicit_new(self):
        self.bridge.ask('a', 'first')
        for changes in ({'sandbox': 'workspace-write'}, {'model': 'synthetic-model'}):
            with self.assertRaisesRegex(ValueError, 'configuration_changed'):
                self.bridge.ask('a', 'second', **changes)
        result = self.bridge.ask('a', 'new', sandbox='workspace-write', new_session=True)
        self.assertFalse(result['resumed'])

    def test_cwd_outside_root(self):
        with self.assertRaisesRegex(ValueError, 'cwd_outside'):
            self.bridge.ask('a', 'x', cwd=self.root.parent)

    def test_failure_no_retry_and_explicit_reset(self):
        self.client.fail = True
        with self.assertRaisesRegex(ValueError, 'synthetic_failure'):
            self.bridge.ask('a', 'x')
        self.assertEqual(len(self.client.calls), 1)
        self.client.fail = False
        with self.assertRaisesRegex(ValueError, 'previous_turn_incomplete'):
            self.bridge.ask('a', 'again')
        self.assertEqual(len(self.client.calls), 1)
        self.assertFalse(self.bridge.ask('a', 'new', new_session=True)['resumed'])

    def test_lock(self):
        folder = self.bridge.task_dir('a'); folder.mkdir(parents=True)
        (folder/'turn.lock').touch()
        with self.assertRaisesRegex(ValueError, 'task_busy'):
            self.bridge.ask('a', 'x')
        self.assertEqual(self.client.calls, [])

    def test_invalid_inputs_before_client_call(self):
        cases = [('', 'x', {}), ('../escape', 'x', {}), ('a', '', {}), ('a', 'x'*32001, {}),
                 ('a', 'x', {'timeout': True}), ('a', 'x', {'timeout': 181}),
                 ('a', 'x', {'new_session': 'yes'}), ('a', 'x', {'model': '--bad'}),
                 ('a', 'x', {'sandbox': 'danger-full-access'})]
        for task, prompt, options in cases:
            with self.subTest(options=options):
                with self.assertRaises(ValueError): self.bridge.ask(task, prompt, **options)
        self.assertEqual(self.client.calls, [])

    def test_corrupt_session_refused(self):
        self.bridge.ask('a', 'first')
        path = self.bridge.task_dir('a')/'state.json'
        data = json.loads(path.read_text('utf-8')); data['session_id'] = '--last'
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'session_format'): self.bridge.ask('a', 'again')

    def test_mismatched_resumed_uuid_fails(self):
        self.bridge.ask('a', 'first')
        with patch.object(self.client, 'ask', return_value={'session_id': str(uuid.uuid4()), 'answer': 'wrong'}):
            with self.assertRaisesRegex(ValueError, 'unexpected_session'): self.bridge.ask('a', 'again')

    def test_absent_history_no_state_created(self):
        self.assertEqual(self.bridge.history('missing')['status'], 'not_started')
        self.assertFalse((self.root/'.bridge').exists())

    def test_failed_new_session_preserves_previous_state(self):
        self.bridge.ask('a', 'first')
        original = json.loads((self.bridge.task_dir('a')/'state.json').read_text('utf-8'))
        self.client.fail = True
        with self.assertRaises(ValueError): self.bridge.ask('a', 'new', new_session=True)
        saved = json.loads((self.bridge.task_dir('a')/'0002/previous-state.json').read_text('utf-8'))
        self.assertEqual(saved['session_id'], original['session_id'])


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_allowlisted_environment(self):
        client = module.CodexClient(command=['synthetic'])
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic', 'CODEX_HOME': 'synthetic-home', 'HTTPS_PROXY': 'synthetic-proxy', 'PATH': 'synthetic-path'}):
            env = client.env()
        self.assertNotIn('OPENAI_API_KEY', env); self.assertNotIn('CODEX_HOME', env)
        self.assertNotIn('HTTPS_PROXY', env); self.assertEqual(env['PATH'], 'synthetic-path')

    def test_auth_unknown_and_api_refused(self):
        client = module.CodexClient(command=['synthetic'])
        for mode in ('Logged in using an API key', 'unknown'):
            with patch.object(module, 'bounded_process', return_value=(0, mode)):
                with self.assertRaisesRegex(ValueError, 'chatgpt_login_required'): client.checked_status()

    def test_unsupported_cli_refused(self):
        client = module.CodexClient(command=['synthetic'])
        with patch.object(module, 'bounded_process', side_effect=[(0, 'Logged in using ChatGPT'), (0, 'old help')]):
            with self.assertRaisesRegex(ValueError, 'unsupported_CLI'): client.checked_status()

    def test_npm_shim_without_shell(self):
        shim = self.root/'codex.cmd'; shim.touch()
        entry = self.root/'node_modules/@openai/codex/bin/codex.js'; entry.parent.mkdir(parents=True); entry.touch()
        node = self.root/'node.exe'; node.touch()
        with patch.dict(os.environ, {}, clear=True), patch.object(module.shutil, 'which', side_effect=lambda name: str(shim if name=='codex' else node)):
            self.assertEqual([Path(p).resolve() for p in module.codex_launcher()], [node.resolve(), entry.resolve()])

    def test_missing_npm_entry_refused(self):
        shim = self.root/'codex.cmd'; shim.touch()
        with patch.dict(os.environ, {}, clear=True), patch.object(module.shutil, 'which', return_value=str(shim)):
            with self.assertRaisesRegex(ValueError, 'no_shell_fallback'): module.codex_launcher()

    def test_explicit_native_executable(self):
        executable = self.root/'codex.exe'; executable.touch()
        with patch.dict(os.environ, {'CODEX_EXE': str(executable)}):
            self.assertEqual(module.codex_launcher(), [str(executable.resolve())])

    def test_real_subprocess_fake_events_and_resume_flags(self):
        script = self.root/'fake_cli.py'
        script.write_text('''import json, pathlib, sys, uuid
args=sys.argv[1:]; prompt=sys.stdin.read()
sid=args[args.index('resume')+1] if 'resume' in args else str(uuid.uuid4())
pathlib.Path(args[args.index('-o')+1]).write_text('Synthetic final answer', encoding='utf-8')
print(json.dumps({'type':'thread.started','thread_id':sid}))
print(json.dumps({'type':'item.completed','item':{'type':'reasoning','text':'DO_NOT_PERSIST_SYNTHETIC_REASONING'}}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'output_tokens':1}}))
''', encoding='utf-8')
        client = module.CodexClient(command=[sys.executable, str(script)])
        with patch.object(client, 'checked_status', return_value={'authenticated_chatgpt': True}):
            result = client.ask('x', None, self.root, 'read-only', None, 10)
            resumed = client.ask('y', result['session_id'], self.root, 'read-only', None, 10)
        self.assertEqual(result['session_id'], resumed['session_id'])
        self.assertEqual(resumed['answer'], 'Synthetic final answer')
        self.assertNotIn('DO_NOT_PERSIST', json.dumps(resumed))

    def test_timeout_stops_process(self):
        with self.assertRaisesRegex(ValueError, 'timeout'):
            module.bounded_process([sys.executable, '-c', 'import time;time.sleep(30)'], env=module.CodexClient(['x']).env(), cwd=self.root, timeout=0.2)

    def test_stream_limit_stops_process(self):
        with self.assertRaisesRegex(ValueError, 'stream_limit'):
            module.bounded_process([sys.executable, '-c', 'print("x"*2000)'], env=module.CodexClient(['x']).env(), cwd=self.root, output_limit=100)


class ProtocolTests(unittest.TestCase):
    def test_public_errors_do_not_reveal_paths_or_raw_exceptions(self):
        class Broken:
            def ask(self, *a, **kw): raise OSError('SYNTHETIC_PRIVATE_PATH')
        request={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'ask_chatgpt','arguments':{'task_id':'a','prompt':'x'}}}
        reply=module.handle(request, Broken())
        self.assertTrue(reply['result']['isError']); self.assertNotIn('SYNTHETIC_PRIVATE_PATH', json.dumps(reply))

    def test_initialize_and_list_without_model(self):
        response = module.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'not-supported'}})
        self.assertEqual(response['result']['protocolVersion'], '2025-06-18')
        tools = module.handle({'jsonrpc':'2.0','id':2,'method':'tools/list'})['result']['tools']
        self.assertIn('task_id', tools[0]['inputSchema']['required'])

    def test_malformed_requests(self):
        self.assertEqual(module.handle([])['error']['code'], -32600)
        self.assertIsNone(module.handle({'jsonrpc':'2.0','method':'notifications/initialized'}))
        self.assertEqual(module.handle({'jsonrpc':'2.0','id':1,'method':'tools/call','params':[]})['error']['code'], -32602)

    def test_mcp_resume_uses_same_store(self):
        with tempfile.TemporaryDirectory() as folder:
            bridge = module.Bridge(folder, FakeClient())
            request = {'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'ask_chatgpt','arguments':{'task_id':'a','prompt':'x'}}}
            first = module.handle(request, bridge)['result']; second = module.handle(request, bridge)['result']
            self.assertFalse(json.loads(first['content'][0]['text'])['resumed'])
            self.assertTrue(json.loads(second['content'][0]['text'])['resumed'])

    def test_protocol_parse_error_and_ping_subprocess(self):
        data = b'bad-json\n{"jsonrpc":"2.0","id":1,"method":"ping"}\n'
        result = subprocess.run([sys.executable, '-B', str(Path(module.__file__))], input=data, capture_output=True, timeout=10)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(responses[0]['error']['code'], -32700)
        self.assertEqual(responses[1]['result'], {})


if __name__ == '__main__':
    unittest.main()
