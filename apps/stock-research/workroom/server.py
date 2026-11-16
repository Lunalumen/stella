"""Personal loopback UI only. No broker, proxy, upload or research-file routes."""
import argparse
import base64
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import secrets
import threading
import time
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ASSETS = {'/': 'index.html', '/index.html': 'index.html', '/style.css': 'style.css',
          '/app.js': 'app.js', '/market.js': 'market.js', '/chart.html': 'chart.html', '/lock.js':'lock.js',
          '/cafe-theme.css': 'cafe-theme.css'}
PUBLIC = {'/unlock': 'unlock.html', '/unlock.js': 'unlock.js'}
MIME = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.png': 'image/png'}
SESSION_SECONDS = 8 * 60 * 60

def protect_current_user(value):
    """DPAPI CurrentUser, without CRYPTPROTECT_LOCAL_MACHINE or plaintext files."""
    if os.name != 'nt':
        raise RuntimeError('Windows DPAPI required for a persistent launch key')
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buf = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    source, output = Blob(len(value), buf), Blob()
    crypt32, kernel32 = ctypes.WinDLL('crypt32', use_last_error=True), ctypes.WinDLL('kernel32', use_last_error=True)
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    if not crypt32.CryptProtectData(ctypes.byref(source), 'Moon Lab launch key', None, None, None, 1, ctypes.byref(output)):
        raise OSError('DPAPI encryption failed')
    try:
        return base64.b64encode(ctypes.string_at(output.data, output.size)).decode('ascii')
    finally:
        kernel32.LocalFree(output.data)

class PrivateServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    def __init__(self, port=8767, root=ROOT):
        super().__init__(('127.0.0.1', port), Handler)
        self.root = Path(root).resolve()
        self.origin = f'http://127.0.0.1:{self.server_port}'
        self.key = secrets.token_urlsafe(32)
        self.cookie_name = f'moonlab_{self.server_port}'
        self.sessions = {}
        self.failures = []
        self.auth_lock = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    server_version = 'MoonLab'
    sys_version = ''
    def log_message(self, *_):
        pass  # Do not record URLs, credentials, cookies or request bodies.

    def reply(self, code, body=b'', content_type='text/plain; charset=utf-8', cookie=None, public=False, chart=False):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        # The separate chart page needs the vendor script; the workroom does not.
        script_sources = "'self'"
        if chart:
            inline = self.server.root.joinpath('chart.html').read_text('utf-8').split('<script>', 1)[1].split('</script>', 1)[0]
            script_sources += " https://s3.tradingview.com 'sha256-" + base64.b64encode(hashlib.sha256(inline.encode()).digest()).decode() + "'"
        self.send_header('Content-Security-Policy', f"default-src 'none'; script-src {script_sources}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-src 'self' https://www.tradingview-widget.com; frame-ancestors 'self'; base-uri 'none'; form-action 'self'; object-src 'none'")
        self.send_header('X-Frame-Options', 'DENY' if public else 'SAMEORIGIN')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def valid_request(self):
        if self.client_address[0] != '127.0.0.1' or self.headers.get_all('Host') != [urlsplit(self.server.origin).netloc]:
            self.reply(403, b'Forbidden host'); return False
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.reply(403, b'Cross-site request blocked'); return False
        return True

    def session(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookies.get(self.server.cookie_name)
            key = token.value if token else ''
        except CookieError:
            return ''
        with self.server.auth_lock:
            if self.server.sessions.get(key, 0) > time.monotonic():
                return key
            self.server.sessions.pop(key, None)
        return ''

    def do_GET(self):
        if not self.valid_request(): return
        path = urlsplit(self.path).path
        if path in PUBLIC:
            self.asset(PUBLIC[path], public=True); return
        if path not in ASSETS:
            self.reply(404, b'Not found'); return
        if not self.session():
            if path in ('/', '/index.html'):
                self.asset('unlock.html', public=True)
            else:
                self.reply(401, b'Open this app with workroom/open.ps1')
            return
        self.asset(ASSETS[path], chart=path == '/chart.html')

    do_HEAD = do_GET

    def asset(self, name, **kwargs):
        target = self.server.root / name
        if target.is_symlink() or target.resolve().parent != self.server.root or not target.is_file():
            self.reply(404, b'Not found'); return
        self.reply(200, target.read_bytes(), MIME.get(target.suffix, 'application/octet-stream'), **kwargs)

    def do_POST(self):
        if not self.valid_request(): return
        if self.headers.get('Origin') != self.server.origin:
            self.reply(403, b'Forbidden origin'); return
        path = urlsplit(self.path).path
        if path not in ('/session', '/logout'):
            self.reply(404, b'Not found'); return
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type') != 'application/json':
            self.reply(400, b'JSON required'); return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 512: raise ValueError()
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict): raise ValueError()
        except (ValueError, json.JSONDecodeError):
            self.reply(400, b'Invalid request'); return
        if path == '/logout':
            token = self.session()
            with self.server.auth_lock: self.server.sessions.pop(token, None)
            self.reply(204, cookie=f'{self.server.cookie_name}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'); return
        now = time.monotonic()
        with self.server.auth_lock:
            self.server.failures = [t for t in self.server.failures if now-t < 60]
            if len(self.server.failures) >= 10:
                self.reply(429, b'Try again in one minute'); return
            key = data.get('key')
            if not isinstance(key, str) or not key.isascii() or not secrets.compare_digest(key, self.server.key):
                self.server.failures.append(now)
                self.reply(401, b'Invalid launch key'); return
            self.server.sessions = {k:v for k,v in self.server.sessions.items() if v > now}
            if len(self.server.sessions) >= 16: self.server.sessions.pop(next(iter(self.server.sessions)))
            token = secrets.token_urlsafe(32)
            self.server.sessions[token] = now + SESSION_SECONDS
        self.reply(204, cookie=f'{self.server.cookie_name}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}')

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--state', type=Path, default=ROOT.parent/'private'/'workroom-access.json')
    args = parser.parse_args()
    with PrivateServer(args.port) as server:
        state = dict(url=server.origin, pid=os.getpid(), encrypted_key=protect_current_user(server.key.encode()))
        args.state.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.state.with_suffix('.tmp')
        tmp.write_text(json.dumps(state), encoding='utf-8')
        tmp.replace(args.state)
        print(f'MOON LAB private: {server.origin} (open with workroom/open.ps1)', flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
        finally:
            try:
                if json.loads(args.state.read_text('utf-8')).get('pid') == os.getpid(): args.state.unlink()
            except (OSError, ValueError): pass

if __name__ == '__main__': main()
