import importlib.util, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
reader=load('reader',ROOT/'read_source.py')
cache=reader.load_cache()
class KnownSource(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.root=Path(self.tmp.name);self.db=self.root/'cache.sqlite'
    def tearDown(self):self.tmp.cleanup()
    def args(self,**kwargs):
        values=dict(file=None,source_id=None,db=self.db,course='demo',query='예산',section=None,limit=3,max_chars=1200,max_total_chars=3600,context_sections=0,offset=0,remote_id='',revision='')
        values.update(kwargs);return NS(**values)
    def test_register_reuse_and_direct_id(self):
        f=self.root/'note.txt';f.write_text('예산은 1200원. 예외는 인턴이다.',encoding='utf-8')
        first=reader.perform(cache,self.args(file=f))
        self.assertEqual(first['cache'],'cached')
        second=reader.perform(cache,self.args(file=f))
        self.assertEqual(second['cache'],'unchanged')
        third=reader.perform(cache,self.args(source_id=first['source_id']))
        self.assertEqual(third['cache'],'existing_source')
        self.assertIn('1200원',third['result']['hits'][0]['text'])
    def test_no_other_document_leak(self):
        a=self.root/'a.txt';a.write_text('질문과 무관한 내용',encoding='utf-8')
        b=self.root/'b.txt';b.write_text('예산 '*200,encoding='utf-8')
        reader.perform(cache,self.args(file=b))
        r=reader.perform(cache,self.args(file=a))
        self.assertEqual(r['result']['hits'],[])
    def test_wrong_course_rejected(self):
        f=self.root/'a.txt';f.write_text('예산',encoding='utf-8')
        r=reader.perform(cache,self.args(file=f))
        with self.assertRaises(ValueError):reader.perform(cache,self.args(source_id=r['source_id'],course='other'))
    def test_changed_file_id_not_reused(self):
        f=self.root/'a.txt';f.write_text('예산 1200원',encoding='utf-8')
        r=reader.perform(cache,self.args(file=f))
        f.write_text('예산 900원',encoding='utf-8')
        stale=reader.perform(cache,self.args(source_id=r['source_id']))
        self.assertFalse(stale['result']['hits'])
        fresh=reader.perform(cache,self.args(file=f))
        self.assertIn('900원',fresh['result']['hits'][0]['text'])
    def test_section_read(self):
        f=self.root/'a.txt';f.write_text('예산 1200원',encoding='utf-8')
        r=reader.perform(cache,self.args(file=f,query=None,section=1))
        self.assertEqual(r['result']['text'],'예산 1200원')
    def test_no_sibling_reference_loading(self):
        self.assertEqual(reader.ROUTES['.pdf'],'references/pdf/READ.md')
        self.assertEqual(reader.ROUTES['.pptx'],'references/ppt/READ.md')
        self.assertFalse(any('http' in str(x) for x in reader.ROUTES.values()))
    def test_pdf_direct_page(self):
        from reportlab.pdfgen import canvas
        f=self.root/'sample.pdf';c=canvas.Canvas(str(f))
        c.drawString(40,800,'Budget 1200 USD. Exception interns excluded.');c.save()
        r=reader.perform(cache,self.args(file=f,query=None,section=1))
        self.assertEqual(r['route'],'references/pdf/READ.md')
        self.assertIn('1200 USD',r['result']['text'])
        self.assertIn('page 1',r['result']['location'])
if __name__=='__main__':unittest.main()


