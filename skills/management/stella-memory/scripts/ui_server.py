"""Stella Memory local management UI server.

Standard library only. Binds 127.0.0.1 (this PC only). Every data operation calls memory.Store; this file holds
no storage or conflict logic of its own. Defenses against other web pages driving the API:
  * per-start random token, required in the X-Stella-Token header (other origins cannot read the page to get it)
  * Host header must be 127.0.0.1:<port> or localhost:<port> (DNS rebinding)
  * Origin / Sec-Fetch-Site, when sent, must be this server's own origin
  * API is POST + application/json only; no CORS headers are ever sent
Memory text and imported files are untrusted data: the page renders them with textContent only, under a strict CSP.

Usage: python ui_server.py --db <path to .db> [--port 8765] [--actor user]
"""
import argparse
import hashlib
import hmac
import importlib.util
import json
import secrets
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('stella_memory', HERE / 'memory.py')
mem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mem)

UI_DIR = HERE / 'ui'
STATIC = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
          '/app.css': ('app.css', 'text/css; charset=utf-8')}
MAX_BODY = 7_000_000  # import files are capped at 5 MB by memory.py; JSON wrapping adds some
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; "
       "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _req(body, name, typ=str, required=True, default=None):
    value = body.get(name, default)
    if value is None:
        if required:
            raise ApiError(400, f'{name} is required')
        return default
    if typ is int and isinstance(value, bool) or not isinstance(value, typ):
        raise ApiError(400, f'{name} must be {typ.__name__}')
    return value


class App:
    """Maps API names to memory.Store calls. One Store (one connection) per request."""

    def __init__(self, db_path, actor='user'):
        self.db_path = str(Path(db_path).resolve())
        self.db_existed = Path(self.db_path).is_file()
        self.actor = mem.check_name(actor, 'actor')
        self.token = secrets.token_urlsafe(32)

    def store(self, body):
        return mem.Store(self.db_path, _req(body, 'project'), self.actor)

    def call(self, name, body):
        if name == 'info':
            return {'db': self.db_path, 'db_existed_at_start': self.db_existed, 'db_exists_now': Path(self.db_path).is_file(),
                    'actor': self.actor, 'projects': mem.list_projects(self.db_path),
                    'limits': {'text': mem.TEXT_MAX, 'source_note': mem.SOURCE_NOTE_MAX, 'response': mem.RESPONSE_MAX},
                    'kinds': list(mem.KINDS),
                    'ai_connection': {'connected': False,
                                      'note': 'ChatGPT·Claude 자동 연결은 아직 없습니다. 이 화면은 사용자가 직접 관리하는 용도입니다.'}}
        if name == 'projects':
            return {'projects': mem.list_projects(self.db_path)}
        handler = getattr(self, 'api_' + name, None)
        if handler is None:
            raise ApiError(404, 'unknown api')
        st = self.store(body)
        try:
            return handler(st, body)
        finally:
            st.close()

    # --- reads ---------------------------------------------------------
    def api_list(self, st, b):
        return st.show(include_all=bool(b.get('include_all')))

    def api_search(self, st, b):
        return st.search(_req(b, 'query'), limit=_req(b, 'limit', int, False, 20), max_chars=_req(b, 'max_chars', int, False, 4000),
                         include_global=bool(b.get('include_global')), offset=_req(b, 'offset', int, False, 0),
                         max_response_chars=_req(b, 'max_response_chars', int, False, 20000))

    def api_show(self, st, b):
        return st.show(memory_id=_req(b, 'memory_id'), include_all=True)

    def api_conflict(self, st, b):
        return st.show(conflict_id=_req(b, 'conflict_id'))

    def api_conflicts(self, st, b):
        return st.open_conflicts()

    def api_audit(self, st, b):
        return st.audit_log(_req(b, 'limit', int, False, 100))

    # --- writes (each is one memory.Store call) --------------------------
    def api_add(self, st, b):
        return st.add(_req(b, 'text'), _req(b, 'kind'), key=_req(b, 'key', str, False) or None, requested_by='user',
                      source_note=_req(b, 'source_note', str, False, ''), reactivate=bool(b.get('reactivate')),
                      dry_run=bool(b.get('dry_run')))

    def api_update(self, st, b):
        return st.update(_req(b, 'memory_id'), _req(b, 'expect_rev', int), _req(b, 'text'), kind=_req(b, 'kind', str, False) or None,
                         requested_by='user', source_note=_req(b, 'source_note', str, False, ''), dry_run=bool(b.get('dry_run')))

    def api_resolve(self, st, b):
        return st.resolve(_req(b, 'conflict_id'), _req(b, 'keep'), resolved_by='user')

    def api_retire(self, st, b):
        return st.retire(_req(b, 'memory_id'))

    def api_delete(self, st, b):
        return st.delete(_req(b, 'memory_id'), confirm=b.get('confirm') is True)

    def api_import(self, st, b):
        content = _req(b, 'content')
        digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
        apply = b.get('apply') is True
        if apply and b.get('expect_sha256') != digest:
            raise ApiError(409, '미리보기 이후 파일 내용이 바뀌었습니다. 다시 미리보기 하세요.')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'import.jsonl'
            path.write_text(content, encoding='utf-8')
            result = st.import_jsonl(str(path), apply=apply, requested_by='user')
        result['sha256'] = digest
        return result

    def api_export(self, st, b):
        fmt = _req(b, 'format', str, False, 'jsonl')
        if fmt not in ('jsonl', 'handoff'):
            raise ApiError(400, 'format must be jsonl or handoff')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'export.txt'
            result = st.export(str(out), fmt, include_retired=bool(b.get('include_retired')))
            content = out.read_text(encoding='utf-8')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        result.update(path=None, content=content, filename=f"stella-{st.project}-{stamp}.{'jsonl' if fmt == 'jsonl' else 'md'}")
        return result


