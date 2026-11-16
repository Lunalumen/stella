import re
from datetime import date
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

COMPANIES = [
    dict(id='KR:005930', name='삼성전자', ticker='005930', market='KR', exchange='KRX KOSPI', currency='KRW', corp_code='00126380', yahoo='005930.KS', aliases=['삼성전자', 'Samsung Electronics', '005930']),
    dict(id='US:AAPL', name='Apple', ticker='AAPL', market='US', exchange='Nasdaq', currency='USD', cik='0000320193', yahoo='AAPL', aliases=['애플', 'Apple', 'AAPL']),
    dict(id='US:MSFT', name='Microsoft', ticker='MSFT', market='US', exchange='Nasdaq', currency='USD', cik='0000789019', yahoo='MSFT', aliases=['마이크로소프트', 'Microsoft', 'MSFT']),
    dict(id='US:TSLA', name='Tesla', ticker='TSLA', market='US', exchange='Nasdaq', currency='USD', cik='0001318605', yahoo='TSLA', aliases=['테슬라', 'Tesla', 'TSLA']),
    dict(id='US:SPCX', name='SpaceX', ticker='SPCX', market='US', exchange='Nasdaq', currency='USD', cik='0001181412', yahoo='SPCX', aliases=['스페이스X', '스페이스엑스', 'SpaceX', 'SPCX']),
]

def resolve(query, registry=COMPANIES):
    q = query.strip().casefold()
    hits = [c for c in registry if q in [str(c['id']).casefold()] + [a.casefold() for a in c.get('aliases', [c['ticker'], c['name']])]]
    if len(hits) != 1: raise ValueError('종목 식별 확인 필요: 정확한 기업명·티커·거래소를 지정하세요: ' + query)
    return dict(hits[0])

def intent(text, registry=COMPANIES, last=None):
    mode = 'risk' if '위험' in text and ('바뀐' in text or '이후' in text) else 'update' if ('업데이트' in text or '새 실적' in text) else 'compare' if '비교' in text else 'analyze'
    found = []
    for c in registry:
        for a in sorted(c.get('aliases', [c['ticker'], c['name']]), key=len, reverse=True):
            if not a.strip(): continue
            pattern = (r'(?<![가-힣A-Za-z0-9])' + re.escape(a) + r'(?=$|[\s,·]|와|과|의|을|를|은|는|도|만|랑|하고)') if re.search('[가-힣]', a) else r'(?<![A-Za-z0-9])' + re.escape(a) + r'(?![A-Za-z0-9])'
            if re.search(pattern, text, re.I):
                found.append(c); break
    if not found and mode in ('update', 'risk') and last:
        found = [resolve(x, registry) for x in last]
    if not found or len(found) > 3 or (mode == 'compare' and len(found) < 2):
        raise ValueError('대상 확인 필요: 기업명·티커를 지정하세요. 비교는 2~3개 기업을 지정하세요.')
    if mode != 'compare' and len(found) > 1: raise ValueError('여러 기업은 비교 요청으로 지정하세요')
    return mode, found

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
        if tag in ('p', 'div', 'tr', 'h1', 'h2', 'h3', 'br'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip: self.skip -= 1
    def handle_data(self, text):
        if not self.skip: self.parts.append(text)

def html_text(body):
    p = TextParser(); p.feed(body.decode('utf-8', errors='replace')); p.close()
    return re.sub(r'[ \t]+', ' ', '\n'.join(s.strip() for s in ''.join(p.parts).splitlines() if s.strip()))

TAGS = {
 'revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet'],
 'operating_income': ['OperatingIncomeLoss'], 'net_income': ['NetIncomeLoss', 'ProfitLoss'],
 'operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
 'capex': ['PaymentsToAcquirePropertyPlantAndEquipment'],
 'cash': ['CashAndCashEquivalentsAtCarryingValue'], 'assets': ['Assets'],
 'debt_current': ['LongTermDebtCurrent', 'LongTermDebtAndCapitalLeaseObligationsCurrent'],
 'debt_noncurrent': ['LongTermDebtNoncurrent', 'LongTermDebtAndCapitalLeaseObligations'],
 'inventory': ['InventoryNet'], 'receivables': ['AccountsReceivableNetCurrent'],
 'stock_compensation': ['ShareBasedCompensation'], 'eps': ['EarningsPerShareDiluted', 'EarningsPerShareBasic'],
 'shares': ['WeightedAverageNumberOfDilutedSharesOutstanding'],
}

