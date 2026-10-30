"""Offline text-token and caller-supplied whole-task usage comparisons. Never calls an AI API."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

def integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + ' must be a non-negative integer')
    return value

def delta(before, after):
    return {'before': before, 'after': after, 'saved': before-after,
            'reduction_percent': round(100*(before-after)/before, 2) if before else None}

def read_json(path):
    return json.loads(Path(path).read_text('utf-8-sig'))

def text_comparison(before, after, encoding, required):
    a, b = len(encoding.encode_ordinary(before)), len(encoding.encode_ordinary(after))
    if not isinstance(required,list) or any(not isinstance(x,str) or not x for x in required):
        raise ValueError('required facts must be a list of nonempty strings')
    baseline_missing = [x for x in required if x not in before]
    missing = [x for x in required if x not in after]
    if baseline_missing:
        status='invalid_baseline'
    elif missing:
        status='required_text_missing'
    elif b<a:
        status='text_tokens_reduced_only'
    elif b==a:
        status='text_tokens_unchanged'
    else:
        status='text_tokens_increased'
    return {'mode':'text','status':status,'encoding':encoding.name,'text_tokens':delta(a,b),
            'required_literal_checks':{'count':len(required),'baseline_missing':baseline_missing,'after_missing':missing},
            'semantic_quality_verified':False,'whole_task_savings_verified':False,
            'sha256':{'before':hashlib.sha256(before.encode()).hexdigest(),'after':hashlib.sha256(after.encode()).hexdigest()},
            'caveat':'Supplied plain text only; excludes hidden context, tool wrapping, images, output/reasoning, retries and preparation calls.'}

def summarize_run(run):
    if run.get('origin') not in {'usage_export','synthetic_test'}:
        raise ValueError('origin must be usage_export or synthetic_test')
    for name in ['task_id','model','config_id','quality_basis']:
        if not isinstance(run.get(name),str) or not run[name].strip():
            raise ValueError('Missing ' + name)
    if not isinstance(run.get('calls'),list) or not run['calls']:
        raise ValueError('Provide all calls, including preparation and retries')
    sums={'input_tokens':0,'output_tokens':0,'total_tokens':0,'cached_tokens':0,'reasoning_tokens':0}
    seen=set()
    for call in run['calls']:
        cid=call.get('id')
        if not isinstance(cid,str) or not cid or cid in seen:
            raise ValueError('Each call needs a unique nonempty id')
        seen.add(cid)
        u=call.get('usage')
        if not isinstance(u,dict): raise ValueError('Missing per-call usage')
        inp=integer(u.get('input_tokens'),'input_tokens')
        out=integer(u.get('output_tokens'),'output_tokens')
        total=integer(u.get('total_tokens',inp+out),'total_tokens')
        if total!=inp+out: raise ValueError('total_tokens must equal input_tokens + output_tokens')
        cached=integer(u.get('input_tokens_details',{}).get('cached_tokens',0),'cached_tokens')
        reasoning=integer(u.get('output_tokens_details',{}).get('reasoning_tokens',0),'reasoning_tokens')
        if cached>inp or reasoning>out: raise ValueError('Detail tokens cannot exceed their parent category')
        for k,v in [('input_tokens',inp),('output_tokens',out),('total_tokens',total),('cached_tokens',cached),('reasoning_tokens',reasoning)]:
            sums[k]+=v
    return {'calls':len(seen),**sums,
            'cached_detail_complete':all('cached_tokens' in c['usage'].get('input_tokens_details',{}) for c in run['calls']),
            'reasoning_detail_complete':all('reasoning_tokens' in c['usage'].get('output_tokens_details',{}) for c in run['calls'])}

def usage_comparison(before, after):
    a,b=summarize_run(before),summarize_run(after)
    synthetic=before['origin']=='synthetic_test' or after['origin']=='synthetic_test'
    reasons=[]
    for k in ['task_id','model','config_id']:
        if before[k]!=after[k]: reasons.append(k+'_mismatch')
    for label,run in [('before',before),('after',after)]:
        if run.get('scope')!='whole_task' or run.get('complete') is not True:
            reasons.append(label+'_incomplete_scope')
        if run.get('quality_passed') is not True: reasons.append(label+'_quality_not_passed')
    if synthetic: reasons.append('synthetic_usage_not_real_measurement')
    status='insufficient_evidence' if reasons else ('reported_tokens_reduced' if b['total_tokens']<a['total_tokens'] else 'reported_tokens_not_reduced')
    return {'mode':'usage','status':status,'reasons':reasons,'before':a,'after':b,
            'observed_total':delta(a['total_tokens'],b['total_tokens']),
            'evidence':'synthetic fixture' if synthetic else 'caller-supplied usage export; authenticity and completeness not independently verified',
            'quality_basis':{'before':before['quality_basis'],'after':after['quality_basis']},
            'cost_savings_verified':False,'caveat':'Cache and reasoning are subsets, not added twice. No subscription-cost or API-price estimate.'}

def tokenizer(encoding, runtime, cache):
    if runtime: sys.path.insert(0,str(Path(runtime).resolve()))
    if cache: os.environ['TIKTOKEN_CACHE_DIR']=str(Path(cache).resolve())
    try:
        import tiktoken
        import tiktoken.load
    except ImportError as exc:
        raise ValueError('Text counting needs tiktoken; use an explicitly prepared runtime') from exc
    def deny_download(path):
        raise ValueError('Tokenizer data is not cached; prepare it explicitly before offline use')
    tiktoken.load.read_file=deny_download
    return tiktoken.get_encoding(encoding)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path)
    sub=p.add_subparsers(dest='mode',required=True)
    t=sub.add_parser('text')
    t.add_argument('before',type=Path);t.add_argument('after',type=Path)
    t.add_argument('--encoding',required=True)
    t.add_argument('--runtime',type=Path);t.add_argument('--cache-dir',type=Path)
    t.add_argument('--required',type=Path,help='JSON list of literal facts; not a semantic grader')
    u=sub.add_parser('usage');u.add_argument('before',type=Path);u.add_argument('after',type=Path)
    args=p.parse_args()
    if args.output and args.output.resolve() in {args.before.resolve(),args.after.resolve(),getattr(args,'required',None).resolve() if getattr(args,'required',None) else None}:
        raise ValueError('Output must not overwrite evidence inputs')
    if args.mode=='text':
        enc=tokenizer(args.encoding,args.runtime,args.cache_dir)
        result=text_comparison(args.before.read_text('utf-8-sig'),args.after.read_text('utf-8-sig'),enc,read_json(args.required) if args.required else [])
    else: result=usage_comparison(read_json(args.before),read_json(args.after))
    rendered=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        if args.output.exists(): raise ValueError('Output already exists; choose a new path')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(rendered+'\n',encoding='utf-8')
    print(rendered)

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);sys.exit(1)


