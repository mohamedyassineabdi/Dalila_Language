"""Adapter for the recovered original local reference-conditioned voice worker."""
import os,sys,time,subprocess,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCK=threading.Lock()
def synthesize_reference(text,engine,reference,reference_text,consent,output):
    if consent is not True: raise PermissionError('Authorized voice only')
    if os.getenv('DALILA_ENABLE_RESEARCH_TTS','0')!='1': raise PermissionError('Research TTS disabled pending license review')
    if engine not in ('silma','xtts'): raise ValueError('Unknown research TTS engine')
    if not text.strip() or len(text)>1200: raise ValueError('Invalid speech text')
    if engine=='silma' and not reference_text.strip(): raise ValueError('Reference transcript required')
    if len(reference_text)>1200: raise ValueError('Reference transcript too long')
    py=Path(os.getenv('VOICE_PYTHON') or ROOT/'.venv-voice'/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
    if not py.is_file(): raise RuntimeError('Voice environment not installed')
    import wave
    with wave.open(str(reference),'rb') as w:
        if not 2<=w.getnframes()/w.getframerate()<=30: raise ValueError('Reference must be 2–30 second PCM WAV')
    with LOCK:
        t=time.perf_counter(); p=subprocess.run([str(py),str(ROOT/'legacy/original/voice_worker.py'),engine,str(reference),reference_text,text,str(output)],cwd=ROOT,capture_output=True,timeout=900)
        if p.returncode or not output.is_file() or output.stat().st_size<=44: raise RuntimeError('Research voice worker failed')
    return {'engine':engine,'dialect_authenticity':'not_evaluated','generation_s':time.perf_counter()-t}
