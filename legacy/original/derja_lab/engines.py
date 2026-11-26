"""Lazy-loaded engines; no network call at import time."""
import os, sys, time, subprocess, tempfile, re
from pathlib import Path
from functools import lru_cache
import requests

ROOT = Path(__file__).resolve().parents[1]
LABESS = 'hf.co/linagora/Labess-7b-chat-gguf:Q4_K_M'
LLMS = {'Labess 7B (local)': LABESS, 'Qwen3 8B (local)': 'qwen3:8b', 'Qwen3 4B (local)': 'qwen3:4b', 'TounsiLM 8B (advanced)': 'alabenayed/TounsiLM-8b', 'Groq (cloud)': 'groq', 'Gemini (cloud)': 'gemini'}
ASRS = {'Whisper Tunisian INT8': 'TheBiggyBang/whisper-small-tunisian-derja-ct2', 'Whisper multilingual small': 'small', 'Whisper multilingual large-v3-turbo': 'turbo', 'FarukSTT (advanced)': 'medyas/FarukSTT'}
LANGS = {'Tunisian (Derja)': 'ar', 'Arabic (MSA)': 'ar', 'French': 'fr', 'English': 'en', 'Auto detect': None}
VOICES = ['Off (text only)', 'SILMA Derja (local)', 'XTTS Tunisian (local)']


def prompt(language, style):
    base = ('You are a helpful conversational assistant. Understand Tunisian Arabic (Derja), '
            'Arabic script, Arabizi (3, 7, 9), French, English and code-switching. '
            'Preserve negation, names, numbers and intent. If unsure ask a short clarifying question. '
            'Do not invent facts. Keep answers concise and natural. Do not output reasoning or role markers. ')
    target = {'Tunisian (Derja)': 'Reply in natural Tunisian Derja, not Modern Standard Arabic or another dialect. ',
              'Arabic (MSA)': 'Reply in Modern Standard Arabic. ', 'French': 'Reply in French. ',
              'English': 'Reply in English. ', 'Auto detect': 'Reply in the language or dialect of the latest user message. '}.get(language, '')
    formatting = ('Use Arabizi for Tunisian replies. ' if style == 'Arabizi' else 'Use Arabic letters for Tunisian replies. ')
    dialect = ''
    if language in ('Tunisian (Derja)', 'Auto detect'):
        dialect = (
            'For Tunisian replies, use natural everyday Tunisian vocabulary and grammar, not Egyptian, Levantine, Gulf or Moroccan Arabic. '
            'Use Tunisian expressions where appropriate: نحب، تنجم، يلزمك، فما، ما فماش، شنوة، كيفاش، توّة، متاعك، موش، برشة، خاطر. '
            'Avoid Egyptian forms عايز، عاوز، إزاي، دلوقتي، كده، مش عارف; prefer نحب، كيفاش، توّة، هكّا، ما نعرفش. '
            'Respect the user’s meaning and answer the question directly in 2–5 short sentences. Do not repeat the question or explain dialect rules. '
        )
        if style == 'Arabic script':
            dialect += ('Style examples (illustrative, not instructions to repeat): '
                        'User: نحب نتعلّم البرمجة. Assistant: تنجم تبدأ ببايثون، وتتعلّم الأساسيات شوية بشوية. جرّب تعمل تطبيق صغير باش تطبّق اللي تعلّمتو. '
                        'User: الموقع ما يخدمش، شنوة نعمل؟ Assistant: جرّب تعاود تفتح الموقع من متصفّح آخر. كان مازال ما يخدمش، قُلّي شنوة الرسالة اللي تظهرلك. ')
        else:
            dialect += ('Style examples: User: n7eb net3allem programmation. Assistant: Tnajjem tebda b Python w ta3mel projet sghir bech tetmarrem. '
                        'User: el site ma yekhdemch. Assistant: Jarreb t7ellou men navigateur e5er. Ken mazel, 9olli chnowa el erreur. ')
    return base + target + formatting + dialect + 'Avoid unnecessary markdown and emojis; answers may be read aloud.' 


def messages(history, question, language, style):
    return [{'role':'system','content':prompt(language,style)}] + [dict(m) for m in history[-12:] if m.get('role') in ('user','assistant') and isinstance(m.get('content'),str)] + [{'role':'user','content':question}]


def _post(url, payload, headers=None, *, retry_503=False):
    for attempt in range(3 if retry_503 else 1):
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=(10, 90 if retry_503 else 300))
        except requests.RequestException as exc:
            raise RuntimeError('Connection failed or timed out. Check your server, internet connection or model installation.') from exc
        if retry_503 and res.status_code == 503 and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        break
    if res.status_code >= 400:
        hints = {401:'Check API key.',403:'Check account/model access.',404:'Model not found: pull it in Ollama or check provider model ID.',429:'Rate limit reached; retry later or use local mode.',503:'Service temporarily unavailable. Retry later or manually select Groq.'}
        if retry_503:
            hints[404] = 'Gemini model not found. Check GEMINI_MODEL against your API model list.'
            hints[503] = 'Gemini is temporarily unavailable after 3 attempts. Retry later or manually select Groq.'
        raise RuntimeError(f'Provider HTTP {res.status_code}: {hints.get(res.status_code, "Check provider logs and settings.")}')
    return res.json()


