import importlib.util
import io
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

from .cache import digest
from .data import dart_facts, html_text, sec_facts

def public_meta(r, **extra):
    return {k:r[k] for k in ('url', 'kind', 'hash', 'checked', 'cached', 'modified')} | extra

def samsung_pdf_links(body):
    text = body.decode('utf-8', 'replace').replace('"//images.samsung.com', '"https://images.samsung.com')
    return sorted(set(re.findall(r'https://images\.samsung\.com/[^\s"<>]+/\d{4}_con_quarter\d+_(?:soi|cf)\.pdf', text)), reverse=True)

def extract_text(store, r):
    path = store.root / 'extracted' / (r['hash'] + '.json')
    if path.exists(): return json.loads(path.read_text('utf-8'))['text']
    if r['body'].startswith(b'%PDF'):
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError('PDF 추출에는 선택 의존성 pypdf가 필요합니다') from None
        reader = PdfReader(io.BytesIO(r['body']))
        text = '\n'.join(f'[PDF page {n}]\n{p.extract_text() or ""}' for n, p in enumerate(reader.pages, 1))
    else:
        text = html_text(r['body']) if b'<' in r['body'][:1000] else r['body'].decode('utf-8-sig')
    store.stats['extractions'] += 1
    store.write('extracted', r['hash'] + '.json', dict(text=text, source_url=r['url'], hash=r['hash'], visual_verified=False))
    return text

def bounded_sections(text, risk_only=False, limit=9000):
    terms = [('risk', r'risk factors|위험|리스크|불확실|규제'), ('counterevidence', r'declin|loss|adverse|decreas|손실|감소|하락|부진'),
             ('business', r'item\s*1[.\s:]|business|사업|매출'), ('governance', r'compensation|related.part|주식보상|관계자|자기주식'),
             ('outlook', r'expect|outlook|guidance|전망|예상|계획')]
    out = []
    budget = limit
    for label, pattern in terms:
        if risk_only and label not in ('risk', 'counterevidence'): continue
        matches = list(re.finditer(pattern, text, re.I))
        # Skip table-of-contents fragments where possible; bounded independent slices.
        for m in (matches[1:3] if len(matches) > 2 else matches[:2]):
            start = max(0, m.start() - 100)
            excerpt = text[start:start + min(1000, budget)]
            if not excerpt: continue
            page_marks=list(re.finditer(r'\[PDF page (\d+)\]',text[:m.start()]))
            page=int(page_marks[-1][1]) if page_marks else None
            entry=dict(topic=label, offset=start, text=excerpt, truncated=True, classification='source_excerpt')
            if page is not None: entry['page']=page
            out.append(entry)
            budget -= len(excerpt)
            if budget <= 0: return out
    if not out and not risk_only: out.append(dict(topic='source', offset=0, text=text[:min(limit, 2000)], truncated=True, classification='source_excerpt'))
    return out

