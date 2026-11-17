"""Synthetic dispatcher tests; no real provider is invoked."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('dispatcher', Path(__file__).with_name('bridge.py'))
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
real_load = module.load


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        (self.root/'question.txt').write_text('Synthetic question', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_history_routes_without_contacting_provider(self):
        for target in ('codex', 'claude'):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                module.main(['--root', str(self.root), target, 'history', '--task', 'a'])
            self.assertEqual(json.loads(out.getvalue())['status'], 'not_started')
        self.assertFalse((self.root/'.bridge').exists())

    def test_context_files_are_explicit_and_sensitive_paths_refused(self):
        claude = real_load('source_reader', module.TOOLS/'claude-bridge/bridge.py')
        reader = claude.Bridge(self.root)
        for folder in ('private', 'credentials', 'logs'):
            (self.root/folder).mkdir(); (self.root/folder/'x.md').write_text('synthetic', encoding='utf-8')
            with self.assertRaises(ValueError): reader.read_context(folder+'/x.md')
        (self.root/'.env.md').write_text('synthetic', encoding='utf-8')
        with self.assertRaises(ValueError): reader.read_context('.env.md')

    def test_dispatcher_passes_task_and_context_to_codex(self):
        seen = []
        def loader(name, path):
            result = real_load(name, path)
            if 'codex' in name:
                class FakeBridge:
                    def __init__(self, root): pass
                    def ask(self, task, prompt, **kwargs):
                        seen.append((task, prompt, kwargs))
                        return {'status':'completed','resumed':True,'answer':'synthetic'}
                result.Bridge = FakeBridge
            return result
        with patch.object(module, 'load', side_effect=loader), contextlib.redirect_stdout(io.StringIO()):
            module.main(['--root',str(self.root),'codex','ask','--task','a','--question-file','question.txt'])
        self.assertEqual(seen[0][0], 'a'); self.assertIn('Synthetic question', seen[0][1])
        self.assertEqual(seen[0][2]['sandbox'], 'read-only')


if __name__ == '__main__': unittest.main()