def sec_facts(payload, cik, as_of):
    result = []
    gaap = payload.get('facts', {}).get('us-gaap', {})
    for metric, tags in TAGS.items():
        chosen = {}
        for rank, tag in enumerate(tags):
            for unit, rows in gaap.get(tag, {}).get('units', {}).items():
                if unit != ('USD/shares' if metric == 'eps' else 'shares' if metric == 'shares' else 'USD'): continue
                for r in rows:
                    if r.get('form') not in ('10-K', '10-K/A', '10-Q', '10-Q/A') or r.get('filed', '9999') > as_of or r['end'] > as_of: continue
                    if int(r['end'][:4]) < int(as_of[:4]) - 6: continue
                    start = r.get('start')
                    days = (date.fromisoformat(r['end']) - date.fromisoformat(start)).days if start else None
                    kind = 'instant' if days is None else 'annual' if 330 <= days <= 380 else 'quarter' if 60 <= days <= 110 else 'ytd' if 110 < days < 330 else 'unsupported'
                    if kind == 'unsupported': continue
                    key = (start, r['end'], unit)
                    score = (r['filed'], -rank)
                    if key in chosen and chosen[key][0] >= score: continue
                    acc = r.get('accn', '')
                    chosen[key] = (score, dict(metric=metric, value=r['val'], unit=unit, start=start, end=r['end'],
                        period_kind=kind, scope='consolidated', filed=r['filed'], form=r['form'], document_id=acc,
                        source_url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-", "")}/{acc}-index.html',
                        locator='us-gaap:' + tag, classification='fact'))
        result.extend(v[1] for v in chosen.values())
    return sorted(result, key=lambda x: (x['end'], x.get('start') or '', x['metric']))

def ratios(rows, financial=False):
    groups = {}
    for r in rows:
        groups.setdefault((r.get('start'), r['end'], r['period_kind'], r.get('scope'), r['unit']), {})[r['metric']] = r
    out = []
    for key, values in groups.items():
        if key[-1] not in ('USD', 'KRW') or financial: continue
        for name, first, second, op in [('operating_margin_pct', 'operating_income', 'revenue', 'divide'), ('free_cash_flow', 'operating_cash_flow', 'capex', 'subtract')]:
            if first not in values or second not in values: continue
            a, b = values[first], values[second]
            av, bv = Decimal(str(a['value'])), Decimal(str(b['value']))
            if op == 'divide' and bv <= 0: continue
            if op == 'subtract' and bv < 0: continue
            value = av / bv * 100 if op == 'divide' else av - bv
            out.append(dict(metric=name, value=float(value), unit='%' if op == 'divide' else key[-1], start=key[0], end=key[1], period_kind=key[2], scope=key[3],
                formula=f'{first}/{second}*100' if op == 'divide' else f'{first}-{second}', source_urls=sorted({a['source_url'], b['source_url']}), classification='calculation'))
    return out

def dart_facts(payload, year, report_code):
    if payload.get('status') != '000': raise ValueError('DART 자료 미확인: ' + str(payload.get('status')))
    maps = {'ifrs-full_Revenue':'revenue', 'dart_OperatingIncomeLoss':'operating_income', 'ifrs-full_ProfitLoss':'net_income',
            'ifrs-full_CashFlowsFromUsedInOperatingActivities':'operating_cash_flow', 'ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities':'capex',
            'ifrs-full_CashAndCashEquivalents':'cash', 'ifrs-full_Inventories':'inventory', 'ifrs-full_Assets':'assets'}
    names = {'매출액':'revenue', '수익(매출액)':'revenue', '영업이익':'operating_income', '영업이익(손실)':'operating_income',
             '영업활동현금흐름':'operating_cash_flow', '유형자산의 취득':'capex', '현금및현금성자산':'cash'}
    end = f'{year}-' + {'11011':'12-31','11013':'03-31','11012':'06-30','11014':'09-30'}[report_code]
    out, seen = [], set()
    for r in payload.get('list', []):
        if r.get('fs_div', 'CFS') != 'CFS' or r.get('sj_div') == 'SCE': continue
        metric = maps.get(r.get('account_id')) or names.get(r.get('account_nm'))
        if not metric or metric in seen: continue
        instant = r.get('sj_div') == 'BS'
        cumulative = not instant and r.get('sj_div') in ('IS', 'CIS') and report_code != '11011'
        raw = r.get('thstrm_add_amount') if cumulative else r.get('thstrm_amount')
        if raw in (None, '', '-'): continue
        try: val = Decimal(str(raw).replace(',', ''))
        except InvalidOperation: continue
        if metric == 'capex': val = abs(val)
        receipt = r.get('rcept_no', '')
        out.append(dict(metric=metric, value=float(val), unit=r.get('currency') or 'KRW', start=None if instant else f'{year}-01-01',
             end=end, period_kind='instant' if instant else 'annual' if report_code == '11011' else 'ytd', scope='consolidated',
             document_id=receipt, source_url='https://dart.fss.or.kr/dsaf001/main.do?rcpNo=' + receipt,
             locator=r.get('account_id') or r.get('account_nm'), classification='fact',
             limitation='12월 결산 기준. 다른 결산월 기업은 회사 설정에서 별도 확인 필요.'))
        seen.add(metric)
    return out
