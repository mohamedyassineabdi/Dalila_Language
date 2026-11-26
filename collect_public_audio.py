"""Download a small published LinTO test sample. Never claims independent or personally consented data.
Run only after checking dataset/subsource terms; model training overlap likely. No raw data in release ZIP.
"""
import argparse,json,hashlib,io,random
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO='linagora/linto-dataset-audio-ar-tn'

def collect(n,output,accept):
    if not accept: raise PermissionError('Review dataset license and source terms, then pass --accept-public-terms')
    from huggingface_hub import HfApi
    from datasets import load_dataset,Audio
    import soundfile as sf
    api=HfApi();info=api.dataset_info(REPO);revision=info.sha
    license=getattr(info.card_data,'license',None)
    if license!='cc-by-4.0': raise RuntimeError('Dataset license differs from expected CC BY 4.0; review')
    ds=load_dataset(REPO,'default',split='test',streaming=True,revision=revision).cast_column('audio',Audio(decode=False)).shuffle(seed=42,buffer_size=128)
    output.mkdir(parents=True,exist_ok=True); (output/'wav').mkdir(exist_ok=True);rows=[];seen=set()
    for row in ds:
        if len(rows)>=n: break
        ref=str(row.get('transcript') or '').strip(); aid=str(row.get('audio_id') or '')
        if not ref or not aid or aid in seen:continue
        audio=row['audio'];data=audio.get('bytes');
        if not data: continue
        try:
            y,sr=sf.read(io.BytesIO(data),dtype='float32');duration=len(y)/sr
        except Exception: continue
        if not 1<=duration<=25:continue
        seen.add(aid);name=hashlib.sha256(aid.encode()).hexdigest()[:20]; dest=output/'wav'/f'{name}.wav'; sf.write(dest,y,sr,subtype='PCM_16')
        rows.append(dict(id=name,audio=f'wav/{name}.wav',reference=ref,language='aeb',split='eval',provenance='published_test',review_status='published_reference_unreviewed_by_team',source=REPO,source_revision=revision,source_config='default',source_split='test',source_audio_id=aid,license=license,duration_s=duration,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),training_overlap='possible_or_likely'))
        print(len(rows),aid,flush=True)
    if not rows: raise RuntimeError('No usable public test audio; inspect dataset schema')
    manifest=output/'manifest.jsonl';manifest.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8'); print('Saved',len(rows),'of',n,'to',manifest)
    return manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=60);p.add_argument('--output',type=Path,default=ROOT/'data/public_linto');p.add_argument('--accept-public-terms',action='store_true');a=p.parse_args();collect(a.limit,a.output,a.accept_public_terms)