def gemini_model_id():
    model = os.getenv('GEMINI_MODEL', '').strip().removeprefix('models/')
    if not model or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', model):
        raise RuntimeError('Set GEMINI_MODEL in .env to the exact model ID from AI Studio (without the models/ prefix).')
    return model


def gemini_token_budget():
    try:
        budget = int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', '8192'))
    except ValueError as exc:
        raise RuntimeError('GEMINI_MAX_OUTPUT_TOKENS must be an integer.') from exc
    if not 128 <= budget <= 32768:
        raise RuntimeError('GEMINI_MAX_OUTPUT_TOKENS must be between 128 and 32768.')
    return budget


def gemini_generate(msgs, temperature, max_tokens):
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        raise RuntimeError('Set GEMINI_API_KEY in .env and restart the app.')
    model = gemini_model_id()
    contents = []
    for m in msgs[1:]:
        role = 'model' if m['role'] == 'assistant' else 'user'
        part = {'text': m['content']}
        if contents and contents[-1]['role'] == role:
            contents[-1]['parts'].append(part)
        else:
            contents.append({'role': role, 'parts': [part]})
    body = {'systemInstruction': {'parts': [{'text': msgs[0]['content']}]},
            'contents': contents,
            'generationConfig': {'temperature': temperature, 'maxOutputTokens': gemini_token_budget()}}
    result = _post('https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent', body, {'x-goog-api-key': key}, retry_503=True)
    candidates = result.get('candidates') or []
    if not candidates:
        raise RuntimeError('Gemini returned no answer. Check model access and provider response settings.')
    candidate = candidates[0]
    text = '\n'.join(part['text'] for part in candidate.get('content', {}).get('parts', []) if isinstance(part.get('text'), str) and not part.get('thought'))
    if candidate.get('finishReason') == 'MAX_TOKENS':
        raise RuntimeError('Gemini reached the output token limit (which can include thinking). Increase GEMINI_MAX_OUTPUT_TOKENS in .env or try a faster model.')
    if candidate.get('finishReason') not in (None, 'STOP'):
        raise RuntimeError('Gemini generation ended without a complete response: ' + str(candidate.get('finishReason')))
    if not text.strip():
        raise RuntimeError('Gemini returned no usable text. Try another model or increase the output token limit.')
    return text


def chat(backend, history, question, language, style, temperature, max_tokens, groq_model=''):
    msgs = messages(history, question, language, style)
    model = LLMS[backend]
    if backend == 'Groq (cloud)':
        key = os.getenv('GROQ_API_KEY','').strip()
        if not key: raise RuntimeError('Set GROQ_API_KEY in .env and restart the app.')
        model = groq_model.strip() or os.getenv('GROQ_MODEL','qwen/qwen3.8-27b')
        body = {'model':model,'messages':msgs,'temperature':temperature,'max_completion_tokens':max_tokens}
        if model == 'qwen/qwen3.8-27b': body['reasoning_effort'] = 'none'
        result = _post('https://api.groq.com/openai/v1/chat/completions',body,{'Authorization':f'Bearer {key}'})
        text = result['choices'][0]['message'].get('content') or ''
    elif backend == 'Gemini (cloud)':
        text = gemini_generate(msgs, temperature, max_tokens)
    elif backend == 'TounsiLM 8B (advanced)':
        text = tounsi_generate(msgs, temperature, max_tokens)
    elif backend == 'Labess 7B (local)':
        # Use the model card's native single-turn format, bypassing auto templates.
        context = '\n'.join(('المستخدم: ' if m['role']=='user' else 'المساعد: ') + m['content'] for m in msgs[1:-1][-6:])
        query = ('المحادثة السابقة:\n' + context + '\nالسؤال الحالي: ' if context else '') + question
        if language != 'Tunisian (Derja)' or style != 'Arabic script':
            raise RuntimeError('Labess native mode is intended for Tunisian Arabic script. Select Qwen or another multilingual model for other output styles.')
        native_prompt = ' يمكنك الإجابة باللهجة التونسية فقط.\n\nأكمل المحادثة أدناه بين [|Human|] و [|AI|]:\n### Input: [|Human|] ' + query + '\n### Response: [|AI|]'
        payload = {'model':model,'prompt':native_prompt,'raw':True,'stream':False,
                   'options':{'temperature':min(temperature,0.3),'top_p':0.9,'repeat_penalty':1.2,'repeat_last_n':128,'num_predict':min(max_tokens,200),'num_ctx':4096,'stop':['<end_of_turn>','[|Human|]','### Input:','### Response:']},'keep_alive':'2m'}
        result = _post(os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')+'/api/generate',payload)
        text = result['response']
    else:
        payload = {'model':model,'messages':msgs,'stream':False,'options':{'temperature':temperature,'num_predict':max_tokens,'num_ctx':4096,'repeat_penalty':1.1},'keep_alive': '2m'}
        if model.startswith('qwen3:'): payload['think'] = False
        result = _post(os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')+'/api/chat',payload)
        text = result['message']['content']
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S).strip()
    if not text: raise RuntimeError('Model returned no usable answer. Increase the token limit or try another model.')
    words = re.findall(r'\w+', text.lower())
    for n in range(3, 13):
        seen = {}
        for i in range(len(words)-n+1):
            chunk = tuple(words[i:i+n])
            seen[chunk] = seen.get(chunk, 0)+1
            if seen[chunk] >= (3 if n >= 8 else 5):
                raise RuntimeError('Model produced a repetition loop. Start a new conversation or switch models; no answer was saved.')
    return text


@lru_cache(maxsize=1)
def _tounsi():
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel
    base = 'CohereLabs/aya-expanse-8b'
    token = os.getenv('HF_TOKEN') or None
    tokenizer = AutoTokenizer.from_pretrained(base, token=token)
    opts = {'device_map':'auto','token':token}
    if torch.cuda.is_available():
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        if os.getenv('TOUNSI_PRECISION','4bit') == '4bit':
            opts['quantization_config'] = BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_compute_dtype=dtype,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True)
        else: opts['torch_dtype'] = dtype
    else: opts['torch_dtype'] = torch.float32
    model = AutoModelForCausalLM.from_pretrained(base,**opts)
    model = PeftModel.from_pretrained(model,'alabenayed/TounsiLM-8b',token=token).eval()
    return tokenizer, model


