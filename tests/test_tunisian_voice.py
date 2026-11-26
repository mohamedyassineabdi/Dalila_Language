import wave
from dalila import engines, tunisian_voice, neural_voice

def test_opt_in(monkeypatch):
    monkeypatch.delenv('DALILA_TUNISIAN_RESEARCH',raising=False)
    assert tunisian_voice.readiness()=='not_enabled'
    assert tunisian_voice.prepare() is False

def test_preserve_words_and_numbers():
    assert tunisian_voice.speech_text('نحب  750 m² في صفاقس، dossier')=='نحب 750 m² في صفاقس، dossier'

def write_wave(out):
    with wave.open(str(out),'wb') as w:
        w.setparams((1,2,16000,0,'NONE','not compressed'))
        w.writeframes(b'\x01\x00'*100)

def test_tunisian_route(monkeypatch,tmp_path):
    def fake(text,out):
        assert text=='عسلامة'
        write_wave(out)
        return {'engine':'omnivoice','voice':'aeb-synthetic','dialect_quality_validated':False}
    monkeypatch.setattr(tunisian_voice,'speak_tunisian',fake)
    assert engines.speak('عسلامة','aeb',tmp_path/'a.wav')['engine']=='omnivoice'

def test_other_languages_unchanged(monkeypatch,tmp_path):
    def forbid(*args):raise AssertionError('Wrong dialect')
    def fake(text,voice,out):
        assert voice=='fr'
        write_wave(out)
        return {'engine':'piper','voice':'fr'}
    monkeypatch.setattr(tunisian_voice,'speak_tunisian',forbid)
    monkeypatch.setattr(neural_voice,'speak_neural',fake)
    assert engines.speak('Bonjour','fr',tmp_path/'a.wav')['engine']=='piper'

def test_fallback_if_tunisian_unavailable(monkeypatch,tmp_path):
    def fail(*args):raise RuntimeError('not ready')
    def fake(text,voice,out):
        assert voice=='ar'
        write_wave(out)
        return {'engine':'piper','voice':'ar'}
    monkeypatch.setattr(tunisian_voice,'speak_tunisian',fail)
    monkeypatch.setattr(neural_voice,'speak_neural',fake)
    assert engines.speak('عسلامة','aeb',tmp_path/'a.wav')['engine']=='piper'


def test_repeated_voice_cached(monkeypatch,tmp_path):
    monkeypatch.setenv('DALILA_TUNISIAN_RESEARCH','1')
    monkeypatch.setattr(tunisian_voice,'CACHE',__import__('collections').OrderedDict())
    monkeypatch.setattr(tunisian_voice,'STEPS',4)
    key=tunisian_voice._cache_key('عسلامة')
    original=tmp_path/'original.wav'
    write_wave(original)
    tunisian_voice._remember(key,original,{'engine':'omnivoice','voice':'aeb-synthetic'})
    monkeypatch.setattr(tunisian_voice,'STATE','timed_out')
    out=tmp_path/'cached.wav'
    assert tunisian_voice.speak_tunisian('عسلامة',out)['cache_hit']
    assert out.read_bytes()==original.read_bytes()

def test_timeout_config(monkeypatch):
    monkeypatch.setenv('DALILA_TUNISIAN_TIMEOUT','45')
    assert tunisian_voice.timeout_seconds()==45
    monkeypatch.setenv('DALILA_TUNISIAN_TIMEOUT','9999')
    assert tunisian_voice.timeout_seconds()==120

def test_generation_steps(monkeypatch):
    from dalila.tunisian_worker import generation_steps
    monkeypatch.delenv('DALILA_TUNISIAN_STEPS',raising=False)
    assert generation_steps()==4
    monkeypatch.setenv('DALILA_TUNISIAN_STEPS','16')
    assert generation_steps()==16
