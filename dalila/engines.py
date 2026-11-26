import os,time,subprocess,shutil,threading
from functools import lru_cache
from pathlib import Path
ASR={'tn-small':'TheBiggyBang/whisper-small-tunisian-derja-ct2','tn-whisperx':'montachouig/whisperX-tunisian','small':'small','turbo':'turbo','large-v3':'large-v3','tn-codeswitch':'oddadmix/Whisperv3-tunisian-codeswitch'}
LOCK=threading.RLock()
@lru_cache(maxsize=2)
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
        segments=list(seg); text=' '.join(s.text.strip() for s in segments).strip(); elapsed=time.perf_counter()-start
        logprobs=[s.avg_logprob for s in segments if getattr(s,'avg_logprob',None) is not None]
        mean_logprob=sum(logprobs)/len(logprobs) if logprobs else None
    if not text: raise ValueError('No speech recognized')
    return dict(text=text,model=key,avg_logprob=mean_logprob,asr_language=info.language,language_probability=info.language_probability,duration_s=len(audio)/16000,load_s=load,inference_s=elapsed,rtf=elapsed/(len(audio)/16000))

def route_asr(path,language='auto',key=None):
    # Detect general language before considering a dialect-specific model.
    if key or language != 'auto':
        primary = key or ('tn-small' if language=='aeb' else 'small')
        try:
            return dict(transcribe(path,primary,language),fallback=False)
        except Exception as first:
            if primary=='small': raise
            return dict(transcribe(path,'small',language),fallback=True,failed_model=primary,reason=type(first).__name__)
    try:
        general = transcribe(path,'small','auto')
    except Exception as first:
        return dict(transcribe(path,'tn-small','aeb'),fallback=True,failed_model='small',reason=type(first).__name__)
    if general.get('asr_language') != 'ar':
        return dict(general,fallback=False)
    from .semantic import detect
    detected = detect(general['text'])
    # Keep confidently non-Tunisian Arabic untouched.
    if detected['label'] in ('ar','arq','ayl'):
        return dict(general,fallback=False)
    # Avoid a second complete decode for clear transcripts in the interactive path.
    # The confidence heuristic is not calibrated; full refinement is configurable.
    if detected['best_guess']=='aeb' and (os.getenv('ASR_REFINE_TUNISIAN','low_confidence')=='always' or general.get('avg_logprob') is None or general['avg_logprob'] < -0.65):
        try:
            refined = transcribe(path,'tn-small','aeb')
            return dict(refined,fallback=False,initial_model='small',initial_text=general['text'],language_hint='aeb')
        except Exception as exc:
            return dict(general,fallback=True,failed_model='tn-small',reason=type(exc).__name__)
    return dict(general,fallback=False)

def _windows_speech(text, voice, output):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        source = Path(d)/'text.txt'
        source.write_text(text,encoding='utf-8')
        env = dict(os.environ,DALILA_VOICE_LANG=voice,DALILA_VOICE_TEXT=str(source),DALILA_VOICE_OUTPUT=str(Path(output).resolve()))
        command = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $voice = $s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq $env:DALILA_VOICE_LANG } | Select-Object -First 1
  if (-not $voice) { throw 'No compatible Windows voice' }
  $s.SelectVoice($voice.VoiceInfo.Name)
  $s.SetOutputToWaveFile($env:DALILA_VOICE_OUTPUT)
  $s.Speak([IO.File]::ReadAllText($env:DALILA_VOICE_TEXT,[Text.Encoding]::UTF8))
} finally { $s.Dispose() }
"""
        p = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],env=env,capture_output=True,timeout=60)
        if p.returncode or not Path(output).is_file() or Path(output).stat().st_size<=44:
            raise RuntimeError('No compatible Windows speech voice')
    return {'engine':'windows-sapi','voice':voice,'dialect_authentic':False}


def speak(text,language,output):
    # Generic local intelligibility baseline only; Arabic eSpeak is NOT Derja.
    exe=shutil.which('espeak-ng') or shutil.which('espeak')
    if language not in ('aeb','ar','arq','ayl','fr','en','de','tr'): raise ValueError('Unsupported language')
    if not text.strip() or len(text)>1200: raise ValueError('Speech text must be 1–1200 characters')
    voice='ar' if language in ('aeb','ar','arq','ayl') else language
    start=time.perf_counter()
    if os.name=='nt':
        try:
            result=_windows_speech(text,voice,output)
            return dict(result,generation_s=time.perf_counter()-start)
        except (RuntimeError,OSError,subprocess.SubprocessError):
            Path(output).unlink(missing_ok=True)
    if not exe: raise RuntimeError('No compatible offline server voice')
    p=subprocess.run([exe,'-v',voice,'-w',str(output),'--stdin'],input=text.encode('utf-8'),capture_output=True,timeout=60)
    if p.returncode or not Path(output).is_file() or Path(output).stat().st_size<=44: raise RuntimeError('Local TTS voice unavailable')
    return {'engine':'espeak','voice':voice,'dialect_authentic':False,'generation_s':time.perf_counter()-start}
