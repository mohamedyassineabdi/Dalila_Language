"""Optional experiment with custom remote architecture. Never execute code before explicit review."""
import argparse,json,os,time
from pathlib import Path
from sklearn.metrics import accuracy_score,f1_score
from dalila.core import rows
from dalila.semantic import detect
REPO='algerian-nlp/NUMALIA'
MAP={'tunisian':'aeb','algerian':'arq','libyan':'ayl','msa':'ar','french':'fr'}
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--download-for-review',action='store_true');p.add_argument('--reviewed-local-path',type=Path);p.add_argument('--i-reviewed-code',action='store_true');a=p.parse_args()
 if a.download_for_review:
  from huggingface_hub import HfApi,snapshot_download
  sha=HfApi().model_info(REPO).sha;folder=snapshot_download(REPO,revision=sha,local_dir=str(ROOT/'models/numalia'),allow_patterns=['*.py','*.json','*.safetensors','*.md','LICENSE*']);print('Downloaded without execution. Review all Python code and licensing in',folder,'revision',sha)
 elif a.reviewed_local_path and a.i_reviewed_code:
  from transformers import AutoModelForSequenceClassification
  m=AutoModelForSequenceClassification.from_pretrained(str(a.reviewed_local_path.resolve()),local_files_only=True,trust_remote_code=True).eval()
  data=[r for r in rows() if r['split']=='eval' and r['language'] in MAP.values()]; truth=[r['language'] for r in data];start=time.perf_counter(); result=m.identify([r['text'] for r in data]);pred=[MAP.get(r.language,'unknown') for r in result];detail=[{'id':x['id'],'expected':x['language'],'predicted':y,'prediction_set':list(r.prediction_set),'confidence':float(r.confidence)} for x,y,r in zip(data,pred,result)]; report={'provenance':'synthetic draft, supported languages only','n':len(data),'accuracy':accuracy_score(truth,pred),'macro_f1':f1_score(truth,pred,labels=sorted(set(truth)),average='macro',zero_division=0),'wall_s':time.perf_counter()-start,'detail':detail};(ROOT/'reports/numalia.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(report['accuracy'])
 else: p.error('First download for review; only execute audited local model code in an isolated environment.')
