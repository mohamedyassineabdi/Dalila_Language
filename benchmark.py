import argparse,json,time,statistics,platform,os
from pathlib import Path
from dalila.core import rows,classify,classifier,LANGS
from dalila.metrics import scores
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
ROOT=Path(__file__).parent

def textbench():
    import psutil
    data=[r for r in rows() if r['split']=='eval']; results={}
    for target in ('language','intent'):
        for kind in ('word','char'):
            t=time.perf_counter(); classifier(target,kind); fit=time.perf_counter()-t; ts=[]; predictions=[]
            for r in data:
                t=time.perf_counter(); pred=classify(r['text'],target,kind); ts.append(time.perf_counter()-t); predictions.append(pred['label'])
            truth=[r[target] for r in data]; labels=sorted(set(truth)); tn=[i for i,r in enumerate(data) if r['language']=='aeb']
            results[target+'_'+kind]={'accuracy':accuracy_score(truth,predictions),'macro_f1':f1_score(truth,predictions,average='macro',zero_division=0),'tn_accuracy':accuracy_score([truth[i] for i in tn],[predictions[i] for i in tn]),'labels':labels,'confusion':confusion_matrix(truth,predictions,labels=labels).tolist(),'train_s':fit,'median_ms':statistics.median(ts)*1000,'errors':[{'id':r['id'],'expected':r[target],'predicted':p} for r,p in zip(data,predictions) if r[target]!=p]}
    return {'provenance':'synthetic unreviewed draft; not generalization evidence','eval_count':len(data),'dev_count':len(rows())-len(data),'platform':platform.platform(),'rss_mb':psutil.Process().memory_info().rss/1e6,'results':results}

def asrbench(manifest,keys):
    from dalila.engines import transcribe,model
    records=[json.loads(x) for x in manifest.read_text(encoding='utf-8').splitlines() if x.strip()]; results={}
    if not records: raise ValueError('No recordings. Populate manifest with consented human recordings.')
    for key in keys:
        model.cache_clear(); detail=[]
        for r in records:
            if r.get('review_status')!='human_verified' or r.get('consent') is not True or r.get('split')!='eval' or not r.get('reference','').strip(): raise ValueError('Use only verified, consented evaluation recordings')
            try:
                p=manifest.parent/r['audio']; result=transcribe(p,key,r['language']); detail.append(dict(id=r['id'],**result,**scores(r['reference'],result['text'])))
            except Exception as exc: detail.append({'id':r['id'],'error':type(exc).__name__+': '+str(exc)[:300]})
        ok=[d for d in detail if 'wer' in d]; den=sum(d['reference_words'] for d in ok); cden=sum(d['reference_chars'] for d in ok)
        results[key]={'coverage':len(ok)/len(records),'wer_success_only':sum(d['word_edits'] for d in ok)/den if den else None,'cer_success_only':sum(d['char_edits'] for d in ok)/cden if cden else None,'median_rtf':statistics.median(d['rtf'] for d in ok) if ok else None,'detail':detail}
    return results
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--audio',type=Path); p.add_argument('--models',nargs='+',default=['tn-small','tn-whisperx','small','turbo']); p.add_argument('--out',type=Path,default=ROOT/'reports/text_benchmark.json'); a=p.parse_args(); result=asrbench(a.audio,a.models) if a.audio else textbench(); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({k:({m:{j:v for j,v in x.items() if j not in ('errors','confusion','labels')} for m,x in val.items()} if k=='results' else val) for k,val in result.items()},ensure_ascii=False,indent=2))