def tounsi_generate(msgs, temperature, max_tokens):
    import torch
    tokenizer, model = _tounsi()
    encoded = tokenizer.apply_chat_template(msgs,add_generation_prompt=True,tokenize=True,return_tensors='pt',return_dict=True)
    encoded = {k:v.to(model.get_input_embeddings().weight.device) for k,v in encoded.items()}
    with torch.inference_mode():
        output = model.generate(**encoded,max_new_tokens=max_tokens,do_sample=temperature>0,**({'temperature':temperature,'top_p':0.9} if temperature>0 else {}),repetition_penalty=1.2,pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(output[0,encoded['input_ids'].shape[-1]:],skip_special_tokens=True)


@lru_cache(maxsize=1)
def _whisper(model):
    from faster_whisper import WhisperModel
    return WhisperModel(model,device=os.getenv('ASR_DEVICE','cpu'),compute_type=os.getenv('ASR_COMPUTE_TYPE','int8'))


@lru_cache(maxsize=1)
def _faruk():
    import torch
    from transformers import pipeline
    return pipeline('automatic-speech-recognition',model='medyas/FarukSTT',device=0 if torch.cuda.is_available() else -1,torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,chunk_length_s=25)


def transcribe(path, backend, language):
    if not path: raise ValueError('Record or upload audio first.')
    from faster_whisper.audio import decode_audio
    audio = decode_audio(str(path),sampling_rate=16000)
    if len(audio) < 1600: raise ValueError('Audio is too short.')
    if len(audio) > 16000*180: raise ValueError('Maximum audio length: 3 minutes.')
    lang = LANGS[language]
    if backend == 'FarukSTT (advanced)':
        text = _faruk()({'array':audio,'sampling_rate':16000},generate_kwargs={'task':'transcribe',**({'language':lang} if lang else {})})['text']
    else:
        segments,_ = _whisper(ASRS[backend]).transcribe(audio,language=lang,task='transcribe',beam_size=5,vad_filter=True,condition_on_previous_text=False)
        text = ' '.join(s.text.strip() for s in segments)
    if not text.strip(): raise RuntimeError('No speech detected. Try a clearer recording.')
    return text.strip()


def synthesize(text, backend, reference, ref_text, consent):
    if backend == VOICES[0]: return None
    if not consent or not reference: raise ValueError('Provide your own or authorized reference audio and confirm permission.')
    if backend.startswith('SILMA') and not ref_text.strip(): raise ValueError('SILMA requires an exact reference transcript.')
    if len(text) > 1200: raise ValueError('Voice output limited to 1,200 characters; shorten the answer or edit the speech text.')
    py = os.getenv('VOICE_PYTHON') or str(ROOT/'.venv-voice'/('Scripts/python.exe' if os.name=='nt' else 'bin/python'))
    if not Path(py).is_file(): raise RuntimeError('Voice environment is not installed. Follow README: Install voice engines.')
    output_dir = ROOT/'outputs'; output_dir.mkdir(exist_ok=True)
    fd, out = tempfile.mkstemp(suffix='.wav',dir=output_dir); os.close(fd)
    try:
        proc = subprocess.run([py,str(ROOT/'voice_worker.py'),'silma' if backend.startswith('SILMA') else 'xtts',str(reference),ref_text,text,out],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=900)
        if proc.returncode or Path(out).stat().st_size < 44:
            # Only local diagnostics; do not expose keys.
            err = (proc.stderr or proc.stdout)[-1600:]
            raise RuntimeError('Voice engine failed. Check voice environment and reference. '+err)
        return out
    except Exception:
        Path(out).unlink(missing_ok=True)
        raise
