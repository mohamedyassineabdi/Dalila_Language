from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
import tempfile, os, base64
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from dalila.semantic import understand
from dalila.voice import synthesize_reference
from dalila.core import analyze, LANGS
from dalila.engines import route_asr, speak

app = FastAPI(title="Dalila Language Lab", version="0.3.0")
ROOT = Path(__file__).parent


def _cloud_allowed():
    return os.getenv("DALILA_ALLOW_CLOUD", "0") == "1"


def choose_semantic_backend(preferred: str = "auto") -> str:
    if preferred and preferred != "auto":
        return preferred
    # Prefer local Ollama if reachable, then explicitly allowed cloud providers, else baseline.
    try:
        import requests
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=(0.5, 1.5))
        if r.ok:
            return "ollama"
    except Exception:
        pass
    if _cloud_allowed() and os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_MODEL"):
        return "gemini"
    if _cloud_allowed() and os.getenv("GROQ_API_KEY") and os.getenv("GROQ_MODEL"):
        return "groq"
    return "baseline"


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
        'voice_reply': True,
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
        result = understand(request.text, request.language, request.history, backend, request.style)
        lang = result.get('language') or result.get('language_detection', {}).get('best_guess') or 'aeb'
        reply = result.get('response') or 'I understood your message, but I still need verified AFI data before I can give a confirmed answer.'
        return {
            'user_text': request.text,
            'assistant_text': reply,
            'language': lang,
            'detected_language': result.get('language'),
            'needs_language_confirmation': result.get('needs_language_confirmation', False),
            'intent': result.get('intent', {}),
            'semantic_backend': result.get('semantic_backend', backend),
            'technical': result,
        }
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
            return route_asr(path, language, None if model == 'auto' else model)
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
            result = understand(asr['text'], language, [], semantic_backend, 'auto')
            lang = result.get('language') or result.get('language_detection', {}).get('best_guess') or 'aeb'
            return {
                'transcript': asr['text'],
                'asr': asr,
                'assistant_text': result.get('response'),
                'language': lang,
                'technical': result,
            }
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
