"""One-time explicit model downloads with repository revision recorded. No user audio uploaded."""
import argparse,json,os
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT","10")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT","60")
from pathlib import Path
from huggingface_hub import HfApi,snapshot_download
from dalila.engines import ASR
REPOS={**ASR,'small':'Systran/faster-whisper-small','turbo':'mobiuslabsgmbh/faster-whisper-large-v3-turbo','large-v3':'Systran/faster-whisper-large-v3'}
ROOT=Path(__file__).resolve().parent

def prepare(keys):
    api=HfApi(); out={}
    for key in keys:
        repo=REPOS[key]
        try:
            info=api.model_info(repo,files_metadata=True,timeout=15); rev=info.sha
            dest=ROOT/'models'/key; dest.mkdir(parents=True,exist_ok=True)
            if key=='tn-codeswitch':
                source=Path(snapshot_download(repo,revision=rev,allow_patterns=['*.safetensors','*.json','*.txt','*.model']))
                from ctranslate2.converters import TransformersConverter
                copies=[x for x in ['tokenizer.json','preprocessor_config.json'] if (source/x).exists()]
                TransformersConverter(str(source),copy_files=copies).convert(str(dest),quantization='int8',force=True)
            else:
                snapshot_download(repo,revision=rev,local_dir=str(dest),allow_patterns=['*.bin','*.json','*.txt','*.model','README.md','LICENSE*'])
            if not (dest/'model.bin').is_file(): raise ValueError('No CTranslate2 model.bin')
            out[key]={'status':'downloaded','repo':repo,'revision':rev,'license':getattr(info.card_data,'license',None),'path':str(dest.relative_to(ROOT)),'bytes':sum(x.stat().st_size for x in dest.rglob('*') if x.is_file())}
        except Exception as exc: out[key]={'status':'failed','repo':repo,'error':type(exc).__name__+': '+str(exc)[:350]}
        (ROOT/'reports/prepared_models.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
        print(key,out[key]['status'],flush=True)
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--models',nargs='+',choices=REPOS,default=['tn-small','tn-whisperx','small']);a=p.parse_args();prepare(a.models)
