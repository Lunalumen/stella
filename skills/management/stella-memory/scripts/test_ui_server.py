"""Tests for the local management UI server. Synthetic data and a temporary DB only."""
import http.client
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ui_server', ROOT / 'ui_server.py')
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)


class ServerBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'ui.db'
        self.httpd, self.app = ui.make_server(self.db, port=0)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def raw(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        data = json.dumps(body).encode('utf-8') if isinstance(body, dict) else body
        conn.request(method, path, body=data, headers=headers or {})
        res = conn.getresponse()
        payload = res.read()
        conn.close()
        return res, payload

    def good_headers(self, **extra):
        h = {'Host': f'127.0.0.1:{self.port}', 'Content-Type': 'application/json', 'X-Stella-Token': self.app.token,
             'Origin': f'http://127.0.0.1:{self.port}', 'Sec-Fetch-Site': 'same-origin'}
        h.update(extra)
        return h

    def api(self, name, body=None, expect=200, **headers):
        res, payload = self.raw('POST', '/api/' + name, body or {}, self.good_headers(**headers))
        data = json.loads(payload.decode('utf-8'))
        self.assertEqual(res.status, expect, data)
        return data


class Security(ServerBase):
    def test_binds_loopback_only(self):
        self.assertEqual(self.httpd.server_address[0], '127.0.0.1')

    def test_page_carries_token_and_strict_headers(self):
        res, body = self.raw('GET', '/', headers={'Host': f'127.0.0.1:{self.port}'})
        self.assertEqual(res.status, 200)
        self.assertIn(self.app.token.encode(), body)
        self.assertNotIn(b'__STELLA_TOKEN__', body)
        csp = res.getheader('Content-Security-Policy')
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertEqual(res.getheader('X-Content-Type-Options'), 'nosniff')
        self.assertIsNone(res.getheader('Access-Control-Allow-Origin'))

    def test_api_refuses_requests_a_foreign_page_could_send(self):
        body = {'project': 'p1', 'text': '외부 요청', 'kind': 'decision', 'key': 'x'}
        cases = {
            'no token': self.good_headers(**{'X-Stella-Token': ''}),
            'wrong token': self.good_headers(**{'X-Stella-Token': 'guess'}),
            'foreign origin': self.good_headers(Origin='http://evil.example'),
            'cross-site fetch': self.good_headers(**{'Sec-Fetch-Site': 'cross-site'}),
            'dns rebinding host': self.good_headers(Host=f'evil.example:{self.port}'),
            'simple form post': self.good_headers(**{'Content-Type': 'text/plain'}),
        }
        for label, headers in cases.items():
            with self.subTest(label):
                res, payload = self.raw('POST', '/api/add', body, headers)
                self.assertIn(res.status, (403, 415), label)
                self.assertIsNone(res.getheader('Access-Control-Allow-Origin'))
        self.assertFalse(self.db.exists() and ui.mem.list_projects(self.db))

    def test_preflight_and_other_methods_refused(self):
        res, _ = self.raw('OPTIONS', '/api/add', headers={'Host': f'127.0.0.1:{self.port}', 'Origin': 'http://evil.example',
                                                          'Access-Control-Request-Method': 'POST'})
        self.assertEqual(res.status, 405)
        self.assertIsNone(res.getheader('Access-Control-Allow-Origin'))
        res, _ = self.raw('GET', '/api/info', headers={'Host': f'127.0.0.1:{self.port}'})
        self.assertEqual(res.status, 404)

    def test_static_page_refused_for_foreign_host(self):
        res, _ = self.raw('GET', '/', headers={'Host': 'evil.example'})
        self.assertEqual(res.status, 403)

    def test_errors_are_json_and_do_not_leak_internals(self):
        self.api('add', {'project': 'BAD NAME', 'text': 'x', 'kind': 'decision'}, expect=400)
        self.api('nope', {'project': 'p1'}, expect=404)
        res, payload = self.raw('POST', '/api/add', b'{not json', self.good_headers())
        self.assertEqual(res.status, 400)


class Flows(ServerBase):
    def test_info_reports_db_and_no_ai_connection(self):
        info = self.api('info')
        self.assertEqual(info['db'], str(self.db.resolve()))
        self.assertFalse(info['db_existed_at_start'])
        self.assertFalse(info['ai_connection']['connected'])

    def test_add_search_show_update(self):
        pre = self.api('add', {'project': 'p1', 'text': '  보고서는 1,000자 이내  ', 'kind': 'constraint', 'key': 'report.length', 'dry_run': True})
        self.assertEqual((pre['status'], pre['dry_run']), ('created', True))
        self.assertEqual(self.api('list', {'project': 'p1'})['count'], 0)
        a = self.api('add', {'project': 'p1', 'text': '  보고서는 1,000자 이내  ', 'kind': 'constraint', 'key': 'report.length'})
        s = self.api('search', {'project': 'p1', 'query': '보고서'})
        self.assertEqual((s['returned'], s['results'][0]['text']), (1, '보고서는 1,000자 이내'))
        d = self.api('show', {'project': 'p1', 'memory_id': a['memory_id']})
        self.assertEqual((d['rev'], len(d['revisions'])), (1, 1))
        prev = self.api('update', {'project': 'p1', 'memory_id': a['memory_id'], 'expect_rev': 1, 'text': '보고서는 1,500자 이내', 'dry_run': True})
        self.assertEqual((prev['previous_text'], prev['text']), ('보고서는 1,000자 이내', '보고서는 1,500자 이내'))
        u = self.api('update', {'project': 'p1', 'memory_id': a['memory_id'], 'expect_rev': 1, 'text': '보고서는 1,500자 이내'})
        self.assertEqual(u['rev'], 2)
        stale = self.api('update', {'project': 'p1', 'memory_id': a['memory_id'], 'expect_rev': 1, 'text': '덮어쓰기 시도'})
        self.assertEqual(stale['status'], 'stale_revision')
        d = self.api('show', {'project': 'p1', 'memory_id': a['memory_id']})
        self.assertEqual((d['text'], len(d['revisions'])), ('보고서는 1,500자 이내', 2))

    def test_projects_do_not_mix(self):
        a = self.api('add', {'project': 'p1', 'text': 'p1 전용 기억', 'kind': 'decision', 'key': 'k'})
        self.api('add', {'project': 'p2', 'text': 'p2 전용 기억', 'kind': 'decision', 'key': 'k'})
        self.assertEqual(self.api('projects')['projects'], ['p1', 'p2'])
        self.assertEqual(self.api('search', {'project': 'p2', 'query': 'p1'})['total_matched'], 0)
        for name, body in (('show', {}), ('retire', {}), ('delete', {'confirm': True}),
                           ('update', {'expect_rev': 1, 'text': '침범'})):
            with self.subTest(name):
                r = self.api(name, dict(body, project='p2', memory_id=a['memory_id']), expect=400)
                self.assertIn('not_found_in_project', r['error'])
        self.assertEqual(self.api('show', {'project': 'p1', 'memory_id': a['memory_id']})['status'], 'active')

    def test_conflict_listed_and_resolved_by_user_choice(self):
        a = self.api('add', {'project': 'p1', 'text': '마감은 금요일', 'kind': 'decision', 'key': 'deadline'})
        b = self.api('add', {'project': 'p1', 'text': '마감은 목요일', 'kind': 'decision', 'key': 'deadline'})
        self.assertEqual(b['status'], 'conflict_candidate')
        oc = self.api('conflicts', {'project': 'p1'})
        self.assertEqual(oc['count'], 1)
        self.assertEqual({m['status'] for m in oc['conflicts'][0]['members']}, {'conflict'})
        r = self.api('resolve', {'project': 'p1', 'conflict_id': b['conflict_id'], 'keep': a['memory_id'] + ':1'})
        self.assertEqual(r['kept'], a['memory_id'])  # the older one: no newest-wins rule
        self.assertEqual(self.api('conflicts', {'project': 'p1'})['count'], 0)
        self.assertEqual(self.api('show', {'project': 'p1', 'memory_id': b['memory_id']})['status'], 'superseded')

    def test_retire_vs_delete(self):
        a = self.api('add', {'project': 'p1', 'text': '보관할 기억', 'kind': 'decision', 'key': 'r'})
        b = self.api('add', {'project': 'p1', 'text': '지울 기억', 'kind': 'decision', 'key': 'd'})
        self.api('retire', {'project': 'p1', 'memory_id': a['memory_id']})
        self.assertEqual(self.api('show', {'project': 'p1', 'memory_id': a['memory_id']})['status'], 'retired')
        self.assertEqual(self.api('search', {'project': 'p1', 'query': '보관할'})['total_matched'], 0)
        r = self.api('delete', {'project': 'p1', 'memory_id': b['memory_id']}, expect=400)
        self.assertIn('--confirm', r['error'])
        r = self.api('delete', {'project': 'p1', 'memory_id': b['memory_id'], 'confirm': 'yes'}, expect=400)  # only literal true
        self.api('delete', {'project': 'p1', 'memory_id': b['memory_id'], 'confirm': True})
        self.api('show', {'project': 'p1', 'memory_id': b['memory_id']}, expect=400)
        audit = self.api('audit', {'project': 'p1'})
        self.assertNotIn('지울 기억', json.dumps(audit, ensure_ascii=False))

    def test_bad_import_changes_nothing_and_good_import_needs_matching_preview(self):
        self.api('add', {'project': 'p1', 'text': '기존', 'kind': 'decision', 'key': 'base'})
        before = self.api('list', {'project': 'p1', 'include_all': True})
        bad = '\n'.join([json.dumps({'project': 'p1', 'key': 'k1', 'kind': 'decision', 'text': 'A', 'memory_id': 'dup-id'}),
                         json.dumps({'project': 'p1', 'key': 'k2', 'kind': 'decision', 'text': 'B', 'memory_id': 'dup-id'}),
                         json.dumps({'project': 'p1', 'key': 'k3', 'kind': 'decision', 'text': 'C', 'source_note': 'n' * 501})])
        pre = self.api('import', {'project': 'p1', 'content': bad})
        self.assertEqual((pre['status'], pre['valid_rows'], len(pre['errors'])), ('dry_run', 1, 2))
        r = self.api('import', {'project': 'p1', 'content': bad, 'apply': True, 'expect_sha256': pre['sha256']})
        self.assertEqual((r['status'], r['applied']), ('rejected_no_changes', 0))
        self.assertEqual(self.api('list', {'project': 'p1', 'include_all': True}), before)
        good = json.dumps({'project': 'p1', 'key': 'k9', 'kind': 'decision', 'text': '가져온 기억', 'source_verified': True,
                           'requested_by': 'admin'}) + '\n'
        pre = self.api('import', {'project': 'p1', 'content': good})
        self.api('import', {'project': 'p1', 'content': good + '\n', 'apply': True, 'expect_sha256': pre['sha256']}, expect=409)
        r = self.api('import', {'project': 'p1', 'content': good, 'apply': True, 'expect_sha256': pre['sha256']})
        self.assertEqual(r['applied'], 1)
        m = self.api('show', {'project': 'p1', 'memory_id': r['results'][0]['memory_id']})
        self.assertFalse(m['source_verified'])  # file claims are not trusted
        self.assertEqual(m['requested_by'], 'user')

    def test_export_returns_content_without_leaving_files(self):
        self.api('add', {'project': 'p1', 'text': '<script>alert(1)</script> 그대로 저장되는 텍스트', 'kind': 'decision', 'key': 'x'})
        r = self.api('export', {'project': 'p1', 'format': 'jsonl'})
        self.assertEqual(r['count'], 1)
        self.assertIsNone(r['path'])
        self.assertIn('<script>alert(1)</script>', json.loads(r['content'].splitlines()[0])['text'])
        self.assertTrue(r['filename'].endswith('.jsonl'))
        h = self.api('export', {'project': 'p1', 'format': 'handoff'})
        self.assertTrue(h['filename'].endswith('.md'))
        self.assertEqual(sorted(p.name for p in Path(self.tmp.name).iterdir() if not p.name.startswith('ui.db')), [])

    def test_source_note_and_response_limits_over_api(self):
        r = self.api('add', {'project': 'p1', 'text': '경계', 'kind': 'decision', 'key': 's', 'source_note': 'n' * 501}, expect=400)
        self.assertIn('not truncated', r['error'])
        self.api('add', {'project': 'p1', 'text': '경계', 'kind': 'decision', 'key': 's', 'source_note': 'n' * 500})
        for n in range(40):
            self.api('add', {'project': 'p1', 'text': f'대량 {n} ' + 'q' * 300, 'kind': 'decision', 'key': f'bulk{n:02d}'})
        s = self.api('search', {'project': 'p1', 'query': '대량', 'max_response_chars': 3000})
        self.assertLessEqual(s['response_chars'], 3000)
        self.assertEqual(s['returned'] + s['omitted_count'], 40)
        self.assertIsNotNone(s['next_offset'])


if __name__ == '__main__':
    unittest.main()
