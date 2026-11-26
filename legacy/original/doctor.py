from pathlib import Path
import os, importlib.util, sys
import requests
from dotenv import load_dotenv
from derja_lab.engines import ROOT
load_dotenv(ROOT/'.env')
print('Python:',sys.version)
for package in ('gradio','faster_whisper','huggingface_hub','torch','transformers','peft'):
    print(package, 'OK' if importlib.util.find_spec(package) else 'not installed (advanced packages optional)')
try:
    response=requests.get(os.getenv('OLLAMA_URL','http://127.0.0.1:11434')+'/api/tags',timeout=5); response.raise_for_status()
    print('Ollama available:',[m['name'] for m in response.json()['models']])
except requests.RequestException: print('Ollama unavailable; launch Ollama or choose Groq.')
print('Groq key configured:',bool(os.getenv('GROQ_API_KEY')))
print('HF token configured:',bool(os.getenv('HF_TOKEN')))
print('Voice environment:',Path(os.getenv('VOICE_PYTHON') or ROOT/'.venv-voice'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')).is_file())
