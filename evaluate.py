"""Comparative evaluation: draft text plus public/consented audio. No cloud by default."""
import argparse,json,time,statistics,os,platform,sys
from pathlib import Path
from collections import Counter
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
from dalila.core import rows,classify,LANGS,INTENTS,numbers
from dalila.semantic import detect,intent,extract,understand
from dalila.metrics import scores
ROOT=Path(__file__).resolve().parent

def load(path): return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def text_eval(data,backend='baseline'):
    reports={}
    for method in ('phase1_word','phase1_char','hybrid'):
        records=[]
        for r in data:
            start=time.perf_counter()
            if method=='hybrid':
                x=understand(r['text'],backend=backend);l=x['language'];i=x['intent']['label'];guess=x['language_detection']['best_guess']; neg=[e['value'] for e in x['mentions'] if e['type']=='negation_marker']; places=[e['canonical_hint'] for e in x['mentions'] if e['type']=='place_mention']; fallback=x['fallback_reason']
            else:
                kind=method.split('_')[-1];l=classify(r['text'],'language',kind)['label'];i=classify(r['text'],'intent',kind)['label'];guess=l;neg=[];places=[];fallback=None
            records.append(dict(id=r['id'],language_ref=r['language'],language_pred=l or 'unknown',language_best_guess=guess,intent_ref=r['intent'],intent_pred=i,ms=1000*(time.perf_counter()-start),negation_exact=sorted(neg)==sorted(r['negation']) if 'negation' in r else None,place_exact=sorted(places)==sorted(r['places']) if 'places' in r else None,fallback=fallback))
        m={}
        for target in ('language','intent'):
            truth=[r[target+'_ref'] for r in records];pred=[r[target+'_pred'] for r in records]; labels=sorted(set(truth)|set(pred)); m[target]={'accuracy':accuracy_score(truth,pred),'macro_f1':f1_score(truth,pred,labels=sorted(set(truth)),average='macro',zero_division=0),'labels':labels,'confusion':confusion_matrix(truth,pred,labels=labels).tolist()}
        tn=[r for r in records if r['language_ref']=='aeb']; covered=[r for r in records if r['language_pred']!='unknown'];m.update(language_coverage=len(covered)/len(records),language_selective_accuracy=sum(r['language_pred']==r['language_ref'] for r in covered)/len(covered) if covered else None,language_best_guess_accuracy=sum(r['language_ref']==r['language_best_guess'] for r in records)/len(records),tn_language_accuracy=sum(r['language_pred']=='aeb' for r in tn)/len(tn) if tn else None,median_ms=statistics.median(r['ms'] for r in records),fallback_count=sum(bool(r['fallback']) for r in records),detail=records)
        for metric in ('negation_exact','place_exact'):
            val=[r[metric] for r in records if r[metric] is not None];m[metric]=sum(val)/len(val) if val else None
        reports[method]=m
    return reports

def audio_eval(manifest,keys,allow_public=False):
    from dalila.engines import transcribe,model
    import psutil
    data=load(manifest)
    if not data: raise ValueError('No audio records')
    ids=set(); paths=set()
    for r in data:
        if r['id'] in ids or r['audio'] in paths: raise ValueError('Duplicate audio or ID')
        ids.add(r['id']);paths.add(r['audio']);p=(manifest.parent/r['audio']).resolve()
        if not p.is_relative_to(manifest.parent.resolve()) or not p.is_file(): raise ValueError('Invalid audio path')
        human=r.get('consent') is True and r.get('review_status')=='human_verified'
        public=allow_public and r.get('provenance')=='published_test' and bool(r.get('source')) and bool(r.get('license'))
        if r.get('sha256'):
            import hashlib
            if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']: raise ValueError('Audio integrity mismatch')
        if r.get('split')!='eval' or not r.get('reference','').strip() or not (human or public): raise ValueError('Only reviewed consented recordings or explicit published test records')
    results={}
    for key in keys:
        model.cache_clear();detail=[];start=time.perf_counter(); total_words=total_chars=total_we=total_ce=0
        for r in data:
            try:
                x=transcribe(manifest.parent/r['audio'],key,r['language']); hyp=x['text'];error=None
            except Exception as exc: x={};hyp='';error=type(exc).__name__+': '+str(exc)[:220]
            metric=scores(r['reference'],hyp);total_words+=metric['reference_words'];total_chars+=metric['reference_chars'];total_we+=metric['word_edits'];total_ce+=metric['char_edits']; e=extract(hyp);ref_entities=r.get('critical_entities'); ref_neg=r.get('critical_negation');
            detail.append({'id':r['id'],'reference':r['reference'],'hypothesis':hyp,'error':error,'code_switch':r.get('code_switch'),**x,**metric,'numbers_exact':metric['numbers_exact'] if numbers(r['reference']) else None,'intent_correct':intent(hyp)['label']==r['intent'] if hyp and r.get('intent') else False if r.get('intent') else None,'critical_entities_exact':all(v.casefold() in hyp.casefold() for v in ref_entities) if ref_entities else None,'critical_negation_preserved':ref_neg.casefold() in hyp.casefold() if ref_neg else None,'rss_mb_after':psutil.Process().memory_info().rss/1e6})
        ok=[d for d in detail if not d['error']];res={'n':len(data),'coverage':len(ok)/len(data),'wer_all_failure_as_empty':total_we/total_words,'cer_all_failure_as_empty':total_ce/total_chars,'median_rtf_success_only':statistics.median(d['rtf'] for d in ok) if ok else None,'wall_s':time.perf_counter()-start,'max_sampled_rss_mb':max(d['rss_mb_after'] for d in detail),'detail':detail}
        for metric in ('numbers_exact','intent_correct','critical_entities_exact','critical_negation_preserved'):
            val=[d[metric] for d in detail if d[metric] is not None];res[metric]=sum(val)/len(val) if val else None
        results[key]=res;print(key,'coverage',res['coverage'],'WER',res['wer_all_failure_as_empty'],flush=True)
    return results
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--text',type=Path);p.add_argument('--audio',type=Path);p.add_argument('--public',action='store_true');p.add_argument('--models',nargs='+',default=['tn-small','tn-whisperx','small','turbo']);p.add_argument('--backend',choices=['baseline','ollama'],default='baseline');p.add_argument('--out',type=Path,default=ROOT/'reports/advanced_text.json');a=p.parse_args();r=audio_eval(a.audio,a.models,a.public) if a.audio else text_eval(load(a.text) if a.text else [x for x in rows() if x['split']=='eval'],a.backend);a.out.parent.mkdir(exist_ok=True,parents=True);a.out.write_text(json.dumps({'provenance':'published or consented audio; check source overlap' if a.audio else 'synthetic drafts, iterative development; not blind validation','platform':platform.platform(),'results':r},ensure_ascii=False,indent=2),encoding='utf-8'); print('Saved',a.out)
