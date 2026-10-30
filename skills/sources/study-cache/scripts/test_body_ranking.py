import importlib.util, json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cache',ROOT/'study_cache.py')
cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)
class Retrieval(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.root=Path(self.tmp.name)
        self.db=cache.connect(self.root/'test.sqlite')
    def tearDown(self):
        self.db.close();self.tmp.cleanup()
    def add(self,name,blocks):
        p=self.root/name
        tabs=[{'tabProperties':{'title':str(i)},'documentTab':{'body':{'content':[{'paragraph':{'elements':[{'textRun':{'content':b}}]}}]}}} for i,b in enumerate(blocks)]
        p.write_text(json.dumps({'tabs':tabs}),encoding='utf-8')
        return cache.ingest(self.db,NS(file=str(p),course='test',remote_id='',revision=''))
    def search(self,q,**kwargs):
        return cache.search(self.db,NS(query=q,course='test',limit=3,max_chars=1200,max_total_chars=3600,context_sections=0,**kwargs))
    def test_explanation_precedes_short_assignment(self):
        self.add('a.json',['고대 그리스의 미에 대해 설명하시오.', '고대 그리스의 칼론은 찬탄을 일으키는 것을 뜻한다. '+ '개념의 범위와 사례를 설명한다. '*10])
        h=self.search('고대그리스')['hits']
        self.assertIn('칼론',h[0]['text'])
    def test_contained_paragraph_keeps_provenance(self):
        self.add('a.json',['Alpha fact 1200 USD.', 'Alpha fact 1200 USD. Exception interns excluded. '+ 'Background. '*20])
        r=self.search('Alpha')
        self.assertEqual(len(r['hits']),1);self.assertEqual(r['duplicates_omitted'],1)
        self.assertEqual(r['hits'][0]['included_locations'][0]['section'],1)
    def test_unique_exception_not_removed(self):
        self.add('a.json',['Alpha fact 1200 USD. '+ 'Background. '*20,'Alpha fact 1200 USD. Exception contractors excluded.'])
        r=self.search('Alpha')
        self.assertEqual(len(r['hits']),2)
        self.assertIn('contractors excluded',' '.join(h['text'] for h in r['hits']))
    def test_identical_different_sources_retained(self):
        self.add('a.json',['Alpha fact.']);self.add('b.json',['Alpha fact.'])
        self.assertEqual(len(self.search('Alpha')['hits']),2)
    def test_whitespace_not_word_concatenation(self):
        self.add('a.json',['Alpha a part.','Alpha apart.'])
        self.assertEqual(len(self.search('Alpha')['hits']),2)
    def test_short_definition_retained_if_unique(self):
        self.add('a.json',['Alpha is beta.','Alpha background. '+ 'Other discussion. '*15])
        self.assertTrue(any(h['text']=='Alpha is beta.' for h in self.search('Alpha')['hits']))
    def test_truncated_not_deduplicated(self):
        self.add('a.json',['Alpha '+ 'data '*400,'Alpha '+ 'data '*300+' unique fact.'])
        r=cache.search(self.db,NS(query='Alpha',course='test',limit=3,max_chars=20,max_total_chars=100,context_sections=0))
        self.assertEqual(len(r['hits']),2)
        self.assertTrue(all(h['truncated'] for h in r['hits']))
if __name__=='__main__':unittest.main()


