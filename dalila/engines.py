import os,time,subprocess,shutil,threading
from functools import lru_cache
from pathlib import Path
ASR={'tn-small':'TheBiggyBang/whisper-small-tunisian-derja-ct2','tn-whisperx':'montachouig/whisperX-tunisian','small':'small','turbo':'turbo','large-v3':'large-v3','tn-codeswitch':'oddadmix/Whisperv3-tunisian-codeswitch'}
LOCK=threading.RLock()
@lru_cache(maxsize=1)
def model(key):
    from faster_whisper import WhisperModel
    prepared=Path(__file__).resolve().parents[1]/'models'/key
    location=os.getenv('DALILA_ASR_'+key.upper().replace('-','_'),str(prepared) if (prepared/'model.bin').is_file() else ASR[key]); device=os.getenv('ASR_DEVICE','cpu')
    # Codeswitch repository is Transformers format: convert separately before benchmarking.
    if key=='tn-codeswitch' and location==ASR[key]: raise ValueError('Set DALILA_ASR_TN_CODESWITCH to a converted CTranslate2 directory')
    return WhisperModel(location,device=device,compute_type=os.getenv('ASR_COMPUTE_TYPE','int8'),cpu_threads=int(os.getenv('ASR_THREADS','4')),local_files_only=os.getenv('ASR_OFFLINE','0')=='1')

def transcribe(path,key='tn-small',language='auto'):
    if key not in ASR: raise ValueError('Unknown ASR model')
    if language not in ('auto','aeb','ar','fr','en','arq','ayl','de','tr'): raise ValueError('Unknown language')
    from faster_whisper.audio import decode_audio
    audio=decode_audio(str(path),sampling_rate=16000)
    if not 1600<=len(audio)<=16000*120: raise ValueError('Audio must be 0.1–120 seconds')
    forced='ar' if language in ('aeb','ar','arq','ayl') else None if language=='auto' else language
    if key.startswith('tn-'):
        if forced not in ('ar',None): raise ValueError('Tunisian models should not handle other languages')
        forced='ar'
    with LOCK:
        start=time.perf_counter(); m=model(key); load=time.perf_counter()-start; start=time.perf_counter()
        seg,info=m.transcribe(audio,language=forced,task='transcribe',beam_size=int(os.getenv('ASR_BEAM_SIZE','3')),vad_filter=True,condition_on_previous_text=False)
        text=' '.join(s.text.strip() for s in seg).strip(); elapsed=time.perf_counter()-start
    if not text: raise ValueError('No speech recognized')
    return dict(text=text,model=key,asr_language=info.language,language_probability=info.language_probability,duration_s=len(audio)/16000,load_s=load,inference_s=elapsed,rtf=elapsed/(len(audio)/16000))

def route_asr(path,language='auto',key=None):
    if key:
        primary = key
        order = [primary] if primary == 'small' else [primary, 'small']
    else:
        order = ['tn-small', 'small'] if language in ('auto', 'aeb', 'ar', 'arq', 'ayl') else ['small']
        primary = order[0]
    first_error = None
    for idx, candidate in enumerate(order):
        try:
            result = transcribe(path, candidate, language)
            if idx == 0:
                return dict(result, fallback=False)
            return dict(result, fallback=True, failed_model=primary, reason=type(first_error).__name__ if first_error else 'fallback')
        except Exception as exc:
            if first_error is None:
                first_error = exc
            continue
    raise first_error or RuntimeError('No ASR model available')

def speak(text,language,output):
    # Generic local intelligibility baseline only; Arabic eSpeak is NOT Derja.
    exe=shutil.which('espeak-ng') or shutil.which('espeak')
    if not exe: raise RuntimeError('Install eSpeak NG, or keep speech output disabled.')
    if language not in ('aeb','ar','arq','ayl','fr','en','de','tr'): raise ValueError('Unsupported language')
    if not text.strip() or len(text)>1200: raise ValueError('Speech text must be 1–1200 characters')
    voice='ar' if language in ('aeb','ar','arq','ayl') else language
    start=time.perf_counter(); p=subprocess.run([exe,'-v',voice,'-w',str(output),'--stdin'],input=text.encode('utf-8'),capture_output=True,timeout=60)
    if p.returncode or not Path(output).is_file() or Path(output).stat().st_size<=44: raise RuntimeError('Local TTS voice unavailable')
    return {'engine':'espeak','voice':voice,'dialect_authentic':False,'generation_s':time.perf_counter()-start}
