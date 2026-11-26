from dalila.chat import chat_turn
from dalila.llm import installed_ollama_model
from fastapi.testclient import TestClient
from app import app

def test_arabizi_greeting():
    result = chat_turn('ahla bik')
    assert result['language'] == 'aeb'
    assert result['response_style'] == 'arabizi'
    assert result['assistant_text'].startswith('Ahla bik')
    assert result['semantic_backend'] == 'greeting'

def test_installed_model(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'models':[{'name':'qwen3:8b'}]}
    monkeypatch.setenv('OLLAMA_MODEL','qwen3:4b')
    monkeypatch.setattr('dalila.llm.requests.get',lambda *a,**k:Response())
    assert installed_ollama_model() == 'qwen3:8b'

def test_no_model(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'models':[]}
    monkeypatch.setattr('dalila.llm.requests.get',lambda *a,**k:Response())
    assert installed_ollama_model() is None

def test_local_chat_generation(monkeypatch):
    monkeypatch.setattr('dalila.chat.conversational_reply',lambda *a:('إي نحكي بالتونسي','qwen3:4b'))
    r=chat_turn('تفهم فيا؟','aeb',backend='ollama')
    assert r['semantic_backend']=='ollama'
    assert r['assistant_text']=='إي نحكي بالتونسي'

def test_domain_guard(monkeypatch):
    monkeypatch.setattr('dalila.chat.conversational_reply',lambda *a: (_ for _ in ()).throw(AssertionError('domain generation')))
    monkeypatch.setattr('dalila.llm.semantic_json',lambda *a:{'language':'fr','intent':'price','needs_clarification':False})
    r=chat_turn('Quel est le prix ?', 'fr', backend='ollama')
    assert 'ne peux pas donner de réponse confirmée' in r['assistant_text']

def test_chat_endpoint():
    r=TestClient(app).post('/chat',json={'text':'ahla bik','backend':'baseline'})
    assert r.status_code==200 and r.json()['language']=='aeb'
