import wave
from dalila import engines, neural_voice

def test_neural_preferred(monkeypatch,tmp_path):
    def fake(text,voice,output):
        assert voice=='ar'
        with wave.open(str(output),'wb') as w:
            w.setparams((1,2,16000,0,'NONE','not compressed'))
            w.writeframes(b'\x01\x00'*100)
        return {'engine':'piper','voice':'ar_JO-kareem-medium','dialect_authentic':False}
    monkeypatch.setattr(neural_voice,'speak_neural',fake)
    r=engines.speak('عسلامة','aeb',tmp_path/'a.wav')
    assert r['engine']=='piper' and r['dialect_authentic'] is False

def test_neural_failure_fallback(monkeypatch,tmp_path):
    def fail(*args):raise RuntimeError('unavailable')
    monkeypatch.setattr(neural_voice,'speak_neural',fail)
    r=engines.speak('Hello','en',tmp_path/'a.wav')
    assert r['engine']!='piper' and engines._valid_wave(tmp_path/'a.wav')

def test_no_network_on_inference(monkeypatch,tmp_path):
    monkeypatch.setattr(neural_voice,'available',lambda:True)
    monkeypatch.setattr(neural_voice,'PATHS',{})
    def files(voice,download=False):
        assert download is False
        raise RuntimeError('not cached')
    monkeypatch.setattr(neural_voice,'files_for',files)
    import pytest
    with pytest.raises(RuntimeError):
        neural_voice.speak_neural('hello','en',tmp_path/'a.wav')
