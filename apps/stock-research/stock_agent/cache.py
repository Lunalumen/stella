import hashlib
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TTL = {'quote': 900, 'news': 1800, 'disclosures': 900, 'registry': 604800,
       'facts': 86400, 'report': 2592000, 'ir': 21600}
ALLOWED = {'www.sec.gov', 'data.sec.gov', 'opendart.fss.or.kr', 'dart.fss.or.kr',
           'kind.krx.co.kr', 'query1.finance.yahoo.com', 'query2.finance.yahoo.com',
           'www.samsung.com', 'images.samsung.com', 'news.samsung.com',
           'investor.apple.com', 'www.apple.com', 'www.microsoft.com',
           'ir.tesla.com', 'ir.spacex.com'}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def encoded(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def validate_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.hostname not in ALLOWED or p.username or p.password or p.port not in (None, 443):
        raise ValueError('허용되지 않은 자료 URL')
    return url

def safe_url(url):
    p = urllib.parse.urlsplit(url)
    q = [(k, '[REDACTED]' if any(s in k.lower() for s in ('key', 'token', 'secret', 'password')) else v)
         for k, v in urllib.parse.parse_qsl(p.query)]
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), ''))

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        if urllib.parse.urlsplit(newurl).hostname != urllib.parse.urlsplit(req.full_url).hostname:
            raise ValueError('외부 호스트 리디렉션 차단')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class Store:
    def __init__(self, root, transport=None, clock=time.time):
        self.root, self.clock, self.transport = Path(root), clock, transport
        self.root.mkdir(parents=True, exist_ok=True)
        for part in ('raw', 'extracted', 'summaries', 'analyses', 'runs', 'packets'):
            (self.root / part).mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / 'index.sqlite')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''CREATE TABLE IF NOT EXISTS resources (
          key TEXT PRIMARY KEY,url TEXT,kind TEXT,hash TEXT,checked REAL,etag TEXT,modified TEXT,content_type TEXT);
          CREATE TABLE IF NOT EXISTS artifacts (key TEXT PRIMARY KEY,value TEXT);
          CREATE TABLE IF NOT EXISTS versions (key TEXT,hash TEXT,observed REAL,PRIMARY KEY(key,hash));''')
        self.stats = dict(external_requests=0, cache_hits=0, not_modified=0, changed_resources=0,
                          extractions=0, model_calls=0, input_tokens=None, output_tokens=None)

    def close(self):
        self.db.close()

    def artifact(self, key, value=None):
        if value is None:
            r = self.db.execute('SELECT value FROM artifacts WHERE key=?', (key,)).fetchone()
            return json.loads(r[0]) if r else None
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO artifacts VALUES (?,?)', (key, json.dumps(value, ensure_ascii=False)))
        return value

    def write(self, part, name, value):
        path = self.root / part / name
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_bytes(encoded(value))
        os.replace(tmp, path)
        return path

    def fetch(self, url, kind, *, force=False, headers=None, identity=None):
        validate_url(url)
        # Credential-bearing URLs are neither persisted nor used as cache identities.
        public = safe_url(url)
        key = digest((identity or public).encode())
        old = self.db.execute('SELECT * FROM resources WHERE key=?', (key,)).fetchone()
        now = self.clock()
        if old and not force and now - old['checked'] < TTL[kind]:
            self.stats['cache_hits'] += 1
            return self._result(old, True)
        request_headers = {'User-Agent': 'MyeongwolResearch/1.0', 'Accept': '*/*', **(headers or {})}
        if old:
            if old['etag']: request_headers['If-None-Match'] = old['etag']
            if old['modified']: request_headers['If-Modified-Since'] = old['modified']
        self.stats['external_requests'] += 1
        if self.transport:
            status, data, response_headers = self.transport(url, request_headers)
        else:
            try:
                with urllib.request.build_opener(SafeRedirect()).open(
                        urllib.request.Request(url, headers=request_headers), timeout=25) as r:
                    status, data, response_headers = r.status, r.read(32_000_001), dict(r.headers)
            except urllib.error.HTTPError as e:
                if e.code != 304:
                    raise ValueError(f'자료 접근 실패 HTTP {e.code}: {public}') from None
                status, data, response_headers = 304, b'', {}
            except (OSError, urllib.error.URLError):
                raise ValueError('자료 네트워크 접근 실패: ' + public) from None
        if status == 304 and old:
            with self.db: self.db.execute('UPDATE resources SET checked=? WHERE key=?', (now, key))
            self.stats['not_modified'] += 1
        elif status == 200:
            if len(data) > 32_000_000: raise ValueError('자료 크기 제한 초과')
            sha = digest(data)
            path = self.root / 'raw' / (sha + '.bin')
            if not path.exists(): path.write_bytes(data)
            h = {k.lower(): v for k, v in response_headers.items()}
            if not old or old['hash'] != sha: self.stats['changed_resources'] += 1
            with self.db:
                self.db.execute('INSERT OR REPLACE INTO resources VALUES (?,?,?,?,?,?,?,?)',
                                (key, public, kind, sha, now, h.get('etag', ''), h.get('last-modified', ''), h.get('content-type', '')))
                self.db.execute('INSERT OR IGNORE INTO versions VALUES (?,?,?)', (key, sha, now))
        else:
            raise ValueError('자료 HTTP 응답 오류')
        row = self.db.execute('SELECT * FROM resources WHERE key=?', (key,)).fetchone()
        return self._result(row, False)

    def _result(self, row, cached):
        return {**dict(row), 'cached': cached, 'body': (self.root / 'raw' / (row['hash'] + '.bin')).read_bytes()}
