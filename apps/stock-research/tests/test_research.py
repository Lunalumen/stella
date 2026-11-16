import json
import tempfile
import unittest
from pathlib import Path

from stock_agent.cache import Store, digest, safe_url, validate_url
from stock_agent.data import COMPANIES, dart_facts, intent, ratios, resolve, sec_facts
from stock_agent.engine import Research, consistent_comparison, validate_summary
from stock_agent.providers import samsung_pdf_links
from stock_agent.providers import import_local
from stock_agent.catalog import kind_rows

URL = 'https://data.sec.gov/test.json'
TEST_TEMP = Path(__file__).resolve().parents[1] / 'private' / 'test-tmp'
TEST_TEMP.mkdir(parents=True, exist_ok=True)

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=TEST_TEMP); self.now = 1000; self.calls = []; self.body = b'{"a":1}'
        def transport(url, headers):
            self.calls.append((url, headers)); return 200, self.body, {'ETag':'v1'}
        self.store = Store(self.tmp.name, transport=transport, clock=lambda:self.now)
    def tearDown(self): self.store.close(); self.tmp.cleanup()
    def test_repeat_has_zero_new_external_requests(self):
        a = self.store.fetch(URL, 'disclosures'); b = self.store.fetch(URL, 'disclosures')
        self.assertEqual(a['hash'], b['hash']); self.assertEqual(len(self.calls), 1); self.assertTrue(b['cached'])
    def test_force_revalidates_and_sends_etag(self):
        self.store.fetch(URL,'report'); self.store.fetch(URL,'report',force=True)
        self.assertEqual(len(self.calls),2); self.assertEqual(self.calls[-1][1]['If-None-Match'],'v1')
    def test_different_ttl(self):
        self.store.fetch(URL,'quote'); self.now += 901; self.store.fetch(URL,'quote')
        self.assertEqual(len(self.calls),2)
        other=URL+'?report=1'; self.store.fetch(other,'report'); self.now += 901; self.store.fetch(other,'report')
        self.assertEqual(len(self.calls),3)
    def test_changed_only_one_resource_retains_old_raw(self):
        a=self.store.fetch(URL,'report'); self.store.fetch(URL+'?b=1','report')
        self.body=b'{"a":2}'; b=self.store.fetch(URL,'report',force=True)
        self.assertNotEqual(a['hash'],b['hash']); self.assertTrue((self.store.root/'raw'/(a['hash']+'.bin')).exists())
        self.store.fetch(URL+'?b=1','report'); self.assertEqual(len(self.calls),3)
    def test_304_preserves_payload(self):
        a=self.store.fetch(URL,'report'); self.store.transport=lambda u,h:(304,b'',{})
        b=self.store.fetch(URL,'report',force=True); self.assertEqual(a['body'],b['body']); self.assertEqual(self.store.stats['not_modified'],1)
    def test_secrets_not_persisted(self):
        self.store.fetch(URL+'?crtfc_key=TOP_SECRET','facts')
        row=self.store.db.execute('SELECT url FROM resources').fetchone()[0]
        self.assertNotIn('TOP_SECRET',row); self.assertNotIn('TOP_SECRET',safe_url(URL+'?api_key=TOP_SECRET'))
    def test_ssrf_and_nonhttps_blocked(self):
        for url in ('http://data.sec.gov/x','https://127.0.0.1/x','https://www.sec.gov.evil.test/x','https://x@y.sec.gov/x','https://data.sec.gov:444/x'):
            with self.assertRaises(ValueError): validate_url(url)

def fact(metric, value, year=2025, unit='USD', kind='annual'):
    return dict(metric=metric,value=value,unit=unit,start=f'{year}-01-01',end=f'{year}-12-31',period_kind=kind,scope='consolidated',source_url=URL,locator='fixture:synthetic',classification='fact')