class Handler(BaseHTTPRequestHandler):
    server_version = 'StellaMemoryUI'
    sys_version = ''
    app: App = None  # set by make_server

    def log_message(self, fmt, *args):  # no request logging (paths carry no data, but keep the console quiet)
        pass

    def _send(self, status, body, ctype='application/json; charset=utf-8'):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.end_headers()
        self.wfile.write(data)

    def _allowed_hosts(self):
        port = self.server.server_address[1]
        return {f'127.0.0.1:{port}', f'localhost:{port}'}

    def _check_host(self):
        if self.headers.get('Host', '') not in self._allowed_hosts():
            raise ApiError(403, 'host not allowed')

    def _check_api_request(self):
        self._check_host()
        origin = self.headers.get('Origin')
        if origin is not None and origin not in {f'http://{h}' for h in self._allowed_hosts()}:
            raise ApiError(403, 'cross-origin request refused')
        site = self.headers.get('Sec-Fetch-Site')
        if site is not None and site != 'same-origin':
            raise ApiError(403, 'cross-site request refused')
        if not hmac.compare_digest(self.headers.get('X-Stella-Token', ''), self.app.token):
            raise ApiError(403, 'missing or wrong token')
        if not self.headers.get('Content-Type', '').split(';')[0].strip().lower() == 'application/json':
            raise ApiError(415, 'application/json required')

    def do_GET(self):
        try:
            self._check_host()
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise ApiError(403, 'cross-site request refused')
            entry = STATIC.get(self.path.split('?')[0])
            if entry is None:
                raise ApiError(404, 'not found')
            data = (UI_DIR / entry[0]).read_bytes()
            if entry[0] == 'index.html':
                data = data.replace(b'__STELLA_TOKEN__', self.app.token.encode('ascii'))
            self._send(200, data, entry[1])
        except ApiError as e:
            self._send(e.status, {'error': str(e)})

    def do_POST(self):
        try:
            if not self.path.startswith('/api/'):
                raise ApiError(404, 'not found')
            self._check_api_request()
            length = int(self.headers.get('Content-Length') or 0)
            if length <= 0 or length > MAX_BODY:
                raise ApiError(413, 'request body missing or too large')
            try:
                body = json.loads(self.rfile.read(length).decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ApiError(400, 'invalid JSON')
            if not isinstance(body, dict):
                raise ApiError(400, 'JSON object required')
            result = self.app.call(self.path[len('/api/'):], body)
            self._send(200, result)
        except ApiError as e:
            self._send(e.status, {'error': str(e)})
        except ValueError as e:
            self._send(400, {'error': str(e)})
        except sqlite3.OperationalError as e:
            self._send(409, {'error': f'database busy or unavailable: {e}'})
        except Exception as e:  # noqa: BLE001
            self._send(500, {'error': f'internal error: {type(e).__name__}'})

    def _refuse(self):
        self._send(405, {'error': 'method not allowed'})

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _refuse


def make_server(db_path, port=8765, actor='user'):
    app = App(db_path, actor)
    handler = type('BoundHandler', (Handler,), {'app': app})
    httpd = ThreadingHTTPServer(('127.0.0.1', port), handler)  # loopback only; there is no option to change this
    httpd.daemon_threads = True
    return httpd, app


def main(argv=None):
    p = argparse.ArgumentParser(description='Stella Memory local management UI (127.0.0.1 only)')
    p.add_argument('--db', required=True, help='SQLite file to manage (created on the first UI request if missing)')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--actor', default='user')
    args = p.parse_args(argv)
    httpd, app = make_server(args.db, args.port, args.actor)
    port = httpd.server_address[1]
    print(f'Stella Memory 관리 화면: http://127.0.0.1:{port}/', flush=True)
    print(f'DB: {app.db_path} ({"기존 파일" if app.db_existed else "아직 없음 - 화면에서 첫 작업을 할 때 생성"})', flush=True)
    print('종료: Ctrl+C', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    sys.exit(main())
