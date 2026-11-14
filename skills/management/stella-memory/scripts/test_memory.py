"""Synthetic tests ①–⑰ from decision-claude.md. No real user memories are used."""
import importlib.util
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('memory', ROOT / 'memory.py')
mem = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mem)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'm.db')
        self.stores = []
        self.p1 = self.store('p1')

    def tearDown(self):
        for st in self.stores:
            st.db.close()
        self.tmp.cleanup()

    def store(self, project, actor='claude'):
        st = mem.Store(self.db, project, actor)
        self.stores.append(st)
        return st

    def rows(self, table):
        return self.p1.db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]


class Tests(Base):
    def test_01_add_condition(self):
        r = self.p1.add('보고서는 참고문헌 제외 1,000자 이내', 'constraint', key='report.length')
        self.assertEqual(r['status'], 'created')
        s = self.p1.show(memory_id=r['memory_id'])
        self.assertEqual((s['status'], s['rev'], s['key'], s['requested_by'], s['source_verified']),
                         ('active', 1, 'report.length', 'user', False))
        for field in ('memory_id', 'project', 'kind', 'created', 'updated', 'actor'):
            self.assertIn(field, s)

    def test_02_search_only_relevant(self):
        self.p1.add('보고서는 참고문헌 제외 1,000자 이내', 'constraint', key='report.length')
        self.p1.add('보고서 제출일은 10월 31일', 'constraint', key='report.deadline')
        for n in range(8):
            self.p1.add(f'알고리즘 과제 {n}번은 재귀 사용', 'decision', key=f'algo.q{n}')
        r = self.p1.search('보고서')
        self.assertEqual((r['total_matched'], r['returned'], r['partial'], r['mode']), (2, 2, False, 'keyword'))
        self.assertLessEqual(r['chars_returned'], 1500)
        self.assertTrue(all('보고서' in x['text'] for x in r['results']))

    def test_03_duplicate_unchanged(self):
        a = self.p1.add('출력은 한국어로', 'preference', key='output.language')
        b = self.p1.add('  출력은 한국어로 \n', 'preference', key='output.language')
        self.assertEqual((b['status'], b['memory_id']), ('unchanged', a['memory_id']))
        self.assertEqual(self.rows('memories'), 1)

    def test_04_conflict_then_resolve(self):
        a = self.p1.add('출력은 한국어로', 'preference', key='output.language')
        b = self.p1.add('출력은 영어로', 'preference', key='output.language')
        self.assertEqual(b['status'], 'conflict_candidate')
        self.assertEqual(self.rows('memories'), 2)
        s = self.p1.search('출력')
        self.assertEqual(len(s['conflicts']), 1)
        self.assertTrue(all(x['conflict_id'] == b['conflict_id'] for x in s['results']))
        r = self.p1.resolve(b['conflict_id'], f"{b['memory_id']}:1")
        self.assertEqual(r['superseded'], [a['memory_id']])
        self.assertEqual(self.p1.show(memory_id=a['memory_id'])['status'], 'superseded')
        self.assertEqual(self.p1.show(memory_id=b['memory_id'])['status'], 'active')
        self.assertEqual(self.p1.search('출력')['returned'], 1)

    def test_05_project_isolation(self):
        self.p1.add('마감은 금요일', 'constraint', key='deadline')
        p2 = self.store('p2')
        p2.add('마감은 월요일', 'constraint', key='deadline')
        r = p2.search('마감')
        self.assertEqual([x['project'] for x in r['results']], ['p2'])
        self.assertEqual(self.p1.search('마감')['results'][0]['text'], '마감은 금요일')
        g = self.store('global'); g.add('마감 표기는 ISO 날짜', 'preference', key='date.format')
        self.assertEqual(p2.search('마감')['total_matched'], 1)
        self.assertEqual(p2.search('마감', include_global=True)['total_matched'], 2)

    def test_06_retire_and_delete(self):
        a = self.p1.add('임시 조건', 'constraint', key='tmp')
        self.p1.retire(a['memory_id'])
        self.assertEqual(self.p1.search('임시')['total_matched'], 0)
        self.assertEqual(self.p1.show(include_all=True)['count'], 1)
        self.assertEqual(self.p1.show()['count'], 0)
        self.assertEqual(self.p1.add('임시 조건', 'constraint', key='tmp')['status'], 'retired_exists')
        self.assertEqual(self.p1.add('임시 조건', 'constraint', key='tmp', reactivate=True)['status'], 'reactivated')
        with self.assertRaises(ValueError):
            self.p1.delete(a['memory_id'])
        d = self.p1.delete(a['memory_id'], confirm=True)
        self.assertEqual(d['status'], 'deleted')
        self.assertEqual(self.rows('tombstones'), 1)
        with self.assertRaises(ValueError):
            self.p1.show(memory_id=a['memory_id'])

    def test_08_same_text_different_scope(self):
        p2 = self.store('p2')
        ids = {self.p1.add('같은 문장', 'decision', key='k1')['memory_id'],
               p2.add('같은 문장', 'decision', key='k1')['memory_id'],
               self.p1.add('같은 문장', 'decision', key='k2')['memory_id']}
        self.assertEqual(len(ids), 3)
        self.assertEqual(p2.search('문장')['total_matched'], 1)
        self.assertEqual(self.p1.search('문장')['total_matched'], 2)
        self.assertEqual(len({mem.content_hash('같은 문장')}), 1)  # hash equal, ids differ

    def test_09_case_and_inner_whitespace_preserved(self):
        a = self.p1.add('Foo', 'decision', key='c'); b = self.p1.add('foo', 'decision', key='c')
        self.assertEqual(b['status'], 'conflict_candidate')
        self.assertNotEqual(a['memory_id'], b['memory_id'])
        c = self.p1.add('a  b', 'decision', key='w'); d = self.p1.add('a b', 'decision', key='w')
        self.assertEqual(d['status'], 'conflict_candidate')
        self.assertEqual(self.p1.show(memory_id=c['memory_id'])['text'], 'a  b')

    def test_10_resolve_three_way(self):
        a = self.p1.add('A', 'decision', key='k'); b = self.p1.add('B', 'decision', key='k'); c = self.p1.add('C', 'decision', key='k')
        self.assertEqual(b['conflict_id'], c['conflict_id'])
        r = self.p1.resolve(c['conflict_id'], b['memory_id'])
        self.assertEqual(sorted(r['superseded']), sorted([a['memory_id'], c['memory_id']]))
        for mid in (a['memory_id'], c['memory_id']):
            rev = self.p1.db.execute('SELECT superseded_by FROM revisions WHERE memory_id=?', (mid,)).fetchone()[0]
            self.assertEqual(rev, f"{b['memory_id']}:1")
        self.assertEqual(self.p1.db.execute('SELECT status FROM conflicts').fetchone()[0], 'resolved')

    def test_11_stale_update_rejected(self):
        a = self.p1.add('v1', 'decision', key='k')
        self.assertEqual(self.p1.update(a['memory_id'], 1, 'v2')['status'], 'updated')
        r = self.p1.update(a['memory_id'], 1, 'v3')
        self.assertEqual((r['status'], r['conflict'], r['current_rev']), ('stale_revision', True, 2))
        self.assertEqual(self.p1.show(memory_id=a['memory_id'])['text'], 'v2')
        self.assertEqual(self.rows('revisions'), 2)
        ops = [e['op'] for e in self.p1.audit_log()['entries']]
        self.assertIn('update_rejected', ops)

    def test_12_concurrent_duplicate_add(self):
        barrier = threading.Barrier(2)
        results, errors = [], []

        def worker():
            try:
                st = mem.Store(self.db, 'p1', 'codex')
                barrier.wait()
                results.append(st.add('동시 삽입', 'decision', key='race')['status'])
                st.db.close()
            except sqlite3.OperationalError as exc:
                errors.append(str(exc))
        ts = [threading.Thread(target=worker) for _ in range(2)]
        [t.start() for t in ts]; [t.join(timeout=15) for t in ts]
        self.assertEqual(self.rows('memories'), 1)
        self.assertEqual(results.count('created'), 1)
        self.assertEqual(len(results) + len(errors), 2)

    def test_13_budget_edges(self):
        self.p1.add('x' * 300, 'decision', key='big')
        r = self.p1.search('xxx', max_chars=1)
        self.assertEqual((r['returned'], r['results'][0]['truncated'], r['partial']), (1, True, True))
        with self.assertRaises(ValueError):
            self.p1.search('   ')
        for n in range(3):
            self.p1.add(f'예산 항목 {n}', 'decision', key=f'b{n}')
        r = self.p1.search('예산', limit=2)
        self.assertEqual((r['returned'], len(r['omitted_ids']), r['partial']), (2, 1, True))

    def test_14_every_command_is_project_scoped(self):
        a = self.p1.add('p1 전용', 'decision', key='k')
        p2 = self.store('p2')
        for call in (lambda: p2.show(memory_id=a['memory_id']), lambda: p2.update(a['memory_id'], 1, 'x'),
                     lambda: p2.retire(a['memory_id']), lambda: p2.delete(a['memory_id'], confirm=True)):
            with self.assertRaises(ValueError) as cm:
                call()
            self.assertIn('not_found_in_project', str(cm.exception))
        self.assertEqual(self.p1.show(memory_id=a['memory_id'])['status'], 'active')

    def test_15_bad_import_changes_nothing(self):
        f = Path(self.tmp.name) / 'in.jsonl'
        f.write_text(json.dumps({'project': 'p1', 'key': 'k', 'kind': 'decision', 'text': 'ok'}) + '\n'
                     + json.dumps({'project': 'p1', 'key': 'k2', 'kind': 'decision'}) + '\n'
                     + json.dumps({'project': 'p9', 'key': 'k3', 'kind': 'decision', 'text': 'wrong project'}) + '\n'
                     + 'not json\n', encoding='utf-8')
        r = self.p1.import_jsonl(str(f), apply=True)
        self.assertEqual((r['status'], r['valid_rows'], len(r['errors']), r['applied']), ('rejected_no_changes', 1, 3, 0))
        self.assertEqual(self.rows('memories'), 0)
        good = Path(self.tmp.name) / 'good.jsonl'
        good.write_text(json.dumps({'project': 'p1', 'key': 'k', 'kind': 'decision', 'text': 'ok', 'source_verified': True}) + '\n')
        self.assertEqual(self.p1.import_jsonl(str(good))['status'], 'dry_run')
        self.assertEqual(self.rows('memories'), 0)
        r = self.p1.import_jsonl(str(good), apply=True)
        self.assertEqual(r['applied'], 1)
        self.assertFalse(self.p1.show()['memories'][0]['source_verified'])

    def test_16_delete_excluded_and_audit_has_no_text(self):
        a = self.p1.add('삭제될 비밀 문장', 'decision', key='k')
        self.p1.delete(a['memory_id'], confirm=True)
        self.assertEqual(self.p1.search('비밀')['total_matched'], 0)
        out = Path(self.tmp.name) / 'e.jsonl'
        self.assertEqual(self.p1.export(str(out))['count'], 0)
        dump = json.dumps(self.p1.audit_log()['entries'], ensure_ascii=False)
        self.assertNotIn('비밀', dump)
        self.assertNotIn(mem.content_hash('삭제될 비밀 문장'), dump)
        self.assertEqual(self.rows('tombstones'), 1)

    def test_17_reimport_of_deleted_refused(self):
        a = self.p1.add('삭제 후 부활 시도', 'decision', key='k')
        out = Path(self.tmp.name) / 'old.jsonl'
        self.p1.export(str(out))
        self.p1.delete(a['memory_id'], confirm=True)
        r = self.p1.import_jsonl(str(out), apply=True)
        self.assertEqual((r['status'], r['applied']), ('rejected_no_changes', 0))
        self.assertIn('resurrect', r['errors'][0]['error'])
        self.assertEqual(self.rows('memories'), 0)
        r = self.p1.import_jsonl(str(out), apply=True, allow_resurrect=True)
        self.assertEqual(r['applied'], 1)
        self.assertEqual(self.p1.show(memory_id=a['memory_id'])['text'], '삭제 후 부활 시도')

    def test_export_refuses_overwrite_and_handoff_format(self):
        self.p1.add('핸드오프 확인', 'decision', key='k')
        out = Path(self.tmp.name) / 'h.md'
        r = self.p1.export(str(out), fmt='handoff')
        self.assertEqual(r['count'], 1)
        self.assertIn('대상: p1', out.read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):
            self.p1.export(str(out))

    def test_validation_rules(self):
        with self.assertRaises(ValueError): mem.Store(self.db, 'Bad Project', 'claude')
        with self.assertRaises(ValueError): self.p1.add('x', 'decision', key='Bad Key')
        with self.assertRaises(ValueError): self.p1.add('x' * 2001, 'decision', key='k')
        with self.assertRaises(ValueError): self.p1.add('x', 'wish', key='k')
        with self.assertRaises(ValueError): self.p1.add('   ', 'decision', key='k')
        r = self.p1.add('키 없이 저장', 'decision')
        self.assertTrue(r['key'].startswith('unclassified.') and r['key_provisional'])


if __name__ == '__main__':
    unittest.main()
