"""Explicit official catalog refresh, never fuzzy company guessing."""
import json
import os
import re
from .data import html_text

def kind_rows(body, exchange, suffix, source):
    text = body.decode('euc-kr', 'replace')
    header = re.findall(r'<th\b[^>]*>(.*?)</th>',text,re.I|re.S)
    header = [html_text(h.encode()).strip() for h in header]
    if not all(h in header for h in ('회사명','종목코드')): raise ValueError('KIND 목록 열 이름 확인 실패')
    ni, ci = header.index('회사명'), header.index('종목코드')
    out=[]
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text,re.I|re.S):
        cells=[html_text(c.encode()).strip() for c in re.findall(r'<td\b[^>]*>(.*?)</td>',tr,re.I|re.S)]
        if len(cells)<=max(ni,ci): continue
        name,code=cells[ni],cells[ci]
        if not name or not re.fullmatch(r'[0-9A-Z]{6}',code): continue
        sector=cells[header.index('업종')] if '업종' in header else ''
        month=cells[header.index('결산월')] if '결산월' in header else '미확인'
        out.append(dict(id='KR:'+code,name=name,ticker=code,market='KR',exchange=exchange,currency='KRW',yahoo=code+suffix,
                        aliases=[name,code],identity_source=source['url'],identity_checked=source['checked'],
                        financial=bool(re.search('금융|은행|보험',sector)),fiscal_month=month))
    return out

def sync(store, market, refresh=False):
    rows = []
    if market == 'US':
        ua = os.getenv('SEC_USER_AGENT', '')
        if '@' not in ua: raise ValueError('미국 종목 목록 갱신에는 SEC_USER_AGENT가 필요합니다')
        r = store.fetch('https://www.sec.gov/files/company_tickers_exchange.json', 'registry', force=refresh, headers={'User-Agent':ua})
        raw = json.loads(r['body'])
        for values in raw['data']:
            c = dict(zip(raw['fields'], values))
            rows.append(dict(id='US:'+c['ticker'],name=c['name'],ticker=c['ticker'],market='US',exchange=c['exchange'],currency='USD',
                             cik=str(c['cik']).zfill(10),yahoo=c['ticker'].replace('.','-'),aliases=[c['name'],c['ticker']],identity_source=r['url'],identity_checked=r['checked']))
    else:
        for kind, exchange, suffix in [('stockMkt','KRX KOSPI','.KS'),('kosdaqMkt','KRX KOSDAQ','.KQ')]:
            r = store.fetch(f'https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13&marketType={kind}', 'registry', force=refresh)
            rows.extend(kind_rows(r['body'],exchange,suffix,r))
    if not rows: raise ValueError('공식 종목 목록 추출 실패: 기존 목록 보존')
    existing=store.artifact('company-catalog') or []
    store.artifact('company-catalog',[c for c in existing if c['market']!=market]+rows)
    return dict(market=market,registered=len(rows),source='SEC' if market=='US' else 'KRX KIND',stats=store.stats)
