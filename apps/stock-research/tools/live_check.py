"""Live no-paid-API smoke check; reuse a manually reviewed, source-bound example."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stock_agent.cache import Store
from stock_agent.engine import Research

def request(text):
    store=Store(ROOT/'private/research')
    try:return Research(store).run(text,as_of='2026-10-22',target='KR:005930')
    finally:store.close()

def main():
    first=request('삼성전자 기업 분석')
    summary=json.loads((ROOT/'private/verification/samsung-reviewed-summary.json').read_text('utf-8'))
    store=Store(ROOT/'private/research')
    try:saved=Research(store).complete(first['fingerprint'],summary)
    finally:store.close()
    repeat=request('삼성전자 기업 분석')
    update=request('이 기업의 새 실적만 반영해서 업데이트')
    risk=request('지난 분석 이후 바뀐 위험 요인 알려줘')
    result=dict(first=first,repeat=repeat,update=update,risk=risk,sample=saved,
                scope='Live official IR/optional public quote + manually checked Samsung PDF facts; SEC/DART authenticated routes not exercised',
                tokens='unmeasured; current chat usage unavailable; no additional model API calls')
    (ROOT/'private/verification/live-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for key in ('first','repeat','update','risk'):
        x=result[key]; print(json.dumps(dict(stage=key,status=x['status'],changes=x['changes'],stats=x['stats']),ensure_ascii=False))
    print(json.dumps(saved,ensure_ascii=False))
    return 0 if repeat['status']=='analysis_reused' and repeat['changes']==0 and repeat['stats']['external_requests']==0 else 1

if __name__=='__main__':sys.exit(main())
