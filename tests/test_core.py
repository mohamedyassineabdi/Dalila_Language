import pytest
from dalila.core import analyze,normalize,numbers,rows,LANGS,script
from dalila.metrics import scores
from dalila import engines
from fastapi.testclient import TestClient
from app import app
client=TestClient(app)
@pytest.mark.parametrize('language',LANGS)
def test_language_override(language):
    x=analyze('n7eb 750 m² moch 2000',language)
    assert x['language']==language and x['numbers']==['750','2000'] and x['knowledge_status']=='not_connected'
    assert x['response'] and x['original']=='n7eb 750 m² moch 2000'
def test_normalization(): assert normalize('  ma  n7ebch  750 ')=='ma n7ebch 750'
def test_script(): assert script('نحب terrain')=='mixed'
def test_split():
    data=rows(); a=[r for r in data if r['split']=='dev']; b=[r for r in data if r['split']=='eval']; assert len(a)==len(b)==72 and not ({r['text'] for r in a}&{r['text'] for r in b})
def test_metrics(): assert scores('750 pas 2000','750 2000')['wer']==1/3 and not scores('750','2000')['numbers_exact']
def test_invalid(): assert client.post('/analyze',json={'text':'','language':'auto'}).status_code==400
def test_api(): assert client.get('/health').json()['knowledge']=='not_connected' and client.get('/').status_code==200
def test_asr_fallback(monkeypatch):
    def fake(path,key,language):
        if key=='tn-small': raise RuntimeError('test')
        return {'text':'test','model':key}
    monkeypatch.setattr(engines,'transcribe',fake); assert engines.route_asr('fake','aeb')['fallback']
def test_no_silent_claim(): assert analyze('xyz','auto')['knowledge_status']=='not_connected'
def test_audio_route(monkeypatch):
    monkeypatch.setattr('app.route_asr',lambda *a,**k:{'text':'test','model':'mock'})
    assert client.post('/transcribe',files={'file':('test.wav',b'not-a-wave')},data={'language':'aeb'}).json()['model']=='mock'
