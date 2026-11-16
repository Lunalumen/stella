"""Offline tests with a fake client; no external models, keys or real sessions."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid
from unittest.mock import patch

import bridge


class FakeClient:
    def __init__(self, auth=True, fail=False):
        self.auth, self.fail, self.calls = auth, fail, []

    def status(self):
        return {'subscription_login': self.auth}

    def ask(self, prompt, session, resume, cwd, timeout):
        self.calls.append((prompt, session, resume))
        if self.fail:
            raise subprocess.TimeoutExpired('synthetic-only', timeout)
        return {'result': '합성 시험 응답', 'session_id': session, 'usage': {'input_tokens': 1}}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.client = FakeClient()
        self.b = bridge.Bridge(self.root, self.client)

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_and_resume(self):
        a = self.b.ask('t1', '첫 질문')
        b = self.b.ask('t1', '두 번째 질문')
        self.assertFalse(a['resumed'])
        self.assertTrue(b['resumed'])
        self.assertEqual(self.client.calls[0][1], self.client.calls[1][1])
        self.assertEqual(Path(b['answer_file']).read_text('utf-8').strip(), '합성 시험 응답')
        self.assertEqual(len(self.b.history('t1')['turns']), 2)

    def test_separate_tasks_and_explicit_new(self):
        self.b.ask('a', 'a')
        self.b.ask('b', 'b')
        self.b.ask('a', 'new', new_session=True)
        self.assertEqual(len({c[1] for c in self.client.calls}), 3)
        self.assertFalse(self.client.calls[-1][2])

    def test_no_api_fallback(self):
        self.client.auth = False
        with self.assertRaisesRegex(ValueError, 'subscription login'):
            self.b.ask('a', 'test')
        self.assertEqual(self.client.calls, [])
        self.assertFalse((self.root / '.bridge').exists())

    def test_task_traversal(self):
        for task in ('../other', 'A', '', 'a/b'):
            with self.assertRaises(ValueError):
                self.b.ask(task, 'test')

    def test_context_limits_and_paths(self):
        (self.root / 'x.md').write_text('합성 참고', encoding='utf-8')
        self.b.ask('a', 'test', ['x.md'])
        self.assertIn('합성 참고', self.client.calls[0][0])
        with self.assertRaises(ValueError):
            self.b.read_context('../outside.md')
        (self.root / '.bridge/secret.md').write_text('not context', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.b.read_context('.bridge/secret.md')
        (self.root / 'large.md').write_text('x' * 20001)
        with self.assertRaises(ValueError):
            self.b.read_context('large.md')

    def test_lock_prevents_second_call(self):
        d = self.b.task_dir('a')
        d.mkdir(parents=True)
        (d / 'turn.lock').touch()
        with self.assertRaisesRegex(ValueError, 'already running'):
            self.b.ask('a', 'test')
        self.assertEqual(self.client.calls, [])

    def test_timeout_no_retry_or_implicit_new_session(self):
        self.client.fail = True
        with self.assertRaisesRegex(ValueError, 'timed out'):
            self.b.ask('a', 'test')
        self.assertEqual(len(self.client.calls), 1)
        self.client.fail = False
        with self.assertRaisesRegex(ValueError, 'incomplete/failed'):
            self.b.ask('a', 'test again')
        self.assertEqual(len(self.client.calls), 1)
        result = self.b.ask('a', 'new', new_session=True)
        self.assertFalse(result['resumed'])

    def test_limits(self):
        for q in ('', ' ' * 5, 'x' * 12001):
            with self.assertRaises(ValueError):
                self.b.ask('a', q)
        with self.assertRaises(ValueError):
            self.b.ask('a', 'x', timeout=1)

    def test_cli_arguments_and_environment(self):
        client = object.__new__(bridge.ClaudeClient)
        client.executable = self.root / 'claude.exe'
        client.executable.touch()
        cmd = client.command(str(uuid.uuid4()), True)
        self.assertIn('--resume', cmd)
        self.assertIn('--restricted', cmd)
        self.assertEqual(cmd[cmd.index('--tools') + 1], '')
        self.assertNotIn('--dangerously-skip-permissions', cmd)
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'synthetic-key', 'CLAUDE_CODE_USE_BEDROCK': '1'}):
            env = client.env()
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertNotIn('CLAUDE_CODE_USE_BEDROCK', env)

    def test_npm_command_without_shell(self):
        shim = self.root / 'npm/claude.cmd'
        entry = shim.parent / 'node_modules/@anthropic-ai/claude-code/cli.js'
        entry.parent.mkdir(parents=True)
        entry.touch()
        shim.touch()
        node = self.root / 'node.exe'
        node.touch()
        with patch.object(bridge.shutil, 'which', return_value=str(node)):
            self.assertEqual(bridge.launcher(shim), [str(node), str(entry)])
        entry.unlink()
        with self.assertRaisesRegex(ValueError, 'No shell fallback'):
            bridge.launcher(shim)

    def test_path_command_has_priority(self):
        with patch.object(bridge.shutil, 'which', return_value='C:/synthetic/npm/claude.cmd'):
            self.assertEqual(bridge.discover_claude(), Path('C:/synthetic/npm/claude.cmd'))

    def test_native_npm_command_without_shell_or_node(self):
        shim = self.root / 'npm/claude.cmd'
        native = shim.parent / 'node_modules/@anthropic-ai/claude-code/bin/claude.exe'
        native.parent.mkdir(parents=True)
        native.touch()
        shim.touch()
        with patch.object(bridge.shutil, 'which', return_value=None):
            self.assertEqual(bridge.launcher(shim), [str(native)])

    def test_history_absent(self):
        self.assertEqual(self.b.history('missing')['status'], 'not_started')
        self.assertFalse((self.root / '.bridge').exists())


if __name__ == '__main__':
    unittest.main()