class Collector:
    def __init__(self, store, as_of, force=False):
        self.store, self.as_of, self.force = store, as_of, force

    def collect(self, company, risk_only=False, include_quote=True):
        out = dict(company=company, facts=[], sources=[], excerpts=[], limitations=[], quote=None, disclosures=[])
        def attempt(fn):
            try: fn()
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e: out['limitations'].append(str(e))
        attempt(lambda: self.us(company, out, risk_only) if company['market'] == 'US' else self.kr(company, out, risk_only))
        if company['market'] == 'US' and not out['sources']:
            attempt(lambda: self.ir_fallback(company, out, risk_only))
        attempt(lambda: self.configured_sources(company, out, risk_only))
        if include_quote: attempt(lambda: self.quote(company, out))
        return out

    def configured_sources(self, c, out, risk_only):
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / 'config' / 'company-sources.json'
        config = json.loads(path.read_text('utf-8'))
        for item in config.get(c['id'], []):
            if item['published'] > self.as_of: continue
            r = self.store.fetch(item['url'], item['kind'], force=self.force)
            text = extract_text(self.store, r)
            out['sources'].append(public_meta(r, period=item['period'], published=item['published']))
            out['excerpts'].extend(dict(**e, source_url=r['url'], source_hash=r['hash'], period=item['period'], published=item['published']) for e in bounded_sections(text,risk_only,6000))

    def ir_fallback(self, c, out, risk_only):
        urls = {'AAPL':'https://investor.apple.com/investor-relations/default.aspx',
                'MSFT':'https://www.microsoft.com/en-us/Investor/earnings/FY-2026-Q4/press-release-webcast',
                'TSLA':'https://ir.tesla.com/', 'SPCX':'https://ir.spacex.com/investors/'}
        url = urls.get(c['ticker'])
        if not url: return
        r = self.store.fetch(url, 'ir', force=self.force)
        text = extract_text(self.store, r)
        out['sources'].append(public_meta(r))
        out['excerpts'].extend(dict(**e, source_url=r['url'], source_hash=r['hash']) for e in bounded_sections(text, risk_only))
        out['limitations'].append('SEC가 미연결되어 공개 IR 보조 경로를 사용했습니다. IR 페이지에 최신 보고서가 있는지 추가 확인해야 하며 종목 식별은 설정값입니다.')

    def us(self, c, out, risk_only):
        ua = os.getenv('SEC_USER_AGENT', '')
        if not ua or '@' not in ua:
            raise ValueError('SEC_USER_AGENT 미설정: 본인의 연락처가 포함된 식별자를 환경변수로 설정하세요. SEC API 키는 불필요합니다.')
        headers = {'User-Agent': ua}
        submissions = self.store.fetch(f'https://data.sec.gov/submissions/CIK{c["cik"]}.json', 'disclosures', force=self.force, headers=headers)
        sub = json.loads(submissions['body'])
        if c['ticker'] not in sub.get('tickers', []): raise ValueError('SEC 기업·티커 불일치: 설정을 확인하세요')
        out['company']['identity_verified'] = True
        out['company']['financial'] = 6000 <= int(sub.get('sic') or 0) <= 6999
        out['sources'].append(public_meta(submissions, document_id=c['cik']))
        recent = sub['filings']['recent']
        selected, disclosures = [], []
        for i, form in enumerate(recent.get('form', [])):
            if recent['filingDate'][i] > self.as_of: continue
            if form in ('10-K', '10-K/A', '10-Q', '10-Q/A', '8-K', 'DEF 14A'):
                accession = recent['accessionNumber'][i]
                item = dict(document_id=accession, form=form, filed=recent['filingDate'][i],
                            period=recent.get('reportDate', [''] * len(recent['form']))[i],
                            source_url=f'https://www.sec.gov/Archives/edgar/data/{int(c["cik"])}/{accession.replace("-", "")}/{recent["primaryDocument"][i]}')
                disclosures.append(item)
                if form in ('10-K', '10-K/A', '10-Q', '10-Q/A') and not any(x['form'].split('/')[0] == form.split('/')[0] for x in selected): selected.append(item)
            if len(disclosures) >= 16: break
        out['disclosures'] = disclosures
        sig = digest(json.dumps(disclosures, sort_keys=True).encode())
        prior = self.store.artifact('filing-signature:' + c['id'])
        facts = self.store.fetch(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{c["cik"]}.json', 'facts', force=self.force or (prior is not None and prior != sig), headers=headers)
        out['facts'] = sec_facts(json.loads(facts['body']), c['cik'], self.as_of)
        out['sources'].append(public_meta(facts))
        self.store.artifact('filing-signature:' + c['id'], sig)
        for item in selected[:2]:
            try:
                time.sleep(.12)
                r = self.store.fetch(item['source_url'], 'report', force=self.force, headers=headers)
                text = extract_text(self.store, r)
                out['excerpts'].extend(dict(**e, source_url=r['url'], source_hash=r['hash'], document_id=item['document_id'], period=item['period']) for e in bounded_sections(text, risk_only))
                out['sources'].append(public_meta(r, document_id=item['document_id'], period=item['period']))
            except ValueError as e: out['limitations'].append(str(e))
        out['limitations'].append('미국 재무 추출은 US-GAAP 표준 태그만 지원합니다. 기업 고유 태그·IFRS·금융업 지표와 원문 표 시각 검증은 별도 확인이 필요합니다.')

    def kr(self, c, out, risk_only):
        if c['ticker'] == '005930':
            url = 'https://www.samsung.com/global/ir/stock-information/listing-Info/'
            listing = self.store.fetch(url, 'registry', force=self.force)
            text = extract_text(self.store, listing)
            if '005930' not in text: raise ValueError('삼성전자 공식 종목코드 확인 실패')
            out['company']['identity_verified'] = True
            out['sources'].append(public_meta(listing))
        key = os.getenv('DART_API_KEY')
        if key:
            self.dart(c, out, key)
        else:
            out['limitations'].append('DART_API_KEY 미설정: DART 자동 구조화 재무·정정공시 조회는 미연결. 무료 발급 키이며, 공개 IR 수집과 저장 자료 분석은 사용 가능합니다.')
        urls = []
        if c['ticker'] == '005930':
            # Discover actual release links instead of inventing URLs or dates.
            index = self.store.fetch('https://www.samsung.com/global/ir/financial-information/earnings-release/', 'ir', force=self.force)
            out['sources'].append(public_meta(index))
            text = extract_text(self.store, index)
            # Navigation is not company evidence. Store the index but send actual reports.
            # The financial statements index is the source of truth for available periods.
            r = self.store.fetch('https://www.samsung.com/global/ir/financial-information/audited-financial-statements/', 'disclosures', force=self.force)
            out['sources'].append(public_meta(r))
            candidates = samsung_pdf_links(r['body'])
            urls.extend(candidates[:4])
        for url in dict.fromkeys(urls):
            r = self.store.fetch(url, 'report', force=self.force)
            text = extract_text(self.store, r)
            out['sources'].append(public_meta(r))
            # Tables are retained for agent review; no unsafe position-based PDF numeric parsing.
            out['excerpts'].append(dict(topic='financial_table_unverified', text=text[:7000], offset=0, truncated=len(text)>7000, source_url=r['url'], source_hash=r['hash'], classification='source_excerpt'))
        if not out['facts']:
            out['limitations'].append('한국 재무 수치는 검증된 구조화 자료가 아직 없습니다. PDF 숫자를 자동 확정하지 않으며, DART 키 또는 출처·기간이 있는 검토된 facts JSON을 가져오세요.')

    def dart(self, c, out, key):
        if c.get('fiscal_month', '12월') != '12월':
            raise ValueError('12월 이외 결산 기업의 DART 기간 정규화는 별도 설정이 필요합니다')
        if not c.get('corp_code'):
            import zipfile
            from xml.etree import ElementTree
            r = self.store.fetch('https://opendart.fss.or.kr/api/corpCode.xml?' + urlencode({'crtfc_key':key}), 'registry', force=self.force, identity='dart-corporation-codes')
            with zipfile.ZipFile(io.BytesIO(r['body'])) as z:
                if z.getinfo('CORPCODE.xml').file_size > 100_000_000: raise ValueError('DART 기업코드 압축 크기 제한')
                root = ElementTree.fromstring(z.read('CORPCODE.xml'))
            matches=[x.findtext('corp_code') for x in root.findall('list') if x.findtext('stock_code')==c['ticker']]
            if len(matches)!=1: raise ValueError('DART 기업코드 식별 확인 필요')
            c['corp_code']=matches[0]
        query = dict(crtfc_key=key, corp_code=c['corp_code'], bgn_de=f'{int(self.as_of[:4])-1}0101', end_de=self.as_of.replace('-', ''), last_reprt_at='Y', page_count=100)
        r = self.store.fetch('https://opendart.fss.or.kr/api/list.json?' + urlencode(query), 'disclosures', force=self.force, identity='dart-list:' + c['corp_code'] + ':' + query['bgn_de'])
        payload = json.loads(r['body'])
        if payload.get('status') != '000': raise ValueError('DART 공시 목록 조회 실패: ' + str(payload.get('status')))
        out['sources'].append(public_meta(r))
        out['disclosures'] = [dict(document_id=x['rcept_no'], filed=x['rcept_dt'], title=x['report_nm'], source_url='https://dart.fss.or.kr/dsaf001/main.do?rcpNo=' + x['rcept_no']) for x in payload['list']]
        if int(payload.get('total_page', 1)) > 1: out['limitations'].append('DART 최근 공시 첫 100건만 조회했습니다. 이전 공시 전체 검토는 아닙니다.')
        sig = digest(json.dumps(out['disclosures'], sort_keys=True).encode())
        old_sig = self.store.artifact('filing-signature:' + c['id'])
        periods = [(y, '11011') for y in range(int(self.as_of[:4])-3, int(self.as_of[:4]))]
        for x in payload['list']:
            m = re.search(r'(사업|반기|분기)보고서\s*\((\d{4})\.(\d{2})\)', x['report_nm'])
            if m and int(m[2]) == int(self.as_of[:4]):
                code = {'03':'11013','06':'11012','09':'11014','12':'11011'}.get(m[3])
                if code: periods.append((int(m[2]), code))
        for year, code in dict.fromkeys(periods):
            params = dict(crtfc_key=key, corp_code=c['corp_code'], bsns_year=year, reprt_code=code, fs_div='CFS')
            f = self.store.fetch('https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?' + urlencode(params), 'facts', force=self.force or (old_sig is not None and old_sig != sig and year == max(y for y, _ in periods)), identity=f'dart-facts:{c["corp_code"]}:{year}:{code}')
            out['facts'].extend(dart_facts(json.loads(f['body']), year, code))
            out['sources'].append(public_meta(f, period=f'{year}/{code}'))
        self.store.artifact('filing-signature:' + c['id'], sig)

    def quote(self, c, out):
        # Free fallback; do not mislabel an aggregator as official exchange data.
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{c["yahoo"]}?interval=1d&range=5d'
        r = self.store.fetch(url, 'quote', force=self.force)
        meta = json.loads(r['body'])['chart']['result'][0]['meta']
        if meta['currency'] != c['currency'] or meta.get('symbol', c['yahoo']) != c['yahoo']: raise ValueError('시세 종목 또는 통화 불일치')
        timestamp = datetime.fromtimestamp(meta['regularMarketTime'], timezone.utc).isoformat()
        if timestamp[:10] > self.as_of: raise ValueError('시세가 분석 기준일 이후입니다. 과거 분석에는 날짜별 종가를 가져오세요.')
        out['quote'] = dict(price=meta['regularMarketPrice'], currency=meta['currency'], as_of=timestamp,
             type='regular_session_last_or_close; delay_unverified', source='Yahoo Finance (보조 자료)', source_url=r['url'],
             cache_checked_at=datetime.fromtimestamp(r['checked'], timezone.utc).isoformat(), source_hash=r['hash'])
        out['sources'].append(public_meta(r))
        out['limitations'].append('시세는 무료 보조 자료이며 실시간·지연 여부를 확정하지 못했습니다. 거래소 공식 시세가 아닙니다.')

def import_local(store, path, kind, metadata, cache_module):
    spec = importlib.util.spec_from_file_location('myeongwol_study_cache', cache_module)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    sha = module.digest(path)
    if kind == 'facts':
        data = json.loads(path.read_text('utf-8-sig'))
        if not isinstance(data, list): raise ValueError('facts는 행 배열이어야 합니다')
        for r in data:
            if not all(k in r for k in ('metric', 'value', 'unit', 'end', 'period_kind', 'scope', 'source_url', 'locator')): raise ValueError('facts 출처·기간·단위 필드 누락')
            if r['scope'] not in ('consolidated', 'separate'): raise ValueError('연결·별도 구분 오류')
            if r['period_kind'] not in ('annual', 'quarter', 'ytd', 'instant'): raise ValueError('기간 구분 오류')
            if not isinstance(r['value'], (int, float)): raise ValueError('수치 형식 오류')
            if not re.match(r'https://', r['source_url']): raise ValueError('공식 자료 출처 URL 필요')
        text = None
    elif path.suffix.lower() == '.pdf':
        from .pdf_sources import inspect_pdf
        pdf=inspect_pdf(store,path)
        text='\n'.join(f'[PDF page {p["page"]}]\n{p["text"]}' for p in pdf['pages'])
        data=None
    else:
        # Actual reuse of the user's extractor, with an isolated database and namespace.
        from types import SimpleNamespace
        db = module.connect(store.root / 'source-text.sqlite')
        try:
            result = module.ingest(db, SimpleNamespace(file=str(path), course=metadata['company_id'], remote_id=metadata.get('document_id', ''), revision=metadata.get('revision', '')))
            source = db.execute('SELECT * FROM sources WHERE id=?', (result['source_id'],)).fetchone()
            if module.freshness(source) not in ('local_hash_verified', 'remote_revision_unchecked'): raise ValueError('가져온 로컬 자료가 변경됐습니다')
            text = '\n'.join(r['text'] for r in db.execute('SELECT text FROM sections WHERE source_id=? ORDER BY number', (result['source_id'],)))
        finally: db.close()
        data = None
    (store.root / 'raw' / (sha + '.bin')).write_bytes(path.read_bytes())
    record = dict(metadata, hash=sha, kind=kind, facts=data, text=text)
    old = store.artifact('imports:' + metadata['company_id']) or []
    # Same source identity + new revision replaces only that source's current representative.
    identity = metadata.get('document_id') or metadata['source_url']
    prior = next((r for r in old if (r.get('document_id') or r['source_url']) == identity), None)
    if prior and metadata.get('revision') and prior.get('revision') == metadata['revision'] and prior['hash'] != sha:
        raise ValueError('동일 원격 revision의 내용이 다릅니다. 원본 수정 시점을 재확인하세요')
    old = [r for r in old if (r.get('document_id') or r['source_url']) != identity]
    old.append(record)
    store.artifact('imports:' + metadata['company_id'], old)
    store.write('extracted', sha + '.json', record)
    return dict(status='imported', source_hash=sha, model_calls=0)
