import copy, importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('audit',ROOT/'token_audit.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
def run(tokens=1000):
    return {'origin':'usage_export','task_id':'example','model':'same-model','config_id':'same-settings','scope':'whole_task','complete':True,'quality_passed':True,'quality_basis':'Independent comparison supplied by reviewer','calls':[{'id':'one','usage':{'input_tokens':tokens-100,'output_tokens':100,'input_tokens_details':{'cached_tokens':50},'output_tokens_details':{'reasoning_tokens':40}}}]}
class Audit(unittest.TestCase):
    def test_logged_reduction(self):
        self.assertEqual(audit.usage_comparison(run(),run(800))['status'],'reported_tokens_reduced')
    def test_overhead_counts(self):
        after=run(500);after['calls'].append({'id':'preparation','usage':{'input_tokens':700,'output_tokens':100}})
        self.assertEqual(audit.usage_comparison(run(),after)['status'],'reported_tokens_not_reduced')
    def test_details_not_double_counted(self):
        self.assertEqual(audit.summarize_run(run())['total_tokens'],1000)
    def test_missing_evidence_blocks_success(self):
        for key,value in [('complete',False),('quality_passed',False),('model','different'),('origin','synthetic_test')]:
            b=run(800);b[key]=value
            self.assertEqual(audit.usage_comparison(run(),b)['status'],'insufficient_evidence')
    def test_duplicate_ids_rejected(self):
        r=run();r['calls']*=2
        with self.assertRaises(ValueError):audit.summarize_run(r)
    def test_bad_numbers_rejected(self):
        for value in [-1,True,None,1.5]:
            r=run();r['calls'][0]['usage']['input_tokens']=value
            with self.assertRaises(ValueError):audit.summarize_run(r)
    def test_empty_baseline_not_percent(self):
        self.assertIsNone(audit.delta(0,10)['reduction_percent'])
    def test_missing_usage_rejected(self):
        r=run();r['calls'][0].pop('usage')
        with self.assertRaises(ValueError):audit.summarize_run(r)
if __name__=='__main__':unittest.main()
