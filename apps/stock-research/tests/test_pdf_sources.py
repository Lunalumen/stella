import tempfile
import unittest
from pathlib import Path
from stock_agent.cache import Store
from stock_agent.pdf_sources import inspect_pdf,read_page,search,render_page
from stock_agent.providers import import_local

class PDFTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name); self.store=Store(self.root/'data'); self.path=self.root/'synthetic.pdf'
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
        w=PdfWriter();p=w.add_blank_page(width=612,height=792)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        p[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):w._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 40 700 Td (SYNTHETIC Revenue 100; Risk competition) Tj ET')
        p[NameObject('/Contents')]=w._add_object(stream);w.add_blank_page(width=612,height=792)
        w.write(self.path)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_page_text_and_scanned_page_are_distinguished(self):
        d=inspect_pdf(self.store,self.path);self.assertEqual(d['page_count'],2)
        self.assertIn('Revenue 100',d['pages'][0]['text']);self.assertEqual(d['pages'][1]['status'],'no_text_ocr_or_visual_required')
        self.assertFalse(d['visual_verified']);self.assertFalse(d['ocr_performed'])
    def test_unchanged_pdf_is_not_reextracted(self):
        a=inspect_pdf(self.store,self.path);b=inspect_pdf(self.store,self.path)
        self.assertEqual(a['source_hash'],b['source_hash']);self.assertEqual(self.store.stats['extractions'],1)
    def test_rotated_table_text_is_not_mistaken_for_scanned_image(self):
        from pypdf import PdfReader,PdfWriter
        from pypdf.generic import NameObject,DecodedStreamObject
        r=PdfReader(self.path);w=PdfWriter();w.add_page(r.pages[0])
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 0 1 -1 0 500 40 Tm (SYNTHETIC Revenue 100) Tj ET')
        w.pages[0][NameObject('/Contents')]=w._add_object(stream)
        rotated=self.root/'rotated.pdf';w.write(rotated)
        d=inspect_pdf(self.store,rotated);self.assertIn('Revenue 100',d['pages'][0]['text'])
    def test_selected_page_search_and_bounded_output(self):
        d=inspect_pdf(self.store,self.path);sha=d['source_hash']
        r=read_page(self.store,sha,1,max_chars=10);self.assertEqual(len(r['text']),10);self.assertTrue(r['truncated'])
        hits=search(self.store,sha,'Revenue')['hits'];self.assertEqual(hits[0]['page'],1)
        with self.assertRaises(ValueError):read_page(self.store,sha,3)
    def test_pdf_import_preserves_source_and_page_markers(self):
        module=Path(__file__).resolve().parents[3]/'skills/sources/study-cache/scripts/study_cache.py'
        metadata=dict(company_id='US:AAPL',source_url='https://www.sec.gov/fixture.pdf',period='SYNTHETIC',period_end='2025-12-31')
        import_local(self.store,self.path,'text',metadata,module)
        record=self.store.artifact('imports:US:AAPL')[0]
        self.assertIn('[PDF page 1]',record['text']);self.assertIn('[PDF page 2]',record['text'])
    def test_render_is_cached_and_not_claimed_as_reviewed(self):
        import shutil
        if not shutil.which('pdftoppm'):self.skipTest('Poppler is optional outside the bundled environment')
        d=inspect_pdf(self.store,self.path);sha=d['source_hash']
        a=render_page(self.store,sha,1);b=render_page(self.store,sha,1)
        self.assertTrue(Path(a['image']).is_file());self.assertEqual(a['status'],'rendered_not_reviewed');self.assertTrue(b['cached'])

if __name__=='__main__':unittest.main()
