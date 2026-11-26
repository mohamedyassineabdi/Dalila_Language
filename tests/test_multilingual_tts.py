"""Real offline synthesis smoke tests: audio generation, not pronunciation quality."""
import base64, io, wave
import pytest
from fastapi.testclient import TestClient
from app import app
from dalila import engines

SAMPLES={
'aeb':'عسلامة، كيفاش نجم نعاونك؟',
'ar':'مرحباً، كيف يمكنني مساعدتك؟',
'arq':'واش راك؟ نقدر نعاونك.',
'ayl':'أهلا، شن نقدر نعاونك؟',
'fr':'Bonjour, comment puis-je vous aider ?',
'en':'Hello, how can I help you?',
'de':'Hallo, wie kann ich Ihnen helfen?',
'tr':'Merhaba, size nasıl yardımcı olabilirim?'
}

@pytest.mark.parametrize('lang',SAMPLES)
def test_real_packaged_voice(lang,tmp_path):
    assert engines.packaged_voice_available()
    path=tmp_path/'speech.wav'
    engines._packaged_speech(SAMPLES[lang],engines.VOICE_MAP[lang],path)
    assert engines._valid_wave(path)

def test_speak_api():
    r=TestClient(app).post('/speak',json={'text':SAMPLES['aeb'],'language':'aeb'})
    assert r.status_code==200, r.text
    data=r.json()
    assert data['voice']=='ar' and data['dialect_authentic'] is False
    with wave.open(io.BytesIO(base64.b64decode(data['audio_base64'])),'rb') as wav:
        assert wav.getnframes()>0

def test_no_silent_arabizi(monkeypatch):
    from dalila.chat import chat_turn
    monkeypatch.setattr('dalila.chat.conversational_reply',lambda *a:({'language':'aeb','category':'social','reply':'ey labes','speech_text':''},'qwen3:4b'))
    r=chat_turn('t7eb ta7ki m3aya','aeb',backend='ollama')
    assert r['speech_text'] and r['fallback_reason']

def test_normal_speech_matches_reply(monkeypatch):
    from dalila.chat import chat_turn
    monkeypatch.setattr('dalila.chat.conversational_reply',lambda *a:({'language':'fr','category':'social','reply':'Bien sûr !','speech_text':'Hello'},'qwen3:4b'))
    r=chat_turn('Tu me comprends ?', 'fr', backend='ollama')
    assert r['assistant_text']==r['speech_text']=='Bien sûr !'
