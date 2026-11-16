"""Stella Memory: local SQLite store of user-requested memories shared by ChatGPT and Claude.

Standard library only. Every command is scoped to --project. Writes are single BEGIN IMMEDIATE
transactions with a finite busy timeout and no retry loop. Deletion is logical for search/export
purposes; the audit table never stores memory text or content hashes.
Korean whitespace-tolerant matching (study_pattern) follows skills/sources/study-cache/scripts/study_cache.py.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]{0,63}$')
KINDS = ('preference', 'constraint', 'decision', 'open_question')
STATUSES = ('active', 'superseded', 'conflict', 'retired')
TEXT_MAX = 2000
SOURCE_NOTE_MAX = 500
RESPONSE_MAX = 4000  # whole search response, compact JSON characters
RESPONSE_MIN = 1200
SCHEMA = '''
CREATE TABLE IF NOT EXISTS memories(
  memory_id TEXT PRIMARY KEY, project TEXT NOT NULL, key TEXT NOT NULL, key_provisional INTEGER NOT NULL DEFAULT 0,
  kind TEXT NOT NULL CHECK(kind IN ('preference','constraint','decision','open_question')),
  status TEXT NOT NULL CHECK(status IN ('active','superseded','conflict','retired')),
  created TEXT NOT NULL, current_rev INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS memories_scope ON memories(project, key, status);
CREATE TABLE IF NOT EXISTS revisions(
  memory_id TEXT NOT NULL, rev INTEGER NOT NULL, text TEXT NOT NULL, content_hash TEXT NOT NULL,
  actor TEXT NOT NULL, requested_by TEXT NOT NULL, source_note TEXT NOT NULL DEFAULT '',
  source_verified INTEGER NOT NULL DEFAULT 0, created TEXT NOT NULL, superseded_by TEXT,
  PRIMARY KEY(memory_id, rev));
CREATE TABLE IF NOT EXISTS conflicts(
  conflict_id TEXT PRIMARY KEY, project TEXT NOT NULL, key TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('open','resolved','dissolved')),
  resolved_memory TEXT, resolved_rev INTEGER, resolved_by TEXT, resolved_at TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS conflict_members(
  conflict_id TEXT NOT NULL, memory_id TEXT NOT NULL, rev INTEGER NOT NULL, PRIMARY KEY(conflict_id, memory_id));
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT, op TEXT NOT NULL, memory_id TEXT, project TEXT NOT NULL,
  key TEXT, revs INTEGER, actor TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tombstones(memory_id TEXT PRIMARY KEY, project TEXT NOT NULL, deleted_at TEXT NOT NULL);
'''


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def normalize(text):
    """Conservative: NFC + strip ends only. Case and inner whitespace are preserved."""
    return unicodedata.normalize('NFC', text).strip()


def content_hash(text):
    return hashlib.sha256(normalize(text).encode('utf-8')).hexdigest()


def check_name(value, what):
    if not isinstance(value, str) or not NAME_RE.match(value):
        raise ValueError(f'{what} must match {NAME_RE.pattern}')
    return value


def check_text(text):
    if not isinstance(text, str) or not normalize(text):
        raise ValueError('text must be a nonempty string')
    if len(text) > TEXT_MAX:
        raise ValueError(f'text exceeds {TEXT_MAX} characters')
    return normalize(text)


def check_source_note(note):
    """Same limit on add/update/import. Over-limit notes are rejected, never silently cut."""
    if note is None:
        return ''
    if not isinstance(note, str):
        raise ValueError('source_note must be a string')
    if len(note) > SOURCE_NOTE_MAX:
        raise ValueError(f'source_note is {len(note)} characters; limit is {SOURCE_NOTE_MAX} (not truncated, shorten it)')
    return note


def list_projects(path):
    """Read-only list of project names present in a DB file (for the local UI). Missing file -> []."""
    path = Path(path)
    if not path.is_file():
        return []
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5.0)
    try:
        names = set()
        for table in ('memories', 'conflicts', 'audit'):
            try:
                names.update(r[0] for r in db.execute(f'SELECT DISTINCT project FROM {table}'))
            except sqlite3.OperationalError:
                pass
        return sorted(names)
    finally:
        db.close()


def check_kind(kind):
    if kind not in KINDS:
        raise ValueError(f'kind must be one of {KINDS}')
    return kind


def study_pattern(term):
    # From study_cache.py: Hangul terms ignore internal spacing; other terms match literally.
    return r'\s*'.join(re.escape(ch) for ch in term) if re.fullmatch(r'[가-힣]+', term) else re.escape(term)


class Store:
    def __init__(self, path, project, actor):
        self.project = check_name(project, 'project')
        self.actor = check_name(actor, 'actor')
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5.0, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.executescript(SCHEMA)

    # --- helpers -------------------------------------------------------
    def close(self):
        self.db.close()

    def _begin(self):
        self.db.execute('BEGIN IMMEDIATE')

    def _audit(self, op, memory_id=None, key=None, revs=None):
        self.db.execute('INSERT INTO audit(op,memory_id,project,key,revs,actor,at) VALUES(?,?,?,?,?,?,?)',
                        (op, memory_id, self.project, key, revs, self.actor, now()))

    def _memory(self, memory_id):
        row = self.db.execute('SELECT * FROM memories WHERE memory_id=? AND project=?', (memory_id, self.project)).fetchone()
        if row is None:
            raise ValueError('not_found_in_project')
        return row

    def _current(self, memory_id):
        return self.db.execute('SELECT r.* FROM revisions r JOIN memories m ON m.memory_id=r.memory_id AND m.current_rev=r.rev '
                               'WHERE r.memory_id=?', (memory_id,)).fetchone()

    def _open_conflict(self, key):
        return self.db.execute("SELECT * FROM conflicts WHERE project=? AND key=? AND status='open'", (self.project, key)).fetchone()

    def _conflict_of(self, memory_id):
        return self.db.execute("SELECT c.* FROM conflicts c JOIN conflict_members cm ON cm.conflict_id=c.conflict_id "
                               "WHERE cm.memory_id=? AND c.status='open'", (memory_id,)).fetchone()

    def _record(self, memory, rev=None):
        rev = rev or self._current(memory['memory_id'])
        conflict = self._conflict_of(memory['memory_id'])
        return {'memory_id': memory['memory_id'], 'project': memory['project'], 'key': memory['key'],
                'key_provisional': bool(memory['key_provisional']), 'kind': memory['kind'], 'status': memory['status'],
                'rev': rev['rev'], 'text': rev['text'], 'actor': rev['actor'], 'requested_by': rev['requested_by'],
                'source_note': rev['source_note'], 'source_verified': bool(rev['source_verified']),
                'created': memory['created'], 'updated': rev['created'],
                'conflict_id': conflict['conflict_id'] if conflict else None}

    # --- commands ------------------------------------------------------
    def _join_conflict(self, key, mid, rev, live, ts):
        """Put `mid` and every live peer of the same (project, key) into the open conflict group (create one if needed)."""
        conflict = self._open_conflict(key)
        cid = conflict['conflict_id'] if conflict else str(uuid.uuid4())
        if not conflict:
            self.db.execute("INSERT INTO conflicts(conflict_id,project,key,status,created) VALUES(?,?,?,'open',?)",
                            (cid, self.project, key, ts))
        for p in live:
            self.db.execute('INSERT OR IGNORE INTO conflict_members VALUES(?,?,?)', (cid, p['memory_id'], p['current_rev']))
            self.db.execute("UPDATE memories SET status='conflict' WHERE memory_id=?", (p['memory_id'],))
        self.db.execute('INSERT OR IGNORE INTO conflict_members VALUES(?,?,?)', (cid, mid, rev))
        self.db.execute("UPDATE memories SET status='conflict' WHERE memory_id=?", (mid,))
        self._audit('conflict_candidate', mid, key, rev)
        members = self.db.execute('SELECT COUNT(*) FROM conflict_members WHERE conflict_id=?', (cid,)).fetchone()[0]
        return {'conflict_id': cid, 'candidates': members, 'note': 'same key holds different content; user decides via resolve'}

    def _add_in_tx(self, text, kind, key=None, requested_by='user', source_note='', reactivate=False, allow_resurrect=False,
                   memory_id=None):
        """Body of add(); the caller owns the transaction (used by add and by import's single transaction)."""
        text = check_text(text)
        check_kind(kind)
        check_name(requested_by, 'requested_by')
        source_note = check_source_note(source_note)
        h = content_hash(text)
        provisional = key is None
        mid = memory_id or str(uuid.uuid4())
        if memory_id:
            check_name(memory_id.replace('-', ''), 'memory_id')
            if self.db.execute('SELECT 1 FROM memories WHERE memory_id=?', (mid,)).fetchone():
                raise ValueError('memory_id_exists; import cannot create a memory under an existing id (use update)')
        key = f'unclassified.{mid[:8]}' if provisional else check_name(key, 'key')
        if self.db.execute('SELECT 1 FROM tombstones WHERE memory_id=?', (mid,)).fetchone() and not allow_resurrect:
            raise ValueError('memory_id_deleted; pass --allow-resurrect to reinstate')
        peers = self.db.execute("SELECT m.*, r.content_hash, r.text AS cur_text FROM memories m JOIN revisions r "
                                "ON r.memory_id=m.memory_id AND r.rev=m.current_rev "
                                "WHERE m.project=? AND m.key=? AND m.status!='superseded'", (self.project, key)).fetchall()
        # Hash equality alone is not identity: confirm the normalized text too (review-chatgpt-2 hash-injection note).
        same = [p for p in peers if p['content_hash'] == h and normalize(p['cur_text']) == text]
        live = [p for p in peers if p['status'] in ('active', 'conflict')]
        ts = now()
        if same:
            peer = same[0]
            if peer['status'] != 'retired':
                return {'status': 'unchanged', 'memory_id': peer['memory_id'], 'key': key}
            if not reactivate:
                return {'status': 'retired_exists', 'memory_id': peer['memory_id'], 'key': key}
            self.db.execute("UPDATE memories SET status='active' WHERE memory_id=?", (peer['memory_id'],))
            self._audit('reactivate', peer['memory_id'], key, peer['current_rev'])
            result = {'status': 'reactivated', 'memory_id': peer['memory_id'], 'key': key, 'rev': peer['current_rev']}
            if live and not provisional:  # R2: a reactivated memory must face the same conflict check as a new one
                result.update(self._join_conflict(key, peer['memory_id'], peer['current_rev'], live, ts))
                result['status'] = 'reactivated_conflict_candidate'
            return result
        self.db.execute('INSERT INTO memories VALUES(?,?,?,?,?,?,?,?)',
                        (mid, self.project, key, int(provisional), kind, 'active', ts, 1))
        self.db.execute('INSERT INTO revisions(memory_id,rev,text,content_hash,actor,requested_by,source_note,source_verified,created) '
                        'VALUES(?,?,?,?,?,?,?,?,?)', (mid, 1, text, h, self.actor, requested_by, source_note, 0, ts))
        self._audit('add', mid, key, 1)
        result = {'status': 'created', 'memory_id': mid, 'key': key, 'key_provisional': provisional, 'rev': 1}
        if live and not provisional:
            result.update(self._join_conflict(key, mid, 1, live, ts))
            result['status'] = 'conflict_candidate'
        return result

    def add(self, *args, dry_run=False, **kwargs):
        """dry_run runs the real add logic and rolls back, so a preview shows exactly what saving would do."""
        self._begin()
        try:
            result = self._add_in_tx(*args, **kwargs)
            if dry_run:
                self.db.execute('ROLLBACK')
                result['dry_run'] = True
                if result['status'] in ('created', 'conflict_candidate'):
                    result['note_dry_run'] = 'nothing saved; memory_id and conflict_id are assigned anew on the real save'
                return result
            self.db.execute('COMMIT')
            return result
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def search(self, query, limit=5, max_chars=1500, include_global=False, offset=0, max_response_chars=RESPONSE_MAX):
        """Keyword search with two budgets: max_chars for result text and max_response_chars for the whole
        compact-JSON response (metadata included). Counts and conflict warnings are always kept; lists shrink
        first and `next_offset` pages to the rest."""
        terms = list(dict.fromkeys(re.findall(r'[\w-]+', query)))
        if not terms:
            raise ValueError('Provide at least one search term')
        if not isinstance(limit, int) or limit < 1:
            raise ValueError('limit must be a positive integer')
        if not isinstance(offset, int) or offset < 0:
            raise ValueError('offset must be a non-negative integer')
        if not isinstance(max_response_chars, int) or max_response_chars < RESPONSE_MIN:
            raise ValueError(f'max_response_chars must be at least {RESPONSE_MIN}')
        patterns = [re.compile(study_pattern(t), re.IGNORECASE) for t in terms]
        projects = [self.project] + (['global'] if include_global and self.project != 'global' else [])
        rows = self.db.execute(f"SELECT m.*, r.text, r.created AS updated FROM memories m JOIN revisions r ON r.memory_id=m.memory_id "
                               f"AND r.rev=m.current_rev WHERE m.project IN ({','.join('?' * len(projects))}) "
                               f"AND m.status IN ('active','conflict')", projects).fetchall()
        hits = []
        for row in rows:
            counts = [len(p.findall(row['text'])) + len(p.findall(row['key'])) for p in patterns]
            matched = sum(c > 0 for c in counts)
            if matched:
                hits.append((matched, min(sum(counts), 20), row))
        hits.sort(key=lambda h: (-h[0], -h[1], h[2]['updated'], h[2]['memory_id']))
        page = [h[2] for h in hits[offset:]]
        # Results are a contiguous run from `offset`, so next_offset always continues without gaps.
        selected, used = [], 0
        matched_of = {h[2]['memory_id']: h[0] for h in hits}
        for row in page:
            if len(selected) >= limit:
                break
            text, truncated = row['text'], False
            if used + len(text) > max_chars:
                room = max_chars - used
                if selected or room <= 0:
                    break
                text, truncated = text[:room], True
            used += len(text)
            conflict = self._conflict_of(row['memory_id'])
            selected.append({'memory_id': row['memory_id'], 'project': row['project'], 'key': row['key'], 'kind': row['kind'],
                             'status': row['status'], 'rev': row['current_rev'], 'text': text, 'truncated': truncated,
                             'matched_terms': matched_of[row['memory_id']], 'updated': row['updated'], 'conflict_id': conflict['conflict_id'] if conflict else None})
        groups = {}
        for _, _, row in hits:
            c = self._conflict_of(row['memory_id'])
            if c and c['conflict_id'] not in groups:
                members = {r[0] for r in self.db.execute('SELECT memory_id FROM conflict_members WHERE conflict_id=?', (c['conflict_id'],))}
                groups[c['conflict_id']] = (c['key'], members)

        def build(k, ids_cap, conf_cap, trim=None):
            shown = selected[:k]
            if trim is not None and shown:  # last resort: shorten the first result instead of returning nothing
                shown[0] = dict(shown[0], text=shown[0]['text'][:trim], truncated=True)
            shown_ids = {s['memory_id'] for s in shown}
            rest = [r['memory_id'] for r in page[k:]]
            conflicts = [{'conflict_id': cid, 'key': key, 'candidates': len(members), 'shown': len(members & shown_ids),
                          'omitted': len(members - shown_ids)} for cid, (key, members) in groups.items()]
            more = []
            if rest:
                more.append(f'{len(rest)} more after this page: repeat the search with offset={offset + k}')
            if ids_cap < len(rest):
                more.append('omitted_ids is shortened to fit the response budget; page with offset')
            if conf_cap < len(conflicts):
                more.append('conflicts list is shortened; conflict_count is complete; open the conflicts view or show --conflict')
            out = {'mode': 'keyword', 'scope': {'project': self.project, 'include_global': include_global},
                   'query_terms': terms, 'total_matched': len(hits), 'offset': offset, 'returned': k,
                   'omitted_count': len(rest), 'omitted_ids': rest[:ids_cap], 'omitted_ids_complete': ids_cap >= len(rest),
                   'partial': offset > 0 or bool(rest) or any(s['truncated'] for s in shown),
                   'chars_returned': sum(len(s['text']) for s in shown),
                   'budget': {'limit': limit, 'max_chars': max_chars, 'max_response_chars': max_response_chars},
                   'conflict_count': len(conflicts), 'conflicts': conflicts[:conf_cap], 'conflicts_complete': conf_cap >= len(conflicts),
                   'results': shown, 'next_offset': offset + k if rest else None, 'more': more,
                   'note': 'keyword match only; absence from results is not proof the fact was never stored',
                   'response_chars': 0}
            for _ in range(3):  # the size field changes the size; let it settle
                out['response_chars'] = len(json.dumps(out, ensure_ascii=False))
            return out

        k, ids_cap, conf_cap, trim = len(selected), len(page) - len(selected), len(groups), None
        while True:
            out = build(k, ids_cap, conf_cap, trim)
            if out['response_chars'] <= max_response_chars:
                return out
            if ids_cap > 0:
                ids_cap //= 2
            elif k > 1:
                k -= 1
            elif conf_cap > 0:
                conf_cap //= 2
            elif k == 1 and (trim is None or trim > 0):
                trim = len(selected[0]['text']) // 2 if trim is None else trim // 2
            else:
                raise ValueError(f'search response envelope alone exceeds max_response_chars={max_response_chars}; shorten the query')

    def show(self, memory_id=None, conflict_id=None, include_all=False):
        if conflict_id:
            c = self.db.execute('SELECT * FROM conflicts WHERE conflict_id=? AND project=?', (conflict_id, self.project)).fetchone()
            if c is None:
                raise ValueError('not_found_in_project')
            members = []
            for m in self.db.execute('SELECT * FROM conflict_members WHERE conflict_id=?', (conflict_id,)):
                row = self.db.execute('SELECT * FROM memories WHERE memory_id=? AND project=?', (m['memory_id'], self.project)).fetchone()
                if row is not None:
                    members.append(self._record(row))
                    continue
                # R3: history of a resolved/dissolved group may reference a memory deleted later; describe, don't fail.
                tomb = self.db.execute('SELECT deleted_at FROM tombstones WHERE memory_id=?', (m['memory_id'],)).fetchone()
                members.append({'memory_id': m['memory_id'], 'rev': m['rev'], 'status': 'deleted',
                                'deleted_at': tomb['deleted_at'] if tomb else None, 'text': None})
            conflict = dict(c)
            conflict['resolved_memory_deleted'] = bool(c['resolved_memory']) and not self.db.execute(
                'SELECT 1 FROM memories WHERE memory_id=?', (c['resolved_memory'],)).fetchone()
            return {'conflict': conflict, 'members': members}
        if memory_id:
            m = self._memory(memory_id)
            rec = self._record(m)
            if include_all:
                rec['revisions'] = [dict(r) for r in self.db.execute('SELECT * FROM revisions WHERE memory_id=? ORDER BY rev', (memory_id,))]
            return rec
        status_filter = '' if include_all else "AND status IN ('active','conflict')"
        rows = self.db.execute(f'SELECT * FROM memories WHERE project=? {status_filter} ORDER BY key, created', (self.project,)).fetchall()
        return {'project': self.project, 'count': len(rows), 'memories': [self._record(r) for r in rows]}

    def open_conflicts(self):
        ids = [r[0] for r in self.db.execute("SELECT conflict_id FROM conflicts WHERE project=? AND status='open' ORDER BY created",
                                             (self.project,))]
        return {'project': self.project, 'count': len(ids), 'conflicts': [self.show(conflict_id=c) for c in ids]}

    def update(self, memory_id, expect_rev, text, kind=None, requested_by='user', source_note='', dry_run=False):
        text = check_text(text)
        check_name(requested_by, 'requested_by')
        source_note = check_source_note(source_note)
        if kind:
            check_kind(kind)
        self._begin()
        try:
            m = self._memory(memory_id)
            if m['status'] in ('superseded', 'retired'):
                raise ValueError(f"memory is {m['status']}; cannot update")
            if m['current_rev'] != expect_rev:
                self._audit('update_rejected', memory_id, m['key'], m['current_rev'])
                self.db.execute('COMMIT')
                return {'status': 'stale_revision', 'conflict': True, 'memory_id': memory_id,
                        'expected_rev': expect_rev, 'current_rev': m['current_rev'],
                        'note': 'another change landed first; re-read with show and decide'}
            h = content_hash(text)
            cur = self._current(memory_id)
            # Same rule as add(): hash equality alone is not identity, so confirm the normalized text too.
            if cur['content_hash'] == h and normalize(cur['text']) == text and not kind:
                self.db.execute('COMMIT')
                return {'status': 'unchanged', 'memory_id': memory_id, 'rev': expect_rev}
            new_rev, ts = expect_rev + 1, now()
            self.db.execute('INSERT INTO revisions(memory_id,rev,text,content_hash,actor,requested_by,source_note,source_verified,created) '
                            'VALUES(?,?,?,?,?,?,?,?,?)', (memory_id, new_rev, text, h, self.actor, requested_by, source_note, 0, ts))
            self.db.execute('UPDATE revisions SET superseded_by=? WHERE memory_id=? AND rev=?', (f'{memory_id}:{new_rev}', memory_id, expect_rev))
            changed = self.db.execute('UPDATE memories SET current_rev=?, kind=COALESCE(?,kind) WHERE memory_id=? AND current_rev=?',
                                      (new_rev, kind, memory_id, expect_rev)).rowcount
            if changed != 1:
                raise ValueError('concurrent modification detected')
            self.db.execute('UPDATE conflict_members SET rev=? WHERE memory_id=?', (new_rev, memory_id))
            self._audit('update', memory_id, m['key'], new_rev)
            if dry_run:
                previous = self.db.execute('SELECT text FROM revisions WHERE memory_id=? AND rev=?', (memory_id, expect_rev)).fetchone()[0]
                self.db.execute('ROLLBACK')
                return {'status': 'updated', 'dry_run': True, 'memory_id': memory_id, 'rev': new_rev,
                        'previous_text': previous, 'text': text}
            self.db.execute('COMMIT')
            return {'status': 'updated', 'memory_id': memory_id, 'rev': new_rev}
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def resolve(self, conflict_id, keep, resolved_by='user'):
        keep_id, _, keep_rev = keep.partition(':')
        check_name(resolved_by, 'resolved_by')
        self._begin()
        try:
            c = self.db.execute("SELECT * FROM conflicts WHERE conflict_id=? AND project=? AND status='open'", (conflict_id, self.project)).fetchone()
            if c is None:
                raise ValueError('open conflict not_found_in_project')
            members = self.db.execute('SELECT * FROM conflict_members WHERE conflict_id=?', (conflict_id,)).fetchall()
            ids = {m['memory_id'] for m in members}
            if keep_id not in ids:
                raise ValueError('kept memory is not a member of this conflict')
            kept = self._memory(keep_id)
            if keep_rev and int(keep_rev) != kept['current_rev']:
                raise ValueError(f"kept revision {keep_rev} is not current ({kept['current_rev']}); re-read first")
            ts = now()
            for m in members:
                if m['memory_id'] == keep_id:
                    self.db.execute("UPDATE memories SET status='active' WHERE memory_id=?", (keep_id,))
                else:
                    self.db.execute("UPDATE memories SET status='superseded' WHERE memory_id=?", (m['memory_id'],))
                    self.db.execute('UPDATE revisions SET superseded_by=? WHERE memory_id=? AND rev=?',
                                    (f"{keep_id}:{kept['current_rev']}", m['memory_id'], m['rev']))
            self.db.execute("UPDATE conflicts SET status='resolved', resolved_memory=?, resolved_rev=?, resolved_by=?, resolved_at=? WHERE conflict_id=?",
                            (keep_id, kept['current_rev'], resolved_by, ts, conflict_id))
            self._audit('resolve', keep_id, c['key'], len(members))
            self.db.execute('COMMIT')
            return {'status': 'resolved', 'conflict_id': conflict_id, 'kept': keep_id,
                    'superseded': sorted(ids - {keep_id})}
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def retire(self, memory_id):
        self._begin()
        try:
            m = self._memory(memory_id)
            self.db.execute("UPDATE memories SET status='retired' WHERE memory_id=?", (memory_id,))
            self._dissolve_if_single(m)
            self._audit('retire', memory_id, m['key'], m['current_rev'])
            self.db.execute('COMMIT')
            return {'status': 'retired', 'memory_id': memory_id, 'note': 'kept in store; excluded from search and new exports'}
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def _dissolve_if_single(self, m):
        c = self._conflict_of(m['memory_id'])
        if not c:
            return
        self.db.execute('DELETE FROM conflict_members WHERE conflict_id=? AND memory_id=?', (c['conflict_id'], m['memory_id']))
        rest = self.db.execute('SELECT memory_id FROM conflict_members WHERE conflict_id=?', (c['conflict_id'],)).fetchall()
        if len(rest) <= 1:
            for r in rest:
                self.db.execute("UPDATE memories SET status='active' WHERE memory_id=? AND status='conflict'", (r['memory_id'],))
            self.db.execute("UPDATE conflicts SET status='dissolved', resolved_by='single_member_left', resolved_at=? WHERE conflict_id=?",
                            (now(), c['conflict_id']))

    def delete(self, memory_id, confirm=False):
        if not confirm:
            raise ValueError('delete requires --confirm (user-requested only)')
        self._begin()
        try:
            m = self._memory(memory_id)
            revs = self.db.execute('SELECT COUNT(*) FROM revisions WHERE memory_id=?', (memory_id,)).fetchone()[0]
            self._dissolve_if_single(m)  # leaves an open group; membership rows in resolved/dissolved groups stay as history
            self.db.execute('DELETE FROM revisions WHERE memory_id=?', (memory_id,))
            self.db.execute('DELETE FROM memories WHERE memory_id=?', (memory_id,))
            self.db.execute('INSERT OR REPLACE INTO tombstones VALUES(?,?,?)', (memory_id, self.project, now()))
            self._audit('delete', memory_id, m['key'], revs)
            self.db.execute('COMMIT')
            return {'status': 'deleted', 'memory_id': memory_id, 'revisions_removed': revs,
                    'note': 'logical deletion: removed from store, search and new exports; earlier exports/inbox copies and '
                            'database pages/backups are not scrubbed'}
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def export(self, out, fmt='jsonl', include_retired=False):
        out = Path(out)
        if out.exists():
            raise ValueError('output exists; choose a new path (no overwrite)')
        statuses = "('active','conflict','retired')" if include_retired else "('active','conflict')"
        rows = self.db.execute(f'SELECT * FROM memories WHERE project=? AND status IN {statuses} ORDER BY key, created', (self.project,)).fetchall()
        records = [self._record(r) for r in rows]
        out.parent.mkdir(parents=True, exist_ok=True)
        if fmt == 'jsonl':
            body = ''.join(json.dumps({k: v for k, v in r.items() if k not in ('actor',)}, ensure_ascii=False) + '\n' for r in records)
        else:
            lines = [f'대상: {self.project} / 기억 {len(records)}건', f'기준: {now()} 저장소 상태', '결과:']
            for r in records:
                flag = ' [충돌 미해결]' if r['conflict_id'] else ''
                lines.append(f"- ({r['kind']}) {r['key']}{flag}: {r['text']}  <{r['memory_id'][:8]} r{r['rev']}>")
            lines += ['확인: 저장소에서 직접 읽음. 사용자 발언 원문은 재확인하지 않음',
                      '미확인: retired·삭제 건 제외. 검색 누락 ≠ 저장 부재', '다음: 수신자가 변경 제안은 JSONL로 inbox에 둠']
            body = '\n'.join(lines) + '\n'
        with out.open('x', encoding='utf-8') as f:
            f.write(body)
        self._audit('export', None, None, len(records))
        return {'status': 'exported', 'path': str(out), 'count': len(records), 'format': fmt}

    def import_jsonl(self, path, apply=False, requested_by='user', allow_resurrect=False):
        check_name(requested_by, 'requested_by')
        raw = Path(path).read_bytes()
        if len(raw) > 5_000_000:
            raise ValueError('import file exceeds 5 MB')
        lines = raw.decode('utf-8-sig').splitlines()
        plan, errors, seen_ids = [], [], {}
        for n, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError('row must be an object')
                if row.get('project') != self.project:
                    raise ValueError(f"project {row.get('project')!r} does not match --project {self.project}")
                item = {'text': check_text(row.get('text', '')), 'kind': check_kind(row.get('kind')),
                        'key': check_name(row['key'], 'key') if row.get('key') else None,
                        'memory_id': row.get('memory_id'), 'source_note': check_source_note(row.get('source_note', ''))}
                mid = item['memory_id']
                if mid is not None:
                    if not isinstance(mid, str):
                        raise ValueError('memory_id must be a string')
                    check_name(mid.replace('-', ''), 'memory_id')
                    if mid in seen_ids:
                        raise ValueError(f'memory_id duplicated in file (first on line {seen_ids[mid]})')
                    seen_ids[mid] = n
                    if self.db.execute('SELECT 1 FROM memories WHERE memory_id=?', (mid,)).fetchone():
                        raise ValueError('memory_id already exists in store; import does not overwrite (use update)')
                    if self.db.execute('SELECT 1 FROM tombstones WHERE memory_id=?', (mid,)).fetchone() and not allow_resurrect:
                        raise ValueError('memory_id was deleted; refusing to resurrect without --allow-resurrect')
                plan.append(item)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                errors.append({'line': n, 'error': str(exc)})
        result = {'status': 'dry_run', 'valid_rows': len(plan), 'errors': errors, 'applied': 0,
                  'note': 'file author/source_verified fields are ignored; imported rows are source_verified=false; '
                          'apply is all-or-nothing'}
        if errors or not apply:
            if errors and apply:
                result['status'] = 'rejected_no_changes'
            return result
        # R1: one transaction for the whole file; any failure rolls back every row.
        self._begin()
        try:
            applied = [self._add_in_tx(item['text'], item['kind'], key=item['key'], requested_by=requested_by,
                                       source_note=item['source_note'], allow_resurrect=allow_resurrect, memory_id=item['memory_id'])
                       for item in plan]
            self.db.execute('COMMIT')
        except Exception as exc:
            self.db.execute('ROLLBACK')
            result.update(status='rejected_no_changes', errors=[{'line': None, 'error': f'apply failed, rolled back: {exc}'}])
            return result
        result.update(status='applied', applied=len(applied), results=applied)
        return result

    def audit_log(self, limit=50):
        rows = self.db.execute('SELECT * FROM audit WHERE project=? ORDER BY id DESC LIMIT ?', (self.project, limit)).fetchall()
        return {'project': self.project, 'entries': [dict(r) for r in rows]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--db', required=True)
    p.add_argument('--project', required=True)
    p.add_argument('--actor', default='claude', help='who runs this command: claude, chatgpt, codex or user')
    sub = p.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add'); a.add_argument('text'); a.add_argument('--kind', required=True, choices=KINDS)
    a.add_argument('--key'); a.add_argument('--requested-by', default='user'); a.add_argument('--source-note', default='')
    a.add_argument('--reactivate', action='store_true'); a.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('search'); s.add_argument('query'); s.add_argument('--limit', type=int, default=5)
    s.add_argument('--max-chars', type=int, default=1500); s.add_argument('--include-global', action='store_true')
    s.add_argument('--offset', type=int, default=0); s.add_argument('--max-response-chars', type=int, default=RESPONSE_MAX)
    sh = sub.add_parser('show'); sh.add_argument('--id'); sh.add_argument('--conflict'); sh.add_argument('--all', action='store_true')
    u = sub.add_parser('update'); u.add_argument('--id', required=True); u.add_argument('--expect-rev', type=int, required=True)
    u.add_argument('text'); u.add_argument('--kind', choices=KINDS); u.add_argument('--requested-by', default='user')
    u.add_argument('--source-note', default=''); u.add_argument('--dry-run', action='store_true')
    r = sub.add_parser('resolve'); r.add_argument('--conflict', required=True); r.add_argument('--keep', required=True, help='memory_id[:rev]')
    r.add_argument('--resolved-by', default='user')
    rt = sub.add_parser('retire'); rt.add_argument('--id', required=True)
    d = sub.add_parser('delete'); d.add_argument('--id', required=True); d.add_argument('--confirm', action='store_true')
    e = sub.add_parser('export'); e.add_argument('--out', required=True); e.add_argument('--format', choices=['jsonl', 'handoff'], default='jsonl')
    e.add_argument('--include-retired', action='store_true')
    i = sub.add_parser('import'); i.add_argument('--file', required=True); i.add_argument('--apply', action='store_true')
    i.add_argument('--requested-by', default='user'); i.add_argument('--allow-resurrect', action='store_true')
    au = sub.add_parser('audit'); au.add_argument('--limit', type=int, default=50)
    args = p.parse_args(argv)
    st = Store(args.db, args.project, args.actor)
    if args.cmd == 'add':
        out = st.add(args.text, args.kind, key=args.key, requested_by=args.requested_by, source_note=args.source_note, reactivate=args.reactivate,
                     dry_run=args.dry_run)
    elif args.cmd == 'search':
        out = st.search(args.query, args.limit, args.max_chars, args.include_global, args.offset, args.max_response_chars)
        print(json.dumps(out, ensure_ascii=False))  # printed exactly as measured by response_chars
        return
    elif args.cmd == 'show':
        out = st.show(args.id, args.conflict, args.all)
    elif args.cmd == 'update':
        out = st.update(args.id, args.expect_rev, args.text, args.kind, args.requested_by, args.source_note, args.dry_run)
    elif args.cmd == 'resolve':
        out = st.resolve(args.conflict, args.keep, args.resolved_by)
    elif args.cmd == 'retire':
        out = st.retire(args.id)
    elif args.cmd == 'delete':
        out = st.delete(args.id, args.confirm)
    elif args.cmd == 'export':
        out = st.export(args.out, args.format, args.include_retired)
    elif args.cmd == 'import':
        out = st.import_jsonl(args.file, args.apply, args.requested_by, args.allow_resurrect)
    else:
        out = st.audit_log(args.limit)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
