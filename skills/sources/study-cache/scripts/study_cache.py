"""Small local, source-located study cache. No network or model calls."""
import argparse
import hashlib
import json
import posixpath
import re
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

DEFAULT_DB = Path.cwd() / '.study-cache' / 'sources.sqlite'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS sources (
      id TEXT PRIMARY KEY, course TEXT NOT NULL, path TEXT NOT NULL,
      sha256 TEXT NOT NULL, remote_id TEXT NOT NULL, revision TEXT NOT NULL, updated TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sections (
      source_id TEXT NOT NULL, number INTEGER NOT NULL, location TEXT NOT NULL, text TEXT NOT NULL,
      PRIMARY KEY(source_id, number));
    CREATE INDEX IF NOT EXISTS course_index ON sources(course);
    ''')
    return db

def doc_paragraphs(content):
    for item in content:
        if 'paragraph' in item:
            text = ''.join(e.get('textRun', {}).get('content', '') for e in item['paragraph'].get('elements', []))
            if text.strip():
                yield text.rstrip()
        if 'table' in item:
            for row in item['table'].get('tableRows', []):
                for cell in row.get('tableCells', []):
                    yield from doc_paragraphs(cell.get('content', []))

def extract(path):
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError('PDF support requires pypdf; install it in the selected environment') from exc
        try:
            reader = PdfReader(path)
            if reader.is_encrypted:
                raise ValueError('Encrypted PDF: provide an authorized unencrypted copy; no password guessing')
            pages = []
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ''
                status = 'text extracted; layout/tables/figures unverified' if text.strip() else 'no extracted text; OCR/visual review required'
                pages.append((f'page {number}; {status}', text))
            if not any(text.strip() for _, text in pages):
                raise ValueError('PDF has no extractable text; OCR/visual review required; prior cache preserved')
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('PDF extraction failed; prior cache preserved: ' + str(exc)) from exc
        yield from pages
    elif suffix == '.pptx':
        with zipfile.ZipFile(path) as z:
            rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))}
            root = ET.fromstring(z.read('ppt/presentation.xml'))
            for n, slide in enumerate(root.findall(f'.//{P}sldId'), 1):
                target = rels[slide.get(R + 'id')]
                member = target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/' + target)
                xml = ET.fromstring(z.read(member))
                text = '\n'.join(''.join(p.itertext()).strip() for p in xml.findall('.//' + A + 'p'))
                yield f'slide {n}; visuals/formulas unverified', text
    elif suffix == '.docx':
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read('word/document.xml'))
            for n, p in enumerate(root.findall('.//' + W + 'p'), 1):
                text = ''.join(t.text or '' for t in p.findall('.//' + W + 't'))
                if text.strip():
                    yield f'paragraph {n}; visuals unverified', text
    elif suffix == '.json':
        data = json.loads(path.read_text('utf-8-sig'))
        data = data.get('structuredContent', data)
        if not ('tabs' in data or 'body' in data):
            raise ValueError('Expected saved native Google Docs API JSON response')
        def tabs(items):
            for tab in items:
                props = tab.get('tabProperties', {})
                label = f"tab {props.get('title', '')} [{props.get('tabId', '')}]"
                for n, text in enumerate(doc_paragraphs(tab.get('documentTab', {}).get('body', {}).get('content', [])), 1):
                    yield f'{label}; paragraph {n}', text
                yield from tabs(tab.get('childTabs', []))
        if data.get('tabs'):
            yield from tabs(data['tabs'])
        else:
            for n, text in enumerate(doc_paragraphs(data.get('body', {}).get('content', [])), 1):
                yield f'paragraph {n}', text
    elif suffix in {'.md', '.txt'}:
        lines = path.read_text('utf-8-sig').splitlines()
        for n in range(0, len(lines), 30):
            yield f'lines {n + 1}-{min(n + 30, len(lines))}', '\n'.join(lines[n:n + 30])
    else:
        raise ValueError('Unsupported source: use a designated PDF/PPTX/DOCX/TXT/MD/Google Docs JSON')

def freshness(source):
    path = Path(source['path'])
    if not path.is_file():
        return 'missing_snapshot' if source['remote_id'] else 'missing_local_source'
    if digest(path) != source['sha256']:
        return 'changed_snapshot' if source['remote_id'] else 'changed_local_source'
    return 'remote_revision_unchecked' if source['remote_id'] else 'local_hash_verified'

def ingest(db, args):
    path = Path(args.file).resolve(strict=True)
    sha = digest(path)
    source_id = hashlib.sha256((args.course + '\0' + (args.remote_id or str(path))).encode('utf-8')).hexdigest()[:20]
    previous = db.execute('SELECT * FROM sources WHERE id=?', (source_id,)).fetchone()
    if bool(args.remote_id) != bool(args.revision):
        raise ValueError('Remote sources require both --remote-id and --revision')
    if previous and args.remote_id and previous['revision'] == args.revision and previous['sha256'] != sha:
        raise ValueError('Same remote revision has different snapshot bytes; recheck remote metadata first')
    if previous and previous['sha256'] == sha and previous['revision'] == args.revision:
        with db:
            db.execute('UPDATE sources SET path=? WHERE id=?', (str(path), source_id))
        return {'source_id': source_id, 'status': 'unchanged', 'extracted_sections': 0}
    sections = list(extract(path))
    if not sections:
        raise ValueError('No readable sections; prior cache preserved')
    with db:
        db.execute('DELETE FROM sections WHERE source_id=?', (source_id,))
        db.execute('INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?,?)',
                   (source_id, args.course, str(path), sha, args.remote_id, args.revision, datetime.now(timezone.utc).isoformat()))
        db.executemany('INSERT INTO sections VALUES (?,?,?,?)',
                       ((source_id, n, loc, text) for n, (loc, text) in enumerate(sections, 1)))
    return {'source_id': source_id, 'status': 'cached', 'extracted_sections': len(sections), 'visual_validation': False}

def study_pattern(term):
    # Only Hangul spelling variants ignore whitespace; English word boundaries remain unchanged.
    return r'\s*'.join(re.escape(ch) for ch in term) if re.fullmatch(r'[가-힣]+', term) else re.escape(term)

def search(db, args):
    terms = list(dict.fromkeys(re.findall(r'[\w-]+', args.query.casefold())))
    if not terms:
        raise ValueError('Provide at least one search term')
    patterns = [re.compile(study_pattern(t), re.IGNORECASE) for t in terms]
    compact_query = re.sub(r'\s+', '', args.query)
    phrase = re.compile(study_pattern(compact_query) if re.fullmatch(r'[가-힣]+', compact_query)
                        else re.escape(args.query.strip()), re.IGNORECASE)
    sources = db.execute('SELECT * FROM sources WHERE course=? ORDER BY id', (args.course,)).fetchall()
    hits, skipped = [], []
    for source in sources:
        state = freshness(source)
        if state not in {'local_hash_verified', 'remote_revision_unchecked'}:
            skipped.append({'source_id': source['id'], 'state': state})
            continue
        for row in db.execute('SELECT * FROM sections WHERE source_id=? ORDER BY number', (source['id'],)):
            counts = [len(p.findall(row['text'])) for p in patterns]
            matched = sum(n > 0 for n in counts)
            if not matched:
                continue
            first = min(p.search(row['text']).start() for p in patterns if p.search(row['text']))
            start = max(0, first - 150)
            hits.append({'source_id': source['id'], 'section': row['number'], 'location': row['location'],
                         'source_path': source['path'], 'remote_id': source['remote_id'], 'revision': source['revision'],
                         'freshness': state, 'offset': start, 'text': row['text'][start:start + args.max_chars],
                         'truncated': start > 0 or start + args.max_chars < len(row['text']),
                         'score': sum(counts), 'matched_terms': matched, 'query_terms': len(terms),
                         'phrase_match': bool(phrase.search(row['text']))})
    hits.sort(key=lambda h: (-h['matched_terms'], -int(h['phrase_match']), -min(h['score'], 20)))
    budget = getattr(args, 'max_total_chars', None) or args.limit * args.max_chars
    selected, used = [], 0
    for hit in hits[:args.limit]:
        if used >= budget:
            break
        original_length = len(hit['text'])
        hit['text'] = hit['text'][:budget - used]
        hit['truncated'] = hit['truncated'] or len(hit['text']) < original_length
        used += len(hit['text'])
        selected.append(hit)
    context_count = getattr(args, 'context_sections', 0)
    seen = {(h['source_id'], h['section']) for h in selected}
    context_omitted = False
    if context_count:
        for hit in selected:
            hit['context'] = []
            for number in range(max(1, hit['section'] - context_count), hit['section'] + context_count + 1):
                key = (hit['source_id'], number)
                if key in seen:
                    continue
                row = db.execute('SELECT * FROM sections WHERE source_id=? AND number=?', key).fetchone()
                if not row:
                    continue
                # Only PDF pages and PPT slides have safe same-document sequential neighbors.
                if not (hit['location'].startswith('page ') and row['location'].startswith('page ')
                        or hit['location'].startswith('slide ') and row['location'].startswith('slide ')):
                    continue
                if used >= budget:
                    context_omitted = True
                    continue
                text = row['text'][:min(args.max_chars, budget - used)]
                hit['context'].append({'section': number, 'location': row['location'], 'text': text,
                                       'offset': 0, 'truncated': len(text) < len(row['text'])})
                used += len(text)
                seen.add(key)
    return {'hits': selected, 'skipped': skipped, 'matched_sections': len(hits), 'model_calls': 0,
            'returned_text_chars': used, 'text_char_budget': budget, 'context_omitted_for_budget': context_omitted}

def read(db, args):
    source = db.execute('SELECT * FROM sources WHERE id=?', (args.source_id,)).fetchone()
    if not source:
        raise ValueError('Unknown source ID')
    state = freshness(source)
    if state not in {'local_hash_verified', 'remote_revision_unchecked'}:
        raise ValueError('Do not read stale cache: ' + state)
    row = db.execute('SELECT * FROM sections WHERE source_id=? AND number=?', (args.source_id, args.section)).fetchone()
    if not row:
        raise ValueError('Unknown section')
    text = row['text'][args.offset:args.offset + args.max_chars]
    return {'source_id': source['id'], 'location': row['location'], 'source_path': source['path'],
            'remote_id': source['remote_id'], 'revision': source['revision'], 'freshness': state,
            'offset': args.offset, 'text': text, 'total_chars': len(row['text']),
            'truncated': args.offset > 0 or args.offset + len(text) < len(row['text'])}

def positive(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('ingest')
    p.add_argument('file')
    p.add_argument('--course', required=True)
    p.add_argument('--remote-id', default='')
    p.add_argument('--revision', default='')
    p = sub.add_parser('search')
    p.add_argument('query')
    p.add_argument('--course', required=True)
    p.add_argument('--limit', type=positive, default=3)
    p.add_argument('--max-chars', type=positive, default=1200)
    p.add_argument('--max-total-chars', type=positive, default=None, help='Shared text budget, excluding JSON metadata')
    p.add_argument('--context-sections', type=int, choices=range(0, 3), default=0, help='Neighbor PDF pages or PPT slides')
    p = sub.add_parser('read')
    p.add_argument('source_id')
    p.add_argument('section', type=positive)
    p.add_argument('--offset', type=int, default=0)
    p.add_argument('--max-chars', type=positive, default=2500)
    args = parser.parse_args()
    if getattr(args, 'offset', 0) < 0:
        parser.error('offset must not be negative')
    db = connect(args.db)
    try:
        result = {'ingest': ingest, 'search': search, 'read': read}[args.command](db, args)
        print(json.dumps(result, ensure_ascii=False))
    finally:
        db.close()

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
