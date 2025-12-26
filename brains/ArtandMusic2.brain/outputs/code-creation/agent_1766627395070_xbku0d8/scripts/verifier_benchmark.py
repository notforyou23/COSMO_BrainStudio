import argparse, json, math, random, time
from pathlib import Path

ROOT = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')

def load_dataset(path: Path):
    if path and path.exists():
        txt = path.read_text(encoding='utf-8').strip()
        if not txt: return []
        if txt.lstrip().startswith('['): data = json.loads(txt)
        else: data = [json.loads(l) for l in txt.splitlines() if l.strip()]
        out=[]
        for i,x in enumerate(data):
            q=x.get('question') or x.get('q'); a=x.get('answer') or x.get('gold') or x.get('a')
            ev=x.get('evidence') or x.get('contexts') or []
            if isinstance(ev, dict): ev=[ev]
            ev=[{'id':e.get('id',str(j)),'text':e.get('text') or e.get('snippet') or '', 'citation':e.get('citation') or e.get('cite') or e.get('id',str(j))} for j,e in enumerate(ev)]
            if q and a and ev: out.append({'id':x.get('id',str(i)),'question':q,'answer':a,'evidence':ev})
        return out
    return [
        {'id':'0','question':'What is the capital of France?','answer':'Paris.','evidence':[{'id':'e0','citation':'wiki:France','text':'France\'s capital city is Paris.'}]},
        {'id':'1','question':'Which gas do plants absorb for photosynthesis?','answer':'Carbon dioxide (CO2).','evidence':[{'id':'e0','citation':'bio:textbook','text':'Plants take in carbon dioxide and release oxygen during photosynthesis.'}]},
        {'id':'2','question':'Who wrote Hamlet?','answer':'William Shakespeare.','evidence':[{'id':'e0','citation':'lit:enc','text':'Hamlet is a tragedy written by William Shakespeare.'}]},
    ]

def normalize(s): 
    return ' '.join(''.join(ch.lower() if ch.isalnum() or ch.isspace() else ' ' for ch in s).split())

def token_set(s): 
    return set(normalize(s).split())

def jaccard(a,b):
    A,B=token_set(a),token_set(b)
    return (len(A&B)/(len(A|B) or 1))

def simple_generator(question, evidence, seed=0, style=0):
    rnd=random.Random(seed+style*1337)
    ev = sorted(evidence, key=lambda e: -len(e.get('text','')))
    snippet = ev[0]['text'] if ev else ''
    cite = ev[0].get('citation','e0') if ev else 'e0'
    # style variations
    if style==0: ans = snippet.split('.')[0].strip() + '.'
    elif style==1: ans = f"Based on the evidence [{cite}], " + (snippet.split('.')[0].strip() + '.')
    else:
        words=normalize(snippet).split()
        pick=' '.join(words[:min(len(words), 9+rnd.randint(0,6))]).strip()
        ans = (pick or 'I cannot determine from evidence.') + f" [{cite}]"
    return ans

def verifier_attribution(answer, evidence):
    # score: overlap with any evidence + presence of a citation-like marker
    best=max((jaccard(answer, e['text']) for e in evidence), default=0.0)
    has_cite = ('[' in answer and ']' in answer) or any(e.get('citation','') in answer for e in evidence)
    score = 0.75*best + 0.25*(1.0 if has_cite else 0.0)
    return score, {'best_overlap':best,'has_cite':has_cite}

def verifier_critique(answer, evidence):
    # heuristic: penalize very short/very long answers and low overlap
    overlap=max((jaccard(answer, e['text']) for e in evidence), default=0.0)
    ln=len(normalize(answer).split())
    length_ok = 1.0 if 3 <= ln <= 40 else 0.0
    score=0.6*overlap+0.4*length_ok
    critique = 'ok' if score>=0.6 else ('low_overlap' if overlap<0.4 else 'length_issue')
    return score, {'overlap':overlap,'len':ln,'critique':critique}

def pattern_best_of_n(ex, n, seed):
    cands=[]
    for i in range(n):
        a=simple_generator(ex['question'], ex['evidence'], seed=seed, style=i%3)
        s,meta=verifier_attribution(a, ex['evidence'])
        cands.append({'answer':a,'score':s,'meta':meta})
    best=max(cands, key=lambda x:x['score'])
    return best['answer'], float(best['score']), {'candidates':cands,'selected':'best_score'}

def pattern_entailment_over_evidence(ex, seed):
    a=simple_generator(ex['question'], ex['evidence'], seed=seed, style=2)
    s,meta=verifier_attribution(a, ex['evidence'])
    if s<0.6:
        # revise: force explicit citation and tighter extraction
        ev=ex['evidence'][0]
        a=f"{ev['text'].split('.')[0].strip()}. [{ev.get('citation','e0')}]"
        s2,meta2=verifier_attribution(a, ex['evidence'])
        return a, float(max(s,s2)), {'initial':meta,'revised':meta2,'selected':'revised' if s2>s else 'initial'}
    return a, float(s), {'initial':meta,'selected':'initial'}

def pattern_self_consistency_gate(ex, k, seed):
    cands=[]
    for i in range(k):
        a=simple_generator(ex['question'], ex['evidence'], seed=seed+i*17, style=i%3)
        s1,_=verifier_attribution(a, ex['evidence'])
        s2,meta=verifier_critique(a, ex['evidence'])
        score=0.5*s1+0.5*s2
        cands.append({'answer':a,'score':score,'meta':meta})
    cands.sort(key=lambda x:-x['score'])
    top=cands[0]
    if top['score']<0.65:
        # abstain-like revision: quote evidence directly
        ev=ex['evidence'][0]
        a=f"{ev['text'].split('.')[0].strip()}. [{ev.get('citation','e0')}]"
        s,_=verifier_attribution(a, ex['evidence'])
        return a, float(max(top['score'],s)), {'candidates':cands,'selected':'fallback'}
    return top['answer'], float(top['score']), {'candidates':cands,'selected':'top'}

