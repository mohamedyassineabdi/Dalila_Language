"""Exercise the real Piper checkpoints using fixed public test sentences."""
import tempfile
from pathlib import Path
from dalila import neural_voice, engines
SAMPLES={'ar':'مرحباً، كيف يمكنني مساعدتك؟','en':'Hello, how can I help you?','fr':'Bonjour, comment puis-je vous aider ?','de':'Hallo, wie kann ich Ihnen helfen?','tr':'Merhaba, size nasıl yardımcı olabilirim?'}
if __name__=='__main__':
    with tempfile.TemporaryDirectory() as temp:
        for lang,text in SAMPLES.items():
            assert neural_voice.prepare(lang), f'Could not prepare {lang}'
            out=Path(temp)/f'{lang}.wav'
            result=neural_voice.speak_neural(text,lang,out)
            assert engines._valid_wave(out),f'Invalid audio for {lang}'
            print(lang,result,flush=True)
    print('Five neural voice smoke tests passed (no pronunciation rating).',flush=True)
