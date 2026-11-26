import json, wave, os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app import app
from dalila.semantic import understand,extract,detect
from dalila.llm import validate,semantic_json
from dalila.voice import synthesize_reference
from evaluate import audio_eval
client=TestClient(app)
@pytest.mark.parametrize('lang',['aeb','ar','fr','en','arq','ayl','de','tr'])
def test_override(lang):
    x=understand('n7eb 750 m² moch 2000 fi Sfax',lang)
    assert x['language']==lang and x['original']=='n7eb 750 m² moch 2000 fi Sfax' and x['numbers']==['750','2000'] and x['knowledge_status']=='not_connected'
    for e in x['mentions']: assert x['original'][e['start']:e['end']]==e['value']
def test_arabizi():
    x=understand('n7eb 750 m² moch 2000 fi Sfax','aeb');assert x['response_style']=='arabizi' and x['response'].startswith('Ta9sed')
def test_mixed(): assert detect('نحب terrain industriel').get('code_switch_candidate')
def test_numbers_negation():
    x=extract('ما نحبش 750 m² موش 2000 في صفاقس');assert [e['value'] for e in x if e['type']=='negation_marker']==['ما نحبش','موش'];assert [e['value'] for e in x if e['type']=='numeric_mention']==['750 m²','2000']
def test_unknown(): assert understand('xqvzz')['needs_language_confirmation']
def test_language_switch():
    r=understand('I need the supporting documents','en',['نحب نعمل مشروع']);assert r['language']=='en' and r['context_turns']==1 and r['response'].startswith('Are you asking')
def test_cloud_block(monkeypatch):
    monkeypatch.delenv('DALILA_ALLOW_CLOUD',raising=False)
    monkeypatch.setattr('requests.post',lambda *a,**k:pytest.fail('Network should not be used'))
    x=understand('نحب الأوراق','aeb',backend='gemini');assert x['semantic_backend']=='baseline' and 'PermissionError' in x['fallback_reason']
def test_llm_schema():
    assert validate({'language':'aeb','intent':'price','needs_clarification':True})['language']=='aeb'
    with pytest.raises(ValueError):validate({'language':'aeb','intent':'price','needs_clarification':True,'answer':'fake price'})
    with pytest.raises(ValueError):validate({'language':'aeb','intent':'price','needs_clarification':'false'})
def test_llm_proposal(monkeypatch):
    monkeypatch.setattr('dalila.llm.semantic_json',lambda *args:{'language':'aeb','intent':'price','needs_clarification':False});x=understand('some text','fr',backend='ollama');assert x['language']=='fr' and x['semantic_backend']=='ollama' and x['intent']['label']=='price' and x['knowledge_status']=='not_connected'
def test_llm_bad_fallback(monkeypatch):
    def fail(*args):raise RuntimeError('private token should not appear')
    monkeypatch.setattr('dalila.llm.semantic_json',fail);x=understand('text','en',backend='ollama');assert x['semantic_backend']=='baseline' and 'private token' not in x['fallback_reason']
def test_tts_consent(tmp_path,monkeypatch):
    with pytest.raises(PermissionError):synthesize_reference('hello','silma',tmp_path/'a.wav','hi',False,tmp_path/'b.wav')
    monkeypatch.delenv('DALILA_ENABLE_RESEARCH_TTS',raising=False)
    with pytest.raises(PermissionError):synthesize_reference('hello','silma',tmp_path/'a.wav','hi',True,tmp_path/'b.wav')
def test_api():
    x=client.post('/understand',json={'text':'n7eb 750 m² fi Sfax','language':'aeb'}); assert x.status_code==200 and x.json()['numbers']==['750']
    assert client.post('/understand',json={'text':'x','history':['a']*7}).status_code==422
    assert client.post('/speak-reference',files={'file':('ref.wav',b'x')},data={'text':'hi'}).status_code==400

def test_asr_eval_rejects_unreviewed(tmp_path):
    p=tmp_path/'a.wav';p.write_bytes(b'x');m=tmp_path/'manifest.jsonl';m.write_text(json.dumps(dict(id='1',audio='a.wav',reference='test',language='aeb',split='eval')))
    with pytest.raises(ValueError):audio_eval(m,['small'])
def test_asr_eval_counts_failed(monkeypatch,tmp_path):
    for name in ['a.wav','b.wav']:(tmp_path/name).write_bytes(b'x')
    m=tmp_path/'manifest.jsonl';m.write_text('\n'.join(json.dumps(dict(id=str(i),audio=n,reference='test text',language='aeb',split='eval',consent=True,review_status='human_verified')) for i,n in enumerate(['a.wav','b.wav'])))
    def transcribe(path,*args):
        if path.name=='b.wav':raise RuntimeError('mock')
        return {'text':'test text','rtf':.1}
    monkeypatch.setattr('dalila.engines.transcribe',transcribe);r=audio_eval(m,['small'])['small'];assert r['coverage']==.5 and r['wer_all_failure_as_empty']==.5

def test_controlled_reply_topic():
    x=understand('What is the price?','en');assert 'the price' in x['response'] and 'cannot provide a confirmed answer' in x['response']
def test_short_followup():
    x=understand('and Sfax?','en',['What is the price?']);assert x['intent']['label']=='price' and x['intent']['reason']=='previous_intent_candidate' and x['intent']['needs_confirmation']
