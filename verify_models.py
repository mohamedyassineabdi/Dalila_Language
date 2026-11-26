"""Run with internet on your own PC. Metadata only, no weights or audio upload."""
import json,urllib.request,urllib.error
from pathlib import Path
MODELS=['montachouig/whisperX-tunisian','montachouig/whisper-large-v3-tunisian','TheBiggyBang/whisper-small-tunisian-derja-ct2','oddadmix/Whisperv3-tunisian-codeswitch','algerian-nlp/NUMALIA','Ghazouaniwala/silma-tts-derja','oddadmix/lahgtna-omnivoice-v2','ESPRIT-Group/ESPRIT-Derja-Qwen3-8B-v2']
report={}
for model in MODELS:
 try:
  with urllib.request.urlopen('https://huggingface.co/api/models/'+model+'?blobs=true',timeout=20) as r: m=json.load(r)
  files=[{'path':x.get('rfilename'),'bytes':x.get('size')} for x in m.get('siblings',[])]
  report[model]={'revision':m.get('sha'),'license':(m.get('cardData') or {}).get('license'),'base_model':(m.get('cardData') or {}).get('base_model'),'files':files,'total_known_bytes':sum(x['bytes'] or 0 for x in files),'all_sizes_known':all(x['bytes'] is not None for x in files)}
 except Exception as e: report[model]={'error':str(e)}
Path('reports/model_metadata.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print('Saved reports/model_metadata.json')
