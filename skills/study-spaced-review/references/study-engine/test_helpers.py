import json
import re
import unittest
from datetime import datetime
import flexible_grading
import spaced_review

def normalize(value):
    return re.sub(r'[\s\W_]+','',value.casefold())

def record(status,hour):
    q={'id':str(hour),'type':'short','topic':'same','source_ids':['fixture'],'prompt':'sample question','answer':'hidden-key','explanation':'hidden-explanation'}
    return {'id':str(hour),'created':f'2026-01-01T{hour:02}:00:00+09:00','course':'sample',
            'payload':json.dumps({'exam':'기말고사','questions':[q],'scopes':['sample']}),
            'result':json.dumps({'submittedAt':f'2026-01-01T{hour:02}:00:00+09:00','rows':[{'id':str(hour),'status':status}]})}

class Helpers(unittest.TestCase):
    def test_accepted_wrapper(self):
        self.assertEqual(flexible_grading.short_match('정답은 이중 모방입니다.',['이중 모방'],normalize),'wrapper')
    def test_negation_not_correct(self):
        self.assertEqual(flexible_grading.short_match('이중 모방이 아니다',['이중 모방'],normalize),'review')
    def test_exact_due_boundary(self):
        c={'sample':{'name':'Sample'}}
        before=spaced_review.report([record('incorrect',10)],c,now=datetime(2026,1,1,11,59,tzinfo=spaced_review.KST))
        at=spaced_review.report([record('incorrect',10)],c,now=datetime(2026,1,1,12,tzinfo=spaced_review.KST))
        self.assertEqual(before['dueCount'],0);self.assertEqual(at['dueCount'],1)
    def test_correct_after_error_keeps_schedule(self):
        items,_=spaced_review.schedule([record('incorrect',10),record('correct',12)],{'sample':{'name':'Sample'}})
        self.assertEqual(items[0]['due'].hour,14)
    def test_report_has_no_solutions(self):
        report=spaced_review.report([record('incorrect',10)],{'sample':{'name':'Sample'}})
        text=json.dumps(report)
        self.assertNotIn('hidden-key',text);self.assertNotIn('hidden-explanation',text)
    def test_completed_midterm_keeps_final_separate(self):
        r=record('incorrect',10);p=json.loads(r['payload']);p['exam']='중간고사';r['payload']=json.dumps(p)
        old=spaced_review.COMPLETED_COURSES
        try:
            spaced_review.COMPLETED_COURSES={'sample'}
            self.assertEqual(spaced_review.report([r],{'sample':{'name':'Sample'}})['scheduledCount'],0)
            self.assertEqual(spaced_review.report([record('incorrect',10)],{'sample':{'name':'Sample'}})['scheduledCount'],1)
        finally:spaced_review.COMPLETED_COURSES=old

if __name__=='__main__':unittest.main()
