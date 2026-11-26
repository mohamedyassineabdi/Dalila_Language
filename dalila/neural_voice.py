"""CPU neural voice adapters. Model files are public; user text stays local."""
import importlib.util
import logging
import threading
import time
import wave
from functools import lru_cache
from pathlib import Path

REPO='rhasspy/piper-voices'
REVISION='5b44ec7bab7c5822cfec48fbd5aa99db71a823d6'
VOICES={
    'ar':'ar/ar_JO/kareem/medium/ar_JO-kareem-medium',
    'fr':'fr/fr_FR/siwis/medium/fr_FR-siwis-medium',
    'en':'en/en_US/lessac/medium/en_US-lessac-medium',
    'de':'de/de_DE/thorsten/medium/de_DE-thorsten-medium',
    'tr':'tr/tr_TR/dfki/medium/tr_TR-dfki-medium',
}
VOICE_LOCK=threading.RLock()
PREP_LOCK=threading.Lock()
STATUS={k:'not_prepared' for k in VOICES}
PATHS={}
LOG=logging.getLogger(__name__)

def available():
    return importlib.util.find_spec('piper') is not None

def files_for(voice, download=False):
    from huggingface_hub import hf_hub_download
    stem=VOICES[voice]
    args=dict(repo_id=REPO,revision=REVISION,token=False,local_files_only=not download)
    model=hf_hub_download(filename=stem+'.onnx',**args)
    config=hf_hub_download(filename=stem+'.onnx.json',**args)
    return model,config

def prepare(voice, download=True):
    if not available(): return False
    with PREP_LOCK:
        if voice in PATHS:return True
        STATUS[voice]='preparing'
        try:
            PATHS[voice]=files_for(voice,download)
            STATUS[voice]='ready'
            return True
        except Exception as exc:
            STATUS[voice]='unavailable'
            LOG.warning('Neural voice %s: %s',voice,type(exc).__name__)
            return False

def prepare_all():
    for voice in ('ar','en','fr','de','tr'):
        prepare(voice)

def readiness():
    return dict(STATUS)

@lru_cache(maxsize=2)
def load_voice(model,config):
    from piper import PiperVoice
    return PiperVoice.load(model,config_path=config,use_cuda=False)

def speak_neural(text,voice,output):
    if not available(): raise RuntimeError('Piper not installed')
    # Never download synchronously during a chat turn.
    paths=PATHS.get(voice)
    if paths is None:
        if STATUS[voice]=='preparing': raise RuntimeError('Voice preparing')
        paths=files_for(voice,download=False)
        PATHS[voice]=paths
        STATUS[voice]='ready'
    started=time.perf_counter()
    with VOICE_LOCK:
        speaker=load_voice(*paths)
        with wave.open(str(output),'wb') as wav:
            speaker.synthesize_wav(text,wav)
    return {'engine':'piper','voice':VOICES[voice].split('/')[-1],
            'generation_s':round(time.perf_counter()-started,3),'dialect_authentic':False}