def exactish_match(pred, gold):
    return normalize(gold) in normalize(pred) or normalize(pred) in normalize(gold) or jaccard(pred,gold)>=0.6

def metrics(rows, bins=10):
    y=[1 if r['is_correct'] else 0 for r in rows]
    p=[min(1.0,max(0.0,float(r['verifier_score']))) for r in rows]
    # error detection: treat "flag error" if score < t
    ts=[i/100 for i in range(1,100)]
    best={'f1':-1}
    for t in ts:
        pred_err=[1 if s<t else 0 for s in p]
        true_err=[1-yy for yy in y]
        tp=sum(1 for pe,te in zip(pred_err,true_err) if pe==1 and te==1)
        fp=sum(1 for pe,te in zip(pred_err,true_err) if pe==1 and te==0)
        fn=sum(1 for pe,te in zip(pred_err,true_err) if pe==0 and te==1)
        prec=tp/(tp+fp or 1); rec=tp/(tp+fn or 1)
        f1=2*prec*rec/(prec+rec or 1)
        if f1>best['f1']: best={'t':t,'precision':prec,'recall':rec,'f1':f1}
    # calibration (ECE)
    bs=[[] for _ in range(bins)]
    for yy,ss in zip(y,p):
        bi=min(bins-1,int(ss*bins))
        bs[bi].append((ss,yy))
    ece=0.0; cal=[]
    n=len(rows) or 1
    for i,b in enumerate(bs):
        if not b: 
            cal.append({'bin':i,'count':0,'p_avg':None,'acc':None}); continue
        pavg=sum(s for s,_ in b)/len(b); acc=sum(yy for _,yy in b)/len(b)
        ece += (len(b)/n)*abs(acc-pavg)
        cal.append({'bin':i,'count':len(b),'p_avg':pavg,'acc':acc})
    # AUROC/AUPRC (prob=correct)
    pairs=sorted(zip(p,y), key=lambda x:-x[0])
    P=sum(y); N=len(y)-P
    tpr=fpr=0.0; prev=None; auc=0.0
    for s,yy in pairs:
        if prev is not None and s!=prev: auc += (fpr-prev_fpr)*(tpr+prev_tpr)/2
        if s!=prev: prev,prev_tpr,prev_fpr=s,tpr,fpr
        if yy==1: tpr += 1/(P or 1)
        else: fpr += 1/(N or 1)
    auc += (fpr-prev_fpr)*(tpr+prev_tpr)/2 if prev is not None else 0.0
    # AUPRC
    tp=fp=0; ap=0.0; last_rec=0.0
    for s,yy in pairs:
        if yy==1: tp+=1
        else: fp+=1
        prec=tp/(tp+fp or 1); rec=tp/(P or 1)
        ap += prec*(rec-last_rec); last_rec=rec
    return {'n':len(rows),'accuracy':sum(y)/n,'error_detection_best':best,'ece':ece,'calibration_bins':cal,'auroc':auc,'auprc':ap}

def run(args):
    ds=load_dataset(Path(args.dataset) if args.dataset else None)
    rnd=random.Random(args.seed)
    patterns={
        'best_of_n': lambda ex: pattern_best_of_n(ex, args.n, rnd.randint(0,10**9)),
        'entailment_evidence': lambda ex: pattern_entailment_over_evidence(ex, rnd.randint(0,10**9)),
        'self_consistency_gate': lambda ex: pattern_self_consistency_gate(ex, args.k, rnd.randint(0,10**9)),
    }
    chosen=[p for p in args.patterns.split(',') if p in patterns]
    if not chosen: chosen=['best_of_n','entailment_evidence','self_consistency_gate']
    run_id=args.run_id or time.strftime('%Y%m%d_%H%M%S')
    out_dir=ROOT/'runs'/'verifier_benchmark'/run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    all_results={}
    for pname in chosen:
        rows=[]
        for ex in ds[:args.limit or None]:
            pred,score,meta=patterns[pname](ex)
            ok=exactish_match(pred, ex['answer'])
            rows.append({'id':ex['id'],'question':ex['question'],'gold_answer':ex['answer'],'pred_answer':pred,
                         'verifier_score':score,'is_correct':ok,'pattern':pname,'meta':meta,
                         'evidence':[{'id':e['id'],'citation':e.get('citation'), 'text':e['text']} for e in ex['evidence']]})
        m=metrics(rows, bins=args.cal_bins)
        all_results[pname]={'metrics':m,'rows':rows}
        (out_dir/f'{pname}.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n', encoding='utf-8')
        (out_dir/f'{pname}_metrics.json').write_text(json.dumps(m,indent=2,ensure_ascii=False), encoding='utf-8')
    (out_dir/'summary.json').write_text(json.dumps({p:all_results[p]['metrics'] for p in all_results},indent=2,ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'run_id':run_id,'out_dir':str(out_dir),'patterns':chosen,'n_examples':len(ds[:args.limit or None])}, ensure_ascii=False))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dataset', type=str, default='')
    ap.add_argument('--patterns', type=str, default='best_of_n,entailment_evidence,self_consistency_gate')
    ap.add_argument('--n', type=int, default=3)
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--cal-bins', dest='cal_bins', type=int, default=10)
    ap.add_argument('--run-id', type=str, default='')
    args=ap.parse_args()
    run(args)

if __name__=='__main__': main()
