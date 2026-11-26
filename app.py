from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
import tempfile, os, base64, time, threading, logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from dalila.semantic import understand
from dalila.voice import synthesize_reference
from dalila.core import analyze, LANGS
from dalila.engines import route_asr, speak, packaged_voice_available, VOICE_MAP, warm_asr, general_asr_key
from dalila.llm import installed_ollama_model
from dalila.chat import chat_turn
from dalila import neural_voice, tunisian_voice

app = FastAPI(title="Dalila Language Lab", version="0.8.0")
ROOT = Path(__file__).parent
WARM_STATUS='not_started'

@app.on_event('startup')
def prepare_local_models():
    if os.getenv('DALILA_PREPARE_MODELS','0')!='1': return
    def prepare():
        global WARM_STATUS
        WARM_STATUS='loading'
        try:
            warm_asr()
            WARM_STATUS='ready'
        except Exception as exc:
            WARM_STATUS='unavailable'
            logging.getLogger(__name__).warning('ASR prewarm: %s',type(exc).__name__)
        neural_voice.prepare_all()
    threading.Thread(target=prepare,daemon=True,name='dalila-model-preparation').start()
    if tunisian_voice.enabled():
        threading.Thread(target=tunisian_voice.prepare,daemon=True,name='dalila-tunisian-voice').start()


def _cloud_allowed():
    return os.getenv("DALILA_ALLOW_CLOUD", "0") == "1"


def choose_semantic_backend(preferred: str = "auto") -> str:
    if preferred and preferred != "auto":
        return preferred
    # Automatic mode stays local; cloud providers require explicit selection.
    return "ollama" if installed_ollama_model() else "baseline"


class TextRequest(BaseModel):
    text: str
    language: str = "auto"


class SemanticRequest(BaseModel):
    text: str = Field(max_length=4000)
    language: str = "auto"
    history: list[str] = Field(default_factory=list, max_length=6)
    backend: str = "auto"
    style: str = "auto"


class VoiceRequest(BaseModel):
    text: str
    language: str


@app.get('/', response_class=HTMLResponse)
def home():
    return (ROOT / 'static/index.html').read_text(encoding='utf-8')


@app.get('/health')
def health():
    return {
        'status': 'ok',
        'version': app.version,
        'mode': 'research_only',
        'knowledge': 'not_connected',
        'languages': LANGS,
        'default_backend': choose_semantic_backend('auto'),
        'cloud_enabled': _cloud_allowed(),
    }


@app.get('/capabilities')
def capabilities():
    backend = choose_semantic_backend('auto')
    return {
        'default_language': 'auto',
        'semantic_backend': backend,
        'voice_reply': bool(packaged_voice_available() or os.name=='nt' or __import__('shutil').which('espeak-ng') or __import__('shutil').which('espeak')),
        'packaged_tts': packaged_voice_available(),
        'neural_tts': neural_voice.readiness(),
        'tunisian_tts': tunisian_voice.readiness(),
        'general_asr': general_asr_key(),
        'asr_warmup': WARM_STATUS,
        'tts_language_map': VOICE_MAP,
        'version': app.version,
        'ollama_model': installed_ollama_model() if backend == 'ollama' else None,
        'research_voice_enabled': os.getenv('DALILA_ENABLE_RESEARCH_TTS', '0') == '1',
        'cloud_enabled': _cloud_allowed(),
    }


@app.post('/analyze')
def text(request: TextRequest):
    try:
        return analyze(request.text, request.language)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/understand')
def semantic(request: SemanticRequest):
    try:
        backend = choose_semantic_backend(request.backend)
        return understand(request.text, request.language, request.history, backend, request.style)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/chat')
def chat(request: SemanticRequest):
    try:
        backend = choose_semantic_backend(request.backend)
        return chat_turn(request.text, request.language, request.history, backend, request.style)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/transcribe')
def audio(file: UploadFile = File(...), language: str = Form('auto'), model: str = Form('auto')):
    try:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'audio'
            size = 0
            with path.open('wb') as f:
                while chunk := file.file.read(65536):
                    size += len(chunk)
                    if size > 20 * 1024 * 1024:
                        raise HTTPException(413, 'Maximum audio upload 20 MB')
                    f.write(chunk)
            started = time.perf_counter()
            result = route_asr(path, language, None if model == 'auto' else model)
            return dict(result, total_s=round(time.perf_counter()-started,3))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, f'ASR unavailable: {type(e).__name__}: See local model setup documentation')
    finally:
        file.file.close()


@app.post('/voice-chat')
def voice_chat(file: UploadFile = File(...), language: str = Form('auto'), backend: str = Form('auto')):
    try:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'audio'
            size = 0
            with path.open('wb') as f:
                while chunk := file.file.read(65536):
                    size += len(chunk)
                    if size > 20 * 1024 * 1024:
                        raise HTTPException(413, 'Maximum audio upload 20 MB')
                    f.write(chunk)
            asr = route_asr(path, language, None)
            semantic_backend = choose_semantic_backend(backend)
            hint = asr.get('language_hint') or asr.get('asr_language')
            selected = hint if language=='auto' and hint in ('fr','en','de','tr','aeb') else language
            result = chat_turn(asr['text'], selected, [], semantic_backend, 'auto')
            return dict(result, transcript=asr['text'], asr=asr)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, f'Voice chat unavailable: {type(e).__name__}')
    finally:
        file.file.close()


@app.post('/speak')
def voice(request: VoiceRequest):
    try:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'speech.wav'
            result = speak(request.text, request.language, path)
            return dict(result, audio_base64=base64.b64encode(path.read_bytes()).decode())
    except Exception as e:
        raise HTTPException(422, 'TTS unavailable: See local model setup documentation')


@app.post('/speak-reference')
def voice_reference(file: UploadFile = File(...), text: str = Form(...), reference_text: str = Form(''), engine: str = Form('silma'), consent: bool = Form(False)):
    if not consent:
        raise HTTPException(400, 'Authorized reference required')
    try:
        with tempfile.TemporaryDirectory() as d:
            ref = Path(d) / 'reference.wav'
            size = 0
            with ref.open('wb') as f:
                while chunk := file.file.read(65536):
                    size += len(chunk)
                    if size > 10 * 1024 * 1024:
                        raise HTTPException(413, 'Reference too large')
                    f.write(chunk)
            out = Path(d) / 'speech.wav'
            result = synthesize_reference(text, engine, ref, reference_text, consent, out)
            return dict(result, audio_base64=base64.b64encode(out.read_bytes()).decode())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, 'Reference TTS unavailable: ' + type(e).__name__)
    finally:
        file.file.close()
