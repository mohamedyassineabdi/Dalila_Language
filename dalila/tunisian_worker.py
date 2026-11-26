"""Isolated local OmniVoice research worker; synthetic voice, no reference or cloud inference."""
import contextlib
import json
import os
from pathlib import Path
import sys
import time

MODEL_ID = "k2-fsa/OmniVoice"
REVISION = "995b1b114ae423a4fd69b3834a6fd86423dd361c"

def emit(obj):
    print(json.dumps(obj,ensure_ascii=True),flush=True)

def load():
    from huggingface_hub import snapshot_download
    import torch
    from omnivoice import OmniVoice
    model_dir=snapshot_download(MODEL_ID,revision=REVISION,token=False,
                                allow_patterns=["*.json","*.safetensors","*.jinja","*.txt"])
    if not (Path(model_dir)/"audio_tokenizer").is_dir():
        raise RuntimeError("Pinned snapshot lacks audio tokenizer")
    torch.set_num_threads(min(4,os.cpu_count() or 1))
    model=OmniVoice.from_pretrained(model_dir,device_map="cpu",dtype=torch.float32,load_asr=False,
                                    local_files_only=True)
    if "aeb" not in model.supported_language_ids():
        raise RuntimeError("Tunisian language ID missing")
    return model

def generate(model,text,output):
    import soundfile as sf
    import numpy as np
    started=time.perf_counter()
    audio=model.generate(text=text,language="aeb",num_step=16)
    samples=np.asarray(audio[0],dtype=np.float32).reshape(-1)
    rate=int(model.sampling_rate)
    if not samples.size or not np.isfinite(samples).all() or np.max(np.abs(samples))<1e-5:
        raise RuntimeError("Invalid synthesized audio")
    sf.write(str(output),samples,rate,subtype="PCM_16")
    return {"seconds":round(time.perf_counter()-started,3),"audio_seconds":round(samples.size/rate,3)}

def main():
    if os.getenv("DALILA_TUNISIAN_RESEARCH","0")!="1":
        raise SystemExit("Research mode must be explicitly enabled")
    # Libraries may print progress; reserve stdout for machine-readable messages.
    with contextlib.redirect_stdout(sys.stderr):
        model=load()
    emit({"ready":True})
    for line in sys.stdin:
        try:
            req=json.loads(line)
            text=req["text"]
            if not isinstance(text,str) or not text.strip() or len(text)>1200:
                raise ValueError("Invalid text")
            with contextlib.redirect_stdout(sys.stderr):
                result=generate(model,text,req["output"])
            emit({"ok":True,**result})
        except Exception as exc:
            emit({"ok":False,"error":type(exc).__name__})

if __name__=="__main__":
    main()
