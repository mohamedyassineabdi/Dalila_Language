import unittest, os, json
from unittest.mock import patch, Mock
from pathlib import Path
import app
from derja_lab import engines as e

class PrototypeTests(unittest.TestCase):
    def test_ui_build(self):
        self.assertGreater(len(app.build().config['components']),30)
    def test_prompt_context(self):
        hist=[{'role':'user','content':'3aslema'},{'role':'assistant','content':'عسلامة'}]
        msg=e.messages(hist,'شنوة حوالك؟','Tunisian (Derja)','Arabic script')
        self.assertIn('Derja',msg[0]['content']); self.assertEqual(msg[-1]['content'],'شنوة حوالك؟'); self.assertEqual(len(msg),4)
    @patch('derja_lab.engines.requests.post')
    def test_ollama(self,post):
        # Updated fixture: recovered Labess native path calls /api/generate, not /api/chat.
        post.return_value=Mock(status_code=200,json=lambda:{'response':'عسلامة'})
        self.assertEqual(e.chat('Labess 7B (local)',[],'hello','Tunisian (Derja)','Arabic script',.5,256),'عسلامة')
        self.assertEqual(post.call_args.kwargs['json']['model'],e.LABESS)
    @patch('derja_lab.engines.requests.post')
    def test_cloud(self,post):
        post.return_value=Mock(status_code=200,json=lambda:{'choices':[{'message':{'content':'عسلامة'}}]})
        with patch.dict(os.environ,{'GROQ_API_KEY':'test-key'}):
            self.assertEqual(e.chat('Groq (cloud)',[],'hello','Tunisian (Derja)','Arabic script',.5,256,'qwen/qwen3.8-27b'),'عسلامة')
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'],'Bearer test-key')
    @patch('derja_lab.engines.requests.post')
    def test_rate_limit(self,post):
        post.return_value=Mock(status_code=429)
        with self.assertRaisesRegex(RuntimeError,'Rate limit'):
            e._post('http://localhost',{})
    @patch('derja_lab.engines.chat',return_value='عسلامة')
    @patch('derja_lab.engines.synthesize',side_effect=RuntimeError('voice offline'))
    def test_chat_survives_voice_error(self,tts,chat):
        hist,logs,audio,reply,question,status,metrics,asr=app.send('3aslema',[],[],{'original_transcript':'عسلامة'},'Labess 7B (local)','Tunisian (Derja)','Arabic script',.5,256,'','SILMA Derja (local)','ref.wav','text',True)
        self.assertEqual(len(hist),2); self.assertEqual(logs[0]['answer'],'عسلامة'); self.assertIsNone(audio); self.assertIn('voice failed',status); self.assertEqual(metrics['original_transcript'],'عسلامة')
        rated,_=app.rate(logs,5,4,4,0,3,'test')
        self.assertIsNone(rated[0]['ratings']['voice_naturalness'])
        path=Path(app.export(rated))
        try: self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['turns'][0]['ratings']['understanding'],5)
        finally: path.unlink()
    @patch('derja_lab.engines.transcribe',return_value='شنوة حوالك؟')
    def test_transcription_callback(self,engine):
        text,metrics,status=app.transcribe_audio('audio.wav','Whisper Tunisian INT8','Tunisian (Derja)')
        self.assertEqual(text,'شنوة حوالك؟'); self.assertIn('stt_seconds',metrics)
    def test_consent(self):
        with self.assertRaises(ValueError): e.synthesize('test','SILMA Derja (local)','a.wav','test',False)
    def test_reset(self):
        self.assertEqual(app.clear()[0:2],([],[]))

if __name__=='__main__': unittest.main()
