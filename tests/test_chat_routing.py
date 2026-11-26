import pytest
from dalila.chat import chat_turn
from dalila.llm import installed_ollama_model
from dalila import engines
from fastapi.testclient import TestClient
from app import app

@pytest.mark.parametrize('text',['ahla bik','ahla bik*','Ahla bik!'])
def test_arabizi_greeting(text):
    r=chat_turn(text)
    assert r['language']=='aeb' and r['response_style']=='arabizi'
    assert r['assistant_text'].startswith('Ahla bik') and r['speech_text'].startswith('أهلا')
    assert r['semantic_backend']=='greeting'

def test_installed_model(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'models':[{'name':'qwen3:4b-cloud','remote_host':'cloud'},{'name':'qwen3:8b'}]}
    monkeypatch.setenv('OLLAMA_MODEL','qwen3:4b')
    monkeypatch.setattr('dalila.llm.requests.get',lambda *a,**k:Response())
    assert installed_ollama_model()=='qwen3:8b'

def test_no_model(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'models':[]}
    monkeypatch.setattr('dalila.llm.requests.get',lambda *a,**k:Response())
    assert installed_ollama_model() is None

def test_local_chat_generation(monkeypatch):
    monkeypatch.setattr('dalila.chat.conversational_reply',lambda *a:({'language':'aeb','category':'social','reply':'إي نحكي بالتونسي','speech_text':'إي نحكي بالتونسي'},'qwen3:4b'))
    r=chat_turn('تحكي بالتونسي؟','aeb',backend='ollama')
    assert r['semantic_backend']=='ollama' and r['assistant_text']=='إي نحكي بالتونسي'

def test_domain_guard(monkeypatch):
    monkeypatch.setattr('dalila.chat.conversational_reply',lambda *a: pytest.fail('domain generation'))
    monkeypatch.setattr('dalila.llm.semantic_json',lambda *a:{'language':'fr','intent':'price','needs_clarification':False})
    r=chat_turn('Quel est le prix ?', 'fr', backend='ollama')
    assert 'ne peux pas donner de réponse confirmée' in r['assistant_text']

def test_chat_endpoint():
    r=TestClient(app).post('/chat',json={'text':'ahla bik*','backend':'baseline'})
    assert r.status_code==200 and r.json()['language']=='aeb'

def test_asr_multilingual_not_forced_arabic(monkeypatch):
    calls=[]
    def transcribe(path,key,language):
        calls.append((key,language))
        return {'text':'Bonjour','asr_language':'fr','model':key}
    monkeypatch.setattr(engines,'transcribe',transcribe)
    assert engines.route_asr('fake')['asr_language']=='fr'
    assert calls==[('small','auto')]

def test_auto_cloud_disabled(monkeypatch):
    from app import choose_semantic_backend
    monkeypatch.setattr('app.installed_ollama_model',lambda:None)
    monkeypatch.setenv('DALILA_ALLOW_CLOUD','1')
    monkeypatch.setenv('GEMINI_API_KEY','fake')
    monkeypatch.setenv('GEMINI_MODEL','fake')
    assert choose_semantic_backend()=='baseline'


def test_chat_timing_and_script(monkeypatch):
    monkeypatch.setattr('dalila.chat.conversational_reply',lambda *a:({'language':'aeb','category':'social','reply':'Ahla bik','speech_text':'أهلا بيك','_timing':{'llm_s':0.1}},'qwen3:4b'))
    r=chat_turn('تحكي بالتونسي؟','aeb',backend='ollama')
    assert r['assistant_text']=='أهلا بيك' and r['timing']['llm_s']==0.1
    assert r['timing']['total_s']>=0

def test_project_clarification():
    r=chat_turn('نحب نحل مشروع صغير تنجم تعاوني','aeb')
    assert 'نوع المشروع' in r['assistant_text'] and r['semantic_backend']=='guided'

def test_confident_domain_does_not_need_model(monkeypatch):
    monkeypatch.setattr('dalila.llm.semantic_json',lambda *a:pytest.fail('unnecessary LLM call'))
    r=chat_turn('Quel est le prix ?', 'fr', backend='ollama')
    assert 'prix' in r['assistant_text']

def test_fast_asr_avoids_second_decode(monkeypatch):
    monkeypatch.setenv('ASR_REFINE_TUNISIAN','low_confidence')
    calls=[]
    def transcribe(path,key,language):
        calls.append(key)
        return {'text':'نحب نعرف شنوة يلزمني','asr_language':'ar','avg_logprob':-0.2,'model':key}
    monkeypatch.setattr(engines,'transcribe',transcribe)
    monkeypatch.setattr('dalila.semantic.detect',lambda text:{'label':'aeb','best_guess':'aeb'})
    assert engines.route_asr('fake')['model']=='small' and calls==['small']

def test_uncertain_asr_refines(monkeypatch):
    monkeypatch.setenv('ASR_REFINE_TUNISIAN','low_confidence')
    calls=[]
    def transcribe(path,key,language):
        calls.append(key)
        return {'text':'نحب نعرف شنوة يلزمني','asr_language':'ar','avg_logprob':-0.9,'model':key}
    monkeypatch.setattr(engines,'transcribe',transcribe)
    monkeypatch.setattr('dalila.semantic.detect',lambda text:{'label':'aeb','best_guess':'aeb'})
    assert engines.route_asr('fake')['model']=='tn-small' and calls==['small','tn-small']


def test_fast_base_english(monkeypatch):
    monkeypatch.setenv('DALILA_GENERAL_ASR','base')
    calls=[]
    def transcribe(path,key,language):
        calls.append(key)
        return {'text':'Hello','asr_language':'en','language_probability':.98,'avg_logprob':-.15,'model':key}
    monkeypatch.setattr(engines,'transcribe',transcribe)
    assert engines.route_asr('fake')['model']=='base' and calls==['base']

def test_uncertain_base_general(monkeypatch):
    monkeypatch.setenv('DALILA_GENERAL_ASR','base')
    calls=[]
    def transcribe(path,key,language):
        calls.append(key)
        return {'text':'Hello','asr_language':'en','language_probability':.5,'avg_logprob':-.9,'model':key}
    monkeypatch.setattr(engines,'transcribe',transcribe)
    assert engines.route_asr('fake')['model']=='small' and calls==['base','small']

def test_base_preserves_tunisian_specialist(monkeypatch):
    monkeypatch.setenv('DALILA_GENERAL_ASR','base')
    calls=[]
    def transcribe(path,key,language):
        calls.append(key)
        return {'text':'نحب نعرف شنوة يلزمني','asr_language':'ar','avg_logprob':-.1,'model':key}
    monkeypatch.setattr(engines,'transcribe',transcribe)
    monkeypatch.setattr('dalila.semantic.detect',lambda text:{'label':'aeb','best_guess':'aeb'})
    assert engines.route_asr('fake')['model']=='tn-small' and calls==['base','tn-small']