class FinancialTests(unittest.TestCase):
    def test_krx_header_mapping_and_financial_sector(self):
        body='<table><tr><th>회사명</th><th>시장구분</th><th>종목코드</th><th>업종</th><th>결산월</th></tr><tr><td>테스트은행</td><td>유가</td><td>123456</td><td>은행</td><td>12월</td></tr></table>'.encode('euc-kr')
        rows=kind_rows(body,'KRX KOSPI','.KS',{'url':URL,'checked':1})
        self.assertEqual(rows[0]['ticker'],'123456'); self.assertTrue(rows[0]['financial'])
    def test_protocol_relative_official_pdf_links(self):
        links=samsung_pdf_links(b'<a href="//images.samsung.com/a/2026_con_quarter02_soi.pdf">PDF</a>')
        self.assertEqual(links,['https://images.samsung.com/a/2026_con_quarter02_soi.pdf'])
    def test_identification_and_ambiguity(self):
        self.assertEqual(resolve('삼성전자')['id'],'KR:005930'); self.assertEqual(resolve('AAPL')['market'],'US')
        for q in ('삼성','스페이스','005935','모르는기업'):
            with self.assertRaises(ValueError): resolve(q)
    def test_four_natural_requests(self):
        self.assertEqual(intent('삼성전자 기업 분석')[0],'analyze')
        self.assertEqual([c['ticker'] for c in intent('애플과 마이크로소프트 비교')[1]],['AAPL','MSFT'])
        self.assertEqual(intent('이 기업의 새 실적만 반영해서 업데이트',last=['US:AAPL'])[0],'update')
        self.assertEqual(intent('지난 분석 이후 바뀐 위험 요인 알려줘',last=['US:AAPL'])[0],'risk')
    def test_context_free_update_requires_identity(self):
        with self.assertRaises(ValueError): intent('이 기업 업데이트')
    def test_common_stock_not_mistaken_for_preferred_or_empty_alias(self):
        with self.assertRaises(ValueError): intent('삼성전자우 분석')
        blank=dict(COMPANIES[0],id='KR:000001',aliases=[''])
        self.assertEqual(len(intent('삼성전자 기업 분석',COMPANIES+[blank])[1]),1)
    def test_ratio_math_and_definition(self):
        result=ratios([fact('revenue',200),fact('operating_income',40),fact('operating_cash_flow',70),fact('capex',20)])
        self.assertEqual({r['metric']:r['value'] for r in result},{'operating_margin_pct':20,'free_cash_flow':50})
    def test_no_mixed_period_currency_scope_or_bank_ratios(self):
        self.assertEqual(ratios([fact('revenue',100),fact('operating_income',20,year=2024)]),[])
        self.assertEqual(ratios([fact('revenue',100),fact('operating_income',20,unit='KRW')]),[])
        b=fact('operating_income',20); b['scope']='separate'
        self.assertEqual(ratios([fact('revenue',100),b]),[])
        self.assertEqual(ratios([fact('revenue',100),fact('operating_income',20)],financial=True),[])
    def test_sec_latest_amendment_and_no_future(self):
        rows=[dict(start='2025-01-01',end='2025-12-31',val=v,filed=d,form=f,accn=str(v)) for v,d,f in [(100,'2026-02-01','10-K'),(110,'2026-03-01','10-K/A'),(999,'2027-01-01','10-K')]]
        result=sec_facts({'facts':{'us-gaap':{'Revenues':{'units':{'USD':rows}}}}},'1','2026-10-22')
        self.assertEqual(len(result),1); self.assertEqual(result[0]['value'],110); self.assertEqual(result[0]['period_kind'],'annual')
    def test_sec_quarter_ytd_and_annual_separate(self):
        rows=[dict(start=s,end=e,val=1,filed='2026-08-01',form='10-Q',accn='1') for s,e in [('2026-04-01','2026-06-30'),('2026-01-01','2026-06-30')]]
        result=sec_facts({'facts':{'us-gaap':{'Revenues':{'units':{'USD':rows}}}}},'1','2026-10-22')
        self.assertEqual({r['period_kind'] for r in result},{'quarter','ytd'})
    def test_dart_cumulative_not_quarter(self):
        row=dict(account_id='ifrs-full_Revenue',sj_div='IS',thstrm_amount='60',thstrm_add_amount='110',rcept_no='1',currency='KRW')
        result=dart_facts({'status':'000','list':[row]},2026,'11012')
        self.assertEqual(result[0]['value'],110); self.assertEqual(result[0]['period_kind'],'ytd')
    def test_comparison_only_identical_contexts(self):
        a=dict(company={'id':'a'},facts=[fact('revenue',100)],calculations=[])
        b=dict(company={'id':'b'},facts=[fact('revenue',200,year=2024)],calculations=[])
        self.assertEqual(consistent_comparison([a,b]),[])
        b['facts']=[fact('revenue',200)]; self.assertEqual(consistent_comparison([a,b])[0]['values'],{'a':100,'b':200})

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=TEST_TEMP); self.store=Store(self.tmp.name); self.version=1
        def collector(c,mode,refresh):
            return dict(company=c,facts=[fact('revenue',100+self.version),fact('operating_income',20)],sources=[dict(url=URL,kind='facts',hash=str(self.version),cached=True,checked=1)],excerpts=[dict(topic='risk',text='SYNTHETIC: competition',source_url=URL,source_hash=str(self.version),classification='source_excerpt')],limitations=['SYNTHETIC TEST ONLY'],quote=None,disclosures=[])
        self.research=Research(self.store,collector=collector)
    def tearDown(self): self.store.close(); self.tmp.cleanup()
    def summary(self, result):
        packet=json.loads(Path(result['packet']).read_text('utf-8')); sid=next(iter(packet['evidence']))
        return dict(claims=[dict(section='성장 동력과 주요 위험',text='SYNTHETIC evidence review',kind='inference',polarity='risk',source_ids=[sid])],limitations=['SYNTHETIC, not real investment analysis'])
    def test_first_then_complete_then_repeat_reuses_analysis(self):
        a=self.research.run('삼성전자 기업 분석','2026-10-22')
        self.assertEqual(a['status'],'evidence_ready')
        self.research.complete(a['fingerprint'],self.summary(a))
        b=self.research.run('삼성전자 기업 분석','2026-10-22')
        self.assertEqual(a['fingerprint'],b['fingerprint']); self.assertEqual(b['status'],'analysis_reused')
        self.assertEqual(b['changes'],0)
    def test_two_documents_with_same_url_do_not_create_false_changes(self):
        original=self.research.collector
        def collector(c,mode,refresh):
            result=original(c,mode,refresh)
            result['sources'].append(dict(url=URL,kind='facts',document_id='reviewed-import',hash='second',cached=True,checked=1))
            return result
        self.research.collector=collector
        self.research.run('삼성전자 기업 분석','2026-10-22')
        b=self.research.run('삼성전자 기업 분석','2026-10-22'); self.assertEqual(b['changes'],0)
    def test_changed_data_invalidates_only_dependent_analysis(self):
        a=self.research.run('삼성전자 기업 분석','2026-10-22'); self.research.complete(a['fingerprint'],self.summary(a))
        self.version=2; b=self.research.run('삼성전자 기업 분석','2026-10-22')
        self.assertNotEqual(a['fingerprint'],b['fingerprint']); self.assertEqual(b['status'],'evidence_ready'); self.assertEqual(b['changes'],1)
    def test_new_update_compares_with_full_baseline(self):
        self.research.run('삼성전자 기업 분석','2026-10-22'); self.version=2
        b=self.research.run('이 기업 새 실적 업데이트','2026-10-22'); self.assertEqual(b['mode'],'update'); self.assertEqual(b['changes'],1)
    def test_quote_only_change_is_not_an_earnings_or_risk_change(self):
        original=self.research.collector
        def collector(c,mode,refresh):
            result=original(c,mode,refresh)
            result['sources'].append(dict(url='https://query1.finance.yahoo.com/quote',kind='quote',hash=str(self.version),cached=True,checked=1))
            return result
        self.research.collector=collector
        self.research.run('삼성전자 기업 분석','2026-10-22')
        b=self.research.run('이 기업 새 실적 업데이트','2026-10-22')
        self.assertEqual(b['changes'],0)
    def test_risk_packet_preserves_counterevidence(self):
        self.research.run('삼성전자 기업 분석','2026-10-22')
        b=self.research.run('지난 분석 이후 바뀐 위험 요인 알려줘','2026-10-22')
        packet=json.loads(Path(b['packet']).read_text('utf-8')); self.assertTrue(all(x.get('topic')=='risk' for x in packet['evidence'].values()))
    def test_missing_or_foreign_citation_rejected(self):
        a=self.research.run('삼성전자 기업 분석','2026-10-22'); summary=self.summary(a); summary['claims'][0]['source_ids']=['forged']
        with self.assertRaises(ValueError): self.research.complete(a['fingerprint'],summary)
    def test_counterevidence_cannot_be_dropped(self):
        a=self.research.run('삼성전자 기업 분석','2026-10-22'); summary=self.summary(a); summary['claims'][0]['polarity']='support'
        with self.assertRaises(ValueError): self.research.complete(a['fingerprint'],summary)
    def test_fingerprint_path_traversal_rejected(self):
        with self.assertRaises(ValueError): self.research.complete('../../outside',{})
    def test_report_has_asof_period_source_currency(self):
        a=self.research.run('삼성전자 기업 분석','2026-10-22'); result=self.research.complete(a['fingerprint'],self.summary(a)); text=Path(result['report']).read_text('utf-8')
        for marker in ('2026-10-22','KRW','2025-12-31','consolidated',URL): self.assertIn(marker,text)
    def test_existing_study_cache_code_is_actually_reused(self):
        path=Path(self.tmp.name)/'source.md'; path.write_text('현금흐름 근거와 반대 증거',encoding='utf-8')
        module=Path(__file__).resolve().parents[3]/'skills/sources/study-cache/scripts/study_cache.py'
        metadata=dict(company_id='KR:005930',source_url=URL,document_id='doc1',revision='r1',period='2025',period_end='2025-12-31')
        a=import_local(self.store,path,'text',metadata,module); b=import_local(self.store,path,'text',metadata,module)
        self.assertEqual(a['source_hash'],b['source_hash']); self.assertTrue((self.store.root/'source-text.sqlite').exists())
        self.assertEqual(len(self.store.artifact('imports:KR:005930')),1)
        path.write_text('수정된 자료',encoding='utf-8')
        with self.assertRaises(ValueError): import_local(self.store,path,'text',metadata,module)

if __name__=='__main__': unittest.main()
